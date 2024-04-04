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
        text = maintext().get_text()
        input_lines = text.splitlines()
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
            line = line.rstrip("\r\n")
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
                f"  --> 'be' counted {be_cnt_in_file} times and 'he' counted {he_cnt_in_file} times in file. Looking for suspect phrases..."
            )
        checker_dialog.add_entry("")

        be_suspects_cnt = self.find_and_report_be_phrases(wbs, wbl, checker_dialog)
        he_suspects_cnt = self.find_and_report_he_phrases(wbs, wbl, checker_dialog)

        if be_suspects_cnt == 0 and he_suspects_cnt == 0:
            checker_dialog.add_entry("    No suspect phrases found.")

    def find_and_report_be_phrases(
        self, wbs: list, wbl: list, checker_dialog: CheckerDialog
    ) -> int:
        """look for suspect "w1 he w2" phrases in paragraphs"""

        ####
        # Looking for 'be' errors.
        ####

        # Search for 3-form pattern "w1 be w2" in a lower-case copy of paragraph.
        suspects_count = 0
        for rec_num, para_lc in enumerate(wbl):
            for match_obj in re.finditer(r"[a-z’]+ be [a-z’]+", para_lc):
                # Have a 3-word form here ("must be taken").
                # See if it's in the list.
                be_form = para_lc[match_obj.start(0) : match_obj.end(0)]
                be_count = self.find_in_dictionary(be_form)
                # Change 'be' to 'he' and lookup that 3-word form.
                he_form = re.sub("be", "he", be_form)
                he_count = self.find_in_dictionary(he_form)
                # At this point we have the 'be' form and how common that is in
                # be_count and the 'he' form and how common that is in he_count.

                # Improved Golang/PPWB format and values calculation
                if he_count > 0 and (
                    be_count == 0 or he_count / be_count > PARANOID_LEVEL_3WORDS
                ):
                    suspects_count += 1
                    info = f"({he_count}/{be_count} - 'he' is seen more frequently than 'be' in this phrase)"

                    # Add this 3-form and its info to the dialog

                    header = f'Query phrase "{be_form}" {info}'
                    # Get whole-words slice from original para text that is approximately
                    # centered on the 3-form phrase.
                    _, _, centered_slice = self.get_para_slice(
                        match_obj.start(0), wbs[rec_num]
                    )
                    self.add_to_dialog(header, centered_slice, checker_dialog)

        return suspects_count

    def find_and_report_he_phrases(
        self, wbs: list, wbl: list, checker_dialog: CheckerDialog
    ) -> int:
        """look for suspect "w1 be w2" phrases in paragraphs"""

        ####
        # Looking for 'he' errors.
        ####

        # Search for 3-form pattern "w1 he w2" in a lower-case copy of paragraph.
        suspects_count = 0
        for rec_num, para_lc in enumerate(wbl):
            for match_obj in re.finditer(r"[a-z’]+ he [a-z’]+", para_lc):
                # Have a 3-word form here ("where he expected").
                # See if it's in the list.
                he_form = para_lc[match_obj.start(0) : match_obj.end(0)]
                he_count = self.find_in_dictionary(he_form)
                # Change 'he' to 'be' and lookup that 3-word form.
                be_form = re.sub("he", "be", he_form)
                be_count = self.find_in_dictionary(be_form)
                # At this point we have the 'he' form and how common that is in
                # he_count and the 'be' form and how common that is in be_count.

                # Improved Golang/PPWB format and values calculation
                if be_count > 0 and (
                    he_count == 0 or be_count / he_count > PARANOID_LEVEL_3WORDS
                ):
                    suspects_count += 1
                    info = f"({be_count}/{he_count} - 'be' is seen more frequently than 'he' in this phrase)"

                    # Add this 3-form and its info to the dialog

                    header = f'Query phrase "{he_form}" {info}'
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
            indx: normally the position in string about which the slice will be
                  centered. If the required slice is the head or tail of the string
                  then indx will be 0 or len(para) - 1 respectively.
            para: a text string from which a 'whole words' slice will be extracted.
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
        """returns frequency in hebe phrase corpus or zero"""

        words = three_form.split()
        key = words[0] + "|" + words[1] + "|" + words[2]
        freq = 0
        if key in self.dictionary:
            freq = self.dictionary[key]

        return freq

    def add_to_dialog(
        self, header: str, para_slice: str, checker_dialog: CheckerDialog
    ) -> None:
        """helper function that abstracts repeated code

        Args:
            header: a 3-form phrase with explanatory info
            para_slice: a slice of a paragraph centered around the 3-form phrase
            checker_dialog: where report text is written
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
                        parts = line.split(":")
                        self.dictionary[parts[0]] = int(parts[1])
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
