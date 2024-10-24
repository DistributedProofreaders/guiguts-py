"""Footnote checking, fixing and tidying functionality"""

import logging
from enum import StrEnum, auto
import tkinter as tk
from tkinter import ttk
from typing import Optional
import regex as re
import roman  # type: ignore[import-untyped]

from guiguts.checkers import CheckerDialog, CheckerEntry
from guiguts.maintext import maintext
from guiguts.misc_tools import tool_save
from guiguts.preferences import (
    PersistentString,
    PrefKey,
)
from guiguts.utilities import (
    IndexRowCol,
    IndexRange,
)
from guiguts.widgets import ToolTip

logger = logging.getLogger(__package__)

_the_footnote_checker: Optional["FootnoteChecker"] = (
    None  # pylint: disable=invalid-name
)

INSERTION_MARK_PREFIX = "ShadowFootnoteMark"


class FootnoteIndexStyle(StrEnum):
    """Enum class to store FN index style types."""

    NUMBER = auto()
    LETTER = auto()
    ROMAN = auto()


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
            hilite_end - End column of highlighting in text.
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
        an_index: Optional[int],
    ) -> None:
        """Initialize FootnoteRecord.

        Args:
            text - Text of the footnote.
            start - Start rowcol of footnote in file.
            end - End rowcol of footnote in file.
            hilite_start - Start column of highlighting in text.
            hilite_end - End column of highlighting in text.
            an_index - Index into anchors array of linked anchor.
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
        self.fn_index_style = PersistentString(PrefKey.FOOTNOTE_INDEX_STYLE)
        self.fn_check_errors = False
        self.fns_have_been_moved = False

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

    def join_to_previous(self) -> None:
        """Join the selected footnote to the previous one."""
        assert _the_footnote_checker is not None
        fn_index = self.get_selected_fn_index()
        if fn_index < 0:
            return  # No selection
        if fn_index == 0:
            return  # Can't join first footnote to previous
        fn_records = _the_footnote_checker.get_fn_records()
        fn_record = fn_records[fn_index]
        fn_cur_start = self.checker_dialog.mark_from_rowcol(fn_record.start)
        fn_cur_end = self.checker_dialog.mark_from_rowcol(fn_record.end)
        prev_record = fn_records[fn_index - 1]
        fn_prev_end = self.checker_dialog.mark_from_rowcol(prev_record.end)
        continuation_text = maintext().get(fn_cur_start, fn_cur_end)[11:]
        maintext().delete(
            f"{fn_cur_start} -1l linestart", f"{fn_cur_end} +1l linestart"
        )
        maintext().delete(f"{fn_prev_end} -1c", f"{fn_prev_end} lineend")
        # ORIG maintext().insert(fn_prev_end, "\n" + continuation_text + "\n")
        maintext().insert(fn_prev_end, "\n" + continuation_text)
        self.checker_dialog.remove_entry_current()
        maintext().see(fn_prev_end)
        self.run_check()
        # display_footnote_entries()

    def autoset_chapter_lz(self) -> None:
        """Insert a 'FOOTNOTES:' LZ header line before each chapter break."""

        # If the last line of the file is not a blank line then add one.
        end_of_file = maintext().end().index()
        if maintext().get(f"{end_of_file} linestart", f"{end_of_file} lineend") != "":
            self.add_blank_line_at_eof()

        search_range = IndexRange(maintext().start(), maintext().end())
        match_regex = r"\n\n\n\n\n"
        # Loop, finding all chapter breaks; i.e. block of 4 blank lines.
        while beg_match := maintext().find_match(
            match_regex, search_range, regexp=True, nocase=True
        ):
            chpt_break_start = beg_match.rowcol.index()
            # Insert a 'FOOTNOTES:' LZ header line before the chapter break.
            maintext().insert(
                f"{chpt_break_start} +1l linestart", "\n\n" + "FOOTNOTES:" + "\n"
            )
            restart_point = maintext().rowcol(f"{chpt_break_start} +4l")
            search_range = IndexRange(restart_point, maintext().end())
        # The file has changed so rebuild an/fn records and refresh dialog.
        self.run_check()
        self.define_buttons()
        display_footnote_entries()

    def autoset_end_lz(self) -> None:
        """Insert a 'FOOTNOTES:' LZ header line at end of file."""

        # If the last line of the file is not a blank line then add one.
        end_of_file = maintext().end().index()
        if maintext().get(f"{end_of_file} linestart", f"{end_of_file} lineend") != "":
            self.add_blank_line_at_eof()

        end_of_file = maintext().end().index()
        # Insert the 'FOOTNOTES:' LZ header line after last line of file.
        maintext().insert(f"{end_of_file} +1l linestart", "\n\n" + "FOOTNOTES:" + "\n")

    def clear_insertion_marks(self) -> None:
        """Clear insertion marks created at paragraph ends."""
        for mark in maintext().mark_names():
            if mark.startswith(INSERTION_MARK_PREFIX):
                maintext().mark_unset(mark)

    def add_blank_line_at_eof(self) -> None:
        """Add a blank line at end of the file.

        An issue arises if the last line of the file is a footnote.
        Inserting a blank line will place it before its end "Checker"
        mark if tk.RIGHT gravity was specified when the mark was set.
        We want the blank line placed after the mark. This avoids
        problems if that footnote is respositioned.

        There will be at most one such "Checker" mark in this case.
        """

        # Note the index of current end of file.
        end_of_file = maintext().end().index()
        blank_line_inserted = False
        mark_name = end_of_file  # Initialise start position of mark search.
        while mark_name := maintext().mark_next(mark_name):  # type: ignore[assignment]
            if mark_name.startswith("Checker"):
                maintext().mark_unset(mark_name)
                maintext().insert(end_of_file, "\n")
                # Set mark again at its original position; i.e. the old end of file.
                maintext().set_mark_position(
                    mark_name,
                    maintext().rowcol(end_of_file),
                    gravity=tk.RIGHT,
                )
                blank_line_inserted = True
                break
        if not blank_line_inserted:
            maintext().insert(end_of_file, "\n")

    def move_footnotes_to_paragraphs(self) -> None:
        """Implements a button command"""
        assert _the_footnote_checker is not None

        # Move footnotes beneath the paragraphs in which they are anchored.

        an_records = self.get_an_records()
        fn_records = self.get_fn_records()

        # If the last line of the file is not a blank line then add one.
        end_of_file = maintext().end().index()
        if maintext().get(f"{end_of_file} linestart", f"{end_of_file} lineend") != "":
            self.add_blank_line_at_eof()

        # First pass.

        # Set a mark before last blank line that separates a paragraph from the start
        # of the next paragraph. The mark is the insertion point to which one or more
        # footnotes will be inserted. The gravity setting for the marks is tk.RIGHT
        # so that when more than one footnote is inserted at the same mark, each
        # footnote will appear to the left of the mark so ensuring that the ascending
        # order of footnote labels is maintained.

        file_end = maintext().end().index()
        match_regex = r"^$"
        an_record_index = 0
        for an_record in an_records:
            # Get the record of the footnote it anchors.
            fn_record = fn_records[an_record.fn_index]
            fn_cur_start = self.checker_dialog.mark_from_rowcol(fn_record.start)
            fn_cur_end = self.checker_dialog.mark_from_rowcol(fn_record.end)

            fn_lines = maintext().get(fn_cur_start, fn_cur_end)
            # Find the end of paragraph in which the footnote anchor is located.
            # Start searching from the line containing the anchor.
            search_range = IndexRange(
                an_record.start, maintext().rowcol(f"{file_end} + 1l linestart")
            )
            while blank_line_match := maintext().find_match(
                match_regex, search_range, regexp=True
            ):
                # This blank line might be one separating a footnote from the paragraph
                # text above or from a preceding footnote. Footnotes are all assumed to
                # be 'mid-paragraph' footnotes so the search continues until the final
                # blank line is reached that separates all above from the first line of
                # a new paragraph or is the end of file.
                blank_line_start = blank_line_match.rowcol.index()
                next_line_text = maintext().get(
                    f"{blank_line_start} +1l linestart",
                    f"{blank_line_start} +1l lineend",
                )
                # If the line below this blank line is not (the first line of) a
                # footnote then we have found the 'end of paragraph' separator.
                if next_line_text[0:10] != "[Footnote ":
                    break
                # Otherwise we have landed on a blank line above one or more footnotes.
                restart_search_point = maintext().rowcol(
                    f"{blank_line_start} +1l linestart"
                )
                # Keep looking for a suitable blank line at which to insert footnote.
                # search_range = IndexRange(restart_search_point, maintext().end())
                search_range = IndexRange(
                    restart_search_point,
                    maintext().rowcol(f"{file_end} + 1l linestart"),
                )
            # End while loop

            # If the insert point is a blank line immediately after a Page Marker, place
            # the insert point at the start of the Page Marker as GG1 does - recall that
            # the gravity setting used for marks is tk.RIGHT.
            line_before = maintext().get(
                f"{blank_line_start} -1l linestart", f"{blank_line_start} -1l lineend"
            )
            if line_before[0:11] == "-----File: ":
                mark_point = maintext().rowcol(f"{blank_line_start} -1l")
                maintext().set_mark_position(
                    f"{INSERTION_MARK_PREFIX}{an_record_index}",
                    mark_point,
                    gravity=tk.RIGHT,
                )
            else:
                # Place the insert point at the start of the blank line we've landed on.
                # Recall that the gravity setting used for marks is tk.RIGHT.
                mark_point = maintext().rowcol(f"{blank_line_start}")
                maintext().set_mark_position(
                    f"{INSERTION_MARK_PREFIX}{an_record_index}",
                    mark_point,
                    gravity=tk.RIGHT,
                )
            an_record_index += 1

        # Second pass

        fn_record_index = 0
        for fn_record in fn_records:
            fn_cur_start = self.checker_dialog.mark_from_rowcol(fn_record.start)
            fn_cur_end = self.checker_dialog.mark_from_rowcol(fn_record.end)
            fn_lines = maintext().get(fn_cur_start, fn_cur_end)

            maintext().delete(
                f"{fn_cur_start} -1l linestart", f"{fn_cur_end} +1l linestart"
            )
            maintext().insert(
                f"{INSERTION_MARK_PREFIX}{fn_record_index}", "\n" + fn_lines + "\n"
            )
            fn_record_index += 1

        # End of final pass over footnotes.

        # Set flag to disable the two 'move FN' buttons when dialog refreshed
        # so user cannot execute a second FN move that might corrupt the file.
        self.fns_have_been_moved = True
        # Footnotes have been moved. Rebuild anchor and footnote record arrays
        # to reflect the changes.
        self.clear_insertion_marks()
        self.run_check()
        self.define_buttons()
        display_footnote_entries()

    def move_footnotes_to_lz(self) -> None:
        """Implements a button command"""

        # Footnotes are always moved downward to a landing zone on a higher-numbered
        # line. Even if a footnote sits immediately below a landing zone, it will be
        # moved to the next one down in the file. If a footnote is located after the
        # last autoset landing zone then a new landing zone ('FOOTNOTES:') is created
        # after the last line in the file and the footnote moved below it. Note that
        # that landing zone is in the same location as the one created when you click
        # the 'Autoset End LZ' button.

        # Start the moves from the last footnote in the file and work upward to the
        # first footnote. Each footnote moved is inserted immediately below the LZ
        # header so pushing down higher-numbered footnotes already moved.

        assert _the_footnote_checker is not None
        fn_records = _the_footnote_checker.get_fn_records()
        fn_records_reversed = fn_records.copy()
        fn_records_reversed.reverse()
        for fn_record in fn_records_reversed:
            fn_cur_start = self.checker_dialog.mark_from_rowcol(fn_record.start)
            fn_cur_end = self.checker_dialog.mark_from_rowcol(fn_record.end)
            fn_lines = maintext().get(fn_cur_start, fn_cur_end)
            # Is there an LZ below this footnote in the file?
            # If not, create one and move footnote below it.
            # Otherwise move footnote below the LZ that was
            # found
            search_range = IndexRange(fn_record.end, maintext().end())
            match_regex = r"FOOTNOTES:"
            if lz_match := maintext().find_match(
                match_regex, search_range, regexp=True
            ):
                # There is a LZ below the footnote.
                lz_start = lz_match.rowcol.index()
                below_lz = f"{lz_start} lineend"
                # Insert the copy of the footnote line(s) below the LZ.
                maintext().insert(below_lz, "\n\n" + fn_lines)
                # Delete the original footnote line(s) along with the
                # blank line above it.
                maintext().delete(
                    f"{fn_cur_start} -1l linestart", f"{fn_cur_end} +1l linestart"
                )
            else:
                # This branch should be entered 0 or 1 times only.
                # Here with a footnote with no landing zone below.
                # There are two situations where this can happen:
                #  1. The last footnote is in the last chapter of
                #     the book and chapter LZ has been selected.
                #     This means that the last 4-line chapter break
                #     found will be the one separating the penultimate
                #     chapter from the final chapter. There is no LZ
                #     after the last paragraph of the last chapter.
                #  2. No LZ was specified before clicking the move
                #     to landing zones button.
                #
                # Insert a LZ after the last line of the file
                # and move the footnote below it. Other footnotes
                # with a lower index may be inserted immediately
                # above it but that will be done in the 'then'
                # branch above because there is now a LZ below
                # those footnotes.

                # Add a LZ at end of file.
                self.autoset_end_lz()
                below_lz = maintext().end().index()
                # Insert the copy of the footnote line(s) below the new LZ.
                maintext().insert(below_lz, "\n" + fn_lines)
                # Delete the original footnote line(s) along with the blank
                # line above it.
                maintext().delete(
                    f"{fn_cur_start} -1l linestart", f"{fn_cur_end} +1l linestart"
                )
                # The last line of the file will be (the last line of) a
                # footnote. Add a blank line after it.
                self.add_blank_line_at_eof()
        # Set flag to disable the two 'move FN' buttons when dialog refreshed
        # so user cannot execute a second FN move that might corrupt the file.
        self.fns_have_been_moved = True
        # The file has changed so rebuild an/fn records and refresh dialog.
        self.run_check()
        self.define_buttons()
        display_footnote_entries()

    def tidy_footnotes(self) -> None:
        """Tidy footnotes after a move.

        Copies and deletes the original then reinserts edited version at same place.
        """
        assert _the_footnote_checker is not None
        fn_records = _the_footnote_checker.get_fn_records()
        for fn_record in fn_records:
            fn_cur_start = self.checker_dialog.mark_from_rowcol(fn_record.start)
            fn_cur_end = self.checker_dialog.mark_from_rowcol(fn_record.end)
            fn_label_and_text_part = maintext().get(
                f"{fn_cur_start} +10c", f"{fn_cur_end} -1c"
            )
            fn_label_and_text_part = re.sub(r"(^.+?):", r"[\1]", fn_label_and_text_part)
            maintext().delete(fn_cur_start, fn_cur_end)
            maintext().insert(fn_cur_start, fn_label_and_text_part)
        self.run_check()
        self.define_buttons()
        display_footnote_entries()

    def get_anchor_hilite_columns(
        self, an_record: AnchorRecord, an_line_text: str
    ) -> tuple:
        """Get new hilite start/end of anchor after it's reindexed.

        The line with an anchor to be reindexed has to be fetched from the file
        each time the reindex() function wants to replace an anchor label. The
        original hilite start/end in the anchor record cannot be relied on as
        the length of the label may change as a result of indexing. That problem
        is compounded if there is more than one anchor on the same line.

        To find the (new position of the) anchor in the line text, first find the
        label of the footnote that it anchors and extract its label. Then search
        for the string '[label]' on the line noting its start/end positions when
        located.

        Returns:
            a tuple containing the new hilite start/end positions of the anchor.
        """
        assert _the_footnote_checker is not None
        fn_records = _the_footnote_checker.get_fn_records()
        # Get FN record that is 'anchored' by this anchor record.
        fn_record = fn_records[an_record.fn_index]
        # Extract the label text from '[Footnote label: ...]'.
        fn_line_text = fn_record.text
        fn_label_start = 10
        fn_label_end = fn_line_text.find(":")
        fn_label = fn_line_text[fn_label_start:fn_label_end]
        # Now find '[label]' on the anchor line and note its start/end positions.
        # Note that there maybe more than one footnote anchor on a line.
        an_start = an_line_text.find(f"[{fn_label}]")
        an_end = an_start + len(f"[{fn_label}]")
        return an_start, an_end

    def alpha(self, label: int) -> str:
        """Converts given footnote number to alphabetic form:
        A,B,...Z,AA,AB,...AZ,BA,BB,...ZZ,AAA,AAB,...ZZZ
        Wraps back to AAA,AAB,etc., if >= 18728 (26^3+26^2+26) footnotes
        """

        label -= 1
        _single = label % 26
        _double = int((label - 26) / 26) % 26
        _triple = int((label - 26 - 676) / 676) % 26
        #
        single_ch = chr(65 + _single)
        double_ch = (chr(65 + _double)) if label >= 26 else ""
        triple_ch = (chr(65 + _triple)) if label >= (676 + 26) else ""
        return triple_ch + double_ch + single_ch

    def set_anchor(self) -> None:
        """Insert anchor using label of selected footnote."""
        assert _the_footnote_checker is not None
        fn_records = _the_footnote_checker.get_fn_records()
        insert_index = maintext().get_insert_index().index()
        # Get label from selected FN.
        fn_record = fn_records[self.get_selected_fn_index()]
        fn_line_text = fn_record.text
        fn_label_start = 10
        fn_label_end = fn_line_text.find(":")
        fn_label = fn_line_text[fn_label_start:fn_label_end]
        maintext().insert(f"{insert_index}", f"[{fn_label}]")

    def set_lz_at_cursor(self) -> None:
        """Insert FOOTNOTES: header at cursor."""
        insert_index = maintext().get_insert_index().index()
        # Place FOOTNOTES: header at cursor; normally the header is
        # spaced two lines down from chapter end or end of book.
        maintext().insert(f"{insert_index}", "FOOTNOTES:" + "\n")

    def reindex(self) -> None:
        """Reindex all footnotes using fn_index_style

        Three radio buttons set fn_index_style. It is persistent
        across runs so style chosen last time will be the current
        labelling style until a different radio button clicked.

        fn_index_style values are 'number', 'letter' or 'roman'
        """
        assert _the_footnote_checker is not None

        # Check index style used last time Footnotes Fixup was run or default if first run.
        index_style = self.fn_index_style.get()
        an_records = self.get_an_records()
        fn_records = self.get_fn_records()
        for index in range(1, len(an_records) + 1):
            if index_style == "number":
                label = index
            elif index_style == "roman":
                label = roman.toRoman(index)
                label = label + "."  # type: ignore[operator]
            elif index_style == "letter":
                label = self.alpha(index)  # type: ignore[assignment]
            else:
                # Default
                label = index
            an_record = an_records[index - 1]
            an_line_text = maintext().get(
                f"{an_record.start.index()} linestart",
                f"{an_record.start.index()} lineend",
            )
            hl_start, hl_end = self.get_anchor_hilite_columns(an_record, an_line_text)
            replacement_text = (
                f"{an_line_text[0:hl_start]}[{label}]{an_line_text[hl_end:]}"
            )
            an_start = f"{an_record.start.index()} linestart"
            maintext().delete(an_start, f"{an_start} lineend")
            maintext().insert(an_start, replacement_text)
            #
            fn_record = fn_records[index - 1]
            fn_line_text = fn_record.text
            hl_start = fn_record.hilite_start
            hl_end = fn_record.hilite_end
            fn_line_text = (
                f"{fn_line_text[0:hl_start + 9]}{label}{fn_line_text[hl_end:]}"
            )
            fn_start = f"{fn_record.start.index()} linestart"
            # Replace (first line of) footnote using new label value.
            # maintext().delete(f"{fn_start} linestart", f"{fn_start} +1l linestart")
            # maintext().insert(f"{fn_start} linestart", fn_line_text + "\n")
            maintext().delete(f"{fn_start}", f"{fn_start} lineend")
            maintext().insert(f"{fn_start}", fn_line_text)
        # Re-run the footnote checks and display the reindexed footnote entries.
        footnote_check()

    def get_selected_fn_index(self) -> int:
        """Get the index of the selected footnote.

        Returns:
            Index into self.fn_records array, negative if none selected."""
        assert _the_footnote_checker is not None
        cur_idx = self.checker_dialog.current_entry_index()
        if cur_idx is None:
            return -1
        text_range = self.checker_dialog.entries[cur_idx].text_range
        assert text_range is not None
        fn_start = text_range.start
        fn_records = _the_footnote_checker.get_fn_records()
        for fn_index, fn_record in enumerate(fn_records):
            if fn_record.start == fn_start:
                return fn_index
        return -1

    def define_buttons(self) -> None:
        """Helper function to create dialog window for run_check."""
        assert _the_footnote_checker is not None

        frame = ttk.Frame(self.checker_dialog.header_frame)
        frame.grid(column=0, row=1, sticky="NSEW")
        fixit_frame = ttk.LabelFrame(frame, text="Fixing Footnotes", padding=10)
        fixit_frame.grid(column=0, row=0, sticky="NSEW")
        join_button = ttk.Button(
            fixit_frame,
            text="Join Selected FN to Previous",
            width=28,
            command=_the_footnote_checker.join_to_previous,
        )
        fixit_frame.grid_columnconfigure(0, weight=0)
        join_button.grid(column=0, row=0, sticky="W")
        anchor_button = ttk.Button(
            fixit_frame,
            text="Set Anchor for Selected FN",
            width=28,
            command=_the_footnote_checker.set_anchor,
        )
        fixit_frame.grid_columnconfigure(1, weight=1)
        anchor_button.grid(column=1, row=0, sticky="E")

        # Reindexing
        reindex_frame = ttk.LabelFrame(frame, text="Reindexing Footnotes", padding=10)
        reindex_frame.grid(column=0, row=2, sticky="NSEW")
        all_to_num = ttk.Radiobutton(
            reindex_frame,
            text="All to Number",
            variable=self.fn_index_style,
            value=FootnoteIndexStyle.NUMBER,
            width=14,
            takefocus=False,
        )
        reindex_frame.grid_columnconfigure(0, weight=1)
        all_to_num.grid(column=0, row=0, sticky="NS")
        all_to_let = ttk.Radiobutton(
            reindex_frame,
            text="All to Letter",
            width=14,
            variable=self.fn_index_style,
            value=FootnoteIndexStyle.LETTER,
            takefocus=False,
        )
        reindex_frame.grid_columnconfigure(1, weight=1)
        all_to_let.grid(column=1, row=0, sticky="NS")
        all_to_rom = ttk.Radiobutton(
            reindex_frame,
            text="All to Roman",
            width=14,
            variable=self.fn_index_style,
            value=FootnoteIndexStyle.ROMAN,
            takefocus=False,
        )
        reindex_frame.grid_columnconfigure(2, weight=1)
        all_to_rom.grid(column=2, row=0, sticky="NS")
        reindex_button = ttk.Button(
            reindex_frame,
            text="Reindex",
            width=28,
            command=self.reindex,
        )
        reindex_frame.grid_columnconfigure(1, weight=1)
        reindex_button.grid(column=1, row=2, sticky="NS")

        # Landing zones
        lz_frame = ttk.LabelFrame(
            frame, text="Moving Footnotes and Landing Zones", padding=10
        )
        lz_frame.grid(column=0, row=3, sticky="NSEW")
        # Row 0
        lz_set_at_cursor_button = ttk.Button(
            lz_frame,
            text="Set LZ @ Cursor",
            width=28,
            command=_the_footnote_checker.set_lz_at_cursor,
        )
        lz_frame.grid_columnconfigure(0, weight=1)
        lz_set_at_cursor_button.grid(column=0, row=0, sticky="NSEW")
        #
        lz_set_at_chapter_button = ttk.Button(
            lz_frame,
            text="Autoset Chap. LZ",
            width=28,
            command=_the_footnote_checker.autoset_chapter_lz,
        )
        lz_frame.grid_columnconfigure(1, weight=1)
        lz_set_at_chapter_button.grid(column=1, row=0, sticky="NSEW")
        #
        lz_set_at_end_button = ttk.Button(
            lz_frame,
            text="Autoset End LZ",
            width=28,
            command=_the_footnote_checker.autoset_end_lz,
        )
        lz_frame.grid_columnconfigure(2, weight=1)
        lz_set_at_end_button.grid(column=2, row=0, sticky="NSEW")
        # Row 1
        move_to_lz_button = ttk.Button(
            lz_frame,
            text="Move FNs to Landing Zone(s)",
            width=28,
            command=_the_footnote_checker.move_footnotes_to_lz,
        )
        lz_frame.grid_columnconfigure(0, weight=0)
        move_to_lz_button.grid(column=0, row=1, sticky="W")
        #
        move_to_para_button = ttk.Button(
            lz_frame,
            text="Move FNs to Paragraphs",
            width=28,
            command=_the_footnote_checker.move_footnotes_to_paragraphs,
        )
        lz_frame.grid_columnconfigure(2, weight=1)
        move_to_para_button.grid(column=2, row=1, sticky="E")

        # Tidying the footnotes
        lz_frame = ttk.LabelFrame(frame, text="Tidying Footnotes", padding=10)
        lz_frame.grid(column=0, row=4, sticky="NSEW")
        fn_tidy_button = ttk.Button(
            lz_frame,
            text="Tidy Footnotes",
            width=28,
            command=_the_footnote_checker.tidy_footnotes,
        )
        lz_frame.grid_columnconfigure(0, weight=1)
        fn_tidy_button.grid(column=0, row=2, sticky="NS")
        if self.fn_check_errors:
            reindex_button.config(state="disable")
            lz_set_at_cursor_button.config(state="disable")
            lz_set_at_chapter_button.config(state="disable")
            lz_set_at_end_button.config(state="disable")
            move_to_lz_button.config(state="disable")
            move_to_para_button.config(state="disable")
        else:
            reindex_button.config(state="normal")
            lz_set_at_cursor_button.config(state="normal")
            lz_set_at_chapter_button.config(state="normal")
            lz_set_at_end_button.config(state="normal")
            move_to_lz_button.config(state="normal")
            move_to_para_button.config(state="normal")
        if self.fns_have_been_moved:
            join_button.config(state="disable")
            anchor_button.config(state="disable")
            reindex_button.config(state="disable")
            lz_set_at_cursor_button.config(state="disable")
            lz_set_at_chapter_button.config(state="disable")
            lz_set_at_end_button.config(state="disable")
            move_to_lz_button.config(state="disable")
            move_to_para_button.config(state="disable")
        else:
            join_button.config(state="normal")
            anchor_button.config(state="normal")
            reindex_button.config(state="normal")
            lz_set_at_cursor_button.config(state="normal")
            lz_set_at_chapter_button.config(state="normal")
            lz_set_at_end_button.config(state="normal")
            move_to_lz_button.config(state="normal")
            move_to_para_button.config(state="normal")

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
                    f"{start.index()}+{beg_match.count + 1}c wordend"
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
                beg_match.count + 1 : colon_pos.col - beg_match.rowcol.col
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
            an_index = None if anchor_match is None else len(self.an_records)
            fnr = FootnoteRecord(
                fn_line, start, end_point, 1, colon_pos.col - start.col, an_index
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
        show_suspects_only=True,
    )

    if _the_footnote_checker is None:
        _the_footnote_checker = FootnoteChecker(checker_dialog)
    elif not _the_footnote_checker.checker_dialog.winfo_exists():
        _the_footnote_checker.checker_dialog = checker_dialog
    _the_footnote_checker.fns_have_been_moved = False

    ToolTip(
        checker_dialog.text,
        "\n".join(
            [
                "Left click: Select & find footnote",
                "Right click: Remove item from list",
                "Shift-Right click: Remove all matching items",
            ]
        ),
        use_pointer_pos=True,
    )

    _the_footnote_checker.define_buttons()
    _the_footnote_checker.run_check()
    display_footnote_entries()


def check_fn_string(fn_record: FootnoteRecord) -> str:
    """Identify common footnote typos in a footnote record.

    NB Only looks at the start of (the first line of) the footnote.

    Args:
        footnote_record: record of a footnote in the file.

    Returns:
        str: 'OK' if FN conformant else an error description.
    """
    # GG1 fixes the next two typos but GG2 just flags them as for any other error.
    if fn_record.text[0:2] == "[ ":
        return "SPACE ERROR"
    if fn_record.text[0:2] == "[f":
        return "CASE ERROR"
    fn_start = fn_record.start
    if (
        fn_record.text[0:11] == "[Footnote: "
        and maintext().get(f"{fn_start.index()}-1c", fn_start.index()) != "*"
    ):
        return "MISSING LABEL"
    # Missing colon?
    pattern = r"\*?\[Footnote [^:\s]{1,9}\s"
    if re.search(pattern, fn_record.text[0:16]):
        return "MISSING COLON"
    # A conformant out-of-line FN starts '[Footnote str: text'.
    # 'str' can be a single symbol, up to three letters, up
    # to four Arabic numerals, or up to eight Roman numerals
    # plus a '.' (essentially between 1-100).
    #
    # Try numeric label first, then letter label, then a single symbol
    # and only look for a label of Roman numerals if the other label
    # styles don't match.
    pattern = r"\*?\[Footnote \p{N}{1,4}:\s|\*?\[Footnote \p{L}{1,3}:\s|\*?\[Footnote [^\p{N}|\p{L}]{1}:\s|\*?\[Footnote [IVXLCDMivxlcdm]{1,8}\.:\s"
    if not re.search(pattern, fn_record.text[0:22]):
        return "INVALID LABEL"
    return "OK"


def display_footnote_entries() -> None:
    """(Re-)display the footnotes in the checker dialog."""
    assert _the_footnote_checker is not None
    checker_dialog = _the_footnote_checker.checker_dialog
    checker_dialog.reset()
    fn_records = _the_footnote_checker.get_fn_records()
    an_records = _the_footnote_checker.get_an_records()
    # Boolean to determine if buttons are to be set disabled or normal.
    _the_footnote_checker.fn_check_errors = False
    for fn_index, fn_record in enumerate(fn_records):
        # Flag common footnote typos. All non-conformant FNs
        # must be fixed before reindexing, etc., can be done.
        error_prefix = check_fn_string(fn_record)
        # Value of error_prefix is either 'OK' or an error description;
        # e.g. 'MISSING LABEL, 'MISSING COLON', etc.
        if error_prefix == "OK":
            # The footnote string is conformant now consider its context; does
            # it have an anchor; is it a continuation footnote; is it out of
            # sequence with its anchor, etc.
            error_prefix = ""
            if fn_record.an_index is None:
                fn_start = fn_record.start
                if maintext().get(f"{fn_start.index()}-1c", fn_start.index()) == "*":
                    error_prefix = "CONTINUATION: "
                else:
                    error_prefix = "NO ANCHOR: "
            else:
                an_record = an_records[fn_record.an_index]
                # Check that no other footnote has the same anchor as this one
                for fni2, fn2 in enumerate(fn_records):
                    if fn2.an_index is None:
                        continue
                    an2 = an_records[fn2.an_index]
                    if fn_index != fni2 and an_record.start == an2.start:
                        error_prefix = "SAME ANCHOR: "
                        break
                # Check anchor of previous footnote and this one are in order (footnotes are always in order)
                if (
                    fn_index > 0
                    and fn_record.an_index is not None
                    and fn_records[fn_index - 1].an_index is not None
                ):
                    an_prev = an_records[fn_records[fn_index - 1].an_index]  # type: ignore[index]
                    if an_prev.start.row > an_record.start.row or (
                        an_prev.start.row == an_record.start.row
                        and an_prev.start.col > an_record.start.col
                    ):
                        error_prefix += "SEQUENCE: "
                # Check anchor of next footnote and this one are in order (footnotes are always in order)
                if (
                    "SEQUENCE: " not in error_prefix
                    and fn_index < len(fn_records) - 1
                    and fn_record.an_index is not None
                    and fn_records[fn_index + 1].an_index is not None
                ):
                    an_next = an_records[fn_records[fn_index + 1].an_index]  # type: ignore[index]
                    if an_next.start.row < an_record.start.row or (
                        an_next.start.row == an_record.start.row
                        and an_next.start.col < an_record.start.col
                    ):
                        error_prefix += "SEQUENCE: "
        if error_prefix != "":
            _the_footnote_checker.fn_check_errors = True
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
    _the_footnote_checker.define_buttons()
    checker_dialog.display_entries()
