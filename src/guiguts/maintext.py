"""Handle main text widget"""


import logging
import subprocess
from textwrap import TextWrapper
import tkinter as tk
from tkinter import ttk
from tkinter import font as tk_font
from typing import Any, Callable, Optional, Literal, Generator

import regex as re

from guiguts.preferences import preferences, PrefKey
from guiguts.utilities import (
    is_mac,
    IndexRowCol,
    IndexRange,
    force_tcl_wholeword,
    convert_to_tcl_regex,
)
from guiguts.widgets import theme_set_tk_widget_colors, themed_style

logger = logging.getLogger(__package__)

TK_ANCHOR_MARK = "tk::anchor1"
WRAP_NEXT_LINE_MARK = "WrapParagraphStart"
INDEX_END_MARK = "IndexEnd"
INDEX_NEXT_LINE_MARK = "IndexLineStart"
WRAP_END_MARK = "WrapSectionEnd"
PAGE_FLAG_TAG = "PageFlag"
PAGEMARK_PIN = "\x7f"  # Temp char to pin page mark locations
BOOKMARK_TAG = "Bookmark"


class FindMatch:
    """Index and length of match found by search method.

    Attributes:
        index: Index of start of match.
        count: Length of match.
    """

    def __init__(self, index: IndexRowCol, count: int):
        self.rowcol = index
        self.count = count


class WrapParams:
    """Stores parameters used when wrapping."""

    def __init__(self, left: int, first: int, right: int):
        """Initialize WrapParams object.

        Args:
            left: Left margin position.
            first: Left margin for first line.
            right: Right margin position.
        """
        self.left = left
        self.first = first
        self.right = right


class TextLineNumbers(tk.Canvas):
    """TextLineNumbers widget adapted from answer at
    https://stackoverflow.com/questions/16369470/tkinter-adding-line-number-to-text-widget

    Attributes:
        textwidget: Text widget to provide line numbers for.
        font: Font used by text widget, also used for line numbers.
        offset: Gap between line numbers and text widget.
    """

    def __init__(
        self,
        parent: tk.Widget,
        text_widget: tk.Text,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.textwidget = text_widget
        self.font = tk_font.nametofont(self.textwidget.cget("font"))
        self.offset = 10
        # Allow for 5 digit line numbers
        width = self.font.measure("88888") + self.offset
        tk.Canvas.__init__(
            self, parent, *args, width=width, highlightthickness=0, **kwargs
        )
        # Canvas needs to listen for theme change
        self.bind("<<ThemeChanged>>", lambda event: self.theme_change())
        self.text_color = "black"

    def redraw(self) -> None:
        """Redraw line numbers."""
        self.delete("all")
        text_pos = self.winfo_width() - self.offset
        index = self.textwidget.index("@0,0")
        while True:
            dline = self.textwidget.dlineinfo(index)
            if dline is None:
                break
            linenum = IndexRowCol(index).row
            self.create_text(
                text_pos,
                dline[1],
                anchor="ne",
                font=self.font,
                text=linenum,
                fill=self.text_color,
            )
            index = self.textwidget.index(index + "+1l")

    def theme_change(self) -> None:
        """Handle change of color theme"""
        self.configure(background=themed_style().lookup("TButton", "background"))
        self.text_color = themed_style().lookup("TButton", "foreground")


class MainText(tk.Text):
    """MainText is the main text window, and inherits from ``tk.Text``."""

    def __init__(self, parent: tk.Widget, root: tk.Tk, **kwargs: Any) -> None:
        """Create a Frame, and put a TextLineNumbers widget, a Text and two
        Scrollbars in the Frame.

        Layout and linking of the TextLineNumbers widget and Scrollbars to
        the Text widget are done here.

        Args:
            parent: Parent widget to contain MainText.
            root: Tk root.
            **kwargs: Optional additional keywords args for ``tk.Text``.
        """

        self.root = root

        # Create surrounding Frame
        self.frame = ttk.Frame(parent)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Create Text itself & place in Frame
        super().__init__(self.frame, **kwargs)
        tk.Text.grid(self, column=1, row=0, sticky="NSEW")

        self.languages = ""

        # Create Line Numbers widget and bind update routine to all
        # events that might change which line numbers should be displayed
        self.linenumbers = TextLineNumbers(self.frame, self)
        self.linenumbers.grid(column=0, row=0, sticky="NSEW")
        self.bind_event("<Configure>", self._on_change, add=True, force_break=False)
        # Use KeyRelease not KeyPress since KeyPress might be caught earlier and not propagated to this point.
        self.bind_event("<KeyRelease>", self._on_change, add=True, force_break=False)
        self.numbers_need_updating = True

        def hscroll_set(*args: Any) -> None:
            self.hscroll.set(*args)
            self._on_change()

        def vscroll_set(*args: Any) -> None:
            self.vscroll.set(*args)
            self._on_change()

        # Create scrollbars, place in Frame, and link to Text
        self.hscroll = ttk.Scrollbar(
            self.frame, orient=tk.HORIZONTAL, command=self.xview
        )
        self.hscroll.grid(column=1, row=1, sticky="EW")
        self["xscrollcommand"] = hscroll_set
        self.vscroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.yview)
        self.vscroll.grid(column=2, row=0, sticky="NS")
        self["yscrollcommand"] = vscroll_set

        # Set up response to text being modified
        # pylint: disable-next=invalid-name
        self.modifiedCallbacks: list[Callable[[], None]] = []
        self.bind_event(
            "<<Modified>>", lambda _event: self.modify_flag_changed_callback()
        )

        self.bind_event("<<Cut>>", lambda _event: self.smart_cut(), force_break=False)
        self.bind_event("<<Copy>>", lambda _event: self.smart_copy(), force_break=False)
        self.bind_event(
            "<<Paste>>", lambda _event: self.smart_paste(), force_break=False
        )
        self.bind_event(
            "<BackSpace>", lambda _event: self.smart_delete(), force_break=False
        )
        self.bind_event(
            "<Delete>", lambda _event: self.smart_delete(), force_break=False
        )

        # Column selection uses Alt key on Windows/Linux, Option key on macOS
        # Key Release is reported as Alt_L on all platforms
        modifier = "Option" if is_mac() else "Alt"
        self.bind_event(f"<{modifier}-ButtonPress-1>", self.column_select_click)
        self.bind_event(f"<{modifier}-B1-Motion>", self.column_select_motion)
        self.bind_event(f"<{modifier}-ButtonRelease-1>", self.column_select_release)
        self.bind_event("<KeyRelease-Alt_L>", lambda _event: self.column_select_stop())
        # Make use of built-in Shift click functionality to extend selections,
        # but adapt for column select with Option/Alt key
        self.bind_event(f"<Shift-{modifier}-ButtonPress-1>", self.column_select_release)
        self.bind_event(f"<Shift-{modifier}-ButtonRelease-1>", lambda _event: "break")
        self.column_selecting = False

        # Add common Mac key bindings for beginning/end of file
        if is_mac():
            self.bind_event("<Command-Up>", lambda _event: self.move_to_start())
            self.bind_event("<Command-Down>", lambda _event: self.move_to_end())
            self.bind_event("<Command-Shift-Up>", lambda _event: self.select_to_start())
            self.bind_event(
                "<Command-Shift-Down>", lambda e_event: self.select_to_end()
            )

        # Since Text widgets don't normally listen to theme changes,
        # need to do it explicitly here.
        self.bind_event(
            "<<ThemeChanged>>", lambda _event: theme_set_tk_widget_colors(self)
        )

        # Configure tags
        self.tag_configure(PAGE_FLAG_TAG, background="gold", foreground="black")
        self.tag_configure(BOOKMARK_TAG, background="lime", foreground="black")

        # Ensure text still shows selected when focus is in another dialog
        if "inactiveselect" not in kwargs:
            self["inactiveselect"] = self["selectbackground"]

        self.current_sel_ranges: list[IndexRange] = []
        self.prev_sel_ranges: list[IndexRange] = []

        maintext(self)  # Register this single instance of MainText

    def bind_event(
        self,
        event_string: str,
        func: Callable[[tk.Event], Optional[str]],
        add: bool = False,
        force_break: bool = True,
        bind_all: bool = False,
    ) -> None:
        """Bind event string to given function. Provides ability to force
        a "break" return in order to stop class binding being executed.

        Args:
            event_string: String describing key/mouse/etc event.
            func: Function to bind to event - may handle return "break" itself.
            add: True to add this binding without removing existing binding.
            force_break: True to always return "break", regardless of return from `func`.
            bind_all: True to bind keystroke to all other widgets as well as maintext
        """

        def break_func(event: tk.Event) -> Any:
            """Call bound function. Force "break" return if needed."""
            func_ret = func(event)
            return "break" if force_break else func_ret

        super().bind(event_string, break_func, add)
        if bind_all:
            self.bind_all(event_string, break_func, add)

    # The following methods are simply calling the Text widget method
    # then updating the linenumbers widget
    def insert(self, index: Any, chars: str, *args: Any) -> None:
        """Override method to ensure line numbers are updated."""
        super().insert(index, chars, *args)
        self._on_change()

    def delete(self, index1: Any, index2: Any = None) -> None:
        """Override method to ensure line numbers are updated."""
        super().delete(index1, index2)
        self._on_change()

    def replace(self, index1: Any, index2: Any, chars: str, *args: Any) -> None:
        """Override method to ensure line numbers are updated."""
        super().replace(index1, index2, chars, *args)
        self._on_change()

    def _do_linenumbers_redraw(self) -> None:
        """Only redraw line numbers once when process becomes idle.

        Several calls to this may be queued by _on_change, but only
        the first will actually do a redraw, because the flag will
        only be true on the first call."""
        if self.numbers_need_updating:
            self.linenumbers.redraw()
        self.numbers_need_updating = False

    def _on_change(self, *_args: Any) -> None:
        """Callback when visible region of file may have changed.

        By setting flag now, and queuing calls to _do_linenumbers_redraw,
        we ensure the flag will be true for the first call to
        _do_linenumbers_redraw."""
        self.numbers_need_updating = True
        self.root.after_idle(self._do_linenumbers_redraw)

    def grid(self, *args: Any, **kwargs: Any) -> None:
        """Override ``grid``, so placing MainText widget actually places surrounding Frame"""
        return self.frame.grid(*args, **kwargs)

    def toggle_line_numbers(self) -> None:
        """Toggle whether line numbers are shown."""
        preferences.set(PrefKey.LINE_NUMBERS, not preferences.get(PrefKey.LINE_NUMBERS))

    def show_line_numbers(self, show: bool) -> None:
        """Show or hide line numbers.

        Args:
            show: True to show, False to hide.
        """
        if show:
            self.linenumbers.grid()
        else:
            self.linenumbers.grid_remove()

    def key_bind(
        self, keyevent: str, handler: Callable[[Any], None], bind_all: bool
    ) -> None:
        """Bind lower & uppercase versions of ``keyevent`` to ``handler``
        in main text window, and all other widgets.

        If this is not done, then use of Caps Lock key causes confusing
        behavior, because pressing ``Ctrl`` and ``s`` sends ``Ctrl+S``.

        Args:
            keyevent: Key event to trigger call to ``handler``.
            handler: Callback function to be bound to ``keyevent``.
            bind_all: True to bind keystroke to all other widgets as well as maintext
        """
        lk = re.sub("(?<=[^A-Za-z])[A-Z]>$", lambda m: m.group(0).lower(), keyevent)
        uk = re.sub("(?<=[^A-Za-z])[a-z]>$", lambda m: m.group(0).upper(), keyevent)

        self.bind_event(lk, handler, bind_all=bind_all)
        self.bind_event(uk, handler, bind_all=bind_all)

    #
    # Handle "modified" flag
    #
    def add_modified_callback(self, func: Callable[[], None]) -> None:
        """Add callback function to a list of functions to be called when
        widget's modified flag changes.

        Args:
            func: Callback function to be added to list.
        """
        self.modifiedCallbacks.append(func)

    def modify_flag_changed_callback(self) -> None:
        """This method is bound to <<Modified>> event which happens whenever
        the widget's modified flag is changed - not just when changed to True.

        Causes all functions registered via ``add_modified_callback`` to be called.
        """
        for func in self.modifiedCallbacks:
            func()

    def set_modified(self, mod: bool) -> None:
        """Manually set widget's modified flag (may trigger call to
        ```modify_flag_changed_callback```).

        Args:
            mod: Boolean setting for widget's modified flag."""
        self.edit_modified(mod)

    def is_modified(self) -> bool:
        """Return whether widget's text has been modified."""
        return self.edit_modified()

    def do_save(self, fname: str) -> None:
        """Save widget's text to file.

        Args:
            fname: Name of file to save text to.
        """
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(self.get_text())
            self.set_modified(False)

    def do_open(self, fname: str) -> None:
        """Load text from file into widget.

        Args:
            fname: Name of file to load text from.
        """
        self.delete("1.0", tk.END)
        try:
            with open(fname, "r", encoding="utf-8") as fh:
                self.insert(tk.END, fh.read())
        except UnicodeDecodeError:
            with open(fname, "r", encoding="iso-8859-1") as fh:
                self.insert(tk.END, fh.read())
        self.set_modified(False)
        self.edit_reset()

    def do_close(self) -> None:
        """Close current file and clear widget."""
        self.delete("1.0", tk.END)
        self.set_modified(False)
        self.edit_reset()

    def undo_block_begin(self) -> None:
        """Begin a block of changes that will be undone with one undo operation.

        Block is automatically closed when system becomes idle.

        Note: this version does not support nesting of blocks.
        """
        self.config(autoseparators=False)
        self.edit_separator()
        self.after_idle(self.undo_block_end)

    def undo_block_end(self) -> None:
        """End a block of changes that will be undone with one undo operation.

        Normally called automatically when system becomes idle, but can safely be
        called manually if required, e.g. to start & end two blocks within one
        user operation.

        Note: this version does not support nesting of blocks.
        """
        self.edit_separator()
        self.config(autoseparators=True)

    def get_insert_index(self) -> IndexRowCol:
        """Return index of the insert cursor as IndexRowCol object.

        Returns:
            IndexRowCol containing position of the insert cursor.
        """
        return self.rowcol(tk.INSERT)

    def set_insert_index(self, insert_pos: IndexRowCol, focus: bool = True) -> None:
        """Set the position of the insert cursor.

        Args:
            insert_pos: Location to position insert cursor.
            focus: Optional, False means focus will not be forced to maintext
        """
        self.mark_set(tk.INSERT, insert_pos.index())
        # The `see` method can leave the desired line at the top or bottom of window.
        # So, we "see" lines above and below desired line incrementally up to
        # half window height each way, ensuring desired line is left in the middle.
        # If performance turns out to be an issue, consider giving `step` to `range`.
        # Step should be smaller than half minimum likely window height.
        start_index = self.index(f"@0,{int(self.cget('borderwidth'))} linestart")
        end_index = self.index(f"@0,{self.winfo_height()} linestart")
        n_lines = IndexRowCol(end_index).row - IndexRowCol(start_index).row
        for inc in range(1, int(n_lines / 2) + 1):
            self.see(f"{tk.INSERT}-{inc}l")
            self.see(f"{tk.INSERT}+{inc}l")
        self.see(tk.INSERT)
        if focus:
            self.focus_set()

    def set_mark_position(
        self,
        mark: str,
        position: IndexRowCol,
        gravity: Literal["left", "right"] = tk.LEFT,
    ) -> None:
        """Set the position of a mark and its gravity.

        Args:
            mark: Name of mark.
            position: Location to position mark.
            gravity: tk.LEFT(default) to stick to left character; tk.RIGHT to stick to right
        """
        self.mark_set(mark, position.index())
        self.mark_gravity(mark, gravity)

    def get_text(self) -> str:
        """Return all the text from the text widget.

        Strips final additional newline that widget adds at tk.END.

        Returns:
            String containing text widget contents.
        """
        return self.get(1.0, f"{tk.END}-1c")

    def get_lines(self) -> Generator[tuple[str, int], None, None]:
        """Yield each line & line number in main text window."""
        for line_num in range(1, self.end().row):
            line = maintext().get(f"{line_num}.0", f"{line_num}.0 lineend")
            yield line, line_num

    def toggle_selection_type(self) -> None:
        """Switch regular selection to column selection or vice versa."""
        sel_ranges = self.selected_ranges()
        if len(sel_ranges) > 1:
            self.do_select(IndexRange(sel_ranges[0].start, sel_ranges[-1].end))
        else:
            self.columnize_selection()

    def columnize_copy(self) -> None:
        """Columnize the current selection and copy it."""
        self.columnize_selection()
        self.column_copy_cut()

    def columnize_cut(self) -> None:
        """Columnize the current selection and copy it."""
        self.columnize_selection()
        self.column_copy_cut(cut=True)

    def columnize_paste(self) -> None:
        """Columnize the current selection, if any, and paste the clipboard contents."""
        self.columnize_selection()
        self.column_paste()

    def columnize_selection(self) -> None:
        """Adjust current selection to column mode,
        spanning a block defined by the two given corners."""
        if not (ranges := self.selected_ranges()):
            return
        self.do_column_select(IndexRange(ranges[0].start, ranges[-1].end))

    def do_column_select(self, col_range: IndexRange) -> None:
        """Use multiple selection ranges to select a block
        defined by the start & end of the given range.

        Args:
            IndexRange containing corners of block to be selected."""
        self.clear_selection()
        min_row = min(col_range.start.row, col_range.end.row)
        max_row = max(col_range.start.row, col_range.end.row)
        min_col = min(col_range.start.col, col_range.end.col)
        max_col = max(col_range.start.col, col_range.end.col)
        for line in range(min_row, max_row + 1):
            beg = IndexRowCol(line, min_col).index()
            end = IndexRowCol(line, max_col).index()
            self.tag_add("sel", beg, end)

    def clear_selection(self) -> None:
        """Clear any current text selection."""
        self.tag_remove("sel", "1.0", tk.END)

    def do_select(self, sel_range: IndexRange) -> None:
        """Select the given range of text.

        Args:
            sel_range: IndexRange containing start and end of text to be selected."""
        self.clear_selection()
        self.tag_add("sel", sel_range.start.index(), sel_range.end.index())

    def selected_ranges(self) -> list[IndexRange]:
        """Get the ranges of text marked with the `sel` tag.

        Returns:
            List of IndexRange objects indicating the selected range(s)
            Each range covers one line of selection from the leftmost
            to the rightmost selected columns in the first/last rows.
            If column is greater than line length it equates to end of line.
        """
        ranges = self.tag_ranges("sel")
        assert len(ranges) % 2 == 0
        sel_ranges = []
        if len(ranges) > 0:
            if len(ranges) == 2:
                # Deal with normal (single) selection first
                sel_ranges.append(IndexRange(ranges[0], ranges[1]))
            else:
                # Now column selection (read in conjunction with do_column_select)
                start_rowcol = IndexRowCol(ranges[0])
                end_rowcol = IndexRowCol(ranges[-1])
                minidx = min(ranges, key=lambda x: IndexRowCol(x).col)
                mincol = IndexRowCol(minidx).col
                maxidx = max(ranges, key=lambda x: IndexRowCol(x).col)
                maxcol = IndexRowCol(maxidx).col
                for row in range(start_rowcol.row, end_rowcol.row + 1):
                    start = IndexRowCol(row, mincol)
                    end = IndexRowCol(row, maxcol)
                    sel_ranges.append(IndexRange(start, end))
        return sel_ranges

    def selected_text(self) -> str:
        """Get the first chunk of text marked with the `sel` tag.

        Returns:
            String containing the selected text, or empty string if none selected.
        """
        ranges = self.tag_ranges("sel")
        assert len(ranges) % 2 == 0
        if ranges:
            return self.get(ranges[0], ranges[1])
        return ""

    def save_selection_ranges(self) -> None:
        """Save current selection ranges if they have changed since last call.

        Also save previous selection ranges, if beginning and end have both changed,
        so they can be restored if needed.
        """
        ranges = maintext().selected_ranges()
        # Inequality tests below rely on IndexCol/IndexRange having `__eq__` method
        if ranges != self.current_sel_ranges:
            # Problem is when the user drags to select, you can get multiple calls to this function,
            # which are really all the same selection. Possible better solution in future, but for now,
            # only save into prev if both the start and end are different to the last call.
            # Also save into prev if there were ranges on previous call, but not this one, i.e. the
            # selection has been cancelled.
            if self.current_sel_ranges and (
                (
                    ranges
                    and ranges[0].start != self.current_sel_ranges[0].start
                    and ranges[-1].end != self.current_sel_ranges[-1].end
                )
                or not ranges
            ):
                self.prev_sel_ranges = self.current_sel_ranges.copy()
            self.current_sel_ranges = ranges.copy()

    def restore_selection_ranges(self) -> None:
        """Restore previous selection ranges."""
        if len(self.prev_sel_ranges) == 1:
            self.do_select(self.prev_sel_ranges[0])
        elif len(self.prev_sel_ranges) > 1:
            col_range = IndexRange(
                self.prev_sel_ranges[0].start, self.prev_sel_ranges[-1].end
            )
            self.do_column_select(col_range)

    def column_delete(self) -> None:
        """Delete the selected column text."""
        if not (ranges := self.selected_ranges()):
            return
        for _range in ranges:
            self.delete(_range.start.index(), _range.end.index())

    def column_copy_cut(self, cut: bool = False) -> None:
        """Copy or cut the selected text to the clipboard.

        A newline character is inserted between each line.

        Args:
            cut: True if cut is required, defaults to False (copy)
        """
        if not (ranges := self.selected_ranges()):
            return
        self.clipboard_clear()
        for _range in ranges:
            start = _range.start.index()
            end = _range.end.index()
            string = self.get(start, end)
            if cut:
                self.delete(start, end)
            self.clipboard_append(string + "\n")

    def column_paste(self) -> None:
        """Paste the clipboard text column-wise, overwriting any selected text.

        If more lines in clipboard than selected ranges, remaining lines will be
        inserted in the same column in lines below. If more selected ranges than
        clipboard lines, clipboard will be repeated until all selected ranges are
        replaced.
        """
        # Trap empty clipboard or no STRING representation
        try:
            clipboard = self.clipboard_get()
        except tk.TclError:
            return
        cliplines = clipboard.splitlines()
        if not cliplines:
            return
        num_cliplines = len(cliplines)

        # If nothing selected, set up an empty selection range at the current insert position
        sel_ranges = self.selected_ranges()
        ranges = []
        if sel_ranges:
            start_rowcol = sel_ranges[0].start
            end_rowcol = sel_ranges[-1].end
            for row in range(start_rowcol.row, end_rowcol.row + 1):
                rbeg = IndexRowCol(row, start_rowcol.col)
                rend = IndexRowCol(row, end_rowcol.col)
                ranges.append(IndexRange(rbeg, rend))
        else:
            insert_index = self.get_insert_index()
            ranges.append(IndexRange(insert_index, insert_index))
        num_ranges = len(ranges)

        # Add any necessary newlines if near end of file
        min_row = ranges[0].start.row
        max_row = min_row + max(num_cliplines, num_ranges)
        end_index = self.rowcol(IndexRowCol(max_row, 0).index())
        if max_row > end_index.row:
            self.insert(
                end_index.index() + " lineend", "\n" * (max_row - end_index.row)
            )

        for line in range(max(num_cliplines, num_ranges)):
            # Add any necessary spaces if line being pasted into is too short
            start_rowcol = IndexRowCol(ranges[0].start.row + line, ranges[0].start.col)
            end_rowcol = IndexRowCol(ranges[0].start.row + line, ranges[-1].end.col)
            end_index = self.rowcol(end_rowcol.index())
            nspaces = start_rowcol.col - end_index.col
            if nspaces > 0:
                self.insert(end_index.index(), " " * nspaces)

            clipline = cliplines[line % num_cliplines]
            if line < num_ranges:
                self.replace(start_rowcol.index(), end_rowcol.index(), clipline)
            else:
                self.insert(start_rowcol.index(), clipline)
        rowcol = self.rowcol(f"{start_rowcol.index()} + {len(clipline)}c")
        self.set_insert_index(rowcol)

    def affirm_clipboard_contents(self) -> None:
        """Ensure clipboard is set to its "current" contents.

        The purpose of this is to set the clipboard by non-Tcl/Tk means.
        This should bypass the bug where Tcl/Tk doesn't update the
        system clipboard counter. Some apps, e.g. BBEdit, need this to detect the
        clipboard has changed: https://github.com/python/cpython/issues/104613
        """
        if not is_mac():
            raise NotImplementedError("This function only works on macOS")

        # Use pbcopy macOS command to "touch" the clipboard contents
        with subprocess.Popen(["/usr/bin/pbcopy"], stdin=subprocess.PIPE) as proc:
            proc.communicate(input=self.clipboard_get().encode())

    def smart_copy(self) -> str:
        """Do column copy if multiple ranges selected, else default copy."""
        if is_mac():
            self.after_idle(self.affirm_clipboard_contents)
        if len(self.selected_ranges()) <= 1:
            return ""  # Permit default behavior to happen
        self.column_copy_cut()
        return "break"  # Skip default behavior

    def smart_cut(self) -> str:
        """Do column cut if multiple ranges selected, else default cut."""
        if is_mac():
            self.after_idle(self.affirm_clipboard_contents)
        if len(self.selected_ranges()) <= 1:
            return ""  # Permit default behavior to happen
        self.column_copy_cut(cut=True)
        return "break"  # Skip default behavior

    def smart_paste(self) -> str:
        """Do column paste if multiple ranges selected, else default paste."""
        if len(self.selected_ranges()) <= 1:
            return ""  # Permit default behavior to happen
        self.column_paste()
        return "break"  # Skip default behavior

    def smart_delete(self) -> str:
        """Do column delete if multiple ranges selected, else default backspace."""
        if len(self.selected_ranges()) <= 1:
            return ""  # Permit default behavior to happen
        self.column_delete()
        return "break"  # Skip default behavior

    def column_select_click(self, event: tk.Event) -> None:
        """Callback when column selection is started via mouse click.

        Args
            event: Event containing mouse coordinates.
        """
        self.column_select_start(self.rowcol(f"@{event.x},{event.y}"))

    def column_select_motion(self, event: tk.Event) -> None:
        """Callback when column selection continues via mouse motion.

        Jiggery-pokery needed because if mouse is on a short (or empty) line,
        and mouse position is to right of the last character, its column
        reported with by "@x,y" is the end of the line, not the screen column
        of the mouse location.

        Args:
            event: Event containing mouse coordinates.
        """
        anchor_rowcol = self.rowcol(TK_ANCHOR_MARK)
        cur_rowcol = self.rowcol(f"@{event.x},{event.y}")
        # Find longest visible line between start of selection and current mouse location
        minrow = min(anchor_rowcol.row, cur_rowcol.row)
        # No point starting before first line of screen
        toprow = self.rowcol("@0,0").row
        minrow = max(minrow, toprow)
        maxrow = max(anchor_rowcol.row, cur_rowcol.row)
        maxlen = -1
        y_maxlen = -1
        for row in range(minrow, maxrow + 1):
            geometry = self.bbox(f"{row}.0")
            if geometry is None:
                continue
            line_len = len(self.get(f"{row}.0", f"{row}.0 lineend"))
            if line_len > maxlen:
                maxlen = line_len
                y_maxlen = geometry[1]
        # Find which column mouse would be at if it was over the longest line
        # but in the same horizontal position - this is the "true" mouse column
        # Get y of longest line, and use actual x of mouse
        truecol_rowcol = self.rowcol(f"@{event.x},{y_maxlen}")
        # At last, we can set the column in cur_rowcol to the "screen" column
        # which is what we need to pass to do_column_select().
        cur_rowcol.col = truecol_rowcol.col

        # Attempt to start up column selection if arriving here without a previous click
        # to start, e.g. user presses modifier key after beginning mouse-drag selection.
        if not self.column_selecting:
            ranges = self.selected_ranges()
            if not ranges:  # Fallback to using insert cursor position
                insert_rowcol = self.get_insert_index()
                ranges = [IndexRange(insert_rowcol, insert_rowcol)]
            if self.compare(cur_rowcol.index(), ">", ranges[0].start.index()):
                anchor = ranges[0].start
            else:
                anchor = ranges[-1].end
            self.column_select_start(anchor)

        self.do_column_select(IndexRange(self.rowcol(TK_ANCHOR_MARK), cur_rowcol))

    def column_select_release(self, event: tk.Event) -> None:
        """Callback when column selection is stopped via mouse button release.

        Args:
            event: Event containing mouse coordinates.
        """
        self.column_select_motion(event)
        self.column_select_stop()

    def column_select_start(self, anchor: IndexRowCol) -> None:
        """Begin column selection.

        Args:
            anchor: Selection anchor (start point) - this is also used by Tk
                    if user switches to normal selection style.
        """
        self.mark_set(TK_ANCHOR_MARK, anchor.index())
        self.column_selecting = True
        self.config(cursor="tcross")

    def column_select_stop(self) -> None:
        """Stop column selection."""
        self.column_selecting = False
        self.config(cursor="")

    def rowcol(self, index: str) -> IndexRowCol:
        """Return IndexRowCol corresponding to given index in maintext.

        Args:
            index: Index to position in maintext.

        Returns:
            IndexRowCol representing the position.
        """
        return IndexRowCol(self.index(index))

    def start(self) -> IndexRowCol:
        """Return IndexRowCol for start of text in widget, i.e. "1.0"."""
        return self.rowcol("1.0")

    def end(self) -> IndexRowCol:
        """Return IndexRowCol for end of text in widget, i.e. "end"."""
        return self.rowcol(tk.END)

    def move_to_start(self) -> None:
        """Set insert position to start of text & clear any selection."""
        self.clear_selection()
        self.set_insert_index(self.start())

    def move_to_end(self) -> None:
        """Set insert position to end of text & clear any selection."""
        self.clear_selection()
        self.set_insert_index(self.end())

    def select_to_start(self) -> None:
        """Select from current position to start of text."""
        self.do_select(IndexRange(self.start(), self.get_insert_index()))
        self.set_insert_index(self.start())

    def select_to_end(self) -> None:
        """Select from current position to start of text."""
        self.do_select(IndexRange(self.get_insert_index(), self.end()))
        self.set_insert_index(self.end())

    def find_match(
        self,
        search_string: str,
        start_range: IndexRowCol | IndexRange,
        nocase: bool = False,
        regexp: bool = False,
        wholeword: bool = False,
        backwards: bool = False,
    ) -> Optional[FindMatch]:
        """Find occurrence of string/regex in given range.

        Args:
            search_string: String/regex to be searched for.
            start_range: Range in which to search, or just start point to search whole file.
            nocase: True to ignore case.
            regexp: True if string is a regex; False for exact string match.
            wholeword: True to only search for whole words (i.e. word boundary at start & end).
            backwards: True to search backwards through text.

        Returns:
            FindMatch containing index of start and count of characters in match.
            None if no match.
        """
        if isinstance(start_range, IndexRowCol):
            start_index = start_range.index()
            stop_index = ""
        else:
            assert isinstance(start_range, IndexRange)
            start_index = start_range.start.index()
            stop_index = start_range.end.index()

        if regexp:
            search_string = convert_to_tcl_regex(search_string)
        if wholeword:
            search_string, regexp = force_tcl_wholeword(search_string, regexp)
        count_var = tk.IntVar()
        try:
            match_start = self.search(
                search_string,
                start_index,
                stop_index,
                count=count_var,
                nocase=nocase,
                regexp=regexp,
                backwards=backwards,
            )
        except tk.TclError as exc:
            if str(exc).startswith("couldn't compile regular expression pattern"):
                raise TclRegexCompileError(str(exc)) from exc
            match_start = None

        if match_start:
            return FindMatch(IndexRowCol(match_start), count_var.get())
        return None

    def find_matches(
        self,
        search_string: str,
        text_range: IndexRange,
        nocase: bool,
        regexp: bool,
        wholeword: bool,
    ) -> list[FindMatch]:
        """Find all occurrences of string/regex in given range.

        Args:
            search_string: String/regex to be searched for.
            text_range: Range in which to search.
            nocase: True to ignore case.
            regexp: True if string is a regex; False for exact string match.
            wholeword: True to only search for whole words (i.e. word boundary at start & end).

        Returns:
            List of FindMatch objects, each containing index of start and count of characters in a match.
            Empty list if no matches.
        """
        start_index = text_range.start.index()
        stop_index = text_range.end.index()
        if regexp:
            search_string = convert_to_tcl_regex(search_string)
        if wholeword:
            search_string, regexp = force_tcl_wholeword(search_string, regexp)

        matches = []
        count_var = tk.IntVar()
        start = start_index
        while start:
            try:
                start = self.search(
                    search_string,
                    start,
                    stop_index,
                    count=count_var,
                    nocase=nocase,
                    regexp=regexp,
                )
            except tk.TclError as exc:
                if str(exc).startswith("couldn't compile regular expression pattern"):
                    raise TclRegexCompileError(str(exc)) from exc
                break
            if start:
                matches.append(FindMatch(IndexRowCol(start), count_var.get()))
                start += f"+{count_var.get()}c"
        return matches

    def get_match_text(self, match: FindMatch) -> str:
        """Return text indicated by given match.

        Args:
            match: Start and length of matched text - assumed to be valid.
        """
        start_index = match.rowcol.index()
        end_index = maintext().index(start_index + f"+{match.count}c")
        return maintext().get(start_index, end_index)

    def select_match_text(self, match: FindMatch) -> None:
        """Select text indicated by given match.

        Args:
            match: Start and length of matched text - assumed to be valid.
        """
        start_index = match.rowcol.index()
        end_index = maintext().index(start_index + f"+{match.count}c")
        maintext().do_select(IndexRange(start_index, end_index))

    def transform_selection(self, fn: Callable[[str], str]) -> None:
        """Transform a text selection by applying a function or method.

        Args:
            fn: Reference to a function or method
        """
        if not (ranges := self.selected_ranges()):
            return
        for _range in ranges:
            start = _range.start.index()
            end = _range.end.index()
            string = self.get(start, end)
            self.delete(start, end)
            # apply transform, then insert at start position
            self.insert(start, fn(string))

    def sentence_case_transformer(self, s: str) -> str:
        """Text transformer to convert a string to "Sentence case".

        The transformation is not aware of sentence structure; if the
        input string consists of multiple sentences, the result will
        likely not be what was desired. This behavior was ported as-is
        from Guiguts 1.x, but could potentially be improved, at least
        for languages structured like English.

        To be more specific: if multiple sentences are selected, the
        first character of the first sentence will be capitalized, and
        the subsequent sentences will begin with a lowercase letter.

        When using column selection, *each line* within the column
        has its first letter capitalized and the remainder lowercased.
        Why anyone would want to use sentence case with a column
        selection is left as an exercise for the reader.

        Args:
            s: an input string to be transformed

        Returns:
            A transformed string
        """
        # lowercase string, then look for first word character.
        # DOTALL allows '.' to match newlines
        m = re.match(r"(\W*\w)(.*)", s.lower(), flags=re.DOTALL)
        if m:
            return m.group(1).upper() + m.group(2)
        return s

    def title_case_transformer(self, s: str) -> str:
        """Text transformer to convert a string to "Title Case"

        Args:
            s: an input string to be transformed

        Returns:
            A transformed string
        """
        # A list of words to *not* capitalize.
        exception_words: tuple[str, ...] = ()
        if any(lang.startswith("en") for lang in self.get_language_list()):
            # This list should only be used for English text.
            exception_words = (
                "a",
                "an",
                "and",
                "at",
                "by",
                "from",
                "in",
                "of",
                "on",
                "the",
                "to",
            )

        def capitalize_first_letter(match: re.regex.Match[str]) -> str:
            word = match.group()
            if word in exception_words:
                return word
            return word.capitalize()

        # Look for word characters either at the start of the string, or which
        # immediately follow whitespace or punctuation; then apply capitalization.
        s2 = re.sub(r"(?<=\s|^|\p{P}\s?)(\w+)", capitalize_first_letter, s.lower())

        # Edge case: if the string started with a word found in exception_words, it
        # will have been lowercased erroneously.
        return s2[0].upper() + s2[1:]

    def set_languages(self, languages: str) -> None:
        """Set languages used in text.

        Multiple languages are separated by "+"
        """
        if languages:
            assert re.match(r"[a-z_]+(\+[a-z_]+)*", languages)
            self.languages = languages

    def get_language_list(self) -> list[str]:
        """Get list of languages used in text.

        Returns:
            List of language strings.
        """
        return self.languages.split("+")

    def rewrap_section(
        self, section_range: IndexRange, tidy_function: Callable[[], None]
    ) -> None:
        """Wrap a section of the text.

        Args:
            section_range: Range of text to be wrapped.
            tidy_function: Function to call to tidy up before returning.
        """
        default_left = preferences.get(PrefKey.WRAP_LEFT_MARGIN)
        default_right = preferences.get(PrefKey.WRAP_RIGHT_MARGIN)
        block_indent = preferences.get(PrefKey.WRAP_BLOCK_INDENT)
        poetry_indent = preferences.get(PrefKey.WRAP_POETRY_INDENT)
        bq_indent = preferences.get(PrefKey.WRAP_BLOCKQUOTE_INDENT)
        bq_right = preferences.get(PrefKey.WRAP_BLOCKQUOTE_RIGHT_MARGIN)

        bq_depth = 0
        paragraph = ""
        paragraph_complete = False
        section_start = section_range.start.index()
        # Mark end since line numbers will change during wrapping process
        self.set_mark_position(WRAP_END_MARK, section_range.end, tk.RIGHT)
        line_start = section_start
        paragraph_start = section_start
        self.set_mark_position(
            WRAP_NEXT_LINE_MARK, IndexRowCol(section_start), tk.RIGHT
        )
        # For efficiency with many wrap operations, it is recommended to
        # re-use a single TextWrapper object, rather than creating new ones.
        wrapper = TextWrapper(break_long_words=False, break_on_hyphens=False)
        # Keep list of wrap_params so user can nest block quotes
        # First is depth=0, i.e. not blockquote
        block_params_list: list[WrapParams] = [
            WrapParams(default_left, default_left, default_right)
        ]
        paragraph_complete = False

        # Loop until we reach the end of the whole section we want to rewrap
        while self.compare(WRAP_NEXT_LINE_MARK, "<", WRAP_END_MARK):
            line_start = self.index(WRAP_NEXT_LINE_MARK)
            self.set_mark_position(
                WRAP_NEXT_LINE_MARK,
                IndexRowCol(self.index(f"{line_start} +1l")),
                tk.RIGHT,
            )
            line = self.get(line_start, WRAP_NEXT_LINE_MARK)

            bq_depth_change = 0
            # Split for non-blank/blank lines
            if re.search(r"\S", line):
                paragraph_complete = False
                # Check for various block markup types
                trimmed = line.lower().rstrip(" \n").replace(PAGEMARK_PIN, "")
                # Begin block quote (maybe customized)
                if match := re.fullmatch(r"/#(\[\d+)?(\.\d+)?(,\d+)?]?", trimmed):
                    bq_depth_change = 1
                    # Default is to just indent left margins by block_indent
                    # Special case if block depth currently zero - use default block right margin not general right margin
                    (
                        new_block_left,
                        new_block_first,
                        new_block_right,
                    ) = self.wrap_interpret_margins(
                        match[1],
                        match[2],
                        match[3],
                        block_params_list[-1].left + bq_indent,
                        block_params_list[-1].left + bq_indent,
                        block_params_list[-1].right if bq_depth > 0 else bq_right,
                    )
                    # Save latest wrap params
                    block_params_list.append(
                        WrapParams(new_block_left, new_block_first, new_block_right)
                    )
                    paragraph_complete = True
                # End block quote
                elif trimmed == "#/":
                    bq_depth_change = -1
                    paragraph_complete = True
                # Some common code for start of all other block types
                elif match := re.fullmatch(
                    r"/([\$xf\*plrci])(\[\d+)?(\.\d+)?(,\d+)?]?", trimmed
                ):
                    block_type = match[1]
                    # Output any previous paragraph
                    if paragraph:
                        self.wrap_paragraph(
                            paragraph_start,
                            line_start,
                            paragraph,
                            block_params_list[bq_depth],
                            wrapper,
                        )
                        paragraph = ""
                    # Reposition line_start in case above wrapping changed line numbering
                    # to be the line after the markup line
                    line_start = self.index(WRAP_NEXT_LINE_MARK)

                    # Find matching close markup within section being wrapped
                    if close_index := self.search(
                        rf"^{re.escape(block_type)}/\s*$",
                        line_start,
                        stopindex=WRAP_END_MARK,
                        nocase=True,
                        regexp=True,
                    ):
                        self.set_mark_position(
                            WRAP_NEXT_LINE_MARK,
                            IndexRowCol(self.index(f"{close_index} +1l")),
                            tk.RIGHT,
                        )
                    else:
                        tidy_function()
                        next_line_rowcol = IndexRowCol(self.index(WRAP_NEXT_LINE_MARK))
                        logger.error(
                            f"No closing markup found to match /{block_type} at line {next_line_rowcol.row-1}"
                        )
                        return

                    # Handle complete no-indent block by skipping the whole thing
                    if block_type in "$xf":
                        pass

                    # Handle complete fixed-indent block
                    elif block_type in "*pl":
                        indent = poetry_indent if block_type == "p" else block_indent
                        left_margin = self.wrap_interpret_single_margin(
                            match[2], block_params_list[-1].left + indent
                        )
                        block_min_left, _ = self.wrap_get_block_limits(
                            line_start, close_index
                        )
                        self.wrap_reindent_block(
                            line_start,
                            close_index,
                            left_margin - block_min_left,
                        )

                    # Handle complete right-align block
                    elif block_type == "r":
                        right_margin = self.wrap_interpret_single_margin(
                            match[2], block_params_list[-1].right
                        )
                        block_min_left, block_max_right = self.wrap_get_block_limits(
                            line_start, close_index
                        )
                        # Ideally, we'd like to insert/delete this number of spaces (negative for delete)
                        # But check we're not deleting so much that block is to the left of left margin
                        n_spaces = right_margin - block_max_right
                        if (
                            n_spaces > 0
                            or -n_spaces <= block_min_left - block_params_list[-1].left
                        ):
                            self.wrap_reindent_block(line_start, close_index, n_spaces)

                    # Handle complete center block
                    elif block_type == "c":
                        default_center = int(
                            (block_params_list[-1].left + block_params_list[-1].right)
                            / 2
                        )
                        center_point = self.wrap_interpret_single_margin(
                            match[2],
                            default_center,
                        )
                        self.wrap_center_block(line_start, close_index, center_point)

                    # Handle complete index block
                    elif block_type == "i":
                        (
                            index_wrap_margin,
                            index_main,
                            index_right,
                        ) = self.wrap_interpret_margins(
                            match[2],
                            match[3],
                            match[4],
                            preferences.get(PrefKey.WRAP_INDEX_WRAP_MARGIN),
                            preferences.get(PrefKey.WRAP_INDEX_MAIN_MARGIN),
                            preferences.get(PrefKey.WRAP_INDEX_RIGHT_MARGIN),
                        )
                        self.wrap_index_block(
                            line_start,
                            close_index,
                            index_wrap_margin,
                            index_main,
                            index_right,
                            wrapper,
                        )

                # End blocks should have been dealt with by the begin block code
                elif match := re.fullmatch(r"([\$\*xfcrpl]/)", trimmed):
                    tidy_function()
                    next_line_rowcol = IndexRowCol(self.index(WRAP_NEXT_LINE_MARK))
                    logger.error(
                        f"{match[1]} markup error at line {next_line_rowcol.row-1}"
                    )
                    return
                else:
                    # Is it the first line of a paragraph?
                    if not paragraph:
                        paragraph_start = line_start
                    paragraph += line
            else:
                # Blank line - end of paragraph
                paragraph_complete = True

            if paragraph_complete and paragraph:
                self.wrap_paragraph(
                    paragraph_start,
                    line_start,
                    paragraph,
                    block_params_list[bq_depth],
                    wrapper,
                )
                paragraph = ""

            if bq_depth_change < 0:
                # Exiting a block level - discard the params
                try:
                    block_params_list.pop()
                    if len(block_params_list) <= 0:
                        raise IndexError
                except IndexError:
                    tidy_function()
                    next_line_rowcol = IndexRowCol(self.index(WRAP_NEXT_LINE_MARK))
                    logger.error(
                        f"Block quote markup error at line {next_line_rowcol.row-1}"
                    )
                    return
            bq_depth += bq_depth_change

        # Output any last paragraph
        if paragraph:
            # If paragraph runs right to end of file, ensure it has a terminating newline
            if (
                IndexRowCol(maintext().index(f"{line_start} +1l")).row
                == maintext().end().row
            ):
                maintext().insert(tk.END, "\n")
            self.wrap_paragraph(
                paragraph_start,
                f"{line_start} +1l",
                paragraph,
                block_params_list[bq_depth],
                wrapper,
            )
        tidy_function()

    def wrap_paragraph(
        self,
        paragraph_start: str,
        paragraph_end: str,
        paragraph: str,
        wrap_params: WrapParams,
        wrapper: TextWrapper,
    ) -> None:
        """Wrap a complete paragraph and replace it in the text.

        Args:
            paragraph_start: Index of start of paragraph.
            paragraph_end: Index of end of paragraph (beginning of line following paragraph).
            paragraph: Text of the paragraph to be wrapped.
            wrap_params: Wrapping parameters.
            wrapper: TextWrapper object to perform the wrapping - re-used for efficiency.
        """
        # Remove leading/trailing space
        paragraph = paragraph.strip()
        # Replace all multiple whitespace with single space
        paragraph = re.sub(r"\s+", " ", paragraph)
        # Don't want pagemark pins to trap spaces around them, so...
        # Remove space between pagemark pins
        paragraph = re.sub(rf"(?<={PAGEMARK_PIN}) (?={PAGEMARK_PIN})", "", paragraph)
        # Remove space after pagemark pins if space (or linestart) before
        paragraph = re.sub(rf"(( |^){PAGEMARK_PIN}+) ", r"\1", paragraph)
        # Remove space before pagemark pins if space (or lineend) after
        paragraph = re.sub(rf" ({PAGEMARK_PIN}+( |$)) ", r"\1", paragraph)

        wrapper.width = wrap_params.right
        wrapper.initial_indent = wrap_params.first * " "
        wrapper.subsequent_indent = wrap_params.left * " "

        wrapped = wrapper.fill(paragraph)
        self.delete(paragraph_start, paragraph_end)
        self.insert(paragraph_start, wrapped + "\n")

    def wrap_center_block(
        self, start_index: str, end_index: str, center_point: int
    ) -> None:
        """Center each line in the block between start_index and end_index
        within the given margins.

        Args:
            start_index: Beginning of first line to center.
            end_index: Beginning of line immediately after text block (the "c/" line).
            center_point: Column to center on.
        """
        line_start = start_index
        while self.compare(line_start, "<", end_index):
            next_start = self.index(f"{line_start} +1l")
            left_limit, right_limit = self.wrap_get_block_limits(line_start, next_start)
            indent = center_point - int((right_limit + left_limit) / 2)
            self.wrap_reindent_block(line_start, next_start, indent)
            line_start = next_start

    def wrap_index_block(
        self,
        start_index: str,
        end_index: str,
        wrap_margin: int,
        main_margin: int,
        right_margin: int,
        wrapper: TextWrapper,
    ) -> None:
        """Wrap the index section between start_index and end_index.

        Index must have been formatted according to DP guidelines, i.e one entry per line,
        indented for sublevels, etc.

        Args:
            start_index: Beginning of first line to center.
            end_index: Beginning of line immediately after text block (the "i/" line).
            left_margin: Left margin that long lines wrap to.
            main_margin: Left margin for main index entries
            right_margin: Right margin to wrap between.
            wrapper: TextWrapper object to perform the wrapping - re-used for efficiency.
        """
        # Mark end_index in case wrapping below changes line numbering
        self.set_mark_position(
            INDEX_END_MARK,
            IndexRowCol(end_index),
            tk.RIGHT,
        )
        line_start = start_index
        while self.compare(line_start, "<", INDEX_END_MARK):
            line_end = self.index(f"{line_start} lineend")
            line = self.get(line_start, line_end).rstrip()
            # Don't include pagemark pins in calculations, since removed after wrapping
            line_no_pin = line.replace(PAGEMARK_PIN, "")
            match = re.match(r"( +)", line_no_pin)
            indent = len(match[1]) if match else 0

            # Mark next line postion in case wrapping below changes line numbering
            self.set_mark_position(
                INDEX_NEXT_LINE_MARK,
                IndexRowCol(self.index(f"{line_start} +1l")),
                tk.RIGHT,
            )
            self.wrap_paragraph(
                line_start,
                f"{line_start}+1l",
                line,
                WrapParams(wrap_margin, main_margin + indent, right_margin),
                wrapper,
            )
            line_start = self.index(INDEX_NEXT_LINE_MARK)

    def wrap_reindent_block(
        self, start_index: str, end_index: str, n_spaces: int
    ) -> None:
        """Re-indent the block by adding/removing spaces at start of lines.

        Args:
            start_index: Beginning of first line to center.
            end_index: Beginning of line immediately after text block (the "c/" line).
            n_spaces: Number of spaces to insert (positive) or delete (negative).
        """
        if n_spaces == 0:
            return
        line_start = start_index
        while self.compare(line_start, "<", end_index):
            line = self.get(line_start, f"{line_start} lineend")
            # Don't include pagemark pins in calculations, since removed after wrapping
            line_no_pin = line.replace(PAGEMARK_PIN, "")
            if length := len(line_no_pin):
                if n_spaces < 0 and length >= -n_spaces:
                    # Can't just delete first few chars, since they may be pagemark pins, not spaces
                    # So, replace just spaces in the line, then replace whole line in text widget
                    line = line.replace(" ", "", -n_spaces)
                    self.delete(line_start, f"{line_start} lineend")
                    self.insert(line_start, line)
                else:
                    self.insert(line_start, n_spaces * " ")
            line_start = self.index(f"{line_start} +1l")

    def wrap_get_block_limits(
        self, start_index: str, end_index: str
    ) -> tuple[int, int]:
        """Get the min left and max right non-space columns of the given block. Also ignore
        pagemark pin characters.

        Args:
            start_index: Beginning of first line of block.
            end_index: Beginning of line immediately after text block (the closing markup line).

        Returns:
            Tuple contain columns of leftmost & rightmost non-space chars in block.
        """
        line_start = start_index
        min_left = 1000
        max_right = 0
        while self.compare(line_start, "<", end_index):
            line_end = self.index(f"{line_start} lineend")
            strip_line = (
                self.get(line_start, line_end).replace(PAGEMARK_PIN, "").rstrip()
            )
            right_col = len(strip_line)
            max_right = max(max_right, right_col)
            if right_col > 0:
                left_col = right_col - len(strip_line.lstrip())
                min_left = min(min_left, left_col)
            line_start = self.index(f"{line_start} +1l")
        return min_left, max_right

    def wrap_interpret_margins(
        self,
        match_left: Optional[str],
        match_first: Optional[str],
        match_right: Optional[str],
        default_left: int,
        default_first: int,
        default_right: int,
    ) -> tuple[int, int, int]:
        """Interpret margins from markup, e.g. `/#[6.4,72]`.

        Args:
            match_left: Matched string for left margin.
            match_first: Matched string for first line's left margin.
            match_right: Matched string for right margin.
            default_left: Default value for left margin if not specified in match.
            default_first: Default value for first line's left margin if neither first nor left specified in match.
            default_right: Default value for right margin if not specified in match.

        Returns:
            Tuple containing the three values.
        """
        new_left = default_left if match_left is None else int(match_left[1:])
        if match_first is None:
            new_first = default_first if match_left is None else new_left
        else:
            new_first = int(match_first[1:])
        new_right = default_right if match_right is None else int(match_right[1:])
        return new_left, new_first, new_right

    def wrap_interpret_single_margin(
        self,
        match_group: Optional[str],
        default_value: int,
    ) -> int:
        """Interpret single margin from markup, e.g. `/*[6]`.

        Args:
            match_group: Matched string for single value.
            default_value: Default value for margin if not specified in match.

        Returns:
            The margin value.
        """
        return default_value if match_group is None else int(match_group[1:])

    def strip_end_of_line_spaces(self) -> None:
        """Remove end-of-line spaces from all lines."""
        start = "1.0"
        while start := self.search(" +$", start, regexp=True):
            self.delete(start, f"{start} lineend")


class TclRegexCompileError(Exception):
    """Raise if Tcl fails to compile regex."""


# For convenient access, store the single MainText instance here,
# with a function to set/query it.
_single_widget = None  # pylint: disable=invalid-name


def maintext(text_widget: Optional[MainText] = None) -> MainText:
    """Store and return the single MainText widget"""
    global _single_widget
    if text_widget is not None:
        assert _single_widget is None
        _single_widget = text_widget
    assert _single_widget is not None
    return _single_widget
