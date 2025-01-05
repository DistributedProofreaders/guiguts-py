"""Jeebies check functionality"""

from enum import StrEnum, auto
from tkinter import ttk
from typing import List

import importlib.resources
import logging
import regex as re

from guiguts.checkers import CheckerDialog, CheckerEntry
from guiguts.data import dictionaries
from guiguts.maintext import maintext
from guiguts.misc_tools import tool_save
from guiguts.utilities import cmd_ctrl_string
from guiguts.preferences import (
    PersistentString,
    PrefKey,
)
from guiguts.utilities import IndexRowCol, IndexRange
from guiguts.widgets import ToolTip

logger = logging.getLogger(__package__)

DEFAULT_DICTIONARY_DIR = importlib.resources.files(dictionaries)
DISCRIMINATOR_LEVEL = 1.0
HB_TOGGLE = {"h": "b", "H": "B", "b": "h", "B": "H"}

_the_jeebies_checker = None  # pylint: disable=invalid-name


########################################################
# jeebies.py
# C author: Jim Tinsley (DP:jim) - 2005
# Go author: Roger Franks (DP:rfrank) - 2020
# Python author: Quentin Campbell (DP:qgc) - 2024
########################################################


class JeebiesParanoiaLevel(StrEnum):
    """Enum class to store Jeebies paranoia level types."""

    PARANOID = auto()
    NORMAL = auto()
    TOLERANT = auto()


class DictionaryNotFoundError(Exception):
    """Raised when no hebe-forms dictionary found."""

    def __init__(self, file: str) -> None:
        self.file = file


class JeebiesCheckerDialog(CheckerDialog):
    """Minimal class to identify dialog type."""

    manual_page = "Tools_Menu#Jeebies"


class JeebiesChecker:
    """Provides jeebies check functionality."""

    def __init__(self) -> None:
        """Initialize SpellChecker class."""
        self.dictionary: dict[str, int] = {}
        self.load_phrases_file_into_dictionary()
        self.paranoia_level = PersistentString(PrefKey.JEEBIES_PARANOIA_LEVEL)

    def check_for_jeebies_in_file(self) -> None:
        """Check for jeebies in the currently loaded file."""

        # Create the checker dialog to show results
        checker_dialog = JeebiesCheckerDialog.show_dialog(
            "Jeebies Results",
            rerun_command=jeebies_check,
            process_command=self.process_jeebies,
        )
        frame = ttk.Frame(checker_dialog.header_frame)
        frame.grid(column=0, row=1, sticky="NSEW")
        ttk.Label(
            frame,
            text="Check Level:",
        ).grid(row=0, column=1, sticky="NSE", padx=(0, 5))
        ttk.Radiobutton(
            frame,
            text="Paranoid",
            variable=self.paranoia_level,
            value=JeebiesParanoiaLevel.PARANOID,
            takefocus=False,
        ).grid(row=0, column=2, sticky="NSE", padx=2)
        ttk.Radiobutton(
            frame,
            text="Normal",
            variable=self.paranoia_level,
            value=JeebiesParanoiaLevel.NORMAL,
            takefocus=False,
        ).grid(row=0, column=3, sticky="NSE", padx=2)
        ttk.Radiobutton(
            frame,
            text="Tolerant",
            variable=self.paranoia_level,
            value=JeebiesParanoiaLevel.TOLERANT,
            takefocus=False,
        ).grid(row=0, column=4, sticky="NSE", padx=2)
        ToolTip(
            checker_dialog.text,
            "\n".join(
                [
                    "Left click: Select & find he/be error",
                    "Right click: Remove he/be error from list",
                    f"With {cmd_ctrl_string()} key: Also toggle queried he/be",
                    "Shift Right click: Also remove all matching he/be errors",
                ]
            ),
            use_pointer_pos=True,
        )
        checker_dialog.reset()

        # Check level used last time Jeebies was run or default if first run.
        check_level = self.paranoia_level.get()

        # Get the paragraph strings and the ancillary lists that allow
        # us to map a hebe in a paragraph string to its actual line/col
        # position in the file.

        (
            input_lines,
            paragraph_strings,
            paragraph_start_line_numbers,
            paragraph_line_boundaries,
        ) = self.build_paragraph_structures()

        # Accumulate counts of 'be' and 'he' in the file.

        be_cnt_in_file = 0
        he_cnt_in_file = 0
        for line in input_lines:
            line_lc = line.lower()
            be_cnt_in_file += len(re.findall(r"(?<=\W|^)be(?=\W|$)", line_lc))
            he_cnt_in_file += len(re.findall(r"(?<=\W|^)he(?=\W|$)", line_lc))

        # We have a list of paragraphs as strings in paragraph_strings and counts
        # of 'he's and 'be's in the file.

        suspects_count = 0

        # Output header line to report. There will be two header lines if
        # the words 'he' and 'be' don't appear in a text. Pretty rare!

        if (be_cnt_in_file + he_cnt_in_file) == 0:
            checker_dialog.add_header(
                f"  --> 'be' counted {be_cnt_in_file} times and 'he' counted {he_cnt_in_file} times in file."
            )
            checker_dialog.add_header("")
            checker_dialog.add_header("    There are no he/be phrases to check.")
        else:
            checker_dialog.add_header(
                f"  --> 'be' counted {be_cnt_in_file} times and 'he' counted {he_cnt_in_file} times in file."
            )
            checker_dialog.add_header("")

            # For each paragraph in book ...

            for paragraph_number, paragraph_text in enumerate(paragraph_strings):
                # Search through paragraph text looking for three-word 'be' suspects.

                # Dialog functionality will rearrange dialog output so that line.col numbers
                # appear in correct sequence in the report after the six function calls below
                # are completed. Without that sorting it is possible that some line.col numbers
                # will be out of sequence. This occurs if one of the function calls reports a
                # suspect jeebie at the end of the paragraph then the next function call reports
                # a different suspect at the start of that paragraph. This can happen because
                # each function call rescans paragraph_text looking for a particular jeebies
                # suspect type.

                # There are two function calls below to identify and report suspect 3-word jeebie
                # phrases and four function calls to report suspect 2-word jeebie phrases; that is,
                # 'he' as first word of a 2-word phrase then 'he' as second word of a 2-word phrase
                # then repeated for 'be'.

                for he_be in ("he", "be"):
                    suspects_count += self.find_and_report_3_word_hebe_suspects(
                        he_be,
                        paragraph_text,
                        paragraph_number,
                        paragraph_start_line_numbers,
                        paragraph_line_boundaries,
                        input_lines,
                        checker_dialog,
                        check_level,
                    )
                    for first_second in ("first", "second"):
                        suspects_count += self.find_and_report_2_word_hebe_suspects(
                            he_be,
                            paragraph_text,
                            paragraph_number,
                            paragraph_start_line_numbers,
                            paragraph_line_boundaries,
                            input_lines,
                            checker_dialog,
                            first_second,
                            check_level,
                        )

            # Tell user if no suspect hebe phrases found in the paragraphs.

            if suspects_count == 0:
                checker_dialog.add_footer("    No suspect phrases found.")

        checker_dialog.display_entries()

    def build_paragraph_structures(self) -> tuple[List, List, List, List]:
        """Make the paragraph strings and the ancillary lists that allow
        us to map a hebe in a paragraph string to its actual line/col
        position in the file.

        """

        # Get the whole of the file from the main text widget
        input_lines = maintext().get_text().splitlines()
        # Ensure last paragraph converts to a line of text
        input_lines.append("")

        # List of paragraphs as single strings, case preserved.
        paragraph_strings = []
        # The line number of the first line in each paragraph.
        paragraph_start_line_numbers = []
        # Line boundaries in each paragraph. It is a list of lists.
        paragraph_line_boundaries = []
        # List of line boundaries for current paragraph. Used only within
        # the function and is refreshed for each new paragraph. Contents
        # will be appended to paragraph_line_boundaries list (see above).
        paragraph_line_ends: List[int] = []

        prev_line_was_blank = True
        line_number = 1
        s = ""
        line_end = 0
        open_paragraph = False

        for line in input_lines:
            # Is this input line blank?
            if re.match(r"^ *$", line):
                # It is blank.
                if open_paragraph:
                    # Close the paragraph we are constructing and save it.
                    # NB A blank line has been appended to input_lines to
                    #    ensure that the last paragraph being constructed
                    #    is always closed and saved.
                    paragraph_strings.append(s.rstrip())
                    # List of lists.
                    paragraph_line_boundaries.append(paragraph_line_ends)
                    paragraph_line_ends = []
                    s = ""
                    open_paragraph = False
                prev_line_was_blank = True
            elif prev_line_was_blank:
                # Not a blank line. Previous line was blank so start of a paragraph.
                # NB prev_line_was_blank is initially set True. This means that if
                #    very first line of the file is not blank then it is treated as
                #    the start of the first paragraph (i.e. line_number is 1).
                paragraph_start_line_numbers.append(line_number)
                open_paragraph = True
                # Start paragraph text string
                s = f"{line} "
                # Mark end of this first line in paragraph
                line_end = len(line) + 1
                paragraph_line_ends.append(line_end)
                prev_line_was_blank = False
            else:
                # Not a blank line and previous line was not blank so
                # continuation of a paragraph
                s = s + f"{line} "
                line_end = line_end + len(line) + 1
                paragraph_line_ends.append(line_end)

            line_number += 1

        return (
            input_lines,
            paragraph_strings,
            paragraph_start_line_numbers,
            paragraph_line_boundaries,
        )

    def find_and_report_2_word_hebe_suspects(
        self,
        hebe: str,
        paragraph_text: str,
        paragraph_number: int,
        paragraph_start_line_numbers: list[int],
        paragraph_line_boundaries: list[list[int]],
        file_lines_list: list[str],
        checker_dialog: JeebiesCheckerDialog,
        order: str,
        check_level: str,
    ) -> int:
        """Look for suspect "word be/he" or "be/he word" phrases in paragraphs."""

        def do_finditer_and_report(regx: str, para_lc: str) -> int:
            """Helper function for abstraction of repeated code."""

            count_of_suspects = 0
            for match_obj in re.finditer(regx, para_lc):
                if order == "first":
                    # Have a 2-word phrase starting with a hebe and prefixed by punctuation.
                    # E.g. '"Be careful!"' or ', he said.'
                    # See if it's in the list. If so get its frequency of occurrence.
                    hebe_form = para_lc[match_obj.start(0) : match_obj.end(0)]
                    hebe_count = self.find_in_dictionary(hebe_form)
                    hebe_start = match_obj.start(0) + hebe_form.index(hebe)
                    # Swap 'he' for 'be' (or vice versa) in 2-word phrase and lookup that.
                    # Avoid the "be behoven" or "he headed" trap.
                    s_hebe = f"{hebe} "
                    s_behe = f"{behe} "
                    behe_form = re.sub(s_hebe, s_behe, hebe_form)
                    behe_count = self.find_in_dictionary(behe_form)
                elif order == "second":
                    # Have a 2-word phrase ending with a hebe followed by punctuation.
                    # E.g. 'could be.'
                    # See if it's in the list. If so get its frequency of occurrence.
                    hebe_form = para_lc[match_obj.start(0) : match_obj.end(0)]
                    hebe_count = self.find_in_dictionary(hebe_form)
                    # Avoid the "the he-goats" trap when indexing for a hebe.
                    s_hebe = f" {hebe}"
                    # The result of 'hebe_form.index(s_hebe)' below will a pointer to the
                    # space in the 's_hebe' string, not the hebe itself. Add 1 so that
                    # 'hebe_start' correctly points at the hebe in the string.
                    hebe_start = match_obj.start(0) + hebe_form.index(s_hebe) + 1
                    # Swap 'he' for 'be' (or vice versa) in 2-word phrase and lookup that.
                    s_behe = f" {behe}"
                    behe_form = re.sub(s_hebe, s_behe, hebe_form)
                    behe_count = self.find_in_dictionary(behe_form)
                else:
                    # Shouldn't reach here.
                    hebe_count = behe_count = hebe_start = 0

                # At this point we have the two versions of the phrase. The variables
                # hebe_count and behe_count are integer frequencies of occurrence of
                # those phrases in a large corpus of DP texts.

                # The algorithm that follows improves on the Golang/PPWB method of identifying
                # suspect hebe phrases.

                if check_level == "tolerant" and (
                    hebe_count > 0 or hebe_count == 0 and behe_count == 0
                ):
                    # Even if the behe_count > hebe_count (see values calculation below) we
                    # won't query the phrase. That is, the 'tolerant' check passes if there
                    # are any 'good' occurrences or no 'bad' occurrences in the dictionary
                    # of examples.
                    continue

                if behe_count > 0 and (
                    hebe_count == 0 or behe_count / hebe_count > DISCRIMINATOR_LEVEL
                ):
                    count_of_suspects += 1
                    info = f"({behe_count}/{hebe_count})"

                    # Add this 2-form and its info to the dialog

                    # We have the start position in the paragraph string of this hebe.
                    # Now locate the actual file line and corresponding position on that
                    # line of this hebe.

                    line_number, hebe_position_on_line = self.locate_file_line(
                        paragraph_number,
                        hebe_start,
                        paragraph_start_line_numbers,
                        paragraph_line_boundaries,
                    )
                    line = file_lines_list[line_number - 1]

                    self.add_to_dialog(
                        info,
                        line,
                        line_number,
                        hebe_position_on_line,
                        checker_dialog,
                    )

                elif (
                    check_level in ("normal", "paranoid")
                    and hebe_count == 0
                    and behe_count == 0
                ):
                    # Neither 'he' nor 'be' versions of our 2-form phrase are in the
                    # dictionary.

                    count_of_suspects += 1
                    info = f"({behe_count}/{hebe_count})"

                    # Query this 2-form phrase in the report.

                    # We have the start position in the paragraph string of its hebe.
                    # Locate the corresponding file line and its column position on
                    # that line.

                    line_number, hebe_position_on_line = self.locate_file_line(
                        paragraph_number,
                        hebe_start,
                        paragraph_start_line_numbers,
                        paragraph_line_boundaries,
                    )
                    line = file_lines_list[line_number - 1]

                    self.add_to_dialog(
                        info,
                        line,
                        line_number,
                        hebe_position_on_line,
                        checker_dialog,
                    )

            return count_of_suspects

        ####
        # Find and report 2-word hebe suspects in paragraph text
        ####

        suspects_count = 0
        # Get the opposite word to the one being reported on.
        behe = "he" if hebe == "be" else "be"

        # Look for 2-form hebe phrases. There are two types:
        #   1. The hebe is the first word of the phrase: e.g. '“Be diligent ....”'
        #   2. The hebe is the second word of the phrase: e.g. '“... could be.”'
        # Note that the hebe in a 2-form phrase is ALWAYS delimited by at least
        # one punctuation character, as in the examples above, or a punctuation
        # character followed by a space as in '... had done. He then ...'. Special
        # treatment needed when phrase involves a contaction as in 'an’ be damned.'
        # See below for this.

        if order == "first":
            # Looking for hebe as first word of 2-word punctuation delimited phrase.

            para_lc = paragraph_text.lower()

            # NB A hebe phrase containing a contraction as in 'an’ be damned' has already
            #    been processed as a 3-form phrase. Avoid it being processed again as a
            #    2-form phrase. Obscure the right curly quote characters whenever they
            #    and a space precede a hebe.
            qs_hebe = f"’ {hebe}"
            ss_hebe = f"  {hebe}"
            para_lc = re.sub(qs_hebe, ss_hebe, para_lc)
            # Look for type 1, 2-form hebe phrases in the edited paragraph string.
            regx = rf"(?<=^|\p{{P}}|\p{{P}} ){hebe} [a-z]+"
            suspects_count += do_finditer_and_report(regx, para_lc)

        elif order == "second":
            # Looking for hebe as second word of 2-word punctuation delimited phrase.

            para_lc = paragraph_text.lower()

            regx = rf"[a-z]+ {hebe}(?=\p{{P}}|$)"
            suspects_count += do_finditer_and_report(regx, para_lc)

        else:
            # Should never get here. Variable 'order' value either 'first' or 'second'.
            pass

        return suspects_count

    def find_and_report_3_word_hebe_suspects(
        self,
        hebe: str,
        paragraph_text: str,
        paragraph_number: int,
        paragraph_start_line_numbers: list[int],
        paragraph_line_boundaries: list[list[int]],
        file_lines_list: list[str],
        checker_dialog: JeebiesCheckerDialog,
        check_level: str,
    ) -> int:
        """Look for suspect "w1 be w2" or "w1 he w2" phrases in paragraphs."""

        def make_dialog_line(info: str, checker_dialog: JeebiesCheckerDialog) -> None:
            """Helper function for abstraction of repeated code."""

            # We have the start position in the paragraph string of a suspect hebe.
            # Locate the corresponding file line and its column position on that
            # line.

            line_number, hebe_position_on_line = self.locate_file_line(
                paragraph_number,
                hebe_start,
                paragraph_start_line_numbers,
                paragraph_line_boundaries,
            )
            line = file_lines_list[line_number - 1]

            self.add_to_dialog(
                info, line, line_number, hebe_position_on_line, checker_dialog
            )

        ####
        # Find and report 3-word hebe suspects in paragraph text
        ####

        suspects_count = 0
        # Get the opposite word to the one being reported on.
        behe = "he" if hebe == "be" else "be"

        # Search for 3-form pattern "w1 he/be w2" in a lower-case copy of paragraph.
        para_lc = paragraph_text.lower()
        for match_obj in re.finditer(f"[a-z’]+ {hebe} [a-z’]+", para_lc):
            # Have a 3-word form here (e.g. "must be taken" or "long he remained").
            # See if it's in the list. If so get its frequency of occurrence.
            hebe_form = para_lc[match_obj.start(0) : match_obj.end(0)]
            hebe_count = self.find_in_dictionary(hebe_form)
            # Avoid the "tribe be not" or "catastrophe he had" trap.
            s_hebe = f" {hebe}"
            hebe_start = match_obj.start(0) + hebe_form.index(s_hebe) + 1
            # Swap 'he' for 'be' (or vice versa) in 3-word form and lookup that.
            # Avoid the "tribe be not" or "catastrophe he had" trap.
            s_behe = f" {behe}"
            behe_form = re.sub(s_hebe, s_behe, hebe_form)
            behe_count = self.find_in_dictionary(behe_form)

            # At this point we have the two versions of the phrase. The variables
            # hebe_count and behe_count are integer frequencies of occurrence of
            # those phrases in a large corpus of DP texts.

            # The algorithm that follows improves on the Golang/PPWB method of identifying
            # suspect hebe phrases.

            if check_level == "tolerant" and hebe_count > 0:
                # Even if the behe_count > hebe_count (see values calculation below) we
                # won't query the phrase.
                continue

            if behe_count > 0 and (
                hebe_count == 0 or behe_count / hebe_count > DISCRIMINATOR_LEVEL
            ):
                # Query this 3-form phrase.
                suspects_count += 1
                info = f"({behe_count}/{hebe_count})"

                # Query this 3-form phrase in the report.

                make_dialog_line(info, checker_dialog)

            elif check_level == "normal" and hebe_count == 0 and behe_count == 0:
                # Neither 'he' nor 'be' versions of our 3-form phrase are in the
                # dictionary. Does it contain a 2-form hebe phrase that is in
                # the dictionary? E.g. the 3-form phrase 'also be contracted' is
                # not in the dictionary but the 2-form hebe phrases 'also be' or
                # 'be contracted' could be. If either in the dictionary don't
                # query the 3-form phrase they're part of.

                # Isolate the 2-form phrases and see if either is in the dictionary.
                parts = hebe_form.split()
                phrase1 = parts[0] + " " + parts[1]
                phrase2 = parts[1] + " " + parts[2]
                if (
                    self.find_in_dictionary(phrase1) > 0
                    or self.find_in_dictionary(phrase2) > 0
                ):
                    continue

                # Neither 2-form phrase in the dictionary.
                suspects_count += 1
                info = f"({behe_count}/{hebe_count})"

                # Query this 3-form phrase in the report.

                make_dialog_line(info, checker_dialog)

            elif check_level == "paranoid" and hebe_count == 0 and behe_count == 0:
                # Neither 'he' nor 'be' versions of our 3-form phrase are in the
                # dictionary. Query it in report.
                suspects_count += 1
                info = f"({behe_count}/{hebe_count})"

                # Query this 3-form phrase in the report.

                make_dialog_line(info, checker_dialog)

        return suspects_count

    def locate_file_line(
        self,
        rec_num: int,
        hebe_start: int,
        paragraph_start_line_numbers: list[int],
        paragraph_line_boundaries: list[list[int]],
    ) -> tuple[int, int]:
        """Returns line number in file and position on that line of a hebe found in paragraph string."""
        paragraph_start_line_number = paragraph_start_line_numbers[rec_num]
        hebe_start_position_on_line = 0
        line_boundaries = paragraph_line_boundaries[rec_num]
        for indx, boundary in enumerate(line_boundaries):
            if hebe_start < boundary:
                # Located file line number
                line_number = paragraph_start_line_number + indx
                if indx == 0:
                    # We are on first line of paragraph
                    hebe_start_position_on_line = hebe_start
                else:
                    hebe_start_position_on_line = hebe_start - line_boundaries[indx - 1]
                break
        return line_number, hebe_start_position_on_line

    def find_in_dictionary(self, phrase: str) -> int:
        """Returns frequency in hebe phrase corpus or zero."""

        freq = self.dictionary.get(phrase, 0)
        if freq != 0:
            return freq
        # Try again with a prefixing " " character
        key = f" {phrase}"
        freq = self.dictionary.get(key, 0)
        if freq != 0:
            return freq
        # Try finally with a trailing " " character
        key = f"{phrase} "
        freq = self.dictionary.get(key, 0)
        return freq

    def add_to_dialog(
        self,
        info: str,  # pylint: disable=unused-argument
        line: str,
        line_number: int,
        hebe_start: int,
        checker_dialog: JeebiesCheckerDialog,
    ) -> None:
        """Helper function that abstracts repeated code.

        Args:
            info: Ratio of 'he' or 'be freq / 'be' or 'he' freq expressed as a string.
            line: Text of file line.
            line_num: Its line number in the file.
            hebe_start: The position on line of string 'he' or 'be'.
            checker_dialog: Where report text is written.
        """
        # Get start/end of 'he' or 'be' string in file.
        error_start = f"{line_number}.{hebe_start}"
        error_end = f"{line_number}.{hebe_start + 2}"
        # Store in structure for file row/col positions & ranges.
        start_rowcol = IndexRowCol(error_start)
        end_rowcol = IndexRowCol(error_end)

        ############################################################
        # To RESTORE ratios in report lines uncomment the following
        # two lines and comment out the third line.
        ############################################################
        # line = f"{info} {line}"
        # highlight_start = hebe_start + len(info) + 1
        highlight_start = hebe_start
        highlight_end = highlight_start + 2

        # Add record to the dialog.
        checker_dialog.add_entry(
            line,
            IndexRange(start_rowcol, end_rowcol),
            highlight_start,
            highlight_end,
        )

    def load_phrases_file_into_dictionary(self) -> None:
        """Load a phrase-per-line file into the target dictionary. Entries in the file
        are either 2-form (e.g. `|he|a:168`) or 3-form (e.g. `since|he|stopped:7`) phrases.
        """
        file = "hebelist.txt"
        path = DEFAULT_DICTIONARY_DIR.joinpath(file)
        try:
            with path.open("r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if ":" in line:
                        key, value = line.split(":")
                        key = key.replace("|", " ")
                        self.dictionary[key] = int(value)
        except FileNotFoundError as exc:
            raise DictionaryNotFoundError(file) from exc

    def process_jeebies(self, checker_entry: CheckerEntry) -> None:
        """Process the Jeebies query."""
        if checker_entry.text_range is None:
            return
        start_mark = JeebiesCheckerDialog.mark_from_rowcol(
            checker_entry.text_range.start
        )
        end_mark = JeebiesCheckerDialog.mark_from_rowcol(checker_entry.text_range.end)
        match_text = maintext().get(start_mark, end_mark)
        # Toggle match text
        replacement_text = HB_TOGGLE[match_text[0]] + match_text[1]
        maintext().replace(start_mark, end_mark, replacement_text)


def jeebies_check() -> None:
    """Check for jeebies in the currently loaded file."""
    global _the_jeebies_checker

    if not tool_save():
        return

    if _the_jeebies_checker is None:
        try:
            _the_jeebies_checker = JeebiesChecker()
        except DictionaryNotFoundError as exc:
            logger.error(f"Dictionary not found: {exc.file}")
            return

    _the_jeebies_checker.check_for_jeebies_in_file()
