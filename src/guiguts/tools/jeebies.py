"""Jeebies check functionality"""

import importlib.resources
import logging
import regex as re

from guiguts.data import dictionaries
from guiguts.checkers import CheckerDialog
from guiguts.maintext import maintext

logger = logging.getLogger(__package__)

DEFAULT_DICTIONARY_DIR = importlib.resources.files(dictionaries)
PARANOID_LEVEL_3WORDS = 1.0

_the_jeebies_checker = None  # pylint: disable=invalid-name


########################################################
# jeebies.py
# C author: Jim Tinsley (DP:jim) - 2005
# Go author: Roger Franks (DP:rfrank) - 2020
# Python author: Quentin Campbell (DP:qgc) - 2024
########################################################


class DictionaryNotFoundError(Exception):
    """Raised when no hebe-forms dictionary found."""

    def __init__(self, file: str) -> None:
        self.file = file


class JeebiesChecker:
    """Provides jeebies check functionality."""

    def __init__(self) -> None:
        """Initialize SpellChecker class."""
        self.dictionary: dict[str, int] = {}
        self.load_phrases_file_into_dictionary()

    def check_for_jeebies_in_file(self) -> None:
        """Check for jeebies in the currently loaded file."""

        # Create the checker dialog to show results
        checker_dialog = CheckerDialog.show_dialog(
            "Jeebies Results", rerun_command=jeebies_check
        )
        checker_dialog.reset()

        # Get the whole of the file from the main text widget
        input_lines = maintext().get_text().splitlines()
        # Ensure last paragraph converts to a line of text
        input_lines.append("")

        # Paragraphs as single string, case preserved
        wbs = []
        # Paragraphs as single string, all lower case
        wbl = []

        # for line, line_num in maintext().get_lines():
        s = ""
        be_cnt_in_file = 0
        he_cnt_in_file = 0
        for line in input_lines:
            line = line.rstrip()
            be_cnt_in_file += len(re.findall(r"(?<=^|\W)be(?=\W|$)", line))
            he_cnt_in_file += len(re.findall(r"(?<=^|\W)he(?=\W|$)", line))
            if line == "":
                # Blank line so end of paragraph
                if s != "":
                    # Something in the paragraph string so save it
                    # after trimming leading and trailing space.
                    s = s.strip()
                    wbs.append(s)
                    wbl.append(s.lower())
                    s = ""
            else:
                # Still in paragraph
                s += " " + line

        if (be_cnt_in_file + he_cnt_in_file) == 0:
            checker_dialog.add_entry(
                f"  --> 'be' counted {be_cnt_in_file} times and 'he' counted {he_cnt_in_file} times in file."
            )
        else:
            checker_dialog.add_entry(
                f"  --> 'be' counted {be_cnt_in_file} times and 'he' counted {he_cnt_in_file} times in file. Checking for suspect phrases..."
            )
        checker_dialog.add_entry("")

        be_suspects_cnt = self.find_and_report_hebe_phrases(
            "be", wbs, wbl, checker_dialog
        )
        he_suspects_cnt = self.find_and_report_hebe_phrases(
            "he", wbs, wbl, checker_dialog
        )

        if be_suspects_cnt == 0 and he_suspects_cnt == 0:
            checker_dialog.add_entry("    No suspect phrases found.")

    def find_and_report_hebe_phrases(
        self, hebe: str, wbs: list, wbl: list, checker_dialog: CheckerDialog
    ) -> int:
        """Look for suspect "w1 be w2" or "w1 he w2" phrases in paragraphs."""
        suspects_count = 0
        # Get the opposite word to the one being reported on.
        behe = "he" if hebe == "be" else "be"

        # Search for 3-form pattern "w1 he/be w2" in a lower-case copy of paragraph.
        for rec_num, para_lc in enumerate(wbl):
            for match_obj in re.finditer(rf"[a-z’]+ {hebe} [a-z’]+", para_lc):
                # Have a 3-word form here (e.g. "must be taken" or "long he remained").
                # See if it's in the list. If so get its frequency of occurrence.
                hebe_form = para_lc[match_obj.start(0) : match_obj.end(0)]
                hebe_count = self.find_in_dictionary(hebe_form)
                # Swap 'he' for 'be' (or vice versa) in 3-word form and lookup that.
                behe_form = re.sub(hebe, behe, hebe_form)
                behe_count = self.find_in_dictionary(behe_form)
                # At this point we have the two forms and how common each are as
                # the variables hebe_count and behe_count.

                # Improved Golang/PPWB format and values calculation
                if behe_count > 0 and (
                    hebe_count == 0 or behe_count / hebe_count > PARANOID_LEVEL_3WORDS
                ):
                    suspects_count += 1
                    info = f"({behe_count}/{hebe_count} - '{behe}' is seen more frequently than '{hebe}' in this phrase)"

                    # Add this 3-form and its info to the dialog

                    header = f'Query phrase "{hebe_form}" {info}'
                    # Get whole-words slice from original para text that is approximately
                    # centered on the 3-form phrase.
                    _, _, centered_slice = self.get_para_slice(
                        match_obj.start(0), wbs[rec_num]
                    )
                    self.add_to_dialog(header, centered_slice, checker_dialog)
        return suspects_count

    def get_para_slice(self, indx: int, para: str) -> tuple[int, int, str]:
        """Define the start and end positions of a slice of a string containing
           only whole words and also return that slice.

        Args:
            indx: Normally the position in string about which the slice will be
                  centered. If the required slice is the head or tail of the string
                  then indx will be 0 or len(para) - 1 respectively.
            para: A text string from which a 'whole words' slice will be extracted.
        """

        # The slice of the paragraph text to be delimited will
        # have as many whole words that can fit into about 60
        # characters.

        if indx == 0:
            # Required slice is the head of the paragraph string.
            llim = 0
            rlim = 60

            rlim = min(rlim, len(para))

        elif indx == len(para) - 1:
            # Required slice is the tail of the paragraph string.
            rlim = len(para)
            llim = rlim - 60

            llim = max(llim, 0)

        else:
            # Required slice is to be centered around indx if possible.
            llim = indx - 30
            rlim = indx + 30

            if llim < 0:
                llim = 0
                rlim = 60

            if rlim > len(para):
                llim = len(para) - 60
                rlim = len(para)

            llim = max(llim, 0)

        # As a result of the abitrary width limit chosen above, the start
        # and end of the slice of the paragrpah string defined by llim and
        # rlim may have partial words. Expand the slice at both ends until first
        # whitespace character found or start or end of paragraph encountered.
        # The slice that is defined will now have only whole words.

        while llim > 0 and para[llim : llim + 1] != " ":
            llim -= 1

        # If not at left margin set llim to start of first word in slice.
        if llim != 0:
            llim += 1

        while rlim < len(para) and para[rlim : rlim + 1] != " ":
            rlim += 1

        # If not at right margin set rlim to end of last word in slice.
        if rlim != len(para) - 1:
            rlim -= 1

        return llim, rlim + 1, para[llim : rlim + 1]

    def find_in_dictionary(self, three_form: str) -> int:
        """Returns frequency in hebe phrase corpus or zero."""

        words = three_form.split()
        key = "|".join(words)
        freq = self.dictionary.get(key, 0)

        return freq

    def add_to_dialog(
        self, header: str, para_slice: str, checker_dialog: CheckerDialog
    ) -> None:
        """Helper function that abstracts repeated code.

        Args:
            header: A 3-form phrase with explanatory info.
            para_slice: A slice of a paragraph centered around the 3-form phrase.
            checker_dialog: Where report text is written.
        """

        record = "    " + para_slice
        # Add header and record to the dialog.
        checker_dialog.add_entry(header)
        checker_dialog.add_entry(record)
        checker_dialog.add_entry(" ")

    def load_phrases_file_into_dictionary(self) -> None:
        """Load a phrase-per-line file into the target dictionary. Entries are
        either 2-form (|he|a:168) or 3-form (since|he|stopped:7) phrases.
        """
        file = "hebelist.txt"
        path = DEFAULT_DICTIONARY_DIR.joinpath(file)
        try:
            with path.open("r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if ":" in line:
                        key, value = line.split(":")
                        self.dictionary[key] = int(value)
        except FileNotFoundError as exc:
            raise DictionaryNotFoundError(file) from exc


def jeebies_check() -> None:
    """Check for jeebies in the currently loaded file."""
    global _the_jeebies_checker

    if _the_jeebies_checker is None:
        try:
            _the_jeebies_checker = JeebiesChecker()
        except DictionaryNotFoundError as exc:
            logger.error(f"Dictionary not found: {exc.file}")
            return

    _the_jeebies_checker.check_for_jeebies_in_file()
