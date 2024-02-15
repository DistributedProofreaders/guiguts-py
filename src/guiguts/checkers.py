"""Support running of checking tools"""

import tkinter as tk
from typing import Any, Optional

from guiguts.maintext import maintext
from guiguts.mainwindow import ScrolledReadOnlyText
from guiguts.utilities import IndexRowCol, IndexRange
from guiguts.widgets import ToplevelDialog

MARK_PREFIX = "chk"
HILITE_TAG_NAME = "chk_hilite"


class CheckerEntry:
    """Class to hold one entry in the Checker dialog.

    Attributes:
        text: Single line of text to display in checker dialog.
        range: Start and end of point of interest in main text widget.
    """

    def __init__(self, text: str, range: IndexRange) -> None:
        """Initialize CheckerEntry object.

        Args:
            text: Single line of text to display in checker dialog.
            range: Optional start and end of point of interest in main text widget.
        """
        self.text = text
        self.range = range


class CheckerDialog(ToplevelDialog):
    """Dialog to show results of running a check.

    Attributes:
        text: Text widget to contain results.
    """

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        """Initialize the dialog.

        Args:
            title:  Title for dialog.
        """
        super().__init__(title, *args, **kwargs)
        self.text = ScrolledReadOnlyText(self.top_frame, wrap=tk.NONE)
        self.text.grid(column=0, row=0, sticky="NSEW")
        self.text.bind("<ButtonRelease-1>", self.jump_to_rowcol)
        self.text.tag_configure(HILITE_TAG_NAME, underline=True)
        self.reset()

    def reset(self) -> None:
        """Reset dialog and associated structures & marks."""
        self.entries: list[CheckerEntry] = []
        self.text.delete("1.0", tk.END)
        for mark in maintext().mark_names():
            if mark.startswith(MARK_PREFIX):
                maintext().mark_unset(mark)

    def add_entry(
        self,
        range: IndexRange,
        text: str,
        hilite_start: Optional[int] = None,
        hilite_end: Optional[int] = None,
    ) -> None:
        """Add an entry to the dialog.

        Also set marks in main text at locations of start & end of point of interest

        Args:
            range: Start & end of point of interest in main text widget.
            entry: Entry to display in the dialog - only first line is displayed
            hilite_start: Optional column to begin higlighting entry in dialog
            hilite_end: Optional column to end higlighting entry in dialog
        """
        line = text.splitlines()[0]
        self.text.insert(tk.END, line + "\n")
        if hilite_start is not None and hilite_end is not None:
            start_rowcol = IndexRowCol(self.text.index(tk.END + "-2line"))
            start_rowcol.col = hilite_start
            end_rowcol = IndexRowCol(start_rowcol.row, hilite_end)
            self.text.tag_add(HILITE_TAG_NAME, start_rowcol.index(), end_rowcol.index())
        entry = CheckerEntry(line, range)
        self.entries.append(entry)
        maintext().mark_set(self._mark_from_rowcol(range.start), range.start.index())
        maintext().mark_set(self._mark_from_rowcol(range.end), range.end.index())

    def jump_to_rowcol(self, event: tk.Event) -> None:
        """Jump to the line in the main text widget that corresponds to
        the line clicked in the dialog.

        Args:
            event: Event object containing mouse click position.
        """
        click_rowcol = IndexRowCol(self.text.index(f"@{event.x},{event.y}"))
        entry_index = click_rowcol.row - 1
        if entry_index < 0 or entry_index >= len(self.entries):
            return
        entry = self.entries[entry_index]
        start = maintext().index(self._mark_from_rowcol(entry.range.start))
        end = maintext().index(self._mark_from_rowcol(entry.range.end))
        maintext().do_select(IndexRange(start, end))
        maintext().set_insert_index(IndexRowCol(start), focus=True)
        self.lift()

    def _mark_from_rowcol(self, rowcol: IndexRowCol) -> str:
        """Return name to use to mark given location in text file.

        Args:
            rowcol: Location in text file to be marked.

        Returns:
            Name for mark, e.g. "chk123.45"
        """
        return f"{MARK_PREFIX}{rowcol.index()}"
