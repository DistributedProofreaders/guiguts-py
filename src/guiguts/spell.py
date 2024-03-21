"""Spell checking functionality"""

import importlib.resources
import logging
from pathlib import Path
from tkinter import ttk
from typing import Callable
import regex as re

from guiguts.data import dictionaries
from guiguts.file import ProjectDict
from guiguts.checkers import CheckerDialog, CheckerEntry
from guiguts.maintext import maintext, FindMatch
from guiguts.preferences import preferences
from guiguts.utilities import IndexRowCol, IndexRange, load_wordfile_into_dict

logger = logging.getLogger(__package__)

DEFAULT_DICTIONARY_DIR = importlib.resources.files(dictionaries)

SPELL_CHECK_OK_YES = 0
SPELL_CHECK_OK_NO = 1
SPELL_CHECK_OK_BAD = 2

_the_spell_checker = None  # pylint: disable=invalid-name


class DictionaryNotFoundError(Exception):
    """Raised when no dictionary found to match languages."""

    def __init__(self, language: str) -> None:
        self.language = language


class SpellingError(FindMatch):
    """Class containing info about spelling error.

    Attributes:
        rowcol: Location of start of word in file.
        count: Number of characters in word.
        word: Word spelt wrongly.
        frequency: Number of occurrences of word.
        bad_word: True if word is in project's bad word list
    """

    def __init__(self, index: IndexRowCol, word: str, bad_word: bool):
        """Initialize SpellingError class."""
        super().__init__(index, len(word))
        self.word = word
        self.frequency = 0
        self.bad_word = bad_word


class SpellChecker:
    """Provides spell check functionality."""

    def __init__(self) -> None:
        """Initialize SpellChecker class."""
        self.dictionary: dict[str, bool] = {}
        for lang in maintext().get_language_list():
            self.add_words_from_language(lang)

    def spell_check_file(self, project_dict: ProjectDict) -> list[SpellingError]:
        """Spell check the currently loaded file.

        Returns:
            List of spelling errors in file.
        """
        spelling_errors = []
        spelling_counts: dict[str, int] = {}
        for line, line_num in maintext().get_lines():
            words = re.split(r"[^\p{Alnum}\p{Mark}'’]", line)
            next_col = 0
            for word in words:
                col = next_col
                next_col = col + len(word) + 1
                if word:
                    spell_check_result = self.spell_check_word(word, project_dict)

                    # If word has leading straight apostrophe, it might be
                    # open single quote; trim it and check again
                    if spell_check_result == SPELL_CHECK_OK_NO and word.startswith("'"):
                        word = word[1:]
                        spell_check_result = self.spell_check_word(word, project_dict)

                    # If trailing straight/curly apostrophe, it might be
                    # close single quote; trim it and check again
                    if spell_check_result == SPELL_CHECK_OK_NO and re.search(
                        r"['’]$", word
                    ):
                        word = word[:-1]
                        spell_check_result = self.spell_check_word(word, project_dict)

                    # If not found in dictionary, and word is not now empty
                    # or only consisting of single quotes, add it to errors list
                    if spell_check_result != SPELL_CHECK_OK_YES and not re.fullmatch(
                        r"['’]*", word
                    ):
                        spelling_errors.append(
                            SpellingError(
                                IndexRowCol(line_num, col),
                                word,
                                spell_check_result == SPELL_CHECK_OK_BAD,
                            )
                        )
                        try:
                            spelling_counts[word] += 1
                        except KeyError:
                            spelling_counts[word] = 1
        # Now all spelling errors have been found, update the frequency of each one
        for spelling in spelling_errors:
            spelling.frequency = spelling_counts[spelling.word]
        return spelling_errors

    def spell_check_word(self, word: str, project_dict: ProjectDict) -> int:
        """Spell check the given word.

        Allows things like numbers, years, decades, etc.

        Args:
            word: Word to be checked.

        Returns:
            SPELL_CHECK_OK_BAD if word is in the bad_words list
            SPELL_CHECK_OK_YES if word is in dictionary
            SPELL_CHECK_OK_NO if neither (wrong spelling)
        """
        word_status = self.spell_check_word_apos(word, project_dict)
        # If it's a bad word or in the dictionary, we're done
        if word_status in (SPELL_CHECK_OK_BAD, SPELL_CHECK_OK_YES):
            return word_status

        # Some languages use l', quest', etc., before word.
        # Accept if the "prefix" and the remainder are both good.
        # Prefix can be with or without apostrophe, but dictionary
        # is safer if prefix has apostrophe to avoid prefix being
        # accepted it it is used as a standalone word.
        match = re.match(r"(?P<prefix>\w+)['’](?P<remainder>\w+)", word)
        if (
            match is not None
            and self.spell_check_word_apos(match.group("remainder"), project_dict)
            == SPELL_CHECK_OK_YES
            and (
                self.spell_check_word_apos(match.group("prefix"), project_dict)
                == SPELL_CHECK_OK_YES
                or self.spell_check_word_apos(match.group("prefix") + "'", project_dict)
                == SPELL_CHECK_OK_YES
                or self.spell_check_word_apos(match.group("prefix") + "’", project_dict)
                == SPELL_CHECK_OK_YES
            )
        ):
            return SPELL_CHECK_OK_YES

        # Now check numbers
        if (
            # word is all digits
            re.fullmatch(r"\d+", word)  # pylint: disable=too-many-boolean-expressions
            # ...1st, ...21st, ...31st, etc
            or re.fullmatch(r"(\d*[02-9])?1st", word, flags=re.IGNORECASE)
            # ...2nd, ...22nd, ...32nd, etc (also 2d, 22d, etc)
            or re.fullmatch(r"(\d*[02-9])?2n?d", word, flags=re.IGNORECASE)
            # ...3rd, ...23rd, ...33rd, etc (also 3d, 33d, etc)
            or re.fullmatch(r"(\d*[02-9])?3r?d", word, flags=re.IGNORECASE)
            # ...0th, ...4th, ...5th, etc
            or re.fullmatch(r"\d*[04-9]th", word, flags=re.IGNORECASE)
            # ...11th, ...12th, ...13th
            or re.fullmatch(r"\d*1[123]th", word, flags=re.IGNORECASE)
        ):
            return SPELL_CHECK_OK_YES

        # Allow decades/years
        if (
            # e.g. '20s or 20s (abbreviation for 1820s)
            re.fullmatch(r"['’]?\d\ds", word)
            # e.g. '62 (abbreviation for 1862)
            or re.fullmatch(r"['’]\d\d", word)
            # e.g. 1820s
            or re.fullmatch(r"1\d{3}s", word)
        ):
            return SPELL_CHECK_OK_YES

        # Allow abbreviations for shillings and pence (not pounds
        # because 20l is common scanno for the number 201)
        # e.g. 15s or 6d (up to 2 digits of old English shillings and pence)
        if re.fullmatch(r"\d{1,2}[sd]", word):
            return SPELL_CHECK_OK_YES

        # <sc> DP markup
        if re.fullmatch(r"sc", word, flags=re.IGNORECASE):
            return SPELL_CHECK_OK_YES

        return SPELL_CHECK_OK_NO

    def spell_check_word_apos(self, word: str, project_dict: ProjectDict) -> int:
        """Spell check the given word.

        Copes with straight or curly apostrophes.

        Args:
            word: Word to be checked.

        Returns:
            SPELL_CHECK_OK_BAD if word is in the bad_words list
            SPELL_CHECK_OK_YES if word is in dictionary
            SPELL_CHECK_OK_NO if neither (wrong spelling)
        """
        word_status = self.spell_check_word_case(word, project_dict)
        # If it's a bad word or in the dictionary, we're done
        if word_status in (SPELL_CHECK_OK_BAD, SPELL_CHECK_OK_YES):
            return word_status

        # Otherwise, try swapping apostrophes if there are any, and re-check
        if "'" in word:
            word = re.sub(r"'", r"’", word)
        elif "’" in word:
            word = re.sub(r"’", r"'", word)
        else:
            return word_status
        return self.spell_check_word_case(word, project_dict)

    def spell_check_word_case(self, word: str, project_dict: ProjectDict) -> int:
        """Spell check word, allowing for differences of case.

        Check same case, lower case, or title case (e.g. LONDON matches London)
        Can't just do case-insensitive check because we don't want "london" to be OK.

        Args:
            word: Word to be checked.

        Returns:
            SPELL_CHECK_OK_BAD if word is in the bad_words list
            SPELL_CHECK_OK_YES if word is in dictionary
            SPELL_CHECK_OK_NO if neither (wrong spelling)
        """
        # Check if word is a bad word - case must match for bad words
        if word in project_dict.bad_words:
            return SPELL_CHECK_OK_BAD

        lower_word = word.lower()
        if lower_word == word:
            lower_word = ""
        # Caution converting to title case - we want "LONDON" to match "London",
        # but we don't want "london" to match London, so leave first letter case
        # as-is, and lowercase the rest
        if len(word) > 1:
            title_word = word[0:1] + word[1:].lower()
            if title_word == word:
                title_word = ""
        else:
            title_word = ""

        # Now check global & project dictionaries for good words
        for dictionary in (self.dictionary, project_dict.good_words):
            if (
                word in dictionary
                or (lower_word and lower_word in dictionary)
                or (title_word and title_word in dictionary)
            ):
                return SPELL_CHECK_OK_YES

        return SPELL_CHECK_OK_NO

    def add_words_from_language(self, lang: str) -> None:
        """Add dictionary words for given language.

        Attempts to load default and user dictionaries.
        Outputs warning if default dictionary doesn't exits.
        Raises DictionaryNotFoundError exception if neither dictionary exists.

        Args:
            lang: Language to be loaded.
        """
        path = DEFAULT_DICTIONARY_DIR.joinpath(f"dict_{lang}_default.txt")
        words_loaded = load_wordfile_into_dict(path, self.dictionary)
        if not words_loaded:
            logger.warning(f"No default dictionary for language {lang}")

        path = Path(preferences.prefsdir, f"dict_{lang}_user.txt")
        if load_wordfile_into_dict(path, self.dictionary):
            words_loaded = True
        if not words_loaded:  # Neither default nor user dictionary exist
            raise DictionaryNotFoundError(lang)


def spell_check(
    project_dict: ProjectDict, add_project_word_callback: Callable[[str], None]
) -> None:
    """Spell check the currently loaded file."""
    global _the_spell_checker

    if _the_spell_checker is None:
        try:
            _the_spell_checker = SpellChecker()
        except DictionaryNotFoundError as exc:
            logger.error(f"Dictionary not found for language: {exc.language}")
            return

    bad_spellings = _the_spell_checker.spell_check_file(project_dict)

    def process_spelling(checker_entry: CheckerEntry) -> None:
        """Process the spelling error by adding the word to the project dictionary."""
        if checker_entry.text_range:
            add_project_word_callback(checker_entry.text.split(maxsplit=1)[0])

    checker_dialog = CheckerDialog.show_dialog(
        "Spelling Check Results",
        rerun_command=lambda: spell_check(project_dict, add_project_word_callback),
        process_command=process_spelling,
    )
    frame = ttk.Frame(checker_dialog.header_frame)
    frame.grid(column=0, row=1, columnspan=2, sticky="NSEW")
    project_dict_button = ttk.Button(
        frame,
        text="Add to Project Dict",
        command=lambda: checker_dialog.process_remove_entry_current(all_matching=True),
    )
    project_dict_button.grid(column=0, row=0, sticky="NSW")
    skip_button = ttk.Button(
        frame,
        text="Skip",
        command=lambda: checker_dialog.remove_entry_current(all_matching=False),
    )
    skip_button.grid(column=1, row=0, sticky="NSW")
    skip_all_button = ttk.Button(
        frame,
        text="Skip All",
        command=lambda: checker_dialog.remove_entry_current(all_matching=True),
    )
    skip_all_button.grid(column=2, row=0, sticky="NSW")

    checker_dialog.reset()
    # Construct opening line describing the search
    checker_dialog.add_entry("Start of Spelling Check")
    checker_dialog.add_entry("")

    for spelling in bad_spellings:
        end_rowcol = IndexRowCol(
            maintext().index(spelling.rowcol.index() + f"+{spelling.count}c")
        )
        bad_str = " ***" if spelling.bad_word else ""
        checker_dialog.add_entry(
            f"{spelling.word} ({spelling.frequency})" + bad_str,
            IndexRange(spelling.rowcol, end_rowcol),
            0,
            spelling.count,
        )
    checker_dialog.add_entry("")
    checker_dialog.add_entry("End of Spelling Check")


def spell_check_clear_dictionary() -> None:
    """Clear the spell check dictionary."""
    global _the_spell_checker
    _the_spell_checker = None
