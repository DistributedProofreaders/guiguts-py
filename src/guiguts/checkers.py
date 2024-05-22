"""Support running of checking tools"""

from enum import Enum, StrEnum, auto
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional, Callable

from guiguts.maintext import maintext
from guiguts.mainwindow import ScrolledReadOnlyText
from guiguts.preferences import PersistentString, PrefKey
from guiguts.root import root
from guiguts.utilities import (
    IndexRowCol,
    IndexRange,
    is_mac,
    sing_plur,
)
from guiguts.widgets import ToplevelDialog, TlDlg, mouse_bind

MARK_ENTRY_TO_SELECT = "MarkEntryToSelect"
HILITE_TAG_NAME = "chk_hilite"


class CheckerEntryType(Enum):
    """Enum class to store Checker Entry types."""

    HEADER = auto()
    CONTENT = auto()
    FOOTER = auto()


class CheckerEntry:
    """Class to hold one entry in the Checker dialog.

    Current implementation enforces (on creation) and assumes (in use) that
    no section contains Entries of more than one type.

    Attributes:
            text: Single line of text to display in checker dialog.
            text_range: Optional start and end of point of interest in main text widget.
            hilite_start: Optional column to begin higlighting entry in dialog.
            hilite_end: Optional column to end higlighting entry in dialog.
            section: Section entry belongs to.
            initial_pos: Position of entry during initial creation.
    """

    def __init__(
        self,
        text: str,
        text_range: Optional[IndexRange],
        hilite_start: Optional[int],
        hilite_end: Optional[int],
        section: int,
        initial_pos: int,
        entry_type: CheckerEntryType,
    ) -> None:
        """Initialize CheckerEntry object.

        Args:
            text: Single line of text to display in checker dialog.
            text_range: Optional start and end of point of interest in main text widget.
            hilite_start: Optional column to begin higlighting entry in dialog.
            hilite_end: Optional column to end higlighting entry in dialog.
            section: Section entry belongs to.
            initial_pos: Position of entry during initial creation.
        """
        self.text = text
        self.text_range = text_range
        self.hilite_start = hilite_start
        self.hilite_end = hilite_end
        self.section = section
        self.initial_pos = initial_pos
        self.entry_type = entry_type


class CheckerSortType(StrEnum):
    """Enum class to store Checker Dialog sort types."""

    ALPHABETIC = auto()
    ROWCOL = auto()


class CheckerDialog(ToplevelDialog):
    """Dialog to show results of running a check.

    Attributes:
        text: Text widget to contain results.
        header_frame: Frame at top of widget containing configuration buttons, fields, etc.
        count_label: Label showing how many linked entries there are in the dialog
    """

    sort_type: PersistentString

    def __init__(
        self,
        title: str,
        rerun_command: Callable[[], None],
        process_command: Optional[Callable[[CheckerEntry], None]] = None,
        sort_key_rowcol: Optional[Callable[[CheckerEntry], tuple]] = None,
        sort_key_alpha: Optional[Callable[[CheckerEntry], tuple]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the dialog.

        Args:
            title: Title for dialog.
            rerun_command: Function to call to re-run the check.
            process_command: Function to call to "process" the current error, e.g. swap he/be
        """
        # Initialize class variables on first instantiation, then remember
        # values for subsequent uses of dialog.
        try:
            CheckerDialog.sort_type
        except AttributeError:
            CheckerDialog.sort_type = PersistentString(PrefKey.CHECKERDIALOG_SORT_TYPE)

        super().__init__(title, **kwargs)
        self.top_frame.rowconfigure(0, weight=0)
        self.header_frame = ttk.Frame(self.top_frame, padding=2)
        self.header_frame.grid(column=0, row=0, sticky="NSEW")

        self.header_frame.columnconfigure(0, weight=1)
        left_frame = ttk.Frame(self.header_frame)
        left_frame.grid(column=0, row=0, sticky="NSEW")
        left_frame.columnconfigure(0, weight=1)
        self.count_label = ttk.Label(left_frame, text="No results")
        self.count_label.grid(column=0, row=0, sticky="NSW")
        ttk.Label(
            left_frame,
            text="Sort:",
        ).grid(row=0, column=1, sticky="NSE", padx=5)
        ttk.Radiobutton(
            left_frame,
            text="Line & Col",
            command=self.display_entries,
            variable=CheckerDialog.sort_type,
            value=CheckerSortType.ROWCOL,
            takefocus=False,
        ).grid(row=0, column=2, sticky="NSE", padx=2)
        ttk.Radiobutton(
            left_frame,
            text="Alpha/Type",
            command=self.display_entries,
            variable=CheckerDialog.sort_type,
            value=CheckerSortType.ALPHABETIC,
            takefocus=False,
        ).grid(row=0, column=3, sticky="NSE", padx=2)

        self.rerun_button = ttk.Button(
            self.header_frame, text="Re-run", command=rerun_command
        )
        self.rerun_button.grid(column=1, row=0, sticky="NSE", padx=20)

        self.top_frame.rowconfigure(1, weight=1)
        self.text = ScrolledReadOnlyText(
            self.top_frame, context_menu=False, wrap=tk.NONE
        )
        self.text.grid(column=0, row=1, sticky="NSEW")

        # 3 binary choices:
        #     remove/not_remove (just select) - controlled by button 3 or button 1
        #     process/not_process - controlled by Cmd/Ctrl pressed or not
        #     match/not_match - controlled by Shift pressed or not
        # Only 7 of the 8 possibilities needed, since "select not_process match" makes no sense
        mouse_bind(self.text, "1", self.select_entry_by_click)
        mouse_bind(self.text, "3", self.remove_entry_by_click)
        mouse_bind(
            self.text,
            "Shift+3",
            lambda event: self.remove_entry_by_click(event, all_matching=True),
        )
        mouse_bind(self.text, "Cmd/Ctrl+1", self.process_entry_by_click)
        mouse_bind(
            self.text,
            "Shift+Cmd/Ctrl+1",
            lambda event: self.process_entry_by_click(event, all_matching=True),
        )
        mouse_bind(self.text, "Cmd/Ctrl+3", self.process_remove_entry_by_click)
        mouse_bind(
            self.text,
            "Shift+Cmd/Ctrl+3",
            lambda event: self.process_remove_entry_by_click(event, all_matching=True),
        )
        self.bind("<Up>", lambda _e: self.select_entry_by_arrow(-1))
        self.bind("<Down>", lambda _e: self.select_entry_by_arrow(1))

        self.process_command = process_command
        self.rowcol_key = sort_key_rowcol or CheckerDialog.sort_key_rowcol
        self.alpha_key = sort_key_alpha or CheckerDialog.sort_key_alpha
        self.text.tag_configure(HILITE_TAG_NAME, foreground="#2197ff")
        self.count_linked_entries = 0  # Not the same as len(self.entries)
        self.section_count = 0
        self.selected_text = ""
        self.selected_text_range: Optional[IndexRange] = None
        self.reset()

        def delete_dialog() -> None:
            """Call its reset method, then destroy the dialog"""
            self.reset()
            self.destroy()

        self.wm_protocol("WM_DELETE_WINDOW", delete_dialog)

    @classmethod
    def show_dialog(
        cls: type[TlDlg],
        title: Optional[str] = None,
        destroy: bool = True,
        **kwargs: Any,
    ) -> TlDlg:
        """Show the instance of this dialog class, or create it if it doesn't exist.

        Args:
            title: Dialog title.
            destroy: True (default) if dialog should be destroyed & re-created, rather than re-used
            args: Optional args to pass to dialog constructor.
            kwargs: Optional kwargs to pass to dialog constructor.
        """
        return super().show_dialog(title, destroy, **kwargs)

    @classmethod
    def sort_key_rowcol(
        cls,
        entry: CheckerEntry,
    ) -> tuple[int, int, int]:
        """Default sort key function to sort entries by row/col.

        Preserve entries in sections.
        If header/footer, then preserve original order
        If no row/col, place content lines before those with row/col
        If row/col, sort by row, then col.
        """
        if entry.entry_type == CheckerEntryType.HEADER:
            return (entry.section, entry.initial_pos, 0)
        if entry.entry_type == CheckerEntryType.FOOTER:
            return (entry.section, entry.initial_pos, 0)

        # Content without row/col comes before content with, and preserves its original order
        if entry.text_range is None:
            return (entry.section, 0, entry.initial_pos)
        # Content with row/col is ordered by row, then col
        return (
            entry.section,
            entry.text_range.start.row,
            entry.text_range.start.col,
        )

    @classmethod
    def sort_key_alpha(
        cls,
        entry: CheckerEntry,
    ) -> tuple[int, str, str, int, int]:
        """Default sort key function to sort entries by text, putting identical upper
            and lower case versions together.

        If text is highlighted, use that, otherwise use whole line of text
        Preserve entries in sections.
        If header/footer, then preserve original order, putting header first & footer last.
        Place text with no row/col before identical text with row/col.
        """
        # Force header before content, and footer after content (though should be
        # unnecessary since in different sections) preserving original order
        if entry.entry_type == CheckerEntryType.HEADER:
            return (
                entry.section,
                "",
                "",
                0,
                entry.initial_pos,
            )
        if entry.entry_type == CheckerEntryType.FOOTER:
            return (
                entry.section,
                "\ufeff",
                "\ufeff",
                0,
                entry.initial_pos,
            )

        # Get text for comparison
        if entry.hilite_start is None:
            text = entry.text
        else:
            text = entry.text[entry.hilite_start : entry.hilite_end]
        text_low = text.lower()

        # Content without row/col comes before identical content with row/col
        if entry.text_range is None:
            return (entry.section, text_low, text, 0, 0)
        return (
            entry.section,
            text_low,
            text,
            entry.text_range.start.row,
            entry.text_range.start.col,
        )

    def reset(self) -> None:
        """Reset dialog and associated structures & marks."""
        super().reset()
        self.entries: list[CheckerEntry] = []
        self.count_linked_entries = 0
        self.section_count = 0
        self.selected_text = ""
        self.selected_text_range = None
        self.update_count_label()
        if self.text.winfo_exists():
            self.text.delete("1.0", tk.END)
        for mark in maintext().mark_names():
            if mark.startswith(self.get_mark_prefix()):
                maintext().mark_unset(mark)

    def new_section(self) -> None:
        """Start a new section in the dialog.

        When entries are sorted, entries within a section remain in the section.
        It's not a problem if a section is empty.
        """
        self.section_count += 1

    def _add_headfoot(self, hf_type: CheckerEntryType, *headfoot_lines: str) -> None:
        """Internal method to add header or footer to dialog.

        Args:
            hf_type: Either header or footer type
            headfoot_lines: Section header or footer (tuple, list, or string with newlines)
        """
        assert hf_type in (CheckerEntryType.HEADER, CheckerEntryType.FOOTER)
        self.new_section()
        if isinstance(headfoot_lines, str):
            headfoot_lines = headfoot_lines.split("\n")
        for line in headfoot_lines:
            self.add_entry(line, None, None, None, hf_type)
        self.new_section()

    def add_header(self, *header_lines: str) -> None:
        """Add header to dialog.

        Args:
            header_lines: strings to add as header lines (strings may contain newlines)
        """
        self._add_headfoot(CheckerEntryType.HEADER, *header_lines)

    def add_footer(self, *footer_lines: str) -> None:
        """Add footer to dialog.

        Args:
            footer_lines: strings to add as footer lines (strings may contain newlines)
        """
        self._add_headfoot(CheckerEntryType.FOOTER, *footer_lines)

    def add_entry(
        self,
        msg: str,
        text_range: Optional[IndexRange] = None,
        hilite_start: Optional[int] = None,
        hilite_end: Optional[int] = None,
        entry_type: CheckerEntryType = CheckerEntryType.CONTENT,
    ) -> None:
        """Add an entry ready to be displayed in the dialog.

        Also set marks in main text at locations of start & end of point of interest.
        Use this for content; use add_header & add_footer for headers & footers.

        Args:
            msg: Entry to be displayed - only first line will be displayed.
            text_range: Optional start & end of point of interest in main text widget.
            hilite_start: Optional column to begin higlighting entry in dialog.
            hilite_end: Optional column to end higlighting entry in dialog.
            entry_type: Defaults to content
        """
        line = msg.splitlines()[0] if msg else ""
        entry = CheckerEntry(
            line,
            text_range,
            hilite_start,
            hilite_end,
            self.section_count,
            len(self.entries),
            entry_type,
        )
        self.entries.append(entry)

        if text_range is not None:
            maintext().set_mark_position(
                self.mark_from_rowcol(text_range.start),
                text_range.start,
                gravity=tk.LEFT,
            )
            maintext().set_mark_position(
                self.mark_from_rowcol(text_range.end), text_range.end, gravity=tk.RIGHT
            )

    def display_entries(self) -> None:
        """Display all the stored entries in the dialog according to
        the sort setting."""

        sort_key: Callable[[CheckerEntry], tuple]
        if CheckerDialog.sort_type.get() == CheckerSortType.ALPHABETIC:
            sort_key = self.alpha_key
        else:
            sort_key = self.rowcol_key
        self.entries.sort(key=sort_key)
        self.text.delete("1.0", tk.END)
        self.count_linked_entries = 0

        for entry in self.entries:
            rowcol_str = ""
            if entry.text_range is not None:
                rowcol_str = (
                    f"{entry.text_range.start.row}.{entry.text_range.start.col}: "
                )
                if entry.text_range.start.col < 10:
                    rowcol_str += " "
                self.count_linked_entries += 1
            self.text.insert(tk.END, rowcol_str + entry.text + "\n")
            if entry.hilite_start is not None and entry.hilite_end is not None:
                start_rowcol = IndexRowCol(self.text.index(tk.END + "-2line"))
                start_rowcol.col = entry.hilite_start + len(rowcol_str)
                end_rowcol = IndexRowCol(
                    start_rowcol.row, entry.hilite_end + len(rowcol_str)
                )
                self.text.tag_add(
                    HILITE_TAG_NAME, start_rowcol.index(), end_rowcol.index()
                )
        # Highlight previously selected line, or if none, the first suitable line
        if self.selected_text:
            for index, entry in enumerate(self.entries):
                if (
                    entry.text == self.selected_text
                    and entry.text_range == self.selected_text_range
                ):
                    self.select_entry(index)
                    break
        else:
            for index, entry in enumerate(self.entries):
                if entry.text_range:
                    self.select_entry(index)
                    break
        self.update_count_label()

    def update_count_label(self) -> None:
        """Update the label showing how many linked entries are in dialog."""
        if self.count_label.winfo_exists():
            self.count_label["text"] = sing_plur(
                self.count_linked_entries, "Entry", "Entries"
            )

    def select_entry_by_arrow(self, increment: int) -> None:
        """Select next/previous line in dialog, and jump to the line in the
        main text widget that corresponds to it.

        Args:
            increment: +1 to move to next line, -1 to move to previous line.
        """
        entry_index = self.current_entry_index()
        if (
            entry_index is None
            or entry_index + increment < 0
            or entry_index + increment >= len(self.entries)
        ):
            return
        self.select_entry(entry_index + increment, focus=False)

    def select_entry_by_click(self, event: tk.Event) -> str:
        """Select clicked line in dialog, and jump to the line in the
        main text widget that corresponds to it.

        Args:
            event: Event object containing mouse click position.

        Returns:
            "break" to avoid calling other callbacks.
        """
        try:
            entry_index = self.entry_index_from_click(event)
        except IndexError:
            return "break"
        self.select_entry(entry_index)
        return "break"

    def process_entry_by_click(
        self, event: tk.Event, all_matching: bool = False
    ) -> str:
        """Select clicked line in dialog, and jump to the line in the
        main text widget that corresponds to it. Finally call the
        "process" callback function, if any.

        Args:
            event: Event object containing mouse click position.

        Returns:
            "break" to avoid calling other callbacks.
        """
        try:
            entry_index = self.entry_index_from_click(event)
        except IndexError:
            return "break"
        self.select_entry(entry_index)
        self.process_entry_current(all_matching=all_matching)
        return "break"

    def remove_entry_by_click(self, event: tk.Event, all_matching: bool = False) -> str:
        """Remove the entry that was clicked in the dialog.

        Args:
            event: Event object containing mouse click position.
            all_matching: If True remove all other entries that have the same
                message as the chosen entry (e.g. same spelling error)

        Returns:
            "break" to avoid calling other callbacks.
        """
        try:
            entry_index = self.entry_index_from_click(event)
        except IndexError:
            return "break"
        self.select_entry(entry_index)
        self.remove_entry_current(all_matching=all_matching)
        return "break"

    def process_remove_entry_by_click(
        self, event: tk.Event, all_matching: bool = False
    ) -> str:
        """Select clicked line in dialog, and jump to the line in the
        main text widget that corresponds to it. Call the
        "process" callback function, if any, then remove the entry.

        Args:
            event: Event object containing mouse click position.
            all_matching: If True remove all other entries that have the same
                message as the chosen entry (e.g. same spelling error)

        Returns:
            "break" to avoid calling other callbacks.
        """
        try:
            entry_index = self.entry_index_from_click(event)
        except IndexError:
            return "break"
        self.select_entry(entry_index)
        self.process_remove_entry_current(all_matching=all_matching)
        return "break"

    def entry_index_from_click(self, event: tk.Event) -> int:
        """Get the index into the list of entries based on the mouse position
        in the click event.

        Args:
            event: Event object containing mouse click position.

        Returns:
            Index into self.entries list
            Raises IndexError exception if out of range
        """
        click_rowcol = IndexRowCol(self.text.index(f"@{event.x},{event.y}"))
        entry_index = click_rowcol.row - 1
        if entry_index < 0 or entry_index >= len(self.entries):
            raise IndexError
        return entry_index

    def process_remove_entries(
        self, process: bool, remove: bool, all_matching: bool
    ) -> None:
        """Process and/or remove the current entry, if any.

        Args:
            process: If True, process the current entry.
            remove: If True, remove the current entry.
            all_matching: If True, repeat for all entries that have the same
                message as the current entry (e.g. same spelling error).
        """
        entry_index = self.current_entry_index()
        if entry_index is None:
            return
        # Mark before starting so location can be selected later
        self.text.mark_set(MARK_ENTRY_TO_SELECT, f"{entry_index + 1}.0")
        match_text = self.entries[entry_index].text
        if all_matching:
            # Work in reverse since may be deleting from list while iterating
            indices = range(len(self.entries) - 1, -1, -1)
        else:
            indices = range(entry_index, entry_index + 1)
        for ii in indices:
            if self.entries[ii].text == match_text:
                if process and self.process_command:
                    self.process_command(self.entries[ii])
                if remove:
                    if self.entries[ii].text_range:
                        self.count_linked_entries -= 1
                    del self.entries[ii]
                    self.text.delete(f"{ii + 1}.0", f"{ii + 2}.0")
        self.update_count_label()
        # Select line that is now where the first processed/removed line was
        entry_rowcol = IndexRowCol(self.text.index(MARK_ENTRY_TO_SELECT))
        entry_index = min(entry_rowcol.row - 1, len(self.entries) - 1)
        if len(self.entries) > 0:
            self.select_entry(entry_index)

    def process_entry_current(self, all_matching: bool = False) -> None:
        """Call the "process" callback function, if any, on the
        currently selected entry, if any.

        Args:
            all_matching: If True process all other entries that have the same
                message as the chosen entry
        """
        self.process_remove_entries(
            process=True, remove=False, all_matching=all_matching
        )

    def remove_entry_current(self, all_matching: bool = False) -> None:
        """Remove the current entry, if any.

        Args:
            all_matching: If True remove all other entries that have the same
                message as the chosen entry
        """
        self.process_remove_entries(
            process=False, remove=True, all_matching=all_matching
        )

    def process_remove_entry_current(self, all_matching: bool = False) -> None:
        """Call the "process" callback function, if any, for the current entry, if any,
        then remove the entry.

        Args:
            all_matching: If True process & remove all other entries that have the same
                message as the chosen entry
        """
        self.process_remove_entries(
            process=True, remove=True, all_matching=all_matching
        )

    def current_entry_index(self) -> Optional[int]:
        """Get the index entry of the currently selected error message.

        Returns:
            Index into self.entries array, or None if no message selected.
        """
        line_num = self.text.get_select_line_num()
        return None if line_num is None else line_num - 1

    def select_entry(self, entry_index: int, focus: bool = True) -> None:
        """Select line in dialog corresponding to given entry index,
        and jump to the line in the main text widget that corresponds to it.

        Args:
            event: Event object containing mouse click position.
        """
        self.text.select_line(entry_index + 1)
        self.text.mark_set(tk.INSERT, f"{entry_index + 1}.0")
        self.text.focus_set()
        entry = self.entries[entry_index]
        self.selected_text = entry.text
        self.selected_text_range = entry.text_range
        if entry.text_range is not None:
            if root().state() == "iconic":
                root().deiconify()
            start = maintext().index(self.mark_from_rowcol(entry.text_range.start))
            end = maintext().index(self.mark_from_rowcol(entry.text_range.end))
            maintext().do_select(IndexRange(start, end))
            maintext().set_insert_index(
                IndexRowCol(start), focus=(focus and not is_mac())
            )
        self.lift()

    @classmethod
    def mark_from_rowcol(cls, rowcol: IndexRowCol) -> str:
        """Return name to use to mark given location in text file.

        Args:
            rowcol: Location in text file to be marked.

        Returns:
            Name for mark, e.g. "Checker123.45"
        """
        return f"{cls.get_mark_prefix()}{rowcol.index()}"

    @classmethod
    def get_mark_prefix(cls) -> str:
        """pass"""
        # Reduce length of common part of mark names
        return cls.__name__.removesuffix("Dialog")
