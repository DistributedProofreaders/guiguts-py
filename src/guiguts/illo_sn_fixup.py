"""Illustration (Illo) or Sidenote (SN) checking, fixing and tidying functionality"""

import logging
from tkinter import ttk
from typing import Optional

from guiguts.checkers import CheckerDialog
from guiguts.maintext import maintext
from guiguts.misc_tools import tool_save
from guiguts.utilities import (
    IndexRowCol,
    IndexRange,
)
from guiguts.widgets import ToolTip

logger = logging.getLogger(__package__)

_the_illosn_checker: Optional["IlloSNChecker"] = None  # pylint: disable=invalid-name


class IlloSNRecord:
    """Record of Illo or SN in file."""

    def __init__(
        self,
        text: str,
        start: IndexRowCol,
        end: IndexRowCol,
        hilite_start: int,
        hilite_end: int,
    ) -> None:
        """Initialize IlloSNRecord.

        Args:
            text - text of the SN or Illo (if caption present).
            start - start rowcol of SN or Illo in file.
            end - end rowcol of SN or Illon in file.
            hilite_start - start column of highlighting in text.
            hilite_end - end column of highlighting in text.
        """
        self.text = text
        self.start = start
        self.end = end
        self.hilite_start = hilite_start
        self.hilite_end = hilite_end


class SelectedIlloSNRecord:
    """Record of start & end line numbers (e.g. '5.0') for selected Illo or SN record"""

    def __init__(self, first: str, last: str) -> None:
        self.first_line_num = first
        self.last_line_num = last


class IlloSNChecker:
    """Find, check & record Illos or SNs."""

    def __init__(self, checker_dialog: CheckerDialog) -> None:
        """Initialize IlloSNChecker."""
        self.illosn_records: list[IlloSNRecord] = []
        self.checker_dialog: CheckerDialog = checker_dialog

    def reset(self) -> None:
        """Reset IlloSNChecker."""
        self.illosn_records = []

    def get_illosn_records(self) -> list[IlloSNRecord]:
        """Return the list of Illo or SN records."""
        return self.illosn_records

    def get_selected_illosn_record(
        self, selected_illosn_index: int
    ) -> SelectedIlloSNRecord:
        """Get line number indexes of the selected Illo or SN record.

        The returned indexes will be the same if selected record is not multi-line;
        e.g. [Illustration]

        Returns:
            Line number index of first line of the record; e.g. '5.0'
            Line number index of last line of the record; e.g. '6.14'
        """
        assert _the_illosn_checker is not None
        # We built a list of Illo or SN records with start/end RowCol details.
        records = _the_illosn_checker.get_illosn_records()
        # Get record of the selected tag
        selected_record = records[selected_illosn_index]
        # Get line number index of the first line of the selected record.
        selected_record_start = selected_record.start.index()
        first_line_num = maintext().index(f"{selected_record_start} linestart")
        # Get line number index of the last line of the selected record.
        # If not a multi-line record then this will be same index as above.
        selected_record_end = selected_record.end.index()
        last_line_num = maintext().index(f"{selected_record_end} linestart")
        rec = SelectedIlloSNRecord(first_line_num, last_line_num)
        return rec

    def get_selected_illosn_index(self) -> int:
        """Get the index of the selected Illo or SN record.

        Returns:
            Index into self.illosn_records array, negative if none selected."""
        assert _the_illosn_checker is not None
        cur_idx = self.checker_dialog.current_entry_index()
        if cur_idx is None:
            return -1
        text_range = self.checker_dialog.entries[cur_idx].text_range
        assert text_range is not None
        illosn_start = text_range.start
        illosn_records = _the_illosn_checker.get_illosn_records()
        for illosn_index, illosn_record in enumerate(illosn_records):
            if illosn_record.start == illosn_start:
                return illosn_index
        return -1

    def run_check(self, tag_type: str) -> None:
        """Run the initial Illustration or Sidenote records check."""
        self.reset()
        search_range = IndexRange(maintext().start(), maintext().end())
        match_regex = (
            r"\[ *illustration" if tag_type == "Illustration" else r"\[ *sidenote"
        )
        # Loop to find all tags of the type specified by argument 'tag_type'.
        # Allow some flexibility in spacing after the opening "[" of the tag.
        while begin_illosn_match := maintext().find_match(
            match_regex, search_range, regexp=True, nocase=True
        ):
            start = begin_illosn_match.rowcol
            # Find colon position, or use end of the required word (i.e. tag_type).
            colon_match = maintext().find_match(
                ":", IndexRange(start, maintext().rowcol(f"{start.row}.end"))
            )
            if colon_match is None:
                colon_pos = maintext().rowcol(
                    f"{start.index()}+{begin_illosn_match.count}c"
                )
            else:
                colon_pos = colon_match.rowcol
            end_point = colon_pos
            # Find closing square bracket - allow open/close bracket within an
            # Illustration or Sidenote record.
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

            # If closing [ not found, use end of line.
            if end_match is None:
                end_point = maintext().rowcol(f"{start.row}.end")
            # Get text of Sidenote
            illosn_line = maintext().get(start.index(), f"{start.row}.end")
            # Create Illo or SN record and add it to the list.
            illosn_rec = IlloSNRecord(
                illosn_line, start, end_point, 1, colon_pos.col - start.col
            )
            self.illosn_records.append(illosn_rec)
            search_range = IndexRange(end_point, maintext().end())

    def update_after_move(self, tag_type: str, selected_illosn_index: int) -> None:
        """Update Illo or SN records list, update dialog and reselect tag just moved

        Args:
            tag_type: either "Illustration" or "Sidenote"
        """
        # Update illosn_records list
        self.run_check(tag_type)
        # Update dialog
        display_illosn_entries()
        # Select again the tag we have just moved so it is highlighted.
        self.checker_dialog.select_entry_by_index(selected_illosn_index)

    def delete_illosn_record_from_file(self, selected: SelectedIlloSNRecord) -> None:
        """Delete the selected Illo/SN record from its original location in the file.

        Do this from the start of (its first) line so that any prefixing '*' is
        included in the deletion. There are 3 cases to consider:
        1. The tag is immediately above a bottom of page Page Marker. Delete the
           tag line(s) and the preceding blank line.
        2. The tag is immediately below a bottom of page Page Marker. Delete the
           tag line(s) and the following blank line.
        3. The tag is mid-page so preceded and followed by a blank line. Delete
           the tag line(s) and the following blank line but leave the preceding
           one.
        """
        # Line before the (first record of the) Illo or SN record.
        prev_line_num = maintext().index(f"{selected.first_line_num}-1l")
        prev_line_txt = maintext().get(prev_line_num, f"{prev_line_num} lineend")
        # Line after the (last record of the) Illo or SN record.
        next_line_num = maintext().index(f"{selected.last_line_num}+1l")
        next_line_txt = maintext().get(next_line_num, f"{next_line_num} lineend")
        # Assume it's a mid-page Illo or SN record unless found otherwise. This is case 3.
        if prev_line_txt != "":
            # Check this line. It's immediately above the (first line of the) Illo or SN record.
            if prev_line_txt[0:10] == "-----File:" and next_line_txt == "":
                # Case 2
                first_delete_line_num = maintext().index(f"{selected.first_line_num}")
                last_delete_line_num = maintext().index(
                    f"{selected.last_line_num}+2l linestart"
                )
                maintext().delete(first_delete_line_num, last_delete_line_num)
                return
        if next_line_txt != "":
            if next_line_txt[:10] == "-----File:" and prev_line_txt == "":
                # Case 1
                first_delete_line_num = maintext().index(
                    f"{selected.first_line_num}-1l"
                )
                last_delete_line_num = maintext().index(
                    f"{selected.last_line_num}+1l linestart"
                )
                maintext().delete(first_delete_line_num, last_delete_line_num)
                return
        if prev_line_txt == "" and next_line_txt == "":
            # Case 3
            first_delete_line_num = maintext().index(f"{selected.first_line_num}")
            last_delete_line_num = maintext().index(
                f"{selected.last_line_num}+2l linestart"
            )
            maintext().delete(first_delete_line_num, last_delete_line_num)
            return
        # We shouldn't get here. If we do just delete the Illo or SN record(s) and ignore any
        # surrounding lines.
        maintext().delete(selected.first_line_num, f"{selected.last_line_num} lineend")
        return

    def move_selection_up(self, tag_type: str) -> None:
        """Move selected Illo/SN tag up towards the start of the file.

        We won't move a tag past another tag of the same type.

        Args:
            tag_type: a string which is either "Sidenote" or "Illustration".
        """
        assert _the_illosn_checker is not None
        selected_illosn_index = self.get_selected_illosn_index()
        if selected_illosn_index < 0:
            return  # No selection
        selected = self.get_selected_illosn_record(selected_illosn_index)
        # Look for a suitable blank line. Start at line immediately above the (first line of
        # the) selected Illo or SN record. NB We may not be able to move the record at all if
        # it means skipping over another tag of the same type.
        line_num = maintext().index(f"{selected.first_line_num}-1l")
        while (
            line_num != "0.0"
        ):  # NB That index does not exist but see at end of while loop.
            # What is on this line?
            line_txt = maintext().get(line_num, f"{line_num} lineend")
            # Is it a tag of the same type as the selected one?
            if tag_type == "Sidenote" and (
                line_txt[0:10] == "[Sidenote:" or line_txt[0:11] == "*[Sidenote:"
            ):
                # Can't move selected Sidenote above another Sidenote.
                return
            if tag_type == "Illustration" and (
                line_txt[0:14] == "[Illustration]"
                or line_txt[0:14] == "[Illustration:"
                or line_txt[0:15] == "*[Illustration]"
                or line_txt[0:15] == "*[Illustration:"
            ):
                # Can't move selected Illustration above another Illustration.
                return
            # No point in inserting the selected tag above the blank line in the situation below
            # as it will become the same place after the deletion of the Illo or SN record lines
            # from their original position.
            #
            # BL
            # ...
            # BL                     <- blank line we are at.
            # [Sidenote: Some text.] <- (first line of) the selected tag.
            # BL
            # ...
            #
            # If we are not in this situation, insert selected tag above the blank line we are at.
            # Otherwise look for next blank line above that one.
            if (
                line_txt == ""
                and not maintext().index(f"{line_num}+1l linestart")
                == selected.first_line_num
            ):
                # We can insert the selected tag above this blank line.
                # Copy the lines of the Illo or SN record to be moved. Don't include the
                # prefixing "*" if present.
                the_selected_record_lines = maintext().get(
                    selected.first_line_num, f"{selected.last_line_num} lineend"
                )
                if the_selected_record_lines[0:1] == "*":
                    the_selected_record_lines = the_selected_record_lines[1:]
                # Delete the selected tag from its current position in the file.
                self.delete_illosn_record_from_file(selected)
                # Insert copied lines above the blank line we are at and prefix it with a blank line.
                maintext().insert(
                    maintext().index(f"{line_num}"),
                    "\n" + the_selected_record_lines + "\n",
                )
                self.update_after_move(tag_type, selected_illosn_index)
                return
            # If we have reached the top of the file, and it is not a blank line, then we
            # have to 'create' non-existent line number '0.0' to terminate the while-loop.
            if line_num == "1.0":
                line_num = "0.0"
            else:
                # Decrement line_num normally.
                line_num = maintext().index(f"{line_num}-1l")
        return

    def move_selection_down(self, tag_type: str) -> None:
        """Move selected Illo/SN tag down towards the end of the file.

        We won't move a tag past another tag of the same type.

        Args:
            tag_type: a string which is either "Sidenote" or "Illustration".
        """
        assert _the_illosn_checker is not None
        selected_illosn_index = self.get_selected_illosn_index()
        if selected_illosn_index < 0:
            return  # No selection
        selected = self.get_selected_illosn_record(selected_illosn_index)
        # Look for a suitable blank line. Start at line immediately below the (last line of
        # the) selected Illo or SN record. NB We may not be able to move the record at all if
        # it means skipping over another tag of the same type.
        line_num = maintext().index(f"{selected.last_line_num}+1l")
        # Set end of loop criteria.
        file_end = maintext().end().index()
        file_end_line_num_plus_1 = maintext().index(f"{file_end}+1l linestart")
        while line_num != file_end_line_num_plus_1:
            # What is on this line?
            line_txt = maintext().get(line_num, f"{line_num} lineend")
            # Is it a tag of the same type as the selected one?
            if tag_type == "Sidenote" and (
                line_txt[0:10] == "[Sidenote:" or line_txt[0:11] == "*[Sidenote:"
            ):
                # Can't move selected Sidenote above another Sidenote.
                return
            if tag_type == "Illustration" and (
                line_txt[0:14] == "[Illustration]"
                or line_txt[0:14] == "[Illustration:"
                or line_txt[0:15] == "*[Illustration]"
                or line_txt[0:15] == "*[Illustration:"
            ):
                # Can't move selected Illustration above another Illustration.
                return
            # No point in inserting the selected tag below the blank line in the situation below
            # as it will become the same place after the deletion of the Illo or SN record lines
            # from their original position.
            #
            # ...
            # BL
            # [Sidenote: Some text.] <- (last line of) the selected tag.
            # BL                     <- blank line we are at.
            # ...
            # BL
            #
            # If we are not in this situation, insert selected tag below the blank line we are at.
            # Otherwise look for next blank line below that one.
            if (
                line_txt == ""
                and not maintext().index(f"{line_num}-1l linestart")
                == selected.last_line_num
            ):
                # We can insert the selected tag below this blank line.
                # Copy the lines of the Illo or SN record to be moved. Don't include the
                # prefixing "*" if present.
                the_selected_record_lines = maintext().get(
                    selected.first_line_num, f"{selected.last_line_num} lineend"
                )
                if the_selected_record_lines[0:1] == "*":
                    the_selected_record_lines = the_selected_record_lines[1:]
                # Insert copied lines below the blank line we are at and suffix it with a blank line.
                maintext().insert(
                    maintext().index(f"{line_num} lineend"),
                    "\n" + the_selected_record_lines + "\n",
                )
                # Delete the selected tag from its current position in the file.
                self.delete_illosn_record_from_file(selected)
                self.update_after_move(tag_type, selected_illosn_index)
                return
            # Increment line_num.
            line_num = maintext().index(f"{line_num}+1l")
        return


def illosn_check(tag_type: str) -> None:
    """Check Illustration or Sidenote tags in the currently loaded file.

    Args:
        tag_type: which tag to check for - "Illustration" or "Sidenote"
    """
    global _the_illosn_checker

    if not tool_save():
        return
    checker_dialog = CheckerDialog.show_dialog(
        f"{tag_type} Check Results",
        rerun_command=lambda: illosn_check(tag_type),
        show_suspects_only=True,
    )
    if _the_illosn_checker is None:
        _the_illosn_checker = IlloSNChecker(checker_dialog)
    elif not _the_illosn_checker.checker_dialog.winfo_exists():
        _the_illosn_checker.checker_dialog = checker_dialog

    ToolTip(
        checker_dialog.text,
        "\n".join(
            [
                f"Left click: Select & find {tag_type} tag",
                "Right click: Remove item from list",
                "Shift-Right click: Remove all matching items",
            ]
        ),
        use_pointer_pos=True,
    )

    frame = ttk.Frame(checker_dialog.header_frame)
    frame.grid(column=0, row=1, sticky="NSEW")
    ttk.Button(
        frame,
        text="Move selection UP",
        command=lambda: _the_illosn_checker.move_selection_up(tag_type),
    ).grid(column=0, row=0, sticky="NSW")
    ttk.Button(
        frame,
        text="Move selection DOWN",
        command=lambda: _the_illosn_checker.move_selection_down(tag_type),
    ).grid(column=1, row=0, sticky="NSW")
    _the_illosn_checker.run_check(tag_type)
    display_illosn_entries()


def display_illosn_entries() -> None:
    """(Re-)display the requested Illo/SN tag types in the checker dialog."""
    assert _the_illosn_checker is not None
    checker_dialog = _the_illosn_checker.checker_dialog
    checker_dialog.reset()
    illosn_records = _the_illosn_checker.get_illosn_records()
    for illosn_record in illosn_records:
        error_prefix = ""
        illosn_start = illosn_record.start
        if maintext().get(f"{illosn_start.index()}-1c", illosn_start.index()) == "*":
            error_prefix = "MIDPARAGRAPH: "
        checker_dialog.add_entry(
            illosn_record.text,
            IndexRange(illosn_record.start, illosn_record.end),
            illosn_record.hilite_start,
            illosn_record.hilite_end,
            error_prefix=error_prefix,
        )
    checker_dialog.display_entries()
