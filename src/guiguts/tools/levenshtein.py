"""Levenshtein edit distance check functionality"""

import time
import importlib.resources
import logging

from enum import StrEnum, auto
from tkinter import ttk
from Levenshtein import distance

import regex as re

from guiguts.checkers import CheckerDialog
from guiguts.spell import SpellChecker
from guiguts.data import dictionaries
from guiguts.file import ProjectDict
from guiguts.maintext import maintext
from guiguts.misc_tools import tool_save
from guiguts.preferences import (
    PersistentString,
    PrefKey,
)
from guiguts.utilities import IndexRowCol, IndexRange
from guiguts.widgets import ToolTip

logger = logging.getLogger(__package__)

DEFAULT_DICTIONARY_DIR = importlib.resources.files(dictionaries)

SPELL_CHECK_OK_YES = 0
SPELL_CHECK_OK_NO = 1
SPELL_CHECK_OK_BAD = 2

LINES_IN_REPORT_LIMIT = 2

_the_levenshtein_checker = None  # pylint: disable=invalid-name


#########################################################
# levenshtein.py
# Python author: Quentin Campbell (DP:qgc) - 2024.
# Based on the processing logic in the PPtxt Go version
# authored by Roger Franks (DP:rfrank - 2020) but using
# a publicly available Levenshtein module authored by
# Max Bachmann.
#########################################################


class LevenshteinEditDistance(StrEnum):
    """Enum class to store Levenshtein Edit Distance."""

    ONE = auto()
    TWO = auto()


class DictionaryNotFoundError(Exception):
    """Raised when no hebe-forms dictionary found."""

    def __init__(self, file: str) -> None:
        self.file = file


class LevenshteinChecker:
    """Provide Levenshtein edit distance functionality."""

    def __init__(self) -> None:
        """Initialize LevenshteinChecker class."""

        self.edit_distance = PersistentString(PrefKey.LEVENSHTEIN_EDIT_DISTANCE)

    def run_levenshtein_check_on_file(self, project_dict: ProjectDict) -> None:
        """Check Levenshtein edit distance between selected file words."""

        ####
        # The following are declared and accessed as 'nonlocal' variables
        # by functions defined within the enclosing scope of this top-most
        # function definition. The names must exist when first encountered
        # as they cannot be created by a first assignment in a nested def.
        ####

        # Each word that is correctly spell-checked is appended to this list,
        # hence can contain many duplicates of a word in all its case forms.
        # E.g. ['another', 'Another', 'another', ...]
        good_words = []
        # Each word that fails the spell check is appended to this list, hence
        # can contain many duplicates of a word in all its case forms.
        # E.g. ['anither', 'Anither', 'anither', ...]
        suspect_words = []
        # Key is a word in whatever case it appears in the text. Maps
        # the frequency with which that word form appears in the text.
        all_words_counts: dict[str, int] = {}
        # Key is a word in whatever case it appears in the text. Maps
        # the word to the line(s) it appears on using a list of
        # tuples: (line_number, start_columan_index).
        # E.g. 'another': [(1, 8), (3, 0), (3, 12)]
        word_to_lines_map: dict[str, list[tuple]] = {}
        # A list of tuples, each tuple containing two, lowercase, words.
        # These are the 'suspect_word/good_word' pairs that differ by the
        # Levenshtein edit distance specified (1 or 2). E.g. of content:
        # [('anither', 'another'), ...]
        distance_check_results: list[tuple] = []
        # Given a lowercase word as a key, the value of that key is a list
        # of different case versions of the key that appear in the text.
        # E.g. 'another': ['Another', 'another', 'ANOTHER']
        all_words_case_map: dict[str, list[str]] = {}

        def build_header_line(result_tuple: tuple) -> str:
            """Function to build a header line for display

            It processes a tuple that contains a pair of words that
            are the required Levenshtein edit distance apart. E.g.
            ('anither', 'another')

            Args:
                result_tuple: contains a pair of lowercase words.

            Returns:
                Formatted string. E.g.
                  Anither (1), anither (2) <-> ANOTHER (1), Another (3), another (7)
            """

            # The tuple argument contains two lowercase strings.
            suspect_word = result_tuple[0]
            test_word = result_tuple[1]

            # Find any different-case versions of each word. The key
            # for this map is always the canonical form of the word;
            # that is, the lowercase version.
            #
            # Note that the strings in an 'all_words_case_map[word]' list
            # are not necessarily in lexicographic order so always sort it.
            # E.g.:
            #     ['Another', 'another', 'ANOTHER']
            # when we want to display
            #     ['ANOTHER', 'Another', 'another'']
            list_sorted_sw = sorted(all_words_case_map[suspect_word])
            list_sorted_gw = sorted(all_words_case_map[test_word])

            # When the same word appears in different cases build a header
            # line that reflects that. E.g:
            #
            #   Anither(1), anither(2) <-> ANOTHER(1), Another(2), another(5)
            #
            # Build it in two sections, left and right parts with the
            # separator between them.

            # NB In the following section the key to the 'all_words_counts'
            # dictionary can be in any case form; that is, they are not
            # expected to be in lowercase canonical form.

            # This half displays one or more case versions of the suspect word.
            left_part = ""
            for word in list_sorted_sw:
                left_part += f"{word}({all_words_counts[word]}), "
            # Chop the trailing ", " characters.
            left_part = left_part[:-2]

            # This half displays one or more case versions of the test word.
            right_part = ""
            for word in list_sorted_gw:
                right_part += f"{word}({all_words_counts[word]}), "
            # Chop the trailing ", " characters.
            right_part = right_part[:-2]

            return f"{left_part} <-> {right_part}"

        def sort_tuples(tuples: list[tuple], key_indx: int) -> list[tuple]:
            """Utility function to sort a list of tuples

            Args:
                tuples: a list of two-element tuples
                key_indx: int 0 or 1 - element of a tuple on which to sort

            Returns:
                Input list of tuples sorted on key_indx element of each tuple
            """

            # Define a key function that returns the desired element of each tuple.
            def key_func(x: tuple) -> int:
                return x[key_indx]

            # key_func = lambda x: x[key_indx]

            # Use the 'sorted' function to sort the list of tuples using the key function.
            sorted_tuples = sorted(tuples, key=key_func)

            return sorted_tuples

        def get_sorted_list_of_linecol_tuples(word: str) -> list:
            """Utility function to sort line_number/column_start_index tuples

            Enables the reporting of every line on which a word occurs (in any of its
            case forms) by increasing order of line number and column index.

            Arg:
                word: all line_number/column_start_index tuples for this word will be
                      collected and sorted.

            Returns:
                list of sorted tuples.
            """

            # The 'word' argument is in canonical form. Put the different
            # case versions of the word into 'word_list'.
            word_list = all_words_case_map[word]

            # Each case version of the word is mapped to a list of tuples.
            # Each tuple represents (line_number, column_start_index) as
            # integers. The list of tuples for each case version represents
            # the location of every occurrence of that form of the word in
            # the file.
            #
            # Gather together all the tuples of each different case version
            # of a word and sort that list into start column order within line
            # number order.
            tuples = []

            for word_entry in word_list:
                # The key to the map below is in any case form.
                tuples_list = word_to_lines_map[word_entry]
                for tuple_entry in tuples_list:
                    tuples.append(tuple_entry)

            # First sort the tuples by column_start_index
            sorted_tuples = sort_tuples(tuples, 1)
            # Then sort the result by line_number
            sorted_tuples = sort_tuples(sorted_tuples, 0)
            # If the original list of tuples was, say
            #   [(2, 5), (1, 2), (4, 4), (2, 3)]
            # it should now be
            #   [(1, 2), (2, 3), (2, 5), (4, 4)]

            return sorted_tuples

        def unpack_and_write_to_dialog(result_tuple: tuple) -> None:
            """Function for reporting word pair results from distance check

            This function is called once for each pair of words that meet
            the required Levenshtein edit distance criteria. It calls utility
            functions to generate the header line and select and highlight all
            the file lines that make up the report for that word pair. It then
            calls CheckerDialog methods to report the header line and all the
            accompanying file lines.

            Arg:
                result_tuple: 2-element tuple containing a lowercase 'suspect'
                              word and a lowercase 'good' word against which
                              it was tested.
            """

            # The tuple argument contains two lowercase strings; that is,
            # they are the canonical form of each word of the pair being
            # reported.
            suspect_word = result_tuple[0]
            test_word = result_tuple[1]

            # In order to build the header line for the report; e.g.
            #   Anither(1), anither(2) <-> ANOTHER(1), Another(2), another(5)
            # will need all other case forms (if any) of the two words. Add
            # the generated header line to the report.
            checker_dialog.add_header(build_header_line(result_tuple))

            # The header line is first followed by all the lines that contain
            # the 'suspect' word in all of it case forms. The occurrence of the
            # word on each line is highlighted as usual.
            tuples = get_sorted_list_of_linecol_tuples(suspect_word)
            for index_tuple in tuples:
                error_start, error_end = make_into_strings(
                    index_tuple, len(suspect_word)
                )
                start_rowcol = IndexRowCol(error_start)
                end_rowcol = IndexRowCol(error_end)
                file_line = maintext().get(
                    error_start + " linestart", error_end + " lineend"
                )
                checker_dialog.add_entry(
                    file_line,
                    IndexRange(start_rowcol, end_rowcol),
                    start_rowcol.col,
                    end_rowcol.col,
                )

            # No more lines to output for the suspect word so add a separator.
            checker_dialog.add_header("----")

            # The separator line is then followed by all the lines that contain
            # the 'good' word that the 'suspect' word was tested against. They
            # are reported just as for the 'suspect' word above.
            tuples = get_sorted_list_of_linecol_tuples(test_word)
            lines_output_count = 0
            for index_tuple in tuples:
                # Limit the number of 'good' word lines reported.
                if lines_output_count == LINES_IN_REPORT_LIMIT:
                    lines_output_count = -1
                    break
                error_start, error_end = make_into_strings(index_tuple, len(test_word))
                start_rowcol = IndexRowCol(error_start)
                end_rowcol = IndexRowCol(error_end)
                file_line = maintext().get(
                    error_start + " linestart", error_end + " lineend"
                )
                checker_dialog.add_entry(
                    file_line,
                    IndexRange(start_rowcol, end_rowcol),
                    start_rowcol.col,
                    end_rowcol.col,
                )
                lines_output_count += 1

            if lines_output_count < 0:
                checker_dialog.add_footer("  ...more")

            # Add a blank line to separate this word-pair report from that of the
            # next pair.
            checker_dialog.add_footer("")

        def make_into_strings(
            index_tuple: tuple, hilite_length: int
        ) -> tuple[str, str]:
            """Utility function to generate error_start & error_end strings from int values

            Args:
                index_tuple: an integer line number and an integer column start index
                hilite_length: integer length of string to be lighlighted on the line.

            Return:
                An error_start string (E.g. "18.3" and an error_end string (E.g. "18.9")
            """

            line_num = str(index_tuple[0])
            col_indx = str(index_tuple[1])
            error_start = f"{line_num}.{col_indx}"
            col_indx = str(index_tuple[1] + hilite_length)
            error_end = f"{line_num}.{col_indx}"

            return error_start, error_end

        def map_words_in_file(project_dict: ProjectDict) -> None:
            """Spell check the currently loaded file and extract a list of suspect
            words and a list of good words. Build a map of the line position index(es)
            of each word and a map of the frequency of each word.

            Outputs into a nonlocal list or dictionary:
                List of suspect words - each an apparent spelling error.
                Counts of those words (as a dictionary).
                List of good words - each found in an English dictionary.
                Counts of those words (as a dictionary).
                Map of the line index(es) of each word and hilite start index on line.
            """

            # These must already exist (see enclosing function) before they are
            # used here. They are the lists and dictionaries into which the results
            # of this function are 'returned'.
            nonlocal good_words
            nonlocal suspect_words
            nonlocal word_to_lines_map
            nonlocal all_words_case_map, all_words_counts

            # Will check spelling using SpellChecker methods from spell.py
            spelling = SpellChecker()

            # The main loop from spell.py with some minor adaptions. It splits each
            # file line into 'words' and calls SpellChecker.spell_check_word() on each.
            # Depending on the result the word is appended either to 'good_words' list
            # (they are in the spelling dictionary) or 'suspect_words' list (not in the
            # spelling dictionary). Some variable names changed to avoid pylint flagging
            # 'duplicate code' with spell.py.
            for line_text, line_number in maintext().get_lines():
                words = re.split(r"[^\p{Alnum}\p{Mark}'’]", line_text)
                next_column = 0
                for word in words:
                    column = next_column
                    next_column = column + len(word) + 1
                    if word:
                        spell_check_result = spelling.spell_check_word(
                            word, project_dict
                        )
                        if spell_check_result == SPELL_CHECK_OK_YES:
                            good_words.append(word)
                            try:
                                all_words_counts[word] += 1
                            except KeyError:
                                all_words_counts[word] = 1

                            try:
                                word_to_lines_map[word].append((line_number, column))
                            except KeyError:
                                word_to_lines_map[word] = [(line_number, column)]
                            continue

                        # If word has leading straight apostrophe, it might be
                        # open single quote; trim it and check again
                        if spell_check_result == SPELL_CHECK_OK_NO and word.startswith(
                            "'"
                        ):
                            word = word[1:]
                            spell_check_result = spelling.spell_check_word(
                                word, project_dict
                            )
                            if spell_check_result == SPELL_CHECK_OK_YES:
                                good_words.append(word)
                                try:
                                    all_words_counts[word] += 1
                                except KeyError:
                                    all_words_counts[word] = 1

                                try:
                                    word_to_lines_map[word].append(
                                        (line_number, column)
                                    )
                                except KeyError:
                                    word_to_lines_map[word] = [(line_number, column)]
                                continue

                        # If trailing straight/curly apostrophe, it might be
                        # close single quote; trim it and check again
                        if spell_check_result == SPELL_CHECK_OK_NO and re.search(
                            r"['’]$", word
                        ):
                            word = word[:-1]
                            spell_check_result = spelling.spell_check_word(
                                word, project_dict
                            )
                            if spell_check_result == SPELL_CHECK_OK_YES:
                                good_words.append(word)
                                try:
                                    all_words_counts[word] += 1
                                except KeyError:
                                    all_words_counts[word] = 1

                                try:
                                    word_to_lines_map[word].append(
                                        (line_number, column)
                                    )
                                except KeyError:
                                    word_to_lines_map[word] = [(line_number, column)]
                                continue

                        # Word not in dictionary. If word is not now empty and not
                        # consisting only of single quotes, add it to suspect words
                        # list.
                        if not re.fullmatch(r"['’]*", word):
                            suspect_words.append(word)
                            try:
                                all_words_counts[word] += 1
                            except KeyError:
                                all_words_counts[word] = 1

                            try:
                                word_to_lines_map[word].append((line_number, column))
                            except KeyError:
                                word_to_lines_map[word] = [(line_number, column)]

            # NB The lists of 'good' words and 'suspect' words are not always mutually
            # exclusive since a lowercase version of a word may not be in the spelling
            # dictionary used but the uppercase version of the word is in that dictionary.
            # An example of this is 'kirk' which is not in spelling dictionary but 'Kirk'
            # is in the dictionary.

            # Build a dictionary, keyed by the lower case version of a word, whose value
            # will be a list of the same word in the different cases in which it appears
            # in the file. E.g.
            #  dict['another'] -> ['ANOTHER', Another', 'another']
            #
            # NB Only words that appear in the text will appear in that list. Thus the
            #    lowercase version of a word that's used as a key will not be in the list
            #    unless it also appears in the text.

            for word in good_words:
                word_lc = word.lower()
                if word_lc in all_words_case_map:
                    # There's a dictionary entry. Is 'word' in the entries list?
                    if word not in all_words_case_map[word_lc]:
                        # Then add it to the list
                        all_words_case_map[word_lc].append(word)
                else:
                    # Create the dictionary entry.
                    all_words_case_map[word_lc] = [word]

            for word in suspect_words:
                word_lc = word.lower()
                if word_lc in all_words_case_map:
                    # There's a dictionary entry. Is 'word' in the entries list?
                    if word not in all_words_case_map[word_lc]:
                        # Then add it to the list
                        all_words_case_map[word_lc].append(word)
                else:
                    # Create the dictionary entry.
                    all_words_case_map[word_lc] = [word]

        def distance_check_words() -> None:
            """Function to select, and edit distance check, pairs of suspect/good words.

            The process involves taking each lowercase form of a suspect word and doing a
            Levenshtein edit distance check against the lowercase form of every good word.

            Keeping the lengths of the respective lists of words as short as possible is
            critical. A book quoting a lot of speech in dialect may have a 'suspect' words
            list of more than 1,000 entries. If the 'good' words list has 8,000 or 9,000
            entries then the number of pairs of suspect<->good words to consider will approach
            10 million. Processing that number of pairs is very demanding of CPU time.
            """

            nonlocal distance_check_results

            # As a word may appear many times in a text, and in many case forms, for example
            # 'ANOTHER', 'Another', 'another, each of the two lists is kept as short as
            # possible by containing just a single lowercase instance of the word: 'another'
            # in the example above.

            # NB For display purposes a separate dictionary maps each case form of a word to
            # its line number and column start index for every occurrence in the file. That is
            # in turn indexed by entries from another dictionary that maps a word in lowercase
            # to any other case form that appears in the file. E.g.: 'another' -> 'ANOTHER',
            # 'Another', 'another'.
            #
            # These dictionaries are only used when processing for display in the report the
            # small number of word pairs that meet the required Levenshtein edit distance criteria.
            # Crucially they free us to do the CPU-intensive word selection and Levenshtein edit
            # distance calculations on the smallest feasible set of word pairs.

            # First make every word lowercase in a copy of each list.
            suspect_words_unique = [x.lower() for x in suspect_words]
            good_words_unique = [x.lower() for x in good_words]
            # The resulting lists still contain multiple occurrences of a word. Use set() to
            # create a unique collection of words from each list. Then turn the result back
            # into a list and sort it.
            suspect_words_unique = sorted(list(set(suspect_words_unique)))
            good_words_unique = sorted(list(set(good_words_unique)))

            # For each lowercase form of a suspect word do distance check against the lowercase
            # form of every good word; i.e. 'test' words. Some obvious filtering of both suspect
            # and test words is done to eliminate some pairs before the edit distance calculation
            # check is made.
            for suspect_wordlc in suspect_words_unique:
                # Must be five letters or more OR contain an unexpected character.
                unexpected = re.sub(r"[a-z0-9’'æœ]", "", suspect_wordlc)
                if len(suspect_wordlc) < 5 and len(unexpected) == 0:
                    continue
                for test_wordlc in good_words_unique:
                    # No point in processing a suspect<->test word pair whose difference in
                    # length is greater than the edit distance to be used in the check (1 or 2).
                    if abs(len(suspect_wordlc) - len(test_wordlc)) > distance_to_check:
                        continue
                    # Check if they are the same word differing only by capitalisation.
                    # This check may seem unnecessary since the two lists are supposed
                    # to contain mutually exclusive collections of words. This may not
                    # always be so. For example 'kirk', the Scottish word for a church
                    # is not in the dictionary so would appear in 'suspect_words' while
                    # the name 'Kirk' IS in the dictionary hence would appear in the
                    # 'good_words/test_words' list.
                    if suspect_wordlc == test_wordlc:
                        continue
                    # Differ only by apparent plural
                    if (
                        suspect_wordlc == f"{test_wordlc}s"
                        or test_wordlc == f"{suspect_wordlc}s"
                    ):
                        continue
                    # If both words are a valid Roman numeral
                    suspect_worduc = suspect_wordlc.upper()
                    test_worduc = test_wordlc.upper()
                    if re.fullmatch(
                        r"(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})",
                        suspect_worduc,
                    ) and re.fullmatch(
                        r"(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})",
                        test_worduc,
                    ):
                        continue
                    # If both words are entirely numerals.
                    if re.match(
                        r"^\p{N}+$",
                        suspect_wordlc,
                    ) and re.match(
                        r"^\p{N}+$",
                        test_wordlc,
                    ):
                        continue

                    # Calculate Levenshtein distance
                    dist = distance(suspect_wordlc, test_wordlc, score_cutoff=2)

                    if dist == distance_to_check:
                        distance_check_results.append((suspect_wordlc, test_wordlc))

        ####
        # Executable section of enclosing function 'run_levenshtein_check_on_file'.
        ####

        # Start time of prgram execution
        prog_start = time.time()

        # Create the checker dialog to show results
        checker_dialog = CheckerDialog.show_dialog(
            "Levenshtein Edit Distance Check",
            rerun_command=lambda: levenshtein_check(project_dict),
        )
        frame = ttk.Frame(checker_dialog.header_frame)
        frame.grid(column=0, row=1, columnspan=2, sticky="NSEW")
        ttk.Label(
            frame,
            text="Edit Distance:",
        ).grid(row=0, column=1, sticky="NSE", padx=(0, 5))
        ttk.Radiobutton(
            frame,
            text="1",
            variable=self.edit_distance,
            value=LevenshteinEditDistance.ONE,
            takefocus=False,
        ).grid(row=0, column=2, sticky="NSE", padx=2)
        ttk.Radiobutton(
            frame,
            text="2",
            variable=self.edit_distance,
            value=LevenshteinEditDistance.TWO,
            takefocus=False,
        ).grid(row=0, column=3, sticky="NSE", padx=2)

        ToolTip(
            checker_dialog.text,
            "\n".join(
                [
                    "Left click: Select & find highlighted word in file",
                    "Right click: Remove line with highlighted word from list",
                    "Shift Right click: Also remove all matching lines from list",
                ]
            ),
            use_pointer_pos=True,
        )

        checker_dialog.reset()

        # Convert to int the edit distance used last time Levenshtein was run or default if first run.
        distance_to_check = 1
        if self.edit_distance.get() == "two":
            distance_to_check = 2

        # Build maps of the good words and the suspect words in the file.
        # Ideally should only do this once and not every time the tool is
        # rerun.
        map_words_in_file(project_dict)

        # For each suspect word, check against each good word in turn.
        # Very compute intensive. Where 90% of the execution time is consumed.
        distance_check_words()

        # Did distance_check_words() find any word pairs that met
        # the required Levenshtein criteria?
        if len(distance_check_results) == 0:
            # No.
            checker_dialog.add_entry("No Levenshtein edit distance queries reported")
            checker_dialog.add_entry("")
        else:
            # Yes.
            for result_tuple in distance_check_results:
                unpack_and_write_to_dialog(result_tuple)

        # Calculate and display execution time of run.
        prog_end = time.time()
        checker_dialog.add_footer(
            f"Execution time: {(prog_end - prog_start):.2f} seconds"
        )

        checker_dialog.display_entries()


def levenshtein_check(project_dict: ProjectDict) -> None:
    """Do Levenshtein edit distance checks"""

    global _the_levenshtein_checker

    if not tool_save():
        return

    if _the_levenshtein_checker is None:
        try:
            _the_levenshtein_checker = LevenshteinChecker()
        except DictionaryNotFoundError as exc:
            logger.error(f"Dictionary not found: {exc.file}")
            return

    _the_levenshtein_checker.run_levenshtein_check_on_file(project_dict)
