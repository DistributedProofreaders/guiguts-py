"""Define key components of main window"""


import logging
import regex as re
import tkinter as tk
from tkinter import ttk
from tkinter import font as tk_font

from typing import Any, Callable, Optional

from guiguts.preferences import preferences
from guiguts.utilities import is_mac, IndexRowCol, IndexRange

logger = logging.getLogger(__package__)

TEXTIMAGE_WINDOW_ROW = 0
TEXTIMAGE_WINDOW_COL = 0
SEPARATOR_ROW = 1
SEPARATOR_COL = 0
STATUSBAR_ROW = 2
STATUSBAR_COL = 0
MIN_PANE_WIDTH = 20
TK_ANCHOR_MARK = "tk::anchor1"


class FindMatch:
    """Index and length of match found by search method.

    Attributes:
        index: Index of start of match.
        count: Length of match.
    """

    def __init__(self, index: IndexRowCol, count: int):
        self.rowcol = index
        self.count = count


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
        self.offset = 5
        # Allow for 5 digit line numbers
        width = self.font.measure("88888") + self.offset
        tk.Canvas.__init__(self, parent, *args, width=width, **kwargs)
        self.textwidget = text_widget

    def redraw(self, *args: Any) -> None:
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
                text_pos, dline[1], anchor="ne", font=self.font, text=linenum
            )
            index = self.textwidget.index(index + "+1l")


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

        # Create Line Numbers widget and bind update routine to all
        # events that might change which line numbers should be displayed
        self.linenumbers = TextLineNumbers(self.frame, self)
        self.linenumbers.grid(column=0, row=0, sticky="NSEW")
        self.bind("<Configure>", self._on_change, add=True)
        self.bind("<KeyPress>", self._on_change, add=True)
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
        self.modifiedCallbacks: list[Callable[[], None]] = []
        self.bind("<<Modified>>", self.modify_flag_changed_callback)

        self.bind("<<Cut>>", self.smart_cut)
        self.bind("<<Copy>>", self.smart_copy)
        self.bind("<<Paste>>", self.smart_paste)

        # Column selection uses Alt key on Windows/Linux, Option key on macOS
        # Key Release is reported as Alt_L on all platforms
        modifier = "Option" if is_mac() else "Alt"
        self.bind(f"<{modifier}-ButtonPress-1>", self.column_select_click)
        self.bind(f"<{modifier}-B1-Motion>", self.column_select_motion)
        self.bind(f"<{modifier}-ButtonRelease-1>", self.column_select_release)
        self.bind("<KeyRelease-Alt_L>", lambda e: self.column_select_stop())
        self.column_selecting = False

        # Ensure text still shows selected when focus is in another dialog
        if "inactiveselect" not in kwargs.keys():
            self["inactiveselect"] = self["selectbackground"]

        maintext(self)  # Register this single instance of MainText

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

    def _on_change(self, *args: Any) -> None:
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
        self.show_line_numbers(not self.line_numbers_shown())

    def show_line_numbers(self, show: bool) -> None:
        """Show or hide line numbers.

        Args:
            show: True to show, False to hide.
        """
        if self.line_numbers_shown() == show:
            return
        if show:
            self.linenumbers.grid()
        else:
            self.linenumbers.grid_remove()
        preferences.set("LineNumbers", show)

    def line_numbers_shown(self) -> bool:
        """Check if line numbers are shown.

        Returns:
            True if shown, False if not.
        """
        return self.linenumbers.winfo_viewable()

    def key_bind(self, keyevent: str, handler: Callable[[Any], None]) -> None:
        """Bind lower & uppercase versions of ``keyevent`` to ``handler``
        in main text window.

        If this is not done, then use of Caps Lock key causes confusing
        behavior, because pressing ``Ctrl`` and ``s`` sends ``Ctrl+S``.

        Args:
            keyevent: Key event to trigger call to ``handler``.
            handler: Callback function to be bound to ``keyevent``.
        """
        lk = re.sub("[A-Z]>$", lambda m: m.group(0).lower(), keyevent)
        uk = re.sub("[a-z]>$", lambda m: m.group(0).upper(), keyevent)

        def handler_break(event: tk.Event, func: Callable[[tk.Event], None]) -> str:
            """In order for class binding not to be called after widget
            binding, event handler for widget needs to return "break"
            """
            func(event)
            return "break"

        self.bind(lk, lambda event: handler_break(event, handler))
        self.bind(uk, lambda event: handler_break(event, handler))

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

    def modify_flag_changed_callback(self, *args: Any) -> None:
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
        with open(fname, "r", encoding="utf-8") as fh:
            self.delete("1.0", tk.END)
            self.insert(tk.END, fh.read())
            self.set_modified(False)
        self.edit_reset()

    def do_close(self) -> None:
        """Close current file and clear widget."""
        self.delete("1.0", tk.END)
        self.set_modified(False)
        self.edit_reset()

    def get_index(self, pos: str) -> IndexRowCol:
        """Return index of given position as IndexRowCol object.

        Wrapper for `Tk::Text.index()`

        Args:
            pos: Index to position in file.

        Returns:
            IndexRowCol containing position in file.
        """
        return IndexRowCol(self.index(pos))

    def get_insert_index(self) -> IndexRowCol:
        """Return index of the insert cursor as IndexRowCol object.

        Returns:
            IndexRowCol containing position of the insert cursor.
        """
        return self.get_index(tk.INSERT)

    def set_insert_index(self, insert_pos: IndexRowCol, focus: bool = True) -> None:
        """Set the position of the insert cursor.

        Args:
            rowcol: Location to position insert cursor.
            focus: Optional, False means focus will not be forced to maintext
        """
        self.mark_set(tk.INSERT, insert_pos.index())
        self.see(tk.INSERT)
        if focus:
            self.focus_set()

    def get_text(self) -> str:
        """Return all the text from the text widget.

        Strips final additional newline that widget adds at tk.END.

        Returns:
            String containing text widget contents.
        """
        return self.get(1.0, f"{tk.END}-1c")

    def columnize_copy(self, *args: Any) -> None:
        """Columnize the current selection and copy it."""
        self.columnize_selection()
        self.column_copy_cut()

    def columnize_cut(self, *args: Any) -> None:
        """Columnize the current selection and copy it."""
        self.columnize_selection()
        self.column_copy_cut(cut=True)

    def columnize_paste(self, *args: Any) -> None:
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
        self.tag_remove("sel", "1.0", tk.END)
        min_row = min(col_range.start.row, col_range.end.row)
        max_row = max(col_range.start.row, col_range.end.row)
        min_col = min(col_range.start.col, col_range.end.col)
        max_col = max(col_range.start.col, col_range.end.col)
        for line in range(min_row, max_row + 1):
            beg = IndexRowCol(line, min_col).index()
            end = IndexRowCol(line, max_col).index()
            # If line is too short for any text to be selected, select to
            # beginning of next line (just captures the newline). This
            # is then dealt with in column_copy_cut.
            if self.get(beg, end) == "":
                end += "+ 1l linestart"
            self.tag_add("sel", beg, end)

    def do_select(self, range: IndexRange) -> None:
        """Select the given range of text.

        Args:
            IndexRange containing start and end of text to be selected."""
        self.tag_remove("sel", "1.0", tk.END)
        self.tag_add("sel", range.start.index(), range.end.index())

    def selected_ranges(self) -> list[IndexRange]:
        """Get the ranges of text marked with the `sel` tag.

        Returns:
            List of IndexRange objects indicating the selected range(s)
        """
        ranges = self.tag_ranges("sel")
        assert len(ranges) % 2 == 0
        sel_ranges = []
        for idx in range(0, len(ranges), 2):
            sel_ranges.append(IndexRange(str(ranges[idx]), str(ranges[idx + 1])))
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

    def column_copy_cut(self, cut: bool = False) -> None:
        """Copy or cut the selected text to the clipboard.

        A newline character is inserted between each line.

        Args:
            cut: True if cut is required, defaults to False (copy)
        """
        if not (ranges := self.selected_ranges()):
            return
        self.clipboard_clear()
        for range in ranges:
            start = range.start.index()
            end = range.end.index()
            # Trap case where line was too short to select any text
            # (in do_column_select) and so selection-end was adjusted to
            # start of next line. Adjust it back again.
            if range.end.row > range.start.row and range.end.col == 0:
                end += "- 1l lineend"
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
        end_index = self.get_index(IndexRowCol(max_row, 0).index())
        if max_row > end_index.row:
            self.insert(
                end_index.index() + " lineend", "\n" * (max_row - end_index.row)
            )

        for line in range(max(num_cliplines, num_ranges)):
            # Add any necessary spaces if line being pasted into is too short
            start_rowcol = IndexRowCol(ranges[0].start.row + line, ranges[0].start.col)
            end_rowcol = IndexRowCol(ranges[0].start.row + line, ranges[-1].end.col)
            end_index = self.get_index(end_rowcol.index())
            nspaces = start_rowcol.col - end_index.col
            if nspaces > 0:
                self.insert(end_index.index(), " " * nspaces)

            clipline = cliplines[line % num_cliplines]
            if line < num_ranges:
                self.replace(start_rowcol.index(), end_rowcol.index(), clipline)
            else:
                self.insert(start_rowcol.index(), clipline)
        rowcol = self.get_index(f"{start_rowcol.index()} + {len(clipline)}c")
        self.set_insert_index(rowcol)

    def smart_copy(self, *args: Any) -> str:
        """Do column copy if multiple ranges selected, else default copy."""
        if len(self.selected_ranges()) <= 1:
            return ""  # Permit default behavior to happen
        self.column_copy_cut()
        return "break"  # Skip default behavior

    def smart_cut(self, *args: Any) -> str:
        """Do column cut if multiple ranges selected, else default cut."""
        if len(self.selected_ranges()) <= 1:
            return ""  # Permit default behavior to happen
        self.column_copy_cut(cut=True)
        return "break"  # Skip default behavior

    def smart_paste(self, *args: Any) -> str:
        """Do column paste if multiple ranges selected, else default paste."""
        if len(self.selected_ranges()) <= 1:
            return ""  # Permit default behavior to happen
        self.column_paste()
        return "break"  # Skip default behavior

    def column_select_click(self, event: tk.Event) -> str:
        """Callback when column selection is started via mouse click.

        Args
            event: Event containing mouse coordinates.

        Returns:
            "break" to stop default binding.
        """
        self.column_select_start(self.get_index(f"@{event.x},{event.y}"))
        return "break"

    def column_select_motion(self, event: tk.Event) -> str:
        """Callback when column selection continues via mouse motion.

        Args:
            event: Event containing mouse coordinates.

        Returns:
            "break" to stop default binding or "" to allow it.
        """
        # Attempt to start up column selection if arriving here without a previous click
        # to start, e.g. user presses modifier key after beginning mouse-drag selection.
        cur_index = self.get_index(f"@{event.x},{event.y}")
        if not self.column_selecting:
            ranges = self.selected_ranges()
            if not ranges:  # Fallback to using insert cursor position
                insert_rowcol = self.get_insert_index()
                ranges = [IndexRange(insert_rowcol, insert_rowcol)]
            if self.compare(cur_index.index(), ">", ranges[0].start.index()):
                anchor = ranges[0].start
            else:
                anchor = ranges[-1].end
            self.column_select_start(anchor)

        self.do_column_select(IndexRange(self.get_index(TK_ANCHOR_MARK), cur_index))
        return "break"

    def column_select_release(self, event: tk.Event) -> str:
        """Callback when column selection is stopped via mouse button release.

        Args:
            event: Event containing mouse coordinates.

        Returns:
            "break" to stop default binding or "" to allow it.
        """
        break_str = self.column_select_motion(event)
        self.column_select_stop()
        return break_str

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

    def find_match(
        self,
        search_string: str,
        start_range: IndexRowCol | IndexRange,
        nocase: bool,
        regexp: bool,
        backwards: bool,
    ) -> Optional[FindMatch]:
        """Find occurrence of string/regex in given range.

        Args:
            search_string: String/regex to be searched for.
            start_range: Range in which to search, or just start point to search whole file.
            nocase: True to ignore case.
            regexp: True if string is a regex; False for exact string match.
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

        count_var = tk.IntVar()
        if match_start := self.search(
            search_string,
            start_index,
            stop_index,
            count=count_var,
            nocase=nocase,
            regexp=regexp,
            backwards=backwards,
        ):
            return FindMatch(IndexRowCol(match_start), count_var.get())
        return None

    def find_matches(
        self, search_string: str, range: IndexRange, nocase: bool, regexp: bool
    ) -> list[FindMatch]:
        """Find all occurrences of string/regex in given range.

        Args:
            search_string: String/regex to be searched for.
            range: Range in which to search.
            nocase: True to ignore case.
            regexp: True if string is a regex; False for exact string match.

        Returns:
            List of FindMatch objects, each containing index of start and count of characters in a match.
            Empty list if no matches.
        """
        start_index = range.start.index()
        stop_index = range.end.index()

        matches = []
        count_var = tk.IntVar()
        start = start_index
        while start:
            start = self.search(
                search_string,
                start,
                stop_index,
                count=count_var,
                nocase=nocase,
                regexp=regexp,
            )
            if start:
                matches.append(FindMatch(IndexRowCol(start), count_var.get()))
                start += f"+{count_var.get()}c"
        return matches


# For convenient access, store the single MainText instance here,
# with a function to set/query it.
_single_widget = None


def maintext(text_widget: Optional[MainText] = None) -> MainText:
    """Store and return the single MainText widget"""
    global _single_widget
    if text_widget is not None:
        assert _single_widget is None
        _single_widget = text_widget
    assert _single_widget is not None
    return _single_widget
