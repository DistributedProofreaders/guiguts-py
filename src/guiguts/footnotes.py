"""Footnote checking, fixing and tidying functionality"""

import logging
from tkinter import ttk
from typing import Optional
import regex as re

from guiguts.checkers import CheckerDialog, CheckerEntry
from guiguts.maintext import maintext
from guiguts.misc_tools import tool_save
from guiguts.utilities import (
    IndexRowCol,
    IndexRange,
)
from guiguts.widgets import ToolTip

logger = logging.getLogger(__package__)

_the_footnote_checker: Optional[
    "FootnoteChecker"
] = None  # pylint: disable=invalid-name


class AnchorRecord:
    """Record of anchor in file."""

    def __init__(
        self,
        text: str,
        start: IndexRowCol,
        end: IndexRowCol,
        hilite_start: int,
        hilite_end: int,
        fn_index: int,
    ) -> None:
        """Initialize AnchorRecord.

        Args:
            text - Text of the anchor.
            start - Start rowcol of anchor in file.
            end - End rowcol of anchor in file.
            hilite_start - Start column of highlighting in text.
            hilite_start - End column of highlighting in text.
            fn_index - Index into footnotes array of linked footnote.
        """
        self.text = text
        self.start = start
        self.end = end
        self.hilite_start = hilite_start
        self.hilite_end = hilite_end
        self.fn_index = fn_index


class FootnoteRecord:
    """Record of footnote in file."""

    def __init__(
        self,
        text: str,
        start: IndexRowCol,
        end: IndexRowCol,
        hilite_start: int,
        hilite_end: int,
        an_index: int,
    ) -> None:
        """Initialize FootnoteRecord.

        Args:
            text - Text of the footnote.
            start - Start rowcol of footnote in file.
            end - End rowcol of footnote in file.
            hilite_start - Start column of highlighting in text.
            hilite_start - End column of highlighting in text.
            fn_index - Index into anchors array of linked anchor.
        """
        self.text = text
        self.start = start
        self.end = end
        self.hilite_start = hilite_start
        self.hilite_end = hilite_end
        self.an_index = an_index


class FootnoteChecker:
    """Find, check & record footnotes."""

    def __init__(self, checker_dialog: CheckerDialog) -> None:
        """Initialize footnote checker."""
        self.fn_records: list[FootnoteRecord] = []
        self.an_records: list[AnchorRecord] = []
        self.checker_dialog: CheckerDialog = checker_dialog

    def reset(self) -> None:
        """Reset FootnoteChecker."""
        self.fn_records = []
        self.an_records = []

    def get_fn_records(self) -> list[FootnoteRecord]:
        """Return the list of footnote records."""
        return self.fn_records

    def get_an_records(self) -> list[AnchorRecord]:
        """Return the list of anchor records."""
        return self.an_records

    def run_check(self) -> None:
        """Run the initial footnote check."""
        self.reset()
        search_range = IndexRange(maintext().start(), maintext().end())
        match_regex = r"\[ *footnote"
        # Loop, finding all footnotes (i.e. beginning with "[Footnote") allowing
        # some flexibility of spacing & case
        while beg_match := maintext().find_match(
            match_regex, search_range, regexp=True, nocase=True
        ):
            start = beg_match.rowcol
            # Find colon position, or use end of the word "Footnote"
            colon_match = maintext().find_match(
                ":", IndexRange(start, maintext().rowcol(f"{start.row}.end"))
            )
            if colon_match is None:
                colon_pos = maintext().rowcol(
                    f"{start.index()}+{beg_match.count+1}c wordend"
                )
            else:
                colon_pos = colon_match.rowcol
            end_point = colon_pos
            # Find closing square bracket - allow open/close bracket within footnote
            end_match = None
            nested = False
            while True:
                end_match = maintext().find_match(
                    "[][]", IndexRange(end_point, maintext().end()), regexp=True
                )
                if end_match is None:
                    break
                end_point = maintext().rowcol(f"{end_match.rowcol.index()}+1c")
                if maintext().get_match_text(end_match) == "]":
                    if not nested:
                        break  # Found the one we want
                    nested = False  # Closing nesting
                else:
                    if nested:
                        end_match = None  # Not attempting to handle double nesting
                        break
                    nested = True  # Opening nesting

            # If closing [ not found, use end of line
            if end_match is None:
                end_point = maintext().rowcol(f"{start.row}.end")

            # Get label of footnote, e.g. "[Footnote 4:..." has label "4"
            fn_line = maintext().get(start.index(), f"{start.row}.end")
            fn_label = fn_line[
                beg_match.count - beg_match.rowcol.col : colon_pos.col
            ].strip()

            # Find previous occurrence of matching anchor, e.g. "[4]"
            # but not where used in context of block markup, e.g. "/#[4]"
            start_point = start
            while True:
                anchor_match = maintext().find_match(
                    f"[{fn_label}]",
                    IndexRange(start_point, maintext().start()),
                    backwards=True,
                )
                if anchor_match is None:
                    break
                anchor_context = maintext().get(
                    f"{anchor_match.rowcol.index()}-2c", anchor_match.rowcol.index()
                )
                if not re.fullmatch("/[#$*FILPXCR]", anchor_context):
                    break
                start_point = anchor_match.rowcol

            fn_index = len(self.fn_records)
            an_index = -1 if anchor_match is None else len(self.an_records)
            fnr = FootnoteRecord(
                fn_line, start, end_point, start.col + 1, colon_pos.col, an_index
            )
            self.fn_records.append(fnr)

            if anchor_match is not None:
                an_line = maintext().get(
                    f"{anchor_match.rowcol.row}.0", f"{anchor_match.rowcol.row}.end"
                )
                anr = AnchorRecord(
                    an_line,
                    anchor_match.rowcol,
                    maintext().rowcol(
                        f"{anchor_match.rowcol.index()}+{anchor_match.count}c",
                    ),
                    anchor_match.rowcol.col,
                    anchor_match.rowcol.col + anchor_match.count,
                    fn_index,
                )
                self.an_records.append(anr)

            search_range = IndexRange(end_point, maintext().end())


def sort_key_type(
    entry: CheckerEntry,
) -> tuple[int, int, int]:
    """Sort key function to sort Footnote entries by type (footnote/anchor), then rowcol.

    Types are distinguished lazily - anchors have a short highlit text, "[1]"
    """
    assert entry.text_range is not None
    assert entry.hilite_start is not None
    assert entry.hilite_end is not None
    return (
        entry.hilite_end - entry.hilite_start,
        entry.text_range.start.row,
        entry.text_range.start.col,
    )


def footnote_check() -> None:
    """Check footnotes in the currently loaded file."""
    global _the_footnote_checker

    if not tool_save():
        return

    checker_dialog = CheckerDialog.show_dialog(
        "Footnote Check Results",
        rerun_command=footnote_check,
        sort_key_alpha=sort_key_type,
    )
    if _the_footnote_checker is None:
        _the_footnote_checker = FootnoteChecker(checker_dialog)
    elif not _the_footnote_checker.checker_dialog.winfo_exists():
        _the_footnote_checker.checker_dialog = checker_dialog

    ToolTip(
        checker_dialog.text,
        "\n".join(
            [
                "Left click: Select & find footnote",
            ]
        ),
        use_pointer_pos=True,
    )
    frame = ttk.Frame(checker_dialog.header_frame)
    frame.grid(column=0, row=1, columnspan=2, sticky="NSEW")

    _the_footnote_checker.run_check()
    display_footnote_entries()


def display_footnote_entries() -> None:
    """(Re-)display the footnotes in the checker dialog."""
    assert _the_footnote_checker is not None
    checker_dialog = _the_footnote_checker.checker_dialog
    checker_dialog.reset()
    fn_records = _the_footnote_checker.get_fn_records()
    an_records = _the_footnote_checker.get_an_records()
    for fn_index, fn_record in enumerate(fn_records):
        error_prefix = ""
        if fn_record.an_index < 0:
            error_prefix = "NO ANCHOR: "
        else:
            an_record = an_records[fn_record.an_index]
            # Check that no other footnote has the same anchor as this one
            for fni2, fn2 in enumerate(fn_records):
                an2 = an_records[fn2.an_index]
                if fn_index != fni2 and an_record.start == an2.start:
                    error_prefix = "SAME ANCHOR: "
                    break
            # Check anchor of previous footnote and this one are in order (footnotes are always in order)
            if (
                fn_index > 0
                and fn_record.an_index >= 0
                and fn_records[fn_index - 1].an_index >= 0
            ):
                an_prev = an_records[fn_records[fn_index - 1].an_index]
                if an_prev.start.row > an_record.start.row or (
                    an_prev.start.row == an_record.start.row
                    and an_prev.start.col > an_record.start.col
                ):
                    error_prefix += "SEQUENCE: "
            # Check anchor of next footnote and this one are in order (footnotes are always in order)
            if (
                "SEQUENCE: " not in error_prefix
                and fn_index < len(fn_records) - 1
                and fn_record.an_index >= 0
                and fn_records[fn_index + 1].an_index >= 0
            ):
                an_next = an_records[fn_records[fn_index + 1].an_index]
                if an_next.start.row < an_record.start.row or (
                    an_next.start.row == an_record.start.row
                    and an_next.start.col < an_record.start.col
                ):
                    error_prefix += "SEQUENCE: "
        checker_dialog.add_entry(
            fn_record.text,
            IndexRange(fn_record.start, fn_record.end),
            fn_record.hilite_start,
            fn_record.hilite_end,
            error_prefix=error_prefix,
        )
    for an_record in _the_footnote_checker.get_an_records():
        checker_dialog.add_entry(
            an_record.text,
            IndexRange(an_record.start, an_record.end),
            an_record.hilite_start,
            an_record.hilite_end,
        )
    checker_dialog.display_entries()
