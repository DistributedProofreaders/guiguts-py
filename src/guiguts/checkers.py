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
        if entry.text_range is not None:
            start = maintext().index(self._mark_from_rowcol(entry.text_range.start))
            end = maintext().index(self._mark_from_rowcol(entry.text_range.end))
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
