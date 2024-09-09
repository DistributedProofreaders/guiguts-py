"""Footnote checking, fixing and tidying functionality"""

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
    """Record of illo or sidenote in file."""

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
            text - text of the sidenote or illustration (if caption present).
            start - Start rowcol of sidenote/illustration in file.
            end - End rowcol of sidenote/illustration in file.
            hilite_start - Start column of highlighting in text.
            hilite_end - End column of highlighting in text.
        """
        self.text = text
        self.start = start
        self.end = end
        self.hilite_start = hilite_start
        self.hilite_end = hilite_end


class IlloSNChecker:
    """Find, check & record footnotes."""

    def __init__(self, checker_dialog: CheckerDialog) -> None:
        """Initialize illosn checker."""
        self.illosn_records: list[IlloSNRecord] = []
        self.checker_dialog: CheckerDialog = checker_dialog

    def reset(self) -> None:
        """Reset IlloSNChecker."""
        self.illosn_records = []

    def get_illosn_records(self) -> list[IlloSNRecord]:
        """Return the list of Illustration or Sidenote records."""
        return self.illosn_records

    def get_selected_illosn_index(self) -> int:
        """Get the index of the selected footnote.

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
        """Run the initial Illustration or Sidenote tag check."""
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
                    f"{start.index()}+{begin_illosn_match.count + 1}c wordend"
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

            # If closing [ not found, use end of line
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

    def action_choices_when_moving_up(
        self, line_num: str, selected_illosn_index: int
    ) -> str:
        """Determine whether we can move selected tag above this blank line.

        Args:
            line_num: line number start index of a blank line; e.g. '5.0'
            selected_illosn_index: index of tag in list of Illo or SN details

        Returns:
            A string describing the action available at this blank line.
        """
        assert _the_illosn_checker is not None
        # The list of Illo or SN records with start/end, etc., details.
        illosn_records = _the_illosn_checker.get_illosn_records()
        # Get line number of the (first line) of the selected tag.
        selected_illosn_record = illosn_records[selected_illosn_index]
        selected_illosn_record_start = selected_illosn_record.start.index()
        selected_tag_line_num = maintext().index(
            f"{selected_illosn_record_start} linestart"
        )

        if selected_illosn_index == 0:
            # No further tags of the selected_tag_type above this blank line so
            # we can move selected tag here unless it's the blank line immediately
            # above the selected tag.
            # Look at record below the blank line and see if it's the selected tag.
            if maintext().index(f"{line_num}+1l linestart") == selected_tag_line_num:
                # The line below the blank line is the selected tag. We can't move it
                # here but can find the next blank line above and move the selected
                # tag there.
                return "find-next-blank-line"
            # The line below the blank line is not the selected tag.
            return "can-move-selected-tag-here"
        # At least one tag of the selected_tag_type is above the blank line we are
        # positioned at. Get the details of the first of these tags.
        above_illosn_index = selected_illosn_index - 1
        above_illosn_record = illosn_records[above_illosn_index]
        # Get the line number index of the *start* of the line on which the *last* line
        # of this tag is located. We assume it's a multi-line tag but this also works
        # for a single-line tag.
        above_illosn_record_end = above_illosn_record.end.index()
        above_tag_last_line_start = maintext().index(
            f"{above_illosn_record_end} linestart"
        )
        # There is one case where we cannot move up the selected tag:
        # ...
        # BL
        # [Sidenote: some text.] <- (last line of) the tag above the blank line
        # BL                     <- blank line we are at
        # [Sidenote: more text.] <- selected tag that we cannot move.
        # BL
        # ...
        # Check for this...
        if (
            maintext().index(f"{line_num}-1l linestart") == above_tag_last_line_start
            and maintext().index(f"{line_num}+1l linestart") == selected_tag_line_num
        ):
            return "cannot-move-selected-tag"
        # There is a related case where trying to move the tag up has the effect of
        # leaving it in the same place. This is when we are at the blank line immediately
        # above the selected tag as illustrated below. Note we are at the same place in
        # the file as in the case above but the lines above the blank line are different.
        # The action here is to find the next blank line above the one we are currently
        # on. Example:
        # ...
        # Bl                          <- next blank line above
        # ...
        # Illo tag/Page Marker/Last line of a paragraph
        # BL                          <- blank line we are at
        # [Sidenote: some text.]      <- selected tag we want to move
        # ...
        # Get the line number of the file line immediately below the blank line.
        line_num_below = maintext().index(f"{line_num}+1l")
        # We already have the line number of (the first line of) the selected tag.
        if line_num_below == selected_tag_line_num:
            return "find-next-blank-line"
        # If we get here we are at a blank line that is safe to move the selected tag to.
        return "can-move-selected-tag-here"

    def action_choices_when_moving_down(
        self, line_num: str, selected_illosn_index: int
    ) -> str:
        """Determine whether we can move selected tag below this blank line.

        Args:
            line_num: line number start index of a blank line; e.g. '5.0'
            selected_illosn_index: index of tag in list of Illo or SN details

        Returns:
            A string describing the action available at this blank line.
        """
        assert _the_illosn_checker is not None
        # The list of Illo or SN records with start/end, etc., details.
        illosn_records = _the_illosn_checker.get_illosn_records()
        # Get line number of the (first line) of the selected tag.
        selected_illosn_record = illosn_records[selected_illosn_index]
        selected_illosn_record_end = selected_illosn_record.end.index()
        selected_tag_line_num = maintext().index(
            f"{selected_illosn_record_end} linestart"
        )

        # Is the selected tag the last one in the list?
        if selected_illosn_index == len(illosn_records) - 1:
            # It is so we know there can be no further tags of the selected_tag_type below
            # this blank line so we can move selected tag here unless it's the blank line
            # immediately below the selected tag.
            if maintext().index(f"{line_num}-1l linestart") == selected_tag_line_num:
                # The line above the blank line is the selected tag. We can't move it
                # here (it's the same place!) but can find the next blank line below
                # and move the selected tag there.
                return "find-next-blank-line"
            # The line above the blank line is not the selected tag.
            return "can-move-selected-tag-here"
        # At least one tag of the selected_tag_type is below the blank line we are
        # positioned at. Get the details of the first of these tags.
        below_illosn_index = selected_illosn_index + 1
        below_illosn_record = illosn_records[below_illosn_index]
        # Get the line number index of (the first line of) this tag.
        below_illosn_record_start = below_illosn_record.start.index()
        below_tag_first_line_start = maintext().index(
            f"{below_illosn_record_start} linestart"
        )
        # Get the line number index of the *start* of the line on which the *last* line of the
        # selected tag sits. We assume it's a multi-line tag but this also works for a single-line
        # tag.
        selected_tag_end_line_num = maintext().index(
            f"{selected_illosn_record_end} linestart"
        )
        # There is one case where we cannot move down the selected tag:
        # ...
        # BL
        # [Sidenote: some text.] <- selected tag that we cannot move.
        # BL                     <- blank line we are at
        # [Sidenote: more text.] <- (first line of) the tag below the blank line.
        # BL
        # ...
        # Check for this...
        if (
            maintext().index(f"{line_num}+1l linestart") == below_tag_first_line_start
            and maintext().index(f"{line_num}-1l linestart")
            == selected_tag_end_line_num
        ):
            return "cannot-move-selected-tag"
        # There is a related case where trying to move the tag down has the effect of
        # leaving it in the same place. This is when we are at the blank line immediately
        # below the selected tag as illustrated below. Note we are at the same place in
        # the file as in the case above but the lines below the blank line are different.
        # The action here is to find the next blank line below the one we are currently
        # on. Example:
        # ...
        # [Sidenote: some text.]      <- selected tag we want to move
        # Bl                          <- blank line we are at
        # Illo tag/Page Marker/Last line of a paragraph
        # ...
        # BL                          <- next blank line below
        # ...
        # Get the line number of the file line immediately above the blank line
        line_num_above = maintext().index(f"{line_num}-1l")
        # We already have the line number of (the last line of) the selected tag.
        if line_num_above == selected_tag_line_num:
            return "find-next-blank-line"
        # If we get here we are at a blank line that is safe to move the selected tag to.
        return "can-move-selected-tag-here"

    def move_selection_up(self, tag_type: str) -> None:
        """Move selected Illo/SN tag towards the start of the file.

           If the selected tag can be moved it is inserted above the first suitable blank
           line that was found. The moved tag is then separated from the preceding line in
           the file by another blank line. This means that every moved tag is repositioned
           with a blank line before it and after it as per the Formatting Guidelines.

           There are some situations where the selected tag cannot be moved - see comments in
           the function 'action_choices_when_moving_up()'.

           When the selected tag is moved, the blank line after it in the file is also removed.

        Args:
            tag_type: a string which is either "Sidenote" or "Illustration".

        """
        assert _the_illosn_checker is not None
        illosn_index = self.get_selected_illosn_index()
        if illosn_index < 0:
            return  # No selection
        # Get details of selected tag.
        illosn_records = _the_illosn_checker.get_illosn_records()
        illosn_record = illosn_records[illosn_index]
        illosn_selected_start = illosn_record.start.index()
        illosn_selected_end = illosn_record.end.index()
        # Get RowCol index of start of selected line; i.e. column value will be '0'.
        line_num = maintext().index(f"{illosn_selected_start} linestart")
        # Save this for later.
        illosn_selected_line_start = line_num
        # Check if selected line is already at start of the file.
        if line_num in ("1.0", "2.0"):
            # A weird file. No sensible place to move Illo/SN tags to.
            return
        # Selected Illo/SN line should be prefixed by a blank line or a page marker
        # and have a blank line after it.
        prev_line_num = maintext().index(f"{line_num}-1l")
        prev_line_txt = maintext().get(prev_line_num, f"{prev_line_num} lineend")
        # Assume the tag is multi-line but logic works for a single line tag too.
        tag_end_line_num = maintext().index(f"{illosn_selected_end} linestart")
        next_line_num = maintext().index(f"{tag_end_line_num}+1l")
        next_line_txt = maintext().get(next_line_num, f"{next_line_num} lineend")
        if (
            not (prev_line_txt == "" or prev_line_txt[:10] == "-----File:")
            or next_line_txt != ""
        ):
            # File not formatted correctly. If we move the selected tag there is a risk
            # of damaging the file by deleting a line that should not be deleted.
            return
        # Find a blank line to which we can move the selected tag. In some circumtances
        # we cannot move the selected tag at all.
        #
        # NB 'while'. If we reach the first line of the file ('1.0') and it is a blank line then
        # we are permitted to move the selected tag above it. The inserted tag will be prefixed
        # by a blank line so the blank line at the start of the file is preserved.
        while line_num != "0.0":
            line_txt = maintext().get(line_num, f"{line_num} lineend")
            if line_txt == "":
                # We're located at a blank line.
                what_to_do = self.action_choices_when_moving_up(line_num, illosn_index)
                if what_to_do == "can-move-selected-tag-here":
                    # We can insert our tag above the blank line (which is at line_num).
                    prev_line_num = maintext().index(f"{line_num}-1l")
                    # NB The 'get' below copies from the selected tag's start; i.e. '[Illustration...'
                    # or '[Sidenote...'. If the tag is prefixed by a '*' that is not included.
                    the_selected_tag_lines = maintext().get(
                        illosn_selected_start, illosn_selected_end
                    )
                    # We have just copied the line(s) of the Illo/SN tag that is to be moved so we
                    # can delete it from the file now. We do this from the start of its (first) line
                    # so that any prefixing '*' is included in the deletion. Also delete the blank
                    # line that should be following the (last line of the) tag.
                    maintext().delete(
                        illosn_selected_line_start,
                        f"{illosn_selected_end}+2l linestart",
                    )
                    # Now insert the copied tag line(s) above the blank line at which we are located
                    # and prefix this with a blank line.
                    if line_num == "1.0":
                        # If the blank line is the first line of the file then the insertion sequence
                        # needs to be modified.
                        maintext().insert(
                            "1.0 linestart", "\n" + the_selected_tag_lines + "\n"
                        )
                    else:
                        maintext().insert(
                            f"{prev_line_num} lineend", "\n\n" + the_selected_tag_lines
                        )
                    self.checker_dialog.remove_entry_current()
                    # Update list of illosn_records (start/end, etc., details of each tag)
                    self.run_check(tag_type)
                    # Update dialog
                    display_illosn_entries()
                    # Select again the tag we have just moved so it is highlighted.
                    self.checker_dialog.select_entry_by_index(illosn_index)
                    return
                if what_to_do == "find-next-blank-line":
                    # Move up a line.
                    line_num = maintext().index(f"{line_num}-1l")
                    continue
                if what_to_do == "cannot-move-selected-tag":
                    # Do nothing in response to request to move selected tag up.
                    return
            # If we have reached the top of the file, and it is not a blank line, then we
            # have to 'create' non-existent line number '0.0' to terminate the while-loop.
            if line_num == "1.0":
                line_num = "0.0"
            else:
                # Decrement line_num normally.
                line_num = maintext().index(f"{line_num}-1l")
        # We may get here if the first line of the file is not a blank line.
        return

    def move_selection_down(self, tag_type: str) -> None:
        """Move selected Illo/SN tag towards the end of the file.

           If the selected tag can be moved it is inserted below the first suitable blank
           line that was found. The moved tag is then separated from the following line in
           the file by another blank line. This means that every moved tag is repositioned
           with a blank line before it and after it as per the Formatting Guidelines.

           There are some situations where the selected tag cannot be moved - see comments in
           the function 'action_choices_when_moving_down()'.

           When the selected tag is moved, the blank line after it in the file is also removed.

        Args:
            tag_type: a string which is either "Sidenote" or "Illustration".

        """
        assert _the_illosn_checker is not None
        illosn_index = self.get_selected_illosn_index()
        if illosn_index < 0:
            return  # No selection
        # Get details of selected tag.
        illosn_records = _the_illosn_checker.get_illosn_records()
        illosn_record = illosn_records[illosn_index]
        illosn_selected_start = illosn_record.start.index()
        illosn_selected_end = illosn_record.end.index()
        # Get RowCol index of start of selected line; i.e. column value will be '0'.
        line_num = maintext().index(f"{illosn_selected_start} linestart")
        # Save this for later.
        illosn_selected_line_start = line_num
        # Selected Illo/SN line should be prefixed by a blank line or a page marker
        # and have a blank line after it.
        prev_line_num = maintext().index(f"{line_num}-1l")
        prev_line_txt = maintext().get(prev_line_num, f"{prev_line_num} lineend")
        # Assume the tag is multi-line but logic works for a single line tag too.
        tag_end_line_num = maintext().index(f"{illosn_selected_end} linestart")
        next_line_num = maintext().index(f"{tag_end_line_num}+1l")
        next_line_txt = maintext().get(next_line_num, f"{next_line_num} lineend")
        if (
            not (prev_line_txt == "" or prev_line_txt[:10] == "-----File:")
            or next_line_txt != ""
        ):
            # File not formatted correctly. If we move the selected tag there is a risk
            # of damaging the file by deleting a line that should not be deleted.
            return
        # Find a blank line to which we can move the selected tag. In some circumtances
        # we cannot move the selected tag at all.
        file_end = maintext().end().index()
        file_end_line_num_plus_1 = maintext().index(f"{file_end}+1l linestart")
        while line_num != file_end_line_num_plus_1:
            line_txt = maintext().get(line_num, f"{line_num} lineend")
            if line_txt == "":
                # We're located at a blank line.
                what_to_do = self.action_choices_when_moving_down(
                    line_num, illosn_index
                )
                if what_to_do == "can-move-selected-tag-here":
                    # We can insert our tag below the blank line (which is at line_num).
                    next_line_num = maintext().index(f"{line_num}+1l")
                    # NB The 'get' below copies from the selected tag's start; i.e. '[Illustration...'
                    # or '[Sidenote...'. If the tag is prefixed by a '*' that is not included.
                    the_selected_tag_lines = maintext().get(
                        illosn_selected_start, illosn_selected_end
                    )
                    # We have just copied the line(s) of the selected Illo/SN tag to be moved. Insert
                    # it after the blank line and suffix it with a blank line.
                    maintext().insert(
                        f"{line_num} lineend", "\n" + the_selected_tag_lines + "\n"
                    )
                    # Can delete it from the file now. We do this from the start of its (first) line
                    # so that any prefixing '*' is included in the deletion. Also delete the blank
                    # line that should be following the (last line of the) tag.
                    maintext().delete(
                        illosn_selected_line_start,
                        f"{illosn_selected_end}+2l linestart",
                    )
                    self.checker_dialog.remove_entry_current()
                    # Update illosn_records
                    self.run_check(tag_type)
                    # Update displays
                    display_illosn_entries()
                    # Select again the tag we have just moved so it is highlighted.
                    self.checker_dialog.select_entry_by_index(illosn_index)
                    return
                if what_to_do == "find-next-blank-line":
                    line_num = maintext().index(f"{line_num}+1l")
                    continue
                if what_to_do == "cannot-move-selected-tag":
                    # Do nothing in response to request to move selected tag up.
                    return
            line_num = maintext().index(f"{line_num}+1l")
        # We may get here if the last line of the file is not a blank line.
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
