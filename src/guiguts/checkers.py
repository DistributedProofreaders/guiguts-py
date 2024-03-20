"""Support running of checking tools"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Optional, Callable

from guiguts.maintext import maintext
from guiguts.mainwindow import ScrolledReadOnlyText
from guiguts.utilities import IndexRowCol, IndexRange, is_mac
from guiguts.widgets import ToplevelDialog

MARK_PREFIX = "chk"
MARK_REMOVED_ENTRY = "MarkRemovedEntry"
HILITE_TAG_NAME = "chk_hilite"
SELECT_TAG_NAME = "chk_select"


class CheckerEntry:
    """Class to hold one entry in the Checker dialog.

    Attributes:
        text: Single line of text to display in checker dialog.
        text_range: Start and end of point of interest in main text widget.
    """

    def __init__(self, text: str, text_range: Optional[IndexRange]) -> None:
        """Initialize CheckerEntry object.

        Args:
            text: Single line of text to display in checker dialog.
            text_range: Optional start and end of point of interest in main text widget.
        """
        self.text = text
        self.text_range = text_range


class CheckerDialog(ToplevelDialog):
    """Dialog to show results of running a check.

    Attributes:
        text: Text widget to contain results.
        header_frame: Frame at top of widget containing configuration buttons, fields, etc.
        count_label: Label showing how many linked entries there are in the dialog
    """

    def __init__(
        self,
        title: str,
        rerun_command: Callable[[], None],
        process_command: Optional[Callable[[CheckerEntry], None]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the dialog.

        Args:
            title: Title for dialog.
            rerun_command: Function to call to re-run the check.
            process_command: Function to call to "process" the current error, e.g. swap he/be
        """
        super().__init__(title, **kwargs)
        self.top_frame.rowconfigure(0, weight=0)
        self.header_frame = ttk.Frame(self.top_frame, padding=2)
        self.header_frame.grid(column=0, row=0, sticky="NSEW")
        self.header_frame.columnconfigure(0, weight=1)
        self.count_label = ttk.Label(self.header_frame, text="No results")
        self.count_label.grid(column=0, row=0, sticky="NSW")
        self.rerun_button = ttk.Button(
            self.header_frame, text="Re-run", command=rerun_command
        )
        self.rerun_button.grid(column=1, row=0, sticky="NSE", padx=20)
        self.top_frame.rowconfigure(1, weight=1)
        self.text = ScrolledReadOnlyText(
            self.top_frame, context_menu=False, wrap=tk.NONE
        )
        self.text.grid(column=0, row=1, sticky="NSEW")

        self.text.bind("<1>", self.select_entry_by_click)
        # On Mac, equivalent of mouse button 3 is button 2 (2-button mice) or
        # Control with button 1 (1 button mice), so 2 bindings per function
        if is_mac():
            self.text.bind("<2>", self.remove_entry_by_click)
            self.text.bind("<Control-1>", self.remove_entry_by_click)
            self.text.bind(
                "<Shift-2>",
                lambda event: self.remove_entry_by_click(event, all_matching=True),
            )
            self.text.bind(
                "<Shift-Control-1>",
                lambda event: self.remove_entry_by_click(event, all_matching=True),
            )
            self.text.bind("<Command-1>", self.process_entry_by_click)
            self.text.bind("<Command-2>", self.process_remove_entry_by_click)
            self.text.bind("<Command-Control-1>", self.process_remove_entry_by_click)
            self.text.bind(
                "<Shift-Command-2>",
                lambda event: self.process_remove_entry_by_click(
                    event, all_matching=True
                ),
            )
            self.text.bind(
                "<Shift-Command-Control-1>",
                lambda event: self.process_remove_entry_by_click(
                    event, all_matching=True
                ),
            )
        else:
            self.text.bind("<3>", self.remove_entry_by_click)
            self.text.bind(
                "<Shift-3>",
                lambda event: self.remove_entry_by_click(event, all_matching=True),
            )
            self.text.bind("<Control-1>", self.process_entry_by_click)
            self.text.bind("<Control-3>", self.process_remove_entry_by_click)
            self.text.bind(
                "<Shift-Control-3>",
                lambda event: self.process_remove_entry_by_click(
                    event, all_matching=True
                ),
            )

        self.process_command = process_command
        self.text.tag_configure(
            SELECT_TAG_NAME, background="#dddddd", foreground="#000000"
        )
        self.text.tag_configure(HILITE_TAG_NAME, foreground="#2197ff")
        self.reset()

    def reset(self) -> None:
        """Reset dialog and associated structures & marks."""
        self.entries: list[CheckerEntry] = []
        self.count_linked_entries = 0  # Not the same as len(self.entries)
        self.update_count_label()
        self.text.delete("1.0", tk.END)
        for mark in maintext().mark_names():
            if mark.startswith(MARK_PREFIX):
                maintext().mark_unset(mark)

    def add_entry(
        self,
        msg: str,
        text_range: Optional[IndexRange] = None,
        hilite_start: Optional[int] = None,
        hilite_end: Optional[int] = None,
    ) -> None:
        """Add an entry to the dialog.

        Also set marks in main text at locations of start & end of point of interest

        Args:
            msg: Entry to display in the dialog - only first line is displayed.
            text_range: Optional Start & end of point of interest in main text widget.
            hilite_start: Optional column to begin higlighting entry in dialog.
            hilite_end: Optional column to end higlighting entry in dialog.
        """
        line = msg.splitlines()[0] if msg else ""
        rowcol_str = ""
        if text_range is not None:
            rowcol_str = f"{text_range.start.row}.{text_range.start.col}: "
            if text_range.start.col < 10:
                rowcol_str += " "
            self.count_linked_entries += 1

        self.text.insert(tk.END, rowcol_str + line + "\n")
        if hilite_start is not None and hilite_end is not None:
            start_rowcol = IndexRowCol(self.text.index(tk.END + "-2line"))
            start_rowcol.col = hilite_start + len(rowcol_str)
            end_rowcol = IndexRowCol(start_rowcol.row, hilite_end + len(rowcol_str))
            self.text.tag_add(HILITE_TAG_NAME, start_rowcol.index(), end_rowcol.index())
        entry = CheckerEntry(line, text_range)
        self.entries.append(entry)
        if text_range is not None:
            maintext().mark_set(
                self._mark_from_rowcol(text_range.start), text_range.start.index()
            )
            maintext().mark_set(
                self._mark_from_rowcol(text_range.end), text_range.end.index()
            )
            # If none selected, select the first message with a text range
            if self.current_entry_index() is None:
                for index, entry in enumerate(self.entries):
                    if entry.text_range:
                        self.select_entry(index)
                        break
        self.update_count_label()

    def update_count_label(self) -> None:
        """Update the label showing how many linked entries are in dialog."""
        word = "Entry" if self.count_linked_entries == 1 else "Entries"
        self.count_label["text"] = f"{self.count_linked_entries} {word}"

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

    def process_entry_by_click(self, event: tk.Event) -> str:
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
        self.process_entry_current()
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
        self.remove_entry_current(all_matching)
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
        self.process_entry_current()
        self.remove_entry_current(all_matching)
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

    def process_entry_current(self) -> None:
        """Call the "process" callback function, if any, on the
        currently selected entry, if any."""
        if self.process_command:
            entry_index = self.current_entry_index()
            if entry_index is not None:
                self.process_command(self.entries[entry_index])

    def remove_entry_current(self, all_matching: bool = False) -> None:
        """Remove the current entry, if any.

        Args:
            all_matching: If True remove all other entries that have the same
                message as the chosen entry (e.g. same spelling error)
        """
        entry_index = self.current_entry_index()
        if entry_index is not None:
            # Mark before removing in case earlier entries get removed due to
            # all_matching being True
            self.text.mark_set(MARK_REMOVED_ENTRY, f"{entry_index+1}.0")
            del_text = self.entries[entry_index].text
            if all_matching:
                # Work in reverse since deleting from list while iterating
                for ii in range(len(self.entries) - 1, -1, -1):
                    if self.entries[ii].text == del_text:
                        if self.entries[ii].text_range:
                            self.count_linked_entries -= 1
                        del self.entries[ii]
                        self.text.delete(f"{ii+1}.0", f"{ii+2}.0")
            else:
                if self.entries[entry_index].text_range:
                    self.count_linked_entries -= 1
                del self.entries[entry_index]
                self.text.delete(f"{entry_index+1}.0", f"{entry_index+2}.0")
            self.update_count_label()
            # Select line after first deleted line
            entry_rowcol = IndexRowCol(self.text.index(MARK_REMOVED_ENTRY))
            entry_index = min(entry_rowcol.row - 1, len(self.entries) - 1)
            if len(self.entries) > 0:
                self.select_entry(entry_index)

    def process_remove_entry_current(self, all_matching: bool = False) -> None:
        """Call the "process" callback function, if any, for the current entry, if any,
        then remove the entry.

        Args:
            all_matching: If True remove all other entries that have the same
                message as the chosen entry (e.g. same spelling error)
        """
        self.process_entry_current()
        self.remove_entry_current(all_matching)

    def current_entry_index(self) -> Optional[int]:
        """Get the index entry of the currently selected error message.

        Returns:
            Index into self.entries array, or None if no message selected.
        """
        if tag_range := self.text.tag_nextrange(SELECT_TAG_NAME, "1.0"):
            return IndexRowCol(tag_range[0]).row - 1
        return None

    def select_entry(self, entry_index: int) -> None:
        """Select line in dialog corresponding to given entry index,
        and jump to the line in the main text widget that corresponds to it.

        Args:
            event: Event object containing mouse click position.
        """
        self.highlight_entry(entry_index)
        self.text.mark_set(tk.INSERT, f"{entry_index+1}.0")
        self.text.focus_set()
        entry = self.entries[entry_index]
        if entry.text_range is not None:
            start = maintext().index(self._mark_from_rowcol(entry.text_range.start))
            end = maintext().index(self._mark_from_rowcol(entry.text_range.end))
            maintext().do_select(IndexRange(start, end))
            maintext().set_insert_index(IndexRowCol(start), focus=False)
        self.lift()

    def highlight_entry(self, entry_index: int) -> None:
        """Highlight the line of text corresponding to the entry_index.

        Args:
            entry_index: Index into self.entries list.
        """
        self.text.tag_remove(SELECT_TAG_NAME, "1.0", tk.END)
        self.text.tag_add(SELECT_TAG_NAME, f"{entry_index+1}.0", f"{entry_index+2}.0")

    def _mark_from_rowcol(self, rowcol: IndexRowCol) -> str:
        """Return name to use to mark given location in text file.

        Args:
            rowcol: Location in text file to be marked.

        Returns:
            Name for mark, e.g. "chk123.45"
        """
        return f"{MARK_PREFIX}{rowcol.index()}"
