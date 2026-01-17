"""PPtxt tool"""

from dataclasses import dataclass
from tkinter import ttk
from typing import Dict, Sequence, List, Any
import regex as re

from guiguts.checkers import CheckerDialog
from guiguts.file import ProjectDict
from guiguts.maintext import maintext
from guiguts.misc_tools import tool_save
from guiguts.preferences import preferences, PrefKey, PersistentBoolean
from guiguts.utilities import IndexRowCol, IndexRange, non_text_line, sing_plur


class PPtxtCheckerDialog(CheckerDialog):
    """PPtxt dialog."""

    manual_page = "Tools_Menu#PPtxt"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize PPtxt dialog."""
        super().__init__(
            "PPtxt Results",
            tooltip="\n".join(
                [
                    "Left click: Select & find issue",
                    "Right click: Hide issue",
                    "Shift Right click: Hide all matching issues",
                ]
            ),
            **kwargs,
        )

        self.custom_frame.columnconfigure(0, weight=1)
        ttk.Checkbutton(
            self.custom_frame,
            text="Verbose",
            variable=PersistentBoolean(PrefKey.PPTEXT_VERBOSE),
        ).grid(row=0, column=0, sticky="NSW")

        frame = ttk.LabelFrame(self.custom_frame, text="Checks")
        frame.grid(row=1, column=0, sticky="NSEW")
        for col in range(0, 5):
            frame.columnconfigure(col, weight=1)

        for cnt, (prefkey, label) in enumerate(
            {
                PrefKey.PPTXT_FILE_ANALYSIS_CHECK: "File Analysis",
                PrefKey.PPTXT_SPACING_CHECK: "Paragraph Spacing",
                PrefKey.PPTXT_REPEATED_WORDS_CHECK: "Repeated Words",
                PrefKey.PPTXT_ELLIPSIS_CHECK: "Ellipses",
                PrefKey.PPTXT_CURLY_QUOTE_CHECK: "Curly Quotes",
                PrefKey.PPTXT_HYPHENATED_WORDS_CHECK: "Hyphenated Words",
                PrefKey.PPTXT_ADJACENT_SPACES_CHECK: "Adjacent Spaces",
                PrefKey.PPTXT_DASH_REVIEW_CHECK: "Hyphens/Dashes",
                PrefKey.PPTXT_SCANNO_CHECK: "Scannos",
                PrefKey.PPTXT_WEIRD_CHARACTERS_CHECK: "Uncommon Characters",
                PrefKey.PPTXT_HTML_CHECK: "HTML Tags",
                PrefKey.PPTXT_UNICODE_NUMERIC_CHARACTER_CHECK: "Numeric Entities",
                PrefKey.PPTXT_SPECIALS_CHECK: "Specials",
            }.items()
        ):
            ttk.Checkbutton(
                frame, variable=PersistentBoolean(prefkey), text=label
            ).grid(row=cnt // 5, column=cnt % 5, sticky="NSEW")


report_limit: int  # Max number of times to report same issue for some checks

found_long_doctype_declaration: bool
checker_dialog: PPtxtCheckerDialog
book: list[str]
word_list_map_count: dict[str, int]
word_list_map_lines: dict[str, list[int]]
word_list_map_words: list[list[str]]
# quote-type counters/flags
ssq: int
sdq: int
csq: int
cdq: int
longest_line: tuple[int, int]
shortest_line: tuple[int, int]


########################################################
# pptxt.py
# Perl author: Roger Franks (DP:rfrank) - 2009
# Go author: Roger Franks (DP:rfrank) - 2020
# Python author: Quentin Campbell (DP:qgc) - 2024
########################################################


@dataclass
class MsgInfo:
    """Class to store info for potential message.
    Stores message when found so can later be processed to avoid near duplicates."""

    msg: str
    text_range: IndexRange
    hilite_start: int
    hilite_end: int


re1 = re.compile(r"<!DOCTYPE")
re2 = re.compile(r"<(?=[!\/a-z]).*?(?<=[\"A-Za-z0-9\/]|-)>")
re3 = re.compile(r"&[a-z0-9#]+?;")
re4 = re.compile(r"&(\p{L}+)(\.)")
re5 = re.compile(r"&(\p{L}+)")
re6 = re.compile(r"\b[0-9]+\/[0-9]+\b")
re7 = re.compile(r"\[[0-9]+?\]|\[[0-9]+?[a-zA-Z]\]")
re8 = re.compile(r"_([\p{L}\p{P}])")
re9 = re.compile(r"([\p{L}\p{Nd}\p{P}])_\b")
re10 = re.compile(r"(\p{L})-(\p{L})")
re11 = re.compile(r"(\p{L})-(\p{L})")
re12 = re.compile(r"(\p{L})-( |$)")
re13 = re.compile(r"( |^)-(\p{L})")
re14 = re.compile(r"(\p{L})’(\p{L})")
re15 = re.compile(r"(\p{L})’(\p{L})")
re16 = re.compile(r"(\p{L})^(\p{L})")
re17 = re.compile(r"(\p{L})’-")
re18 = re.compile(r"(\p{L})-’(\p{L})")
re19 = re.compile(r"(?<=^| )’(\p{L})(?=$| )")
re20 = re.compile(r"(?<=^’)(\p{L})")
re21 = re.compile(r"(?<= ’)(\p{L})")
re22 = re.compile(r"(?<=^| )(\p{L})’(?=$| )")
re23 = re.compile(r"(\p{L})\.\-(\p{L})")
re24 = re.compile(r"--")
re25 = re.compile(r"[^\p{N}\p{L}]")
re26 = re.compile(r"①")
re27 = re.compile(r"②")
re28 = re.compile(r"⑤")
re29 = re.compile(r"⑥")
re30 = re.compile(r"⑦")


def get_words_on_line(line: str) -> list[str]:
    """Extract all the words on one line."""
    global found_long_doctype_declaration

    # Words may be surrounded by abandoned HTML tags, HTML entities,
    # Unicode numeric character references, etc. Remove these from
    # the line first of all so the word-types we want to record are
    # easier to identify.

    # A document starting with a "<!DOCTYPE>" declaration is assumed
    # to be an HTML file. We have to treat this HTML declaration
    # specially as it may overflow onto a second line in the case of
    # older documents (HTML 4 or XHTML). Check for this using the
    # variable 'found_long_doctype_declaration' which needs to exist
    # between calls of this function.

    if found_long_doctype_declaration:
        # Second line of a long <!DOCTYPE> declaration. Toss this 2nd line.
        found_long_doctype_declaration = False
        return []

    if re1.search(line, re.IGNORECASE) and ">" not in line:
        # Looks like a two-line <!DOCTYPE declaration. Toss this 1st line.
        # and set flag to toss the 2nd line too.
        found_long_doctype_declaration = True
        return []

    # A short HTML 5 <!DOCTYPE> declaration will not be detected
    # by the above tests. However it will be detected as an HTML
    # tag next and removed from line.
    line = re2.sub(" ", line)

    # &amp; &#1234;, etc. (&[a-z0-9#]+?;)
    # Replace HTML entities (e.g. &amp;) and numeric character references
    # (&#8212, &#x2014) with a space.
    line = re3.sub(" ", line)

    # Protect '&' in other tokens starting with '&'.
    # Order of subs below important.
    line = re4.sub(r"⑦\1⑤", line)
    line = re5.sub(r"⑦\1", line)

    # Replace 1/2-style fractions with space.
    line = re6.sub(" ", line)

    # Replace [99], [99a], etc., footnote anchors.
    line = re7.sub(" ", line)

    # Remove italic markup (_). Need to consider a two-line italic string.
    # _blah123... or _"blah123...
    line = re8.sub(r"\1", line)
    # ...blah_ or ...blah._ or ...blah"_ or ...blah."_, etc.
    line = re9.sub(r"\1", line)

    # Protect other special cases by masking them temporarily:
    # E.g.
    # high-flying, hasn’t, ’tis, Househ^d
    # all stay intact
    # Capitalisation is retained.
    # Additionally, an emdash separating words in, for
    # example, the ToC is replaced by a space.

    # Need these twice to handle alternates
    # E.g. fo’c’s’le

    # Newcastle-upon-Tyne
    line = re10.sub(r"\1①\2", line)
    line = re11.sub(r"\1①\2", line)
    # paring- or -in (hyphen followed/preceded by whitespace)
    line = re12.sub(r"\1①\2", line)
    line = re13.sub(r"\1①\2", line)
    # fo’c’s’le
    line = re14.sub(r"\1②\2", line)
    line = re15.sub(r"\1②\2", line)
    # House^d
    line = re16.sub(r"\1⑥\2", line)
    # loupin’-on, frien’-o’-mine
    line = re17.sub(r"\1②①", line)
    # by-’n-by
    line = re18.sub(r"\1①②\2", line)
    # by ’n by
    line = re19.sub(r"②\1", line)
    # ’tis at start of line
    line = re20.sub(r"②\1", line)
    # ’tis prefxed by a space
    line = re21.sub(r" ②\1", line)
    # Peep o’ Day (?<=^| )(\p{L})’(?=$| )
    line = re22.sub(r"\1②", line)
    # Lieut.-Col. (\p{L})\.\-(\p{L})
    line = re23.sub(r"\1⑤①\2", line)

    # If user is using "--" in place of emdash convert
    # that to a space so it can be a word separator.

    line = re24.sub(" ", line)

    # Replace all characters with " " other than letters, digits
    # and protected characters. Note that ①, ①, ... are 'numeric'
    # characters and are matched by \p{N}.

    line = re25.sub(" ", line)

    # Restore protected characters

    line = re26.sub(r"-", line)
    line = re27.sub(r"’", line)
    line = re28.sub(r".", line)
    line = re29.sub(r"^", line)
    line = re30.sub(r"&", line)

    # Create a list of whole words from the line.

    line_list = line.split()

    return line_list


######################################################################
# blank line spacing check
######################################################################


def spacing_check() -> None:
    """Blank line spacing check that flags other than 4121, 421 or 411 spacing."""

    checker_dialog.add_header(
        "----- Paragraph spacing check - expecting 4121, 421 or 411 spacing -------------"
    )

    # This routine does not use the line text at all. It is only concerned with
    # counting blank lines between paragraphs and other blocks/lines of text
    # looking for anomolous numbers of blank lines.
    #
    # It expects to see irregular line spacing (e.g. in title page, etc.)
    # until the first 4-line space is encountered. If no 4-line space is
    # found there will be no spacing counts output to the report. However
    # a warning message about this unusual situation is output.

    # Initialise, counters, flags, etc.
    bl_cnt = 0
    prev_line_was_bl = False
    prev_bl_cnt = 0
    bl_spacing_issues = []
    four_line_spacing_found = False
    no_other_spacing_issues = False

    for line_number, line in enumerate(book, start=1):
        if non_text_line(line):
            continue
        blank_line = re.match(r"^ *$", line)
        if blank_line:
            # Blank line.
            bl_cnt += 1
            prev_line_was_bl = True
        elif not blank_line and prev_line_was_bl:
            if bl_cnt == 3 or bl_cnt > 4:
                # i.e. 5..131.., 4..151.., etc, spacing.
                bl_spacing_issues.append((bl_cnt, line_number))
            elif bl_cnt == 4:
                four_line_spacing_found = True
                no_other_spacing_issues = True
            elif bl_cnt == 2:
                if prev_bl_cnt == 2:
                    # i.e. 4..1221..., etc, spacing.
                    bl_spacing_issues.append((bl_cnt, line_number))
            prev_bl_cnt = bl_cnt
            bl_cnt = 0
            prev_line_was_bl = False

    # Output to dialog any line spacing issues found. We have a list
    # of issue tuples: (int: spacing count, int: line number)

    for issue in bl_spacing_issues:
        no_other_spacing_issues = False
        # First value in an issue tuple is queried line spacing count.
        if issue[0] == 2:
            # Repeated 2-line spacing between paragraphs.
            error_text = "End point of repeated 2-line spacing."

            # There is no error as such on line in file. It is simply
            # the line that starts a paragraph after the queried blank
            # line spacing. Use the line_num.line_col string for start
            # of this line as the 'error' since that's what is highlighted
            # in the dialog text. It means the first few characters at the
            # start of the file line are selected when dialog message clicked.

            line_num = str(issue[1])
            line_col = str(0)
            error_start = line_num + "." + line_col
            error_end = line_num + "." + str(len(error_start))
            # Store in new structures for file row/col positions and ranges.
            start_rowcol = IndexRowCol(error_start)
            end_rowcol = IndexRowCol(error_end)
            # Build record to add to dialog.
            record = error_text
            # Add record to dialog. No highlighting.
            checker_dialog.add_entry(record, IndexRange(start_rowcol, end_rowcol))
        else:
            # Here for line count issues other than repeated 2-line spacing.
            error_text = f"End point of unexpected {issue[0]}-line spacing."

            # See comment above.

            line_num = str(issue[1])
            line_col = str(0)
            error_start = line_num + "." + line_col
            error_end = line_num + "." + str(len(error_start))
            # Store in new structures for file row/col positions and ranges.
            start_rowcol = IndexRowCol(error_start)
            end_rowcol = IndexRowCol(error_end)
            # Build record to add to dialog.
            record = error_text
            # Add error msg to dialog. No highlighting.
            checker_dialog.add_entry(record, IndexRange(start_rowcol, end_rowcol))

    if not four_line_spacing_found:
        checker_dialog.add_footer(
            "", "    No 4-line spacing found in book - that is unusual."
        )
    elif no_other_spacing_issues:
        checker_dialog.add_footer(
            "", "    Book appears to conform to DP paragraph/block spacing standards."
        )

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# repeated words check
######################################################################


def repeated_words_check() -> None:
    """Repeated words check."""

    checker_dialog.add_header(
        "----- Repeated words check - can be last word on a line and first on next ------"
    )

    # METHOD
    #
    # Uses the list of words on each line. For each word in the list it builds
    # a regex that searches for pairs of that word separated only by space chars.
    # After noting the start/end position of a repeated pair it obfuscates the
    # first word of the pair before repeating the search using the next word in the
    # list. That word could be the second word of the pair in which case the next
    # search of the line will find the same pair again if obsfucation is not used.
    #
    # A repeated word may be the last word on a line and its repeat the first word
    # on the next line. That is looked for and reported by a separate search.
    #
    # Searching with a regex is compute intensive and is also unnecessary for most
    # lines in the file if there is a quick and cheap way of identifying POSSIBLE
    # pairs of repeated words on a line. Only then is it necessary to use a regex
    # search on that line.
    #
    # Possible pairs of words are cheaply found by comparing each word in the list
    # of words on a line with the next word in the list. This is not determinative
    # of a pair of repeated words, only the possibility. For example, the list of
    # words on a line might contain 'very' followed by 'very'. If that arises from
    # parsing a line that includes "that's very, very true", the repeats of 'very'
    # in that case are not counted as repeated words. The regex search on that line
    # will determine whether such repeats are counted as 'repeated words' or not.

    # NOTE: This could potentially be simplified/improved using `findall` to get all
    # non-overlapping matches of "word word" on the line after adding the first word
    # of the next line. Or maybe slurp whole file, then search for "word \1".

    repeat_msg: list[MsgInfo] = []

    for rec_num, book_line in enumerate(book):
        words_on_line = word_list_map_words[rec_num]
        # Run through words found on a line looking for possible repeats. This quick
        # and cheap check eliminates most lines from being 'possibles'. Numbers are
        # eliminated at the same time; i.e. all-digit 'words'.
        no_numbers_words_on_line = []
        possibles = False
        wordn1 = ""
        for i in range(len(words_on_line) - 1):
            word = words_on_line[i]
            if re.match(r"^[\p{Nd}]+$", word):
                continue
            no_numbers_words_on_line.append(word)
            wordn1 = words_on_line[i + 1]
            # Chop apostrophe and following characters of second word.
            # E.g. "Jackey Jackey's". Note that "he had haddock" as a
            # possible from this edit will be eliminated by the more
            # restrictive regex comparison below using word boundaries.
            if word == wordn1[: len(word)]:
                possibles = True
        # Add last word on line to no_numbers_words_on_line if not a number.
        if len(words_on_line) > 1 and not re.match(r"^[\p{Nd}]+$", wordn1):
            no_numbers_words_on_line.append(wordn1)
        # There may be possible repeats of words (non-numbers) on line.
        if possibles:
            # For each word on line see if a copy follows separated only
            # by one or more spaces. These are the true repeated words.
            for word in no_numbers_words_on_line:
                # Build a regex.
                regx = f"(\\b{word}\\b +\\b{word}\\b)"
                if res := re.search(regx, book_line):
                    repl = " " * len(word)
                    # Obsfucate the first occurence of 'word' in the match so
                    # next re.search can't find it. It's replaced by blanks
                    # to the same length as 'word'.
                    book_line = re.sub(word, repl, book_line, pos=res.start(0), count=1)
                    # Get start/end of the repeated words in file.
                    error_start = str(rec_num + 1) + "." + str(res.start(0))
                    error_end = str(rec_num + 1) + "." + str(res.end(0))
                    # Store in structure for file row/col positions & range.
                    start_rowcol = IndexRowCol(error_start)
                    end_rowcol = IndexRowCol(error_end)
                    # Get whole of file line.
                    line = maintext().get(
                        error_start + " linestart", error_end + " lineend"
                    )
                    record = line
                    # Calculate start/end of repeated words in dialog message.
                    hilite_start = res.start(0)
                    hilite_end = res.end(0)
                    # Add message to dialog.
                    repeat_msg.append(
                        MsgInfo(
                            record,
                            IndexRange(start_rowcol, end_rowcol),
                            hilite_start,
                            hilite_end,
                        )
                    )

        # We may get here also if current line is a blank line.

        if len(no_numbers_words_on_line) > 0 and rec_num < len(book) - 1:
            # Completed determinative search of line for possible repeated words.
            # Now look at last word on the line and the first word of the next.
            word = no_numbers_words_on_line[-1]
            # If last word on current line is same as first word on next line then
            # this is also an instance of repeated words.
            regx1 = f"(\\b{word} *$)"
            regx2 = f"(^ *{word}\\b)"
            if (res1 := re.search(regx1, book[rec_num])) and (
                res2 := re.search(regx2, book[rec_num + 1])
            ):
                # Get start/end of the repeated words in file.
                error_start = str(rec_num + 1) + "." + str(res1.start(0))
                error_end = str(rec_num + 2) + "." + str(res2.end(0))
                # Store in structure for file row/col positions & range.
                start_rowcol = IndexRowCol(error_start)
                end_rowcol = IndexRowCol(error_end)
                # Get whole of file line.
                line = maintext().get(
                    error_start + " linestart", error_end + " lineend"
                )
                record = line
                # Calculate start/end of repeated words in dialog message.
                hilite_start = res1.start(0)
                # Since second repeated word is on next line just highlight
                # to end of current line.
                hilite_end = len(record)
                # Add message to dialog.
                repeat_msg.append(
                    MsgInfo(
                        record,
                        IndexRange(start_rowcol, end_rowcol),
                        hilite_start,
                        hilite_end,
                    )
                )

    # Only output the message if it's on a different line or a different word to the previous
    if repeat_msg:
        consolidate_messages(repeat_msg)
    else:
        checker_dialog.add_footer("", "    No repeated words found.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


def consolidate_messages(repeat_msg: list[MsgInfo], limit: int = 0) -> None:
    """Consolidate messages.

    Args:
        repeat_msg: List of messages to be consolidated.
        limit: If > 0, limit number of messages output.
    """
    prev_msg_info = None
    build_msg = None
    n_matches = 0
    n_messages = 0
    for msg_info in repeat_msg:
        # If this message doesn't match previous message, ignoring multiple spaces...
        if (
            prev_msg_info is None
            or msg_info.text_range.start.row != prev_msg_info.text_range.start.row
            or msg_info.msg != prev_msg_info.msg
            or re.sub(
                "  +",
                " ",
                msg_info.msg[msg_info.hilite_start : msg_info.hilite_end],
            )
            != re.sub(
                "  +",
                " ",
                prev_msg_info.msg[
                    prev_msg_info.hilite_start : prev_msg_info.hilite_end
                ],
            )
        ):
            # Output any combined message we've previously built up
            if build_msg is not None:
                # No more than 5 of any type unless verbose
                n_messages += 1
                if limit > 0 and n_messages >= limit + 1:
                    if n_messages == limit + 1:
                        checker_dialog.add_footer("  ...more")
                    continue

                repeat_str = f"(x{n_matches}) " if n_matches > 1 else ""
                checker_dialog.add_entry(
                    f"{repeat_str}{build_msg.msg}",
                    build_msg.text_range,
                    build_msg.hilite_start + len(repeat_str),
                    build_msg.hilite_end + len(repeat_str),
                )
            # Start a new build message
            build_msg = MsgInfo(
                msg_info.msg,
                msg_info.text_range,
                msg_info.hilite_start,
                msg_info.hilite_end,
            )
            n_matches = 1
        else:
            # "Duplicate" message - amend build message to cover whole relevant range
            assert build_msg is not None
            build_msg.text_range.end = msg_info.text_range.end
            build_msg.hilite_end = msg_info.hilite_end
            n_matches += 1
        prev_msg_info = msg_info
    # Output last message
    if build_msg is not None:
        n_messages += 1
        if limit > 0 and n_messages >= limit + 1:
            if n_messages == limit + 1:
                checker_dialog.add_footer("  ...more")
        else:
            repeat_str = f"(x{n_matches}) " if n_matches > 1 else ""
            checker_dialog.add_entry(
                f"{repeat_str}{build_msg.msg}",
                build_msg.text_range,
                build_msg.hilite_start + len(repeat_str),
                build_msg.hilite_end + len(repeat_str),
            )


######################################################################
# hyphenated/non-hyphenated words check
######################################################################


def hyphenated_words_check() -> None:
    """Repeated words check."""

    checker_dialog.add_header(
        "----- Hyphenated/non-hyphenated words check ------------------------------------"
    )

    first_header = True
    none_found = True

    for word in word_list_map_count:
        if re.search(r"-", word):
            word_with_hyphen = word
            # Hyphenated word found. Make a non-hyphenated version.
            word_with_no_hyphen = re.sub("-", "", word_with_hyphen)
            if word_with_no_hyphen in word_list_map_count:
                # Here when hyphenated and non-hyphenated version of a word.
                none_found = False
                word_count_with_no_hyphen = word_list_map_count[word_with_no_hyphen]
                word_count_with_hyphen = word_list_map_count[word_with_hyphen]
                # Make a header with this info and output it to dialog.
                # E.g. "sandhill (1) <-> sand-hill (3)".
                record = f"{word_with_no_hyphen} ({word_count_with_no_hyphen}) <-> {word_with_hyphen} ({word_count_with_hyphen})"
                # Insert a blank line before each header except the first one.
                if first_header:
                    first_header = False
                else:
                    checker_dialog.add_header("")
                # Add header record to dialog.
                checker_dialog.add_header(record)

                # Under the header add to the dialog every line containing an instance of the
                # hyphenated word. If more than 5 lines stop reporting them and warn, unless verbose.
                # If there are multiple instances of a word on a line then the line will appear in
                # the dialog multiple times, each time highlighting a different instance of word.
                #
                # We will do the same with the non-hyphenated version of the word.

                line_number_list = word_list_map_lines[word_with_hyphen]
                prev_line_number = -1
                template = "{}{}{}"
                regx = template.format("(", word_with_hyphen, "(?!\\p{L}))")
                count = 0
                for line_number in line_number_list:
                    # The same line number can appear multiple times in the list if the word in question
                    # appears multiple times on the line. Treat each appearance of the word separately.
                    # At the first time the line number appears in the list report all the occurrences
                    # on that line then ignore any other instances of that line number in the list.
                    if line_number == prev_line_number:
                        prev_line_number = line_number
                        continue
                    # Maybe limit the length of the report by reporting only first 5 lines for a word ...
                    if count == report_limit:
                        count = -1
                        break
                    # ... but note that a new dialog line is generated for each time the word appears
                    # on the line so there may be more than 5 dialog lines output
                    line = book[line_number - 1]
                    report_all_occurrences_on_line(regx, line, line_number)
                    count += 1
                    prev_line_number = line_number

                if count < 0:
                    checker_dialog.add_footer("  ...more")

                # We do the same for the non-hyphenated version of the word. Separate this
                # list of lines from the ones above with a rule. Maybe limit the number of lines
                # reported to report_limit (5 or 999999).

                checker_dialog.add_header("-----")

                line_number_list = word_list_map_lines[word_with_no_hyphen]
                prev_line_number = -1
                template = "{}{}{}"
                regx = template.format("((?<!-)", word_with_no_hyphen, "(?!\\p{L}))")
                count = 0
                for line_number in line_number_list:
                    # The same line number can appear multiple times in the list if the word in question
                    # appears multiple times on the line. Treat each appearance of the word separately.
                    # At the first time the line number appears in the list report all the occurrences
                    # on that line then ignore any other instances of that line number in the list.
                    if line_number == prev_line_number:
                        prev_line_number = line_number
                        continue
                    # Maybe limit the length of the report by reporting only first 5 lines for a word ...
                    if count == report_limit:
                        count = -1
                        break
                    # ... but note that a new dialog line is generated for each time the word appears
                    # on the line so there may be more than 5 dialog lines output.
                    line = book[line_number - 1]
                    report_all_occurrences_on_line(regx, line, line_number)
                    count += 1
                    prev_line_number = line_number

                if count < 0:
                    checker_dialog.add_footer("  ...more")

    if none_found:
        checker_dialog.add_footer("")
        checker_dialog.add_footer(
            "    No non-hyphenated versions of hyphenated words found."
        )

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# Unusual character check. Collects and reports lines that contain
# characters ('weirdos') not normally found in an an English text.
# Each 'weirdo' on a line in the dialog is highlighted.
######################################################################


def weird_characters_check() -> None:
    """Collects lines containing unusual characters. Lines in the report
    are grouped by unusual character and each instance of the character
    on a report line is highlighted."""

    checker_dialog.add_header(
        "----- Uncommon Characters ------------------------------------------------------"
    )

    first_header = True
    none_found = True

    weirdos_lines_dictionary: Dict[str, list[int]] = {}
    weirdos_counts_dictionary: Dict[str, int] = {}

    # If no curly quotes in file, don't consider straight quotes to be weirdos
    straight_quotes = "\"'" if csq + cdq == 0 else ""
    weirdo_regex = (
        r"[^A-Za-z0-9\s.,:;?!&\\\-_—–=“”‘’\[\]\(\){}¼½¾¹²³⁰⁴-⁹₀-₉⅐-⅞"
        + straight_quotes
        + "]"
    )

    # Build dictionary of unusual characters ('weirdos'). The key is a
    # weirdo and the value a list of line numbers on which that character
    # appears.
    for line_number, line in enumerate(book, start=1):
        if non_text_line(line):
            continue
        # Get list of weirdos on this line. That means any character NOT in the regex.
        weirdos_list = re.findall(weirdo_regex, line)
        # Update dictionary with the weirdos from the line.
        for weirdo in weirdos_list:
            # Skip exceptions
            # Thoughtbreak consists of 5 asterisks equally spaced,
            # and indented by at least 3 spaces.
            if weirdo == "*" and re.fullmatch(r" {3,}\*( {3,10}\*)\1\1\1", line):
                continue
            if weirdo in weirdos_lines_dictionary:
                weirdos_lines_dictionary[weirdo].append(line_number)
            else:
                weirdos_lines_dictionary[weirdo] = [line_number]

            if weirdo in weirdos_counts_dictionary:
                weirdos_counts_dictionary[weirdo] += 1
            else:
                weirdos_counts_dictionary[weirdo] = 1

    # Check whether to ignore Greek letters
    skip_greek = (
        sum(
            1
            for weirdo in weirdos_lines_dictionary
            if re.fullmatch(r"\p{Greek}", weirdo)
        )
        > 5
    )
    if skip_greek:
        checker_dialog.add_footer(
            "[Book contains over 5 different Greek letters so not reporting them]", ""
        )

    # If nothing in the dictioary, nothing to do!
    if len(weirdos_lines_dictionary) != 0:
        none_found = False
        for weirdo, line_list in weirdos_lines_dictionary.items():
            if skip_greek and re.fullmatch(r"\p{Greek}", weirdo):
                continue
            count = weirdos_counts_dictionary[weirdo]
            # Make a header with this info and output it to dialog.
            # E.g. "'¢' (3)".
            record = f"'{weirdo}' ({count})"
            # Insert a blank line before each header except the first one.
            if first_header:
                first_header = False
            else:
                checker_dialog.add_header("")
            # Add header record to dialog.
            checker_dialog.add_header(record)

            # Under the header add to the dialog every line containing an instance of the weirdo.
            # If there are multiple instances of a weirdo on a line then the line will appear in
            # the dialog multiple times, each time highlighting a different instance of it.

            prev_line_number = -1
            regx = "(" + "\\" + weirdo + ")"
            count = 0
            for line_number in line_list:
                # The same line number can appear multiple times in the list if the weirdo in question
                # appears multiple times on the line. Treat each appearance of the weirdo separately.
                # At the first time the line number appears in the list report all the occurrences
                # on that line then ignore any other instances of that line number in the list.
                if line_number == prev_line_number:
                    prev_line_number = line_number
                    continue
                # Maybe limit the length of the report by reporting only first 5 lines for a word ...
                if count == report_limit:
                    count = -1
                    break
                # ... but note that a new dialog line is generated for each time the word appears
                # on the line so there may be more than 5 dialog lines output.
                line = book[line_number - 1]
                report_multiple_occurrences_on_line(regx, line, line_number)

                count += 1
                prev_line_number = line_number

            if count < 0:
                checker_dialog.add_footer("  ...more")

    if none_found:
        checker_dialog.add_footer("", "    No unusual characters found.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# Specials check. Multiple checks done on each line during a single
# read of book lines.
######################################################################


def specials_check(project_dict: ProjectDict) -> None:
    """A series of textual checks done on a single read of the book lines."""

    checker_dialog.add_header(
        "----- Special situations checks ------------------------------------------------"
    )

    # METHOD
    #
    # Multiple checks are performed on each line during a single
    # pass through the book's lines. Thus reports of issues have
    # to be temporarily stored and only output to the dialog at
    # the end of the pass.
    #
    # Use a dictionary to collect reports on lines that contain
    # the 'specials' we are testing for. The keys are the report
    # headings (e.g. "full stop followed by letter") and the value
    # assigned to the key is a list containing one or more tuples
    # that contain the information needed to generate an appropriate
    # dialog message. Each tuple will add a dialog message to display.

    def process_line_with_pattern(
        pattern: str, exceptions: Sequence[str], line: str
    ) -> None:
        """Helper function for abstraction of processing logic.

        METHOD
        On a copy of the line passed in:
        1. Find all the exceptions and replace those matches
           with an obscure string of the same length.
        2. Find remaining matches of pattern in this obscured line.
        3. Highlight text in same position on actual line.
        """

        line_copy = line
        # This function is within the scope of specials_check() function from where it is called.
        line_number = line_index + 1
        for exception in exceptions:
            # Replace the exception with obscure string of same length.
            while res := re.search(exception, line_copy):
                # Obscuring symbol is a dentistry symbol (Hex 23c0, Dec 9152).
                line_copy = (
                    line_copy[: res.start(0)]
                    + "⏀" * (res.end(0) - res.start(0))
                    + line_copy[res.end(0) :]
                )

        # Exceptions on line obscured. Any remaining instances of
        # pattern are to be highlighted.
        # Use re.finditer() to generate a new dialog line for each time the pattern (the issue
        # being checked) appears on the line.

        for match_obj in re.finditer(pattern, line_copy):
            # Get start/end of error in file.
            error_start = str(line_number) + "." + str(match_obj.start(0))
            error_end = str(line_number) + "." + str(match_obj.end(0))
            # Highlight occurrence of word in the line.
            hilite_start = match_obj.start(0)
            hilite_end = match_obj.end(0)
            if heading not in specials_report:
                specials_report[heading] = []
            specials_report[heading].append(
                MsgInfo(
                    line, IndexRange(error_start, error_end), hilite_start, hilite_end
                )
            )

    def process_word(word: str, exceptions: Sequence[str], line: str) -> None:
        """Helper function for abstraction of processing logic.

        METHOD
        On the line passed in:
        1. Find the word on the line.
        2. Highlight text in same position on actual line.
        """

        # This function is within the scope of specials_check() function from where it is called.
        line_number = line_index + 1
        something_to_report = True
        for exception in exceptions:
            if re.match(exception, word):
                # Word matches an exception so nothing to report.
                something_to_report = False
                break
        # Report word if it is not an exception/empty exceptions list.
        if something_to_report:
            # Get all occurrences of word on this line and report them.
            # regx = f"\\b{word}\\b"
            regx = r"(?<!\p{L}|\p{Nd})" + word + r"(?!\p{L}|\p{Nd})"
            for match_obj in re.finditer(regx, line):
                # Get start/end of error in file.
                error_start = str(line_number) + "." + str(match_obj.start(0))
                error_end = str(line_number) + "." + str(match_obj.end(0))
                # Highlight occurrence of word in the line.
                hilite_start = match_obj.start(0)
                hilite_end = match_obj.end(0)
                if heading not in specials_report:
                    specials_report[heading] = []
                specials_report[heading].append(
                    MsgInfo(
                        line,
                        IndexRange(error_start, error_end),
                        hilite_start,
                        hilite_end,
                    )
                )

    specials_report: Dict[str, list[MsgInfo]] = {}

    ####
    # The following series of checks operate on text of each line.
    ####

    none_found = True

    # NOTE: Count from 0 rather than 1. Actual line number for book
    #       text will be line_index + 1.

    for line_index, line in enumerate(book):
        if non_text_line(line):
            continue
        exceptions: List[str] = []
        # Allow Illustrations, Greek, Music or number in '[]'
        heading = "Opening square bracket followed by other than I, G, M, S or digit."
        exceptions.append(r"\[Blank Page\]")
        process_line_with_pattern(r"\[[^IGMS\d]", exceptions, line)

        # Clear out the exceptions for the previous check.
        exceptions = []

        # Don't allow 'Blank Page'
        heading = "Blank Page place holder found."
        process_line_with_pattern(r"\[Blank Page\]", exceptions, line)

        # Mixed hyphen/dash in line"
        heading = "Mixed hyphen/dash in line."
        process_line_with_pattern(r"—-|-—|–-|-–", exceptions, line)

        # Non-breaking space in line
        heading = "Non-breaking space."
        process_line_with_pattern(r"\u00A0", exceptions, line)

        # Soft hyphen in line
        heading = "Soft hyphen in line."
        process_line_with_pattern(r"\u00AD", exceptions, line)

        # Tab character in line
        heading = "Tab character in line."
        process_line_with_pattern(r"\u0009", exceptions, line)

        # Ampersand character in line (excluding unicode numeric character references and '&c.')
        exceptions.append(r"&c\.")
        heading = "Ampersand character in line (excluding '&c.' and unicode numeric character references)."
        process_line_with_pattern(r"&(?!#)", exceptions, line)

        # Clear out the exceptions for the previous check.
        exceptions = []

        # Single character line
        heading = "Single character line."
        process_line_with_pattern(r"^[^]]$", exceptions, line)

        # Broken hyphenation
        heading = "Broken hyphenation."
        process_line_with_pattern(
            r"(\p{L}\- +?\p{L})|(\p{L} +?\-\p{L})", exceptions, line
        )

        # Comma spacing regexes
        heading = "Comma spacing."
        process_line_with_pattern(r"\p{L},\p{L}|\p{L},\p{N}|\s,|^,", exceptions, line)

        # Oct. 8,2023 date fotmat
        heading = "Date format."
        process_line_with_pattern(r",[12]\p{Nd}{3}", exceptions, line)

        # I in place of intended !
        heading = "I/! check."
        process_line_with_pattern(r"I”", exceptions, line)

        # Disjointed contraction. E.g "I 've"
        heading = "Disjointed contraction."
        process_line_with_pattern(r"[A-Za-z]’ +?(m|ve|ll|t)\b", exceptions, line)

        # Title/honorific abbreviations
        heading = "Title abbreviation + comma."
        process_line_with_pattern(
            r"Mr,|Mrs,|Dr,|Drs,|Messrs,|Ms,|Hon,|Prof,", exceptions, line
        )

        # Spaced punctuation
        heading = "Spaced punctuation."
        # Exclude sequences of " ... ", etc.
        exceptions.append(r"(?<=\s|^)\.\.\.(?=\s|$)")
        # " .14567" is permitted, i.e. followed by digit
        exceptions.append(r"(?<=\s|^)\.(?=\d)")
        process_line_with_pattern(r"\s[\?!:;\.]", exceptions, line)

        # Clear out the exceptions for the previous check.
        exceptions = []

        # Abbreviation &c without period
        heading = "Abbreviation &c. without period."
        process_line_with_pattern(r"&c(?= |$)", exceptions, line)

        # Line starts with (selected) punctuation
        heading = "Line start with suspect punctuation."
        process_line_with_pattern(r"^[!;:,.?]", exceptions, line)

        # Line starts with hyphen followed by non-hyphen
        heading = "Line start with hyphen and then non-hyphen."
        process_line_with_pattern(r"^-[^-]", exceptions, line)

        # The following check for standalone 0 consists of:
        #
        # GENERAL TEST
        pattern = r"\b0\b"
        if re.search(pattern, line):
            # Here if possible issue.
            #
            # EXCEPTIONS
            #
            # NB Each regex below returns the pattern in a match
            #    as group(0).
            exceptions = []
            # standalone 0 allowed after dollar/pound sign; E.g. $0 25.
            exceptions.append(r"(?<=[\$£])(0)(?=$|\P{Nd})")
            # 0.123 or 29.0 or 0°
            exceptions.append(r"\b(0)(?=\.)")
            exceptions.append(r"(?<=\.)(0)\b")
            exceptions.append(r"\b(0)(?=°)")
            # Generate dialog tuples only if not an exception.
            heading = "Standalone 0 (excluding exceptions)."
            process_line_with_pattern(pattern, exceptions, line)

        # The following check for standalone 1 consists of:
        #
        # GENERAL TEST
        pattern = r"(?<=^|\P{Nd})(1)(?=$|\P{N})"
        # NB should be equivalent to r"\b1\b"
        if re.search(pattern, line):
            # Here if possible issue.
            #
            # EXCEPTIONS
            #
            # NB Each regex below returns the pattern in a match
            #    as group(0).
            exceptions = []
            # standalone 1 allowed after dollar/pound sign.
            exceptions.append(r"(?<=[\$£])(1)(?=$|\P{Nd})")
            # standalone 1 allowed before comma.
            exceptions.append(r"(?<=^|\P{Nd})(1)(?=,)")
            # standalone 1 allowed before dash+num.
            exceptions.append(r"(?<=^|\P{Nd})(1)(?=[-‑‒–—―]\p{Nd})")
            # standalone 1 allowed after num+dash.
            exceptions.append(r"(?<=\p{Nd}[-‑‒–—―])(1)(?=$|\P{Nd})")
            # 1.nnn or nnn.1 or 1°
            exceptions.append(r"\b(1)(?=\.)")
            exceptions.append(r"(?<=\.)(1)\b")
            exceptions.append(r"\b(1)(?=°)")
            # standalone 1 allowed as "1st".
            exceptions.append(r"(?<=^|\P{Nd})(1)st")
            # standalone 1 allowed as a footnote anchors
            exceptions.append(r"\[(1)\]")
            # Make exceptions of 1s. (1 shilling) and 1d. (1 pence/penny).
            exceptions.append(r"\b1d\.")
            exceptions.append(r"\b1s\.")
            # Generate dialog tuples only if not an exception.
            heading = "Single '1' in a word or a standalone '1' (excluding exceptions)."
            process_line_with_pattern(pattern, exceptions, line)

        # The following check for punctuation after case-insensitive 'the' consists of:
        #
        # GENERAL TEST
        pattern = r"(?i)\bthe\p{P}"
        if re.search(pattern, line):
            # Here if possible issue.
            #
            # EXCEPTIONS
            #
            # NB Each regex below returns the pattern in a match
            #    as group(0).
            exceptions = []
            # Ignore contexts such as "Will-o’-the-wisp"
            exceptions.append(r"(?i)-the-")
            # Ignore contexts such as "the’re", "the’ve"
            exceptions.append(r"(?i)\bthe[’ve|’re]")
            # Ignore "the," - checked below with a limit
            exceptions.append(r"(?i)\bthe,")
            # Generate dialog tuples only if not an exception.
            heading = "Punctuation after 'the' (excluding exceptions)."
            process_line_with_pattern(pattern, exceptions, line)

        # Check for comma after case-insensitive 'the'
        pattern = r"(?i)\bthe,"
        if re.search(pattern, line):
            exceptions = []
            heading = "Comma after 'the'."
            process_line_with_pattern(pattern, exceptions, line)

        # The following check for double punctuation consists of:
        #
        # GENERAL TEST
        pattern = r",\.|,,|(?<!\.)\.\.(?!\.)"
        if re.search(pattern, line):
            # Here if possible issue.
            #
            # EXCEPTIONS
            #
            # NB Each regex below returns the pattern in a match
            #    as group(0).
            exceptions = []
            # Ignore contexts such as 4-dot ellipsis
            exceptions.append(r"(?i)etc\.{4}(?!\.)")
            # Exclude sequences of " ... ", etc.
            exceptions.append(r"(?<=\s|^)\.\.\.(?=\s|$)")
            # Generate dialog tuples only if not an exception.
            heading = "Query double punctuation (excluding exceptions)."
            process_line_with_pattern(pattern, exceptions, line)

        # The following check for period-comma consists of:
        #
        # GENERAL TEST
        pattern = r"\.,"
        if re.search(pattern, line):
            exceptions = []
            # Ignore contexts such as "etc.,", "&c.,"
            exceptions.append(r"(?i)etc\.,")
            exceptions.append(r"(?i)&c\.,")
            # Generate dialog tuples only if not an exception.
            heading = "Query period-comma (excluding exceptions)."
            process_line_with_pattern(pattern, exceptions, line)

        # Unexpected comma check. Commas should not occur after these words:
        pattern = (
            r"(?i)\bit’s,|\btheir,|\ban,|\ba,|\bour,|\bthat’s,|\bits,|\bwhose,|\bevery,"
            r"|\bi’ll,|\byour,|\bmy,|\bmr,|\bmrs,|\bmss,|\bmssrs,|\bft,|\bpm,|\bst,|\bdr,|\brd,|\bpp,|\bcf,"
            r"|\bjr,|\bsr,|\bvs,|\blb,|\blbs,|\bltd,|\bi’m,|\bduring,|\blet,|\btoward,|\bamong,"
        )
        # Generate dialog tuples for pattern, ignoring exceptions.
        exceptions = []
        heading = "Query unexpected comma after certain words."
        process_line_with_pattern(pattern, exceptions, line)

        # Unexpected period check. Periods should not occur after these words:
        pattern = (
            r"(?i)\bevery\.|\bi’m\.|\bduring\.|\bthat’s\.|\bthis’s\.|\btheir\.|\byour\.|\bour\.|\bmy\.|\bor\."
            r"|\band\.|\bbut\.|\bas\.|\bif\.|\bits\.|\bit’s\.|\buntil\.|\bthan\.|\bwhether\.|\bi’ll\."
            r"|\bwhose\.|\bwho\.|\bbecause\.|\bwhen\.|\blet\.|\btill\.|\bvery\.|\ban\.|\bamong\."
            r"|\binto\.|\bwhom\.|\bhaving\.|\bthence\."
        )
        # Generate dialog tuples for pattern, ignoring exceptions.
        exceptions = []
        heading = "Query unexpected period after certain words."
        process_line_with_pattern(pattern, exceptions, line)

        ##
        # The following series of checks operate on individual words
        # on the line.
        ##

        # We already have a list of words for this line. Note that
        # words are stripped of all punctuation except curly apostrophe.
        # Thus &c. 1s. and 1d. on a line will appear as &c 1s and 1d
        # in the list. Similarly "word" appears as word in the list but
        # word’s has the apostrophe preserved and will appears as word’s
        # in the list.

        already_checked = []
        for word in word_list_map_words[line_index]:
            if word in already_checked:
                # Word has occurred again on the line but it has
                # already been reported on. Don't repeat reports.
                continue

            # Looks for mixed case within word but not if the word is in
            # the good words list or occurs more than once in the book.

            if word_list_map_count[word] == 1 and word not in project_dict.good_words:
                if re.search(r".\p{Ll}+(?<!-)\p{Lu}", word):
                    # NB word occurs only once in the book and isn't in good_words.
                    # Generate dialog tuples.
                    heading = (
                        "Mixed case in word (excluding words in project dictionary)."
                    )
                    process_word(word, [], line)

            # Word start and word endings checks.

            if len(word) > 2:
                # Check word ending (last 2 characters).
                last2 = word[len(word) - 2 :]
                # The following pairs of characters are very rare at word end.
                if (
                    re.match(
                        "cb|gb|pb|sb|tb|wh|fr|br|qu|tw|gl|fl|sw|gr|sl|cl|iy",
                        last2,
                        re.IGNORECASE,
                    )
                    and word not in project_dict.good_words
                ):
                    # Generate dialog tuples.
                    heading = f"Query word ending with '{last2}' (excludes words in project dictionary)."
                    process_word(word, [], line)

                # Check word start (first 2 characters)
                first2 = word[0:2]

                # The following pairs of characters are very rare at start of word.
                if (
                    re.match("hr|hl|cb|sb|tb|wb|tl|tn|rn|lt|tj", first2, re.IGNORECASE)
                    and word not in project_dict.good_words
                ):
                    # Generate dialog tuples.
                    heading = f"Query word starting with '{first2}' (excludes words in project dictionary)."
                    process_word(word, [], line)

            # The following check for mixed letters/digits in word consists of:
            #
            # GENERAL TEST
            pattern = r"\p{L}+\p{Nd}+|\p{Nd}+\p{L}+"
            if re.search(pattern, word):
                # Here if possible issue.
                #
                # EXCEPTIONS
                #
                # NB Each regex below returns the pattern in a match
                #    as group(0).
                exceptions = []
                # E.g. 191st
                exceptions.append(r"(?i)\b(\p{Nd}*[02-9]1st|1st)\b")
                # E.g. 282nd
                exceptions.append(r"(?i)\b(\p{Nd}*[02-9]2nd|2nd)\b")
                # E.g. 373rd
                exceptions.append(r"(?i)\b(\p{Nd}*[02-9]3rd|3rd)\b")
                # E.g. 373d
                exceptions.append(r"(?i)\b\p{Nd}*[23]d\b")
                # E.g. 65th
                exceptions.append(r"(?i)\b\p{Nd}*[4567890]th\b")
                # E.g. 511th, 212th, 13th
                exceptions.append(r"(?i)\b\p{Nd}*1[123]th\b")
                # Make exceptions of references to amounts in shillings
                # and pence. E.g. £1 9s. 11d. Note that parsing a line
                # into words strips punctuation except curly apostrophe
                # so value of 'word' here would be '9s' & '11d'. Hence
                # possibility of occasional false negatives.
                if re.fullmatch(r"\p{Nd}{1,2}[sd]", word):
                    exceptions.append(word)
                # Generate dialog tuples only if not an exception.
                heading = "Query mixed letters/digits in word (excluding exceptions)."
                # NB 'heading' is accessed in the 'process_word' function
                #    which is in same scope. flake8 complains about it.
                process_word(word, exceptions, line)

            # If the word occurs again on this line we will not
            # repeat the checks.
            already_checked.append(word)

    # Done with specials checks. Report what, if anything, we've found.

    # Produce dialog lines from the dialog MsgInfos generated by
    # the checks above. The specials_report dictionary may be
    # empty in which case there will be no dialog messages.
    first_header = True
    for header_line, msg_list in specials_report.items():
        none_found = False
        # Insert a blank line before each header except the first one.
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        # Add header record to dialog.
        checker_dialog.add_header(header_line)
        # Some checks have a limit for how many times to report
        limit = (
            report_limit
            if header_line
            in (
                "Comma after 'the'.",
                "Query period-comma (excluding exceptions).",
                "Single '1' in a word or a standalone '1' (excluding exceptions).",
            )
            else 0
        )
        consolidate_messages(msg_list, limit=limit)

    if none_found:
        checker_dialog.add_footer("")
        checker_dialog.add_footer("    No special situations reports.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# abandoned HTML tag check
######################################################################


def html_check() -> None:
    """Abandoned HTML tag check."""

    checker_dialog.add_header(
        "----- Abandoned HTML tag check -------------------------------------------------"
    )

    # Courtesy limit if user uploads fpgen source, etc.
    courtesy_limit = 5
    abandoned_html_tag_count = 0
    lines_with_html_tags = 0

    regx = r"<(?=[!\/a-z]).*?(?<=[\"A-Za-z0-9\/]|-)>"
    for line_number, line in enumerate(book, start=1):
        if non_text_line(line):
            continue
        if re.search(regx, line):
            # Generate a new dialog line for each tag on the line, keeping
            # count of total tags found over all the lines reported.
            abandoned_html_tag_count += report_all_occurrences_on_line(
                regx, line, line_number
            )
            lines_with_html_tags += 1

        # If abandoned_HTML_tag_count > courtesy_limit then it looks like we are
        # not dealing with a plain text file after all. Flag this and report the
        # number of HTML tags found so far then exit loop.

        if abandoned_html_tag_count > courtesy_limit:
            record = f"Source file not plain text: {lines_with_html_tags} book lines with {abandoned_html_tag_count} markup instances so far..."
            checker_dialog.add_footer("", record, "...abandoning check.")
            # Don't search any more book lines for HTML tags.
            break

    # All book lines scanned or scanning abandoned.
    if abandoned_html_tag_count == 0:
        checker_dialog.add_footer("", "    No abandoned HTML tags found.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# Unicode numeric character references check.
######################################################################


def unicode_numeric_character_check() -> None:
    """Unicode numeric character references check."""

    checker_dialog.add_header(
        "----- Unicode numeric character references check -------------------------------"
    )

    # Courtesy limit if user uploads fpgen source, etc.
    courtesy_limit = 5
    numeric_char_reference_count = 0
    lines_with_numeric_char_references = 0

    regx = r"(&#[0-9]{1,5};|&#x[0-9a-fA-F]{1,4};)"
    for line_number, line in enumerate(book, start=1):
        if non_text_line(line):
            continue
        if re.search(regx, line):
            # Generate a new dialog line for each match on the line, keeping
            # count of number of character references encountered.
            numeric_char_reference_count += report_all_occurrences_on_line(
                regx, line, line_number
            )
            lines_with_numeric_char_references += 1

        # If numeric_char_reference_count > courtesy_limit then it looks like we are
        # not dealing with a plain text file afterall. Flag this and report the
        # number of numeric character references found so far then exit loop.

        if numeric_char_reference_count > courtesy_limit:
            checker_dialog.add_entry("")
            record = f"Source file not plain text: {lines_with_numeric_char_references} book lines with {numeric_char_reference_count} unicode numeric character references so far..."
            checker_dialog.add_entry(record)
            checker_dialog.add_entry("...abandoning check.")
            # Don't search any more book lines for numeric character references.
            break

    # All book lines scanned.
    if numeric_char_reference_count == 0:
        checker_dialog.add_footer(
            "", "    No unicode numeric character references found."
        )

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# Scan book for two or more adjacent spaces on a line that
# does not start with a space
######################################################################


def adjacent_spaces_check() -> None:
    """Scans text of each book line for adjacent spaces."""

    checker_dialog.add_header(
        "----- Adjacent spaces check (poetry, block-quotes, etc., are ignored) ----------"
    )

    # If the line starts with one or more spaces (poetry, block-quotes, etc.,
    # adjacent spaced will not be reported.

    no_adjacent_spaces_found = True

    for line_number, line in enumerate(book, start=1):
        if non_text_line(line):
            continue
        #  Spaced poetry, block-quotes, etc., will fail the 'if' below.

        # If adjacent spaces but no leading spaces then ...
        if re.search(r"\s\s+?", line) and not re.search(r"^\s+?", line):
            no_adjacent_spaces_found = False
            # Generate a new dialog line for each match on the line.
            report_multiple_occurrences_on_line(r"\s\s+", line, line_number)

    # All book lines scanned.
    if no_adjacent_spaces_found:
        checker_dialog.add_footer("", "    No lines with adjacent spaces found.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


def double_dash_replace(matchobj: re.Match) -> str:
    """Called to replace exactly 2 emdashes by 1 emdash.

    Args:
        matchobj: A regex match object.
    """

    return matchobj.group(1) + "—" + matchobj.group(2)


def report_multiple_occurrences_on_line(
    pattern: str, line: str, line_number: int, flags: int = 0
) -> None:
    """Report multiple occurrences in one message for this line.

    Args:
        pattern: A regex of the pattern to be matched and highlighted.
        line: The string on which to match the pattern.
        line_number: The line number of the line in the file.
    """

    matches = list(re.finditer(pattern, line, flags=flags))
    if not matches:
        return
    # Get start/end of first/last error on line.
    error_start = matches[0].start()
    error_end = matches[-1].end()
    # Add record to the dialog with prefix if repeated matches.
    repeat_str = f"(x{len(matches)}) " if len(matches) > 1 else ""
    checker_dialog.add_entry(
        f"{repeat_str}{line}",
        IndexRange(f"{line_number}.{error_start}", f"{line_number}.{error_end}"),
        error_start + len(repeat_str),
        error_end + len(repeat_str),
    )


def report_all_occurrences_on_line(pattern: str, line: str, line_number: int) -> int:
    """Abstraction of dialog code that's used repeatedly for reporting.

    Args:
        pattern: A regex of the pattern to be matched and highlighted.
        line: The string on which to match the pattern.
        line_number: The line number of the line in the file.
    """

    count_of_matches = 0
    for match_obj in re.finditer(pattern, line):
        # Get start/end of error in file.
        error_start = str(line_number) + "." + str(match_obj.start(0))
        error_end = str(line_number) + "." + str(match_obj.end(0))
        # Store in structure for file row/col positions & ranges.
        start_rowcol = IndexRowCol(error_start)
        end_rowcol = IndexRowCol(error_end)
        # Highlight occurrence of word in the line.
        hilite_start = match_obj.start(0)
        hilite_end = match_obj.end(0)
        # Add record to the dialog.
        checker_dialog.add_entry(
            line,
            IndexRange(start_rowcol, end_rowcol),
            hilite_start,
            hilite_end,
        )
        count_of_matches += 1

    return count_of_matches


######################################################################
# ellipses check
######################################################################


def ellipsis_check() -> None:
    """Ellipses check."""

    checker_dialog.add_header(
        "----- Ellipsis check -----------------------------------------------------------"
    )

    # It checks for:
    #
    #    3-dot ellipses without a space or opening double quote before them
    #    E.g. “... Him the Almighty Power
    #    3-dot ellipses followed by full-stop and no trailing space
    #      (AKA 4-dot ellipses)
    #    2-dot ellipses
    #    5-or-more-dot ellipses
    #
    # and highlights the suspect ellipsis.

    # The comments and code below are a direct implementation in Python
    # of code written in Go by Roger Franks (rfranks).

    no_suspect_ellipsis_found = True

    # Eliminate correct ellipsis then any sequence of two or more
    # period ('.') characters left on line are highighted as suspect.

    for line_number, line in enumerate(book, start=1):
        if non_text_line(line):
            continue
        line_copy = line
        # Obscure correct 4-dot ellipsis with space of same lenth.
        line_copy = re.sub(r"(\p{L})(\.\.\.\.(?= |$))", r"\1    ", line_copy)
        # Obscure correct 3-dot ellipsis with space of same lenth.
        line_copy = re.sub(r"(?<= |“)\.\.\.(?= )", r"   ", line_copy)
        # Any sequence of two or more period characters are suspect so
        # highlight those sequences.
        pattern = r"\.\.+"
        # Find any remaining 'ellipsis' on edited line ...
        if re.search(pattern, line_copy):
            no_suspect_ellipsis_found = False
            # Note we search line copy ...
            for match_obj in re.finditer(pattern, line_copy):
                # Get start/end of error in file.
                error_start = str(line_number) + "." + str(match_obj.start(0))
                error_end = str(line_number) + "." + str(match_obj.end(0))
                # Store in structure for file row/col positions & ranges.
                start_rowcol = IndexRowCol(error_start)
                end_rowcol = IndexRowCol(error_end)
                # Highlight occurrence of word in the line.
                hilite_start = match_obj.start(0)
                hilite_end = match_obj.end(0)
                # ... but report original line when adding record to the dialog.
                checker_dialog.add_entry(
                    line,
                    IndexRange(start_rowcol, end_rowcol),
                    hilite_start,
                    hilite_end,
                )

    if no_suspect_ellipsis_found:
        checker_dialog.add_footer("", "    No suspect ellipsis found.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# curly quote check (positional, not using a state machine)
######################################################################


def curly_quote_check() -> None:
    """Curly quote check."""

    checker_dialog.add_header(
        "----- Basic (positional) curly-quote check -------------------------------------"
    )

    # Report floating quotes - “” and ‘’ types.

    first_match = True
    no_suspect_curly_quote_found = True
    pattern = r"""
    # === Case A: Match “ ‘ ’ when spaced — always wrong ===
    (?<=\ )[“‘’](?=\ )         |  # space on both sides
    ^[“‘’](?=\ )               |  # start of line, space after
    (?<=\ )[“‘’]$              |  # space before, end of line
    # === Case B: Match ” unless ditto-style (2+ spaces or line start/end on BOTH sides) ===
    (?<= (?<!\s)\s )”(?=\s+)   |  # Exactly one space before, 1+ spaces after
    (?<=\s+)”(?= \s(?!\s) )    |  # 1+ spaces before, exactly one space after
    ^”(?= \s(?!\s) )           |  # start of line, exactly one space after
    (?<= (?<!\s)\s )”$            # exactly one space before, end of line    (
    """

    for line_number, line in enumerate(book, start=1):
        if non_text_line(line):
            continue
        if re.search(pattern, line, flags=re.VERBOSE):
            if first_match:
                first_match = False
                checker_dialog.add_header("floating quote (single or double)")
            report_multiple_occurrences_on_line(
                pattern, line, line_number, flags=re.VERBOSE
            )
            no_suspect_curly_quote_found = False

    # Report 'wrong direction' quotes

    first_match = True

    for line_number, line in enumerate(book, start=1):
        if non_text_line(line):
            continue
        # if |some text.“| or |some text‘| or |”some text|
        pattern = r"(?<=[\.,;!?])[‘“]"
        if re.search(pattern, line):
            if first_match:
                first_match = False
                checker_dialog.add_header("quote direction")
            report_all_occurrences_on_line(pattern, line, line_number)
            no_suspect_curly_quote_found = False
        pattern = r"(?<=\p{L})[\‘\“]"
        if re.search(pattern, line):
            if first_match:
                first_match = False
                checker_dialog.add_header("quote direction")
            report_all_occurrences_on_line(pattern, line, line_number)
            no_suspect_curly_quote_found = False
        pattern = r"”(?=[\p{L}])"
        if re.search(pattern, line):
            if first_match:
                first_match = False
                checker_dialog.add_header("quote direction")
            report_all_occurrences_on_line(pattern, line, line_number)
            no_suspect_curly_quote_found = False

    if no_suspect_curly_quote_found:
        checker_dialog.add_footer("", "    No suspect curly quotes found.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# quote type checks
######################################################################


def file_analysis_check() -> None:
    """Check for mixed straight/curly quotes & line lengths."""

    checker_dialog.add_header(
        "----- File analysis check -------------------------------------------------------",
        "",
    )

    # Any straight single/double quotes?
    if ssq > 0 or sdq > 0:
        # Yep, so what about any curly single and double quotes?
        if csq == 0 and cdq == 0:
            checker_dialog.add_header("Only straight quotes found in this file.")
        elif csq > 0 or cdq > 0:
            checker_dialog.add_header(
                "Both straight and curly quotes found in this file."
            )
    elif (ssq == 0 and sdq == 0) and (csq > 0 or cdq > 0):
        checker_dialog.add_header("Only curly quotes found in this file.")
    elif ssq == 0 and sdq == 0 and csq == 0 and cdq == 0:
        checker_dialog.add_header(
            "No single or double quotes of any type found in file - that is unusual."
        )
    checker_dialog.add_footer("")

    if longest_line[1] > 0:
        pos = maintext().rowcol(f"{longest_line[0]}.0")
        checker_dialog.add_entry(
            f"Longest line - {sing_plur(longest_line[1], 'character')}",
            IndexRange(pos, pos),
        )
    if shortest_line[1] > 0:
        pos = maintext().rowcol(f"{shortest_line[0]}.0")
        checker_dialog.add_entry(
            f"Shortest line - {sing_plur(shortest_line[1], 'character')}",
            IndexRange(pos, pos),
        )
    checker_dialog.add_footer("")


######################################################################
# dash review
######################################################################


def dash_review_check() -> None:
    """Hyphen/dashes check."""

    checker_dialog.add_header(
        "----- Hyphen/dashes check (one or more present on line) ------------------------"
    )

    # The algorithm used below is adopted from the one Roger Franks uses in
    # his Go version of PPTXT for the PPWB. It makes a copy of the book and
    # runs multiple passes over the copy. The first set of passes protects
    # what is allowed by removing them from line. The final pass categorises
    # any dashes that remain and flags them in the report.

    ####
    # In the PPWB Go version of PPTXT, Roger qualifies and protects the following
    # dash characters & sequences:
    #    - hyphen-minus (keyboard "-")
    #              allow these between two letters [\p{L}-\p{L}]
    #              allow 8 or more of these as a separator [-{8,}]
    #    ‐ hyphen
    #              allow these between two letters [\p{L}‐\p{L}]
    #              allow 8 or more of these as a separator [‐{8,}]
    #    ‑ non-breaking hyphen
    #              allow these between two letters [\p{L}‐\p{L}]
    #    ‒ figure dash (i.e. to connect digits in a phone number)
    #              allow these between two numbers [\p{Nd}‒\p{Nd}]
    #    – en dash (to show a range of numbers)
    #              allow these between two numbers \p{Nd}–\p{Nd}
    #              allow these between two numbers \p{Nd}\s–\s\p{Nd}
    #    — em dash
    #              allow patterns:
    #                   [\p{L}—\p{L}] between letters with no spacing
    #                       My favorite food—pizza—originated in Italy.
    #                       My granddaughter—Kenzie—plays volleyball.
    #                   [\p{Ll}—\p{P}] between lower-case letter and punctuation
    #                       “What if we—”
    #                   \p{Ll}— \p{Lu} lower-case letter, en dash, space, upper-case letter
    #                       If you tell him— Wait, I will give you this.
    #
    # These are dash characters that will be flagged if not in circumstances listed above:
    #   - HYPHEN-MINUS
    #   ‐ HYPHEN
    #   ‑ NON-BREAKING HYPHEN
    #   ‒ FIGURE DASH
    #   – EN DASH
    #   — EM DASH
    #
    # The following are among dash characters that will always be flagged:
    #   ֊ ARMENIAN HYPHEN
    #   ־ HEBREW PUNCTUATION MAQAF
    #   ᐀ CANADIAN SYLLABICS HYPHEN
    #        ᠆    MONGOLIAN TODO SOFT HYPHEN
    #   ― HORIZONTAL BAR
    #   ⸗ DOUBLE OBLIQUE HYPHEN
    #   ⸚ HYPHEN WITH DIAERESIS
    #   ⸺ TWO-EM DASH
    #   ⸻ THREE-EM DASH
    #   ⹀ DOUBLE HYPHEN
    #   〜 WAVE DASH
    #   〰 WAVY DASH
    #   ゠ KATAKANA-HIRAGANA DOUBLE HYPHEN
    #   ︱ PRESENTATION FORM FOR VERTICAL EM DASH
    #   ︲ PRESENTATION FORM FOR VERTICAL EN DASH ﹘ SMALL EM DASH
    #   ﹣ SMALL HYPHEN-MINUS
    #   － FULLWIDTH HYPHEN-MINUS
    ####

    # INITIAL PASSES: protect what is allowed by overwriting lines in a copy of the book.

    dbuf = book.copy()

    # The dashes we recognise

    ch_hm = "-"  # hyphen-minus
    ch_hy = "‐"  # hyphen
    ch_nb = "‑"  # non-breaking hyphen
    ch_fd = "‒"  # figure dash
    ch_en = "–"  # endash
    ch_em = "—"  # emdash

    # First pass allows em-dash to start a paragraph.
    #
    # The loop below assumes a paragraph starts after an empty line, which
    # is generally the case, and goes through the book line by line looking
    # for them.
    #
    # Deal with the special case of the first line of the file being the
    # start of a paraqraph; i.e. it is not preceded by a blank line.

    # line number = line_index + 1
    line_index = 0
    while line_index < len(dbuf) - 1:
        if non_text_line(dbuf[line_index]):  # Ignore page separators, etc
            line_index += 1
            continue

        # allow em-dash to start a paragraph.
        if line_index == 0 and re.match(r"^\p{Zs}*—", dbuf[line_index]):
            # Replace only one occurrence; i.e. the prefixing one.
            dbuf[line_index] = dbuf[line_index].replace("—", "", 1)

        else:
            # General case. I.e. paragraphs preceded by an empty line OR
            # the first line of the file contains text which does not
            # start with an em-dash.
            #
            # The purpose of the loop is to obfuscate an em-dash if it
            # appears at the start of a paragraph. NB em-dash can be
            # separated from the left-margin by one or more Unicode
            # space characters.

            if dbuf[line_index] == "" and re.match(r"\p{Zs}*—", dbuf[line_index + 1]):
                # Replace only one occurrence; i.e. the prefixing one.
                dbuf[line_index + 1] = dbuf[line_index + 1].replace("—", "", 1)

        line_index += 1

    # Second pass.
    #
    # Go through the book line by line again and obfuscate valid occurrences
    # of Unicode dash characters. This is the second of the initial passes.
    #
    # The order of execution of these replacements on a line is important!
    reg1 = re.compile(r"—{8,}")
    reg2 = re.compile(r"(?<=[ \p{L}])——(?!$|—)")
    reg3 = re.compile(r"\p{L}-\p{L}")
    reg4 = re.compile(r"\p{L}’-\p{L}")
    reg5 = re.compile(r"\p{L}-’\p{L}")
    reg6 = re.compile(r"(?<=\p{L}\.)-(?=\p{L})")
    reg7 = re.compile(r"\p{L}‐\p{L}")  # U+2010 '‐'
    reg8 = re.compile(r"-{8,}")
    reg9 = re.compile(r"\p{L}-\p{L}")  # U+2011 '-'
    reg10 = re.compile(r"\p{Nd}‒\p{Nd}")  # U+2012 '‒'
    reg11 = re.compile(r"\p{Nd}–\p{Nd}")  # U+2013 '–'
    reg12 = re.compile(r"\p{Nd}\s–\s\p{Nd}")
    reg13 = re.compile(r"\p{L}—\p{L}")
    reg14 = re.compile(r"[\p{Ll}I]—\p{P}")
    reg15 = re.compile(r"[\._=+\)\]]—[\p{L}_=+\()]")
    reg16 = re.compile(r"\p{Ll}— \p{Lu}")
    reg17 = re.compile(r"—\s*$")
    # line number = line_index + 1
    line_index = 0
    while line_index < len(dbuf):
        if non_text_line(dbuf[line_index]):
            line_index += 1
            continue

        line = dbuf[line_index].replace("_", "")

        # em-dash when 8 or more act as a separator
        line = reg1.sub("", line)
        # deleted words E.g. "as soon as Mr. —— had left the ship"
        line = reg2.sub(" QQ ", line)

        # consider exactly two em-dashes as one - WHY?
        # dbuf[line_index] = re.sub(
        #     r"([^—])——([^—])", double_dash_replace, dbuf[line_index]
        # )

        # hyphen-minus between two letters. E.g:
        # sand-hill
        # Repeat to deal with lines like:
        #   "pur-r-rta-a-a-tu-ur? I b’long to the Twenty-secun’ Nor’ Ka-a-a-li-i-na"
        line = reg3.sub("QQ", line)
        line = reg3.sub("QQ", line)
        # Repeat to deal with lines like:
        #   "frien’-o’-mine", etc.
        line = reg4.sub("QQ", line)
        line = reg4.sub("QQ", line)
        # Repeat to deal with lines like:
        #   "by-’n-by", etc.
        line = reg5.sub("QQ", line)
        line = reg5.sub("QQ", line)
        # Hyphen-minus in Lieut.-Governor, etc.
        line = reg6.sub("QQ", line)
        # Hyphen between two letters
        line = reg7.sub("QQ", line)
        line = reg7.sub("QQ", line)
        # hyphen-minus when 8 or more act as a separator
        line = reg8.sub("", line)
        # non-breaking hyphen between two letters
        line = reg9.sub("", line)
        # figure dash between two digits
        line = reg10.sub("", line)
        # en-dash between two digits
        line = reg11.sub("", line)
        # en-dash with spaces between two digits
        line = reg12.sub("", line)
        # em-dash between letters with no spacing
        line = reg13.sub("", line)
        # em-dash between lower-case letter or 'I' and punctuation
        line = reg14.sub("", line)
        # em-dash between period or markup and letter
        line = reg15.sub("", line)
        # lower-case letter, em-dash, space, upper-case letter
        line = reg16.sub("", line)
        # em-dash should not end a line - may be exceptions
        line = reg17.sub("", line)

        dbuf[line_index] = line
        line_index += 1

    # FINAL PASS: flag what remains.

    a_h2 = []
    a_h4 = []
    a_hh = []
    a_hm = []
    a_hy = []
    a_nb = []
    a_fd = []
    a_en = []
    a_em = []
    a_un = []

    dash_suspects_found = False
    line_index = 0
    counth2 = 0
    counth4 = 0

    reg18 = re.compile(r"\p{Pd}")
    reg19 = re.compile(r"(?<!-)--(?!-)")
    reg20 = re.compile(r"(?<!-)----(?!-)")
    reg21 = re.compile(
        r"\p{Pd}\p{Pd}+",
    )
    reg22 = re.compile(r"\p{Pd}")
    while line_index < len(dbuf):
        if non_text_line(dbuf[line_index]):  # Ignore page separators, etc
            line_index += 1
            continue

        line = dbuf[line_index]

        # Does line contain any dashes?
        if reg18.search(line):
            # Line has dashes so generate output records to flag
            # each type of invalid dash types found.

            dash_suspects_found = True
            not_consecutive_dashes = True

            # Look for pairs of hyphen-minus (keyboard "-") possibly being
            # used in place of em-dash. We will check and flag this later.
            if reg19.search(line):
                resall = reg19.findall(line)
                counth2 += len(resall)
                a_h2.append((line_index + 1, book[line_index]))
                # Delete all the pairs just found.
                line = reg19.sub("", line)
            # Look for quads of hyphen-minus (keyboard "-") possibly being
            # used in place of long em-dash. We will check and flag this later.
            if reg20.search(line):
                resall = reg20.findall(line)
                counth4 += len(resall)
                a_h4.append((line_index + 1, book[line_index]))
                # Delete all the quads just found.
                line = reg20.sub("", line)
            # Look for other consecutive dashes (of any kind).
            if reg21.search(line):
                a_hh.append((line_index + 1, book[line_index]))
                # Delete consecutive dashes just found. Any left at final test are 'unrecognised'.
                line = reg21.sub("", line)
                not_consecutive_dashes = False
            # Look for hyphen-minus
            if ch_hm in line and not_consecutive_dashes:
                a_hm.append((line_index + 1, book[line_index]))
                # Delete dash(es) just found. Any left at final test is 'unrecognised'.
                line = line.replace(ch_hm, "")
            # Look for hyphen
            if ch_hy in line:
                a_hy.append((line_index + 1, book[line_index]))
                # Delete dash(es) just found. Any left at final test is 'unrcognised'.
                line = line.replace(ch_hy, "")
            # Look for non-breaking hyphen
            if ch_nb in line:
                a_nb.append((line_index + 1, book[line_index]))
                # Delete dash(es) just found. Any left at final test is 'unrecognised'.
                line = line.replace(ch_nb, "")
            # Look for figure dash
            if ch_fd in line:
                a_fd.append((line_index + 1, book[line_index]))
                # Delete dash(es) just found. Any left at final test is 'unrecognised'.
                line = line.replace(ch_fd, "")
            # Look for endash
            if ch_en in line:
                a_en.append((line_index + 1, book[line_index]))
                # Delete dash(es) just found. Any left at final test is 'unrecognised'.
                line = line.replace(ch_en, "")
            # Look for emdash
            if ch_em in line:
                a_em.append((line_index + 1, book[line_index]))
                # Delete dash(es) just found. Any left at final test is 'unrecognised'.
                line = line.replace(ch_em, "")
            # If any dashes left on line at this point treat them as unrecognised
            if reg22.search(line):
                a_un.append((line_index + 1, book[line_index]))

        line_index += 1

    # Generate dialog entries about remaining entries.

    first_header = True

    # If many pairs of "--" detected report only the first five.

    if len(a_h2) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("'--' (keyboard '-') found")

        count = 0
        for record in a_h2:
            line_number = record[0]
            line = record[1]

            if count < 5:
                report_all_occurrences_on_line(r"(?<!-)--(?!-)", line, line_number)
            count += 1
        if count > 5:
            if len(a_h2) - 5 == 1:
                output_record = "  ...1 more line"
            else:
                output_record = f"  ...{len(a_h2) - 5} more lines"
            checker_dialog.add_footer(output_record)
        if counth2 > 5:
            checker_dialog.add_footer(
                "",
                "    [Book seems to use '--' as em-dash so not reporting these further]",
            )

    # If many pairs of "----" detected report only the first five.

    if len(a_h4) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("'----' (keyboard '-') found")

        count = 0
        for record in a_h4:
            line_number = record[0]
            line = record[1]

            if count < 5:
                report_all_occurrences_on_line(r"(?<!-)----(?!-)", line, line_number)
            count += 1
        if count > 5:
            if len(a_h4) - 5 == 1:
                output_record = "  ...1 more line"
            else:
                output_record = f"  ...{len(a_h4) - 5} more lines"
            checker_dialog.add_footer(output_record)
        if counth4 > 5:
            checker_dialog.add_footer(
                "",
                "    [Book seems to use '----' as long em-dash so not reporting these further]",
            )

    # Report other consecutive dashes

    if len(a_hh) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header(
            "Adjacent dashes (expected at least 8 emdash or keyboard '-' as a separator)"
        )

        for record in a_hh:
            line_number = record[0]
            line = record[1]
            report_multiple_occurrences_on_line(r"(\p{Pd}\p{Pd}+)", line, line_number)

    # Report hyphen-minus

    if len(a_hm) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("Hyphen-minus (single keyboard '-')")
        for record in a_hm:
            line_number = record[0]
            line = record[1]
            pattern = r"(?<![\p{Pd}\p{L}])-(?![\p{Pd}\p{L}])"
            report_all_occurrences_on_line(pattern, line, line_number)

    # Report hyphen

    if len(a_hy) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("Hyphen")
        for record in a_hy:
            line_number = record[0]
            line = record[1]
            report_all_occurrences_on_line(ch_hy, line, line_number)

    # Report non-breaking hyphen

    if len(a_nb) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("Non-breaking hyphen")
        for record in a_nb:
            line_number = record[0]
            line = record[1]
            report_all_occurrences_on_line(ch_nb, line, line_number)

    # Report figure dash

    if len(a_fd) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("Figure dash")
        for record in a_fd:
            line_number = record[0]
            line = record[1]
            report_all_occurrences_on_line(ch_fd, line, line_number)

    # Report en-dash

    if len(a_en) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("En-dash")
        for record in a_en:
            line_number = record[0]
            line = record[1]
            report_all_occurrences_on_line(ch_en, line, line_number)

    # Report em-dash

    if len(a_em) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("Em-dash")
        for record in a_em:
            line_number = record[0]
            line = record[1]
            report_all_occurrences_on_line(ch_em, line, line_number)

    # Report unrecognised dash

    if len(a_un) > 0:
        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        checker_dialog.add_header("Unrecognised dash")
        for record in a_un:
            line_number = record[0]
            line = record[1]
            report_all_occurrences_on_line(r"\p{Pd}", line, line_number)

    # All book lines scanned.
    if not dash_suspects_found:
        checker_dialog.add_footer("", "    No dash suspects found.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# scanno check
######################################################################


def scanno_check() -> None:
    """Checks the 'words' on a line against a long list
    of commonly misspelled words."""

    checker_dialog.add_header(
        "----- Scannos check ------------------------------------------------------------"
    )

    scanno_dictionary = build_scanno_dictionary()
    scanno_outrecs: Dict[str, list[tuple]] = {}
    no_scannos_found = True

    for line_index, line in enumerate(book):
        if non_text_line(line):
            continue

        # We have the list of words on the line already in the
        # array 'word_list_map_words]'. It is indexed from zero.
        word_list = word_list_map_words[line_index]
        previously_found_on_this_line = []

        # Look for scannos among the words on this line.
        for word in word_list:
            word_lc = word.lower()
            if (word_lc in scanno_dictionary) and (
                word_lc not in previously_found_on_this_line
            ):
                # word on line is a scanno and we haven't seen it before on the line.
                no_scannos_found = False
                # We only want to create a tuple here for the first instance
                # of a scanno on this line, ignoring case. When we use the
                # tuples below to add dialog records, we will also find and
                # report to the dialog other instances of the same scanno on
                # this line.
                previously_found_on_this_line.append(word_lc)
                # Add to list of tuples from which dialog entries
                # will be generated later.
                if word_lc not in scanno_outrecs:
                    scanno_outrecs[word_lc] = [(line_index + 1, line)]
                else:
                    scanno_outrecs[word_lc].append((line_index + 1, line))

    # We're done looking for scannos on each line. Report what we found.
    # NB 'scanno_outrecs' is a dictionary. The keys are a scanno and the
    #    value is a list of tuples: [(line number, line text), ...]

    first_header = True
    for scanno, tple_list in scanno_outrecs.items():
        # The value of each scanno key in scanno_outrecs dictionary
        # is a list of tuples: (line_number, line). For a given scanno
        # only one instance of it on a line has been noted in a tuple.
        # Find and add to dialog other instances that may also be on
        # the line.

        if first_header:
            first_header = False
        else:
            checker_dialog.add_header("")
        # Header is the scanno.
        checker_dialog.add_header(scanno)

        for cnt, tple in enumerate(tple_list):
            if cnt >= report_limit:
                checker_dialog.add_footer("  ...more")
                break

            line_number = tple[0]
            line = tple[1]

            # We know that scanno appears at least once on line; it may
            # be repeated, possibly in a different case.
            # Get all occurrences of scanno on line and report them.

            regx = r"(?<!\p{L}|\p{Nd})" + scanno + r"(?!\p{L}|\p{Nd})"
            match_list = list(re.finditer(regx, line, re.IGNORECASE))
            if not match_list:
                continue
            multiplier = f"(x{len(match_list)}) " if len(match_list) > 1 else ""
            # Get start/end of all errors on line.
            start_rowcol = IndexRowCol(line_number, match_list[0].start(0))
            end_rowcol = IndexRowCol(line_number, match_list[-1].end(0))
            # Highlight occurrence of word in the line.
            hilite_start = match_list[0].start(0) + len(multiplier)
            hilite_end = match_list[-1].end(0) + len(multiplier)
            # Add record to the dialog.
            checker_dialog.add_entry(
                f"{multiplier}{line}",
                IndexRange(start_rowcol, end_rowcol),
                hilite_start,
                hilite_end,
            )

    if no_scannos_found:
        checker_dialog.add_footer("")
        checker_dialog.add_footer("    No scannos found.")

    # Add line spacer at end of this checker section.
    checker_dialog.add_footer("")


######################################################################
# build dictionary used by scannos check
######################################################################


def build_scanno_dictionary() -> Dict[str, int]:
    """Builds a dictionary from a list of common misspelled words."""

    # List of common scannos. Add additions to end of the list.
    # Duplicates will be dealt with when building the dictionary.

    # fmt: off
    scannos_misspelled = [
        "1gth", "1lth", "1oth", "1Oth", "2gth", "2ist", "2lst", "oa", "po", "2Oth", "2OTH",
        "2oth", "3lst", "3Oth", "3oth", "abead", "ablc", "Abont", "abovc", "abscnt", "abseut",
        "acadernic", "acbe", "acccpt", "accnse", "accornpany", "accusc", "accustorn", "achc",
        "aclie", "actiou", "activc", "actnal", "adinire", "adinit", "admirc", "adnlt",
        "adrnire", "adrnission", "adrnit", "advicc", "advisc", "affcct", "aftcr", "Aftcr",
        "aftemoon", "agaiu", "Agaiu", "Agaiust", "agam", "Agam", "Agamst", "agc", "agcncy",
        "agcnt", "agencv", "ageucy", "ageut", "agrcc", "agreernent", "ahcad", "ahke", "ahle",
        "Ahont", "Ahout", "ahout", "ahove", "ahroad", "ahsent", "ahve", "aiin", "ainong",
        "ainount", "ainuse", "airn", "A-Iy", "aliead", "alikc", "alinost", "alivc", "aln",
        "alonc", "alond", "aloue", "aloug", "alrnost", "altbough", "altemative", "alwavs",
        "amd", "amnse", "amonnt", "amoug", "amouut", "amusc", "ane", "angcr", "anglc",
        "angrv", "aniinal", "anirnal", "annnal", "annov", "annt", "Anotber", "anotber",
        "Anothcr", "Anotlier", "answcr", "anthor", "antnmn", "anv", "Anv", "anvhow", "anvone",
        "anvwav", "anybow", "anyliow", "anyonc", "appcal", "appcar", "applv", "appointrnent",
        "arca", "arcb", "arcli", "argne", "arguc", "argurnent", "arin", "ariny", "arisc",
        "armv", "arn", "arnbition", "arnbitious", "arnong", "arnongst", "arnount", "arnuse",
        "Aronnd", "aronnd", "arouud", "Arouud", "arrangernent", "arrcst", "arrivc", "arrn",
        "arrny", "asb", "asharned", "asidc", "aslccp", "asli", "aspcct", "asscss", "assct",
        "assernbly", "assessrnent", "assnme", "assuine", "assumc", "assurne", "assurnption",
        "atrnosphere", "attacb", "attacli", "attcnd", "atternpt", "atteud", "au", "aud",
        "Aud", "augle", "augry", "auimal", "Auother", "auswer", "autbor", "autlior",
        "autuinn", "autumu", "auturnn", "auuoy", "auut", "auuual", "Auv", "Auy", "auy",
        "auyhow", "auyoue", "auyway", "avenne", "aveuue", "awakc", "awarc", "awav", "babit",
        "babv", "bair", "bakc", "balf", "bandle", "bappen", "bappy", "barc", "barden",
        "bardly", "Barly", "barm", "barrcl", "bas", "basc", "basiu", "baskct", "basm",
        "basten", "batb", "batbe", "bathc", "batli", "batlie", "batred", "battlc", "bauk",
        "baok", "bav", "bave", "baving", "Bc", "bc", "bcam", "bcan", "bcar", "bcard", "bcast",
        "bcat", "bcauty", "Bccausc", "bccomc", "bcd", "bcforc", "Bcforc", "Bcfore", "Bcgin",
        "bcgin", "Bcgiu", "bchavc", "bchind", "bcing", "bclicf", "bcll", "bclong", "bclow",
        "bclt", "bcnd", "bcrry", "bcsidc", "bcst", "bcttcr", "Bctwccn", "bcyond", "beain",
        "beal", "bealtb", "beanty", "beap", "bearn", "beart", "beautv", "beaven", "beavy",
        "bebave", "bebind", "Becanse", "becoine", "becond", "becorne", "bedroorn", "Beforc",
        "Begiu", "begiu", "Begm", "begm", "behef", "behiud", "behmd", "beigbt", "beiug",
        "beliave", "beliind", "bello", "beloug", "belp", "belped", "bemg", "bence", "ber",
        "bere", "berrv", "Betweeu", "beud", "bevond", "beyoud", "bhnd", "bigb", "bigbly",
        "bim", "bire", "birtb", "birtli", "bis", "bitc", "bittcr", "biud", "bladc", "blaine",
        "blamc", "blarne", "blccd", "blcss", "bliud", "blmd", "blne", "bloodv", "bluc", "bmd",
        "bncket", "bndget", "bnild", "bnilt", "bnnch", "bnndle", "Bnow", "bnrn", "bnrst",
        "bnry", "bns", "bnsh", "bnsy", "bnt", "Bnt", "bntter", "bntton", "bny", "bodv",
        "bole", "bollow", "boly", "bome", "bomes", "bonest", "bonnd", "bonor", "bope",
        "bordcr", "borse", "bost", "bot", "botb", "Botb", "botel", "Botli", "botli", "bottlc",
        "bottoin", "bottorn", "boue", "bour", "bouse", "boused", "bouses", "bouud", "bov",
        "bowever", "braiu", "brancb", "brancli", "brauch", "bravc", "brcad", "brcak",
        "brcath", "breatb", "breatli", "bribc", "bricf", "bridgc", "brigbt", "briglit",
        "brihe", "briug", "brmg", "brnsh", "browu", "brusb", "brusli", "buckct", "buge",
        "buncb", "buncli", "bundlc", "bunger", "burry", "burt", "buru", "burv", "busb",
        "busiiicss", "busli", "busv", "buttcr", "buttou", "buuch", "buudle", "buv", "bv",
        "Bv", "Bven", "cach", "cagc", "cagcr", "cailing", "cainp", "cakc", "calin", "calrn",
        "canse", "camo", "carc", "carccr", "carly", "carn", "carnp", "carnpaign", "carrv",
        "carth", "casb", "casc", "casc", "casily", "casli", "castlc", "casy", "catcb",
        "catcli", "cattlc", "cau", "Cau", "caual", "causc", "cavc", "cbain", "cbair", "cbalk",
        "cbance", "Cbange", "cbange", "cbarm", "cbeap", "cbeat", "cbeck", "cbeer", "cbeese",
        "cbest", "cbief", "cbild", "cboice", "cboose", "cburcb", "ccnt", "ccntcr", "ccntrc",
        "cdgc", "cerernony", "ceut", "ceuter", "ceutre", "cf", "cffcct", "cffort",
        "chairrnan", "chaiu", "chancc", "changc", "Changc", "CHAPTEE", "chargc", "charrn",
        "chauce", "chauge", "Chauge", "chcap", "chcck", "chcst", "chent", "chff", "chicf",
        "chirnney", "chmb", "chnrch", "choicc", "choosc", "circlc", "circurnstance", "cithcr",
        "cither", "citv", "claas", "claiin", "clairn", "clav", "clcan", "clcar", "clcct",
        "clcvcr", "cldcr", "cleau", "cliain", "cliair", "clialk", "cliance", "Cliange",
        "cliange", "cliarge", "cliarm", "clieap", "clieat", "clieck", "clieer", "cliest",
        "clieut", "cliief", "cliild", "cliinb", "climh", "clioice", "clioose", "clirnb",
        "clnb", "clond", "Closc", "closc", "clotb", "clotbe", "clothc", "clotli", "clotlie",
        "clsc", "cluh", "cmcrgc", "cmpirc", "cmploy", "cmpty", "cnablc", "cncmy", "cnd",
        "cnjoy", "cnough", "cnp", "cnre", "cnrl", "cnrse", "cnrve", "cnstom", "cnsurc", "cnt",
        "cntcr", "cntirc", "cntry", "cnvy", "coarsc", "coffcc", "coinb", "Coine", "coine",
        "coiu", "colonr", "colonv", "colouy", "comh", "commou", "concem", "concemed",
        "confirrn", "congh", "conld", "Conld", "connt", "connty", "conple", "conrse", "conrt",
        "Considcr", "consin", "coppcr", "copv", "cornb", "cornbination", "cornbine", "corncr",
        "corne", "Corne", "cornfort", "corning", "cornpanion", "cornpanionship", "cornpany",
        "cornpare", "cornparison", "cornpete", "cornpetitor", "cornplain", "cornplaint",
        "cornplete", "cornpletely", "cornpletion", "cornplex", "cornplicate", "cornplication",
        "cornponent", "cornpose", "cornposition", "coru", "coruer", "cottou", "cou", "cougb",
        "cougli", "couldnt", "countv", "couplc", "coursc", "Cousider", "cousiu", "couut",
        "couuty", "covcr", "cqual", "crasb", "crasli", "crcam", "crcatc", "creain", "crearn",
        "criine", "crimc", "crirne", "crirninal", "criticisrn", "crnel", "crnsh", "crowu",
        "crror", "crucl", "crusb", "crusli", "crv", "cscapc", "cstatc", "curc", "cursc",
        "curvc", "custoin", "custorn", "custornary", "custorner", "cvcn", "cvcnt", "cvcr",
        "cvcry", "cver", "cvil", "cxact", "cxccpt", "cxccss", "cxcitc", "cxcusc", "cxist",
        "cxpcct", "cxpcrt", "cxtcnd", "cxtcnt", "cxtra", "cyc", "cycd", "dailv", "dainage",
        "dainp", "damagc", "dancc", "dangcr", "darc", "darkcn", "darkeu", "darnage", "darnp",
        "datc", "dauce", "dauger", "dav", "davlight", "dc", "dcad", "dcal", "dcar", "dcath",
        "dcbatc", "dcbt", "dccadc", "dccay", "dcccit", "dccd", "dccidc", "dccp", "dccpcn",
        "dccr", "dcfcat", "dcfcnd", "dcfinc", "dcgrcc", "dclay", "dclivcred", "dcmand",
        "dcny", "dcpcnd", "dcpth", "dcputy", "dcrivc", "dcscrt", "dcsign", "dcsirc", "dcsk",
        "dctail", "dcvicc", "dcvil", "deatb", "deatli", "decav", "deepeu", "defeud", "defiue",
        "defme", "dehate", "dehates", "deht", "deinand", "delav", "demaud", "denv",
        "departrnent", "depeud", "depnty", "deptb", "deptli", "deputv", "dernand",
        "dernocratic", "dernonstrate", "desigu", "deterrnine", "deuy", "developrnent",
        "diarnond", "dic", "didnt", "dinc", "dinncr", "dircct", "disb", "discornfort",
        "disli", "disrniss", "ditcb", "ditcli", "diue", "diuuer", "divc", "dividc", "dme",
        "dmner", "dnck", "dne", "dnll", "dnring", "Dnring", "dnst", "dnty", "docurnent",
        "doesnt", "donble", "donbt", "donkev", "dont", "dornestic", "doublc", "douhle",
        "douht", "dowu", "Dowu", "dozcn", "dozeu", "drawcr", "drcam", "drcss", "dreain",
        "drearn", "driuk", "drivc", "drivcr", "drmk", "drng", "drnm", "drowu", "druin",
        "drurn", "drv", "duc", "duriug", "Duriug", "durmg", "Durmg", "dutv", "eacb", "Eacb",
        "Eack", "Eacli", "eacli", "eam", "eamest", "earlv", "Earlv", "eartb", "eartli",
        "earu", "easilv", "eastem", "easv", "econornic", "econorny", "Ee", "Eecause", "Eeep",
        "Eefore", "Eegin", "Eetween", "Eill", "einerge", "einpire", "einploy", "einpty",
        "eitber", "eitlier", "elernent", "emplov", "emptv", "enahle", "eneiny", "enemv",
        "energv", "enerny", "enjov", "enongh", "enougb", "enougli", "ensnre", "entrv",
        "environrnent", "envv", "Eobert", "Eome", "Eoth", "eqnal", "equiprnent", "ernerge",
        "ernphasis", "ernpire", "ernploy", "ernpty", "establishrnent", "estirnate", "euable",
        "eud", "euemy", "euergy", "eujoy", "euough", "eusure", "Eut", "euter", "eutire",
        "eutry", "euvy", "Evcn", "everv", "Eveu", "eveu", "eveut", "exarnination", "exarnine",
        "exarnple", "excnse", "experirnent", "extemal", "exteud", "exteut", "extrerne",
        "extrernely", "Ey", "facc", "fadc", "faine", "fainily", "fainous", "fairlv", "faitb",
        "faitli", "faiut", "famc", "familv", "famons", "famt", "fancv", "fanlt", "farin",
        "fariner", "farmcr", "farne", "farniliar", "farnily", "farnous", "farrn", "farrner",
        "fastcn", "fasteu", "fatber", "fatc", "fathcr", "fatlier", "fattcn", "fatteu", "fau",
        "faucy", "favonr", "fcar", "fcast", "fcc", "fccd", "fccl", "fcllow", "fcncc", "fcvcr",
        "fcw", "Fcw", "feinale", "fernale", "feuce", "fhght", "ficld", "ficrcc", "figbt",
        "figlit", "fignre", "figurc", "filc", "filid", "filin", "finc", "fingcr", "finisb",
        "finisli", "firc", "firin", "firrn", "fisb", "fisli", "fiual", "fiud", "fiue",
        "fiuger", "fiuish", "flaine", "flamc", "flarne", "flasb", "flasli", "flesb", "flesli",
        "fligbt", "fliglit", "flonr", "flv", "fmal", "fmd", "fme", "fmger", "fmish", "fnel",
        "fnll", "fnlly", "fnn", "fnnd", "fnnny", "fnr", "fntnre", "focns", "forcc", "forcst",
        "forgct", "forhid", "forin", "forinal", "foriner", "formcr", "forrn", "forrnal",
        "forrner", "fortb", "fortli", "foud", "fraine", "framc", "frarne", "frarnework",
        "frcc", "frcczc", "frcsh", "freedorn", "freind", "fresb", "fresli", "fricnd",
        "frieud", "frigbt", "friglit", "frnit", "Froin", "froin", "fromt", "Frorn", "frorn",
        "frout", "frow", "frv", "fucl", "fullv", "fumish", "fumiture", "funnv", "furtber",
        "futurc", "fuu", "fuud", "fuuuy", "gaicty", "gaietv", "gaine", "gaiu", "gallou",
        "gamc", "garagc", "gardcn", "gardeu", "garne", "gatber", "gatc", "gathcr", "gatlier",
        "gav", "gcntlc", "gct", "gentlernan", "geutle", "givc", "Givc", "glorv", "gnard",
        "gness", "gnest", "gnide", "gnilt", "gnn", "goldcn", "goldeu", "govcrn", "govem",
        "govemment", "govemor", "governrnent", "goveru", "gracc", "graiu", "graud", "graut",
        "grav", "gravc", "grcasc", "grcat", "Grcat", "grccd", "grccn", "grcct", "grcy",
        "greeu", "grev", "griud", "grmd", "gronnd", "gronp", "grouud", "growtb", "growtli",
        "gth", "gucss", "gucst", "guidc", "guu", "hahit", "hake", "han", "handlc", "happcn",
        "happeu", "happv", "har", "hardcn", "hardeu", "hardlv", "harhor", "harin", "harrel",
        "harrn", "hase", "hasic", "hasin", "hasis", "hasket", "hastc", "hastcn", "hasteu",
        "hatc", "hathe", "hatrcd", "hattle", "haud", "haudle", "haug", "hav", "havc", "Havc",
        "Hc", "hc", "hcad", "hcal", "hcalth", "hcap", "hcar", "hcart", "hcat", "hcavcn",
        "hcavy", "hcight", "hcll", "hcllo", "hclp", "hcncc", "hcr", "hcrc", "hd", "heak",
        "heam", "hean", "heast", "heauty", "heaveu", "heavv", "hecause", "hecome", "hed",
        "heen", "hefore", "heg", "hegan", "hegin", "hehave", "hehind", "heid", "heing",
        "helief", "helieve", "helong", "helow", "helt", "hend", "henefit", "herry", "heside",
        "hest", "hetter", "hetween", "heuce", "heyond", "hfe", "hft", "hght", "hia", "hidc",
        "hie", "hig", "higber", "highlv", "hiii", "hiin", "hiln", "hin", "hindcr", "hirc",
        "hird", "hirn", "hirnself", "hirth", "hite", "hiuder", "hke", "hkely", "hlack",
        "hlade", "hlame", "hleed", "hless", "hlind", "hlock", "hlood", "hloody", "hlow",
        "hlue", "hmb", "hmder", "hmit", "hne", "hnge", "hnk", "hnman", "hnmble", "hnnger",
        "hnnt", "hnrry", "hnrt", "hnt", "hoast", "hoat", "hody", "hoil", "hoine", "holc",
        "holv", "homc", "honcst", "honr", "honse", "hopc", "horder", "horne", "hornecorning",
        "hornernade", "hornework", "horrow", "horsc", "hotcl", "hoth", "hottle", "hottom",
        "houest", "houor", "housc", "Howcvcr", "Howcver", "Howevcr", "hox", "hp", "hquid",
        "hrain", "hranch", "hrass", "hrave", "hread", "hreak", "hreath", "hrick", "hridge",
        "hrief", "hright", "hring", "hroad", "hrown", "hrush", "hst", "hsten", "httle",
        "hucket", "hudget", "hugc", "huild", "huinan", "huinble", "humblc", "humhle",
        "hundle", "hungcr", "hurn", "hurnan", "hurnble", "hurrv", "hurst", "hury", "hus",
        "husy", "hutter", "hutton", "huuger", "huut", "huy", "hve", "hving", "hy", "i3th",
        "i4th", "i5th", "i6th", "i7th", "i8th", "i9th", "ia", "icc", "idca", "idcal", "idlc",
        "ignorc", "iguore", "iie", "iii", "iiie", "iinage", "iinpact", "iinply", "iinpose",
        "iiow", "Ile", "Ilim", "I-low", "imagc", "implv", "imposc", "inad", "inadden",
        "inail", "inain", "inainly", "inajor", "inake", "inanage", "inanner", "inany", "inap",
        "inarch", "inark", "inarket", "inarry", "inass", "inaster", "inat", "inatch",
        "inatter", "inay", "inaybe", "incb", "incli", "incoine", "incomc", "incorne",
        "indccd", "ine", "ineal", "inean", "ineans", "ineat", "ineet", "inelt", "inend",
        "inental", "inercy", "inere", "inerely", "inerry", "inetal", "inethod", "inforin",
        "inforrn", "inforrnation", "iniddle", "inight", "inild", "inile", "inilk", "inill",
        "inind", "inine", "ininute", "inisery", "iniss", "inix", "injnry", "injurv", "inodel",
        "inodern", "inodest", "inodule", "inoney", "inonth", "inoon", "inoral", "inore",
        "inost", "inother", "inotion", "inotor", "inouse", "inouth", "inove", "insidc",
        "insnlt", "insnre", "instrurnent", "insurc", "intcnd", "intemal", "intemational",
        "inuch", "inud", "inurder", "inusic", "inust", "investrnent", "invitc", "iny",
        "inyself", "irnage", "irnaginary", "irnaginative", "irnagine", "irnitate",
        "irnitation", "irnpact", "irnplication", "irnply", "irnportance", "irnportant",
        "irnpose", "irnpossible", "irnpression", "irnprove", "irnprovernent", "irou",
        "islaud", "issne", "issuc", "itcm", "itein", "itern", "itsclf", "iu", "iu", "Iu",
        "iuch", "iucome", "iudeed", "iudex", "iudoor", "iuform", "iujury", "iuk", "iuside",
        "iusist", "iusult", "iusure", "iuteud", "Iuto", "iuto", "iuu", "iuveut", "iuvite",
        "iuward", "jndge", "jnmp", "Jnst", "jnst", "jobn", "joh", "joiu", "joiut", "jom",
        "jomt", "joumey", "jov", "judgc", "juinp", "jurnp", "Kack", "kccp", "Kccp", "Kcep",
        "kcy", "Ke", "Kecause", "Kecp", "Kefore", "Ketween", "kev", "kingdorn", "kiud",
        "kiug", "kmd", "kmg", "kncc", "knccl", "knifc", "Kome", "kuee", "kueel", "kuife",
        "kuock", "kuot", "Kuow", "kuow", "Kut", "Kven", "l0th", "l1ad", "l1th", "l2th",
        "l3th", "l4th", "l5th", "l6th", "l7th", "l8th", "l9th", "labonr", "ladv", "lahour",
        "lainp", "lakc", "langh", "lannch", "largc", "larnp", "latc", "latcly", "latcr",
        "latelv", "lattcr", "laugb", "launcb", "lauuch", "lav", "lawver", "lawycr", "lazv",
        "lcad", "lcadcr", "lcaf", "lcaguc", "lcan", "lcarn", "lcast", "lcavc", "lcft", "lcg",
        "lcgal", "lcnd", "lcngth", "lcss", "lcsscn", "lcsson", "lcttcr", "lcvcl", "leagne",
        "leam", "learu", "leau", "lengtb", "lengtli", "lesseu", "lessou", "leud", "leugth",
        "lgth", "liabit", "liair", "lialf", "liall", "liand", "liandle", "liang", "liappen",
        "liappy", "liarbor", "liard", "liarden", "liardly", "liarm", "lias", "liaste",
        "liasten", "liat", "liate", "liatred", "liave", "lic", "licll", "liead", "lieal",
        "lieap", "liear", "lieart", "lieat", "lieaven", "lieavy", "liell", "liello", "lielp",
        "lience", "liere", "lifc", "ligbt", "liglit", "liide", "liigli", "liill", "liim",
        "liinb", "liinder", "liinit", "liire", "liis", "liit", "Likc", "likc", "likcly",
        "likelv", "limh", "linc", "liold", "liole", "liollow", "lioly", "liome", "lionest",
        "lionor", "liook", "liope", "liorse", "liost", "liot", "liotel", "liour", "liouse",
        "liow", "liqnid", "lirnb", "lirnit", "lirnited", "listcn", "listeu", "littie",
        "Littlc", "littlc", "liue", "liuge", "liuk", "liumble", "liunger", "liunt", "liurry",
        "liurt", "liut", "livc", "liviug", "livmg", "lIy", "llth", "lme", "lmk", "lnck",
        "lnmp", "lnnch", "lnng", "loau", "localitv", "lodgc", "loncly", "lond", "lonelv",
        "loosc", "looscn", "looseu", "losc", "louely", "loug", "Loug", "loval", "lovc",
        "lovcly", "lovelv", "lst", "ltim", "luinp", "luncb", "luncli", "lurnp", "luuch",
        "luug", "maiiaged", "mainlv", "maiu", "maiuly", "makc", "Makc", "malc", "mamly",
        "managc", "managernent", "manncr", "manv", "Manv", "marcb", "marcli", "markct",
        "marrv", "mastcr", "matcb", "matcli", "mattcr", "mau", "mauage", "mauuer", "mauy",
        "Mauy", "mav", "Mav", "mavbe", "maybc", "mayhe", "mb  ", "mbber", "mc", "mcal",
        "mcan", "mcans", "mcat", "mcct", "mch", "mclt", "mcmbcr", "mcmory", "mcnd", "mcntal",
        "mcome", "mcrc", "mcrcly", "mcrcy", "mcrry", "mctal", "mcthod", "mde", "mdeed",
        "mdex", "mdoor", "meantirne", "meanwbile", "meau", "meaus", "memher", "memhers",
        "memorv", "mercv", "merelv", "mernber", "mernbership", "mernory", "merrv", "metbod",
        "metliod", "meud", "meutal", "mform", "middlc", "Migbt", "migbt", "miglit", "Miglit",
        "milc", "minc", "minnte", "minutc", "miscry", "miserv", "miud", "miue", "miuute",
        "mjury", "mk", "mle", "mmd", "mme", "mmute", "mn", "mn", "Mncb", "mnch", "Mnch",
        "mnd", "mnrder", "mnsenm", "mnsic", "mnst", "modcl", "modcrn", "modcst", "modem",
        "moderu", "modnle", "modulc", "momcnt", "momeut", "moming", "moncy", "monev",
        "monkev", "monse", "montb", "montli", "moou", "Morc", "morc", "mornent", "mornentary",
        "motber", "mothcr", "motiou", "motlier", "mouey", "mousc", "moutb", "moutli", "Movc",
        "movc", "movernent", "mral", "msect", "msh", "mside", "msist", "mst", "msult",
        "msure", "mtend", "mto", "Mucb", "mucb", "Mucli", "mucli", "murdcr", "museurn", "mv",
        "mvite", "mvself", "mward", "mysclf", "naine", "namc", "narne", "nativc", "natnre",
        "naturc", "nc", "ncar", "ncarly", "ncat", "nccd", "ncck", "ncphcw", "ncst", "nct",
        "Ncvcr", "ncvcr", "Ncver", "ncw", "ncws", "ncxt", "nearlv", "neitber", "ner",
        "nepbew", "Nevcr", "ngly", "nian", "nicc", "niccc", "nigbt", "niglit", "nlyself",
        "nnable", "nncle", "nnder", "nnion", "nnit", "nnite", "nnited", "nnity", "nnless",
        "nnmber", "nnrse", "nnt", "nntil", "noblc", "nobodv", "nohle", "nohody", "noisc",
        "nonc", "norinal", "norrnal", "norrnally", "nortb", "nortbern", "northem", "nortli",
        "nosc", "notbing", "notc", "noticc", "np", "npon", "npper", "npset", "nrge", "nrgent",
        "ns", "nse", "nsed", "nsefnl", "nser", "nsnal", "Nte", "nuinber", "numbcr", "numher",
        "numhers", "nurnber", "nurnerous", "nursc", "oan", "obcy", "obev", "objcct", "obtaiu",
        "obtam", "occan", "occnr", "oceau", "offcnd", "offcr", "offeud", "officc", "oftcn",
        "ofteu", "ohey", "ohject", "ohtain", "oinit", "okav", "om", "omament", "Onc", "onc",
        "Oncc", "oncc", "onght", "oniy", "Onlv", "onlv", "onnce", "onr", "ont", "Ont",
        "ontpnt", "opcn", "Opcn", "Opeu", "opeu", "opposc", "optiou", "ordcr", "orgau",
        "origiu", "origm", "ornarnent", "ornission", "ornit", "Otber", "otber", "otbers",
        "othcr", "Othcr", "otlier", "Otlier", "Oucc", "Ouce", "ouce", "Oue", "oue", "ougbt",
        "ouglit", "Oulv", "ouly", "Ouly", "ouncc", "outcorne", "outo", "ouuce", "ovcr",
        "Ovcr", "overcorne", "owc", "owncr", "owu", "owuer", "pagc", "paiu", "paiut", "palc",
        "pamt", "pancl", "panse", "papcr", "parccl", "parcnt", "pardou", "pareut",
        "parliarnent", "partlv", "partv", "pastc", "pastrv", "patb", "patli", "pattem", "pau",
        "pauel", "pausc", "pav", "payrnent", "pbase", "pbone", "pcacc", "pcarl", "pcn",
        "pcncil", "pcnny", "Pcoplc", "pcoplc", "Pcople", "pcr", "pcriod", "pcrmit", "pcrson",
        "pct", "pennv", "Peoplc", "perbaps", "perforrn", "perforrnance", "perinit",
        "perrnanent", "perrnission", "perrnit", "persou", "peu", "peucil", "peuuy", "phasc",
        "phonc", "pia", "piccc", "pigcon", "pilc", "pincb", "pincli", "pipc", "pitv", "piu",
        "piuch", "piuk", "piut", "placc", "plaiu", "plam", "platc", "plau", "plaut", "plav",
        "plaver", "playcr", "plcasc", "plcnty", "plentv", "pleuty", "pliase", "plnral",
        "plns", "pmch", "pmk", "pmt", "pnb", "pnblic", "pnll", "pnmp", "pnnish", "pnpil",
        "pnre", "pnrple", "pnsh", "pnt", "Pnt", "pnzzle", "pockct", "pocm", "poct", "poein",
        "poern", "pohte", "poisou", "poiut", "policc", "policv", "polisb", "politc", "pomt",
        "ponnd", "ponr", "pouud", "powcr", "powdcr", "praisc", "prav", "prcach", "prcfcr",
        "prcss", "prctty", "preacb", "preacli", "prettv", "pricc", "pricst", "pridc",
        "priine", "primc", "prirnary", "prirne", "prisou", "priut", "prizc", "prmt",
        "problern", "prohlem", "prohlems", "proinpt", "prond", "propcr", "prornise",
        "prornised", "prornote", "prornpt", "provc", "pubhc", "puh", "puhlic", "puinp",
        "punisb", "punisli", "purc", "purnp", "purplc", "pusb", "pusli", "puuish", "qnart",
        "qneen", "qnick", "qniet", "qnite", "qttict", "Quc", "quc", "quccn", "queeu", "quict",
        "quitc", "racc", "rahhit", "raisc", "raiu", "rangc", "rarc", "Rarly", "ratber",
        "ratc", "rathcr", "ratlier", "rauge", "rauk", "rav", "rcach", "rcad", "rcadcr",
        "rcady", "rcal", "rcally", "rcason", "rccall", "rcccnt", "rccord", "rcd", "rcddcn",
        "rcducc", "rcfcr", "rcform", "rcfusc", "rcgard", "rcgion", "rcgrct", "rcjcct",
        "rclatc", "rclicf", "rcly", "rcmain", "rcmark", "rcmcdy", "rcmind", "rcmovc", "rcnt",
        "rcpair", "rcpcat", "rcply", "rcport", "rcscuc", "rcsign", "rcsist", "rcst", "rcsult",
        "rctain", "rctirc", "rcturn", "rcvcal", "rcvicw", "rcward", "reacb", "reacli",
        "readv", "reallv", "reasou", "Recause", "receut", "reddeu", "rednce", "Reep",
        "refnse", "Refore", "reforin", "reforrn", "regiou", "rehef", "reinain", "reinark",
        "reinedy", "reinind", "reinove", "relv", "remaiu", "remam", "remcrnbered", "remedv",
        "remiud", "remmd", "renlincled", "replv", "requirernent", "rernain", "rernark",
        "rernedy", "rernernber", "rernind", "rernove", "rescne", "resigu", "resnlt", "retaiu",
        "retam", "retnrn", "retum", "returu", "Retween", "reut", "ribbou", "ricb", "ricc",
        "ricli", "ridc", "Rigbt", "rigbt", "riglit", "Riglit", "rihhon", "ripc", "ripcn",
        "ripeu", "risc", "riug", "rivcr", "rmg", "rnachine", "rnachinery", "rnad", "rnadden",
        "rnagazine", "rnail", "rnain", "rnainly", "rnaintain", "rnajor", "rnajority", "rnake",
        "rnale", "rnan", "rnanage", "rnanaged", "rnanagement", "rnanager", "rnankind",
        "rnanner", "rnany", "rnap", "rnarch", "rnark", "rnarket", "rnarriage", "rnarried",
        "rnarry", "rnass", "rnaster", "rnat", "rnatch", "rnaterial", "rnatter", "rnay",
        "rnaybe", "rnb", "rnbber", "rnde", "rne", "rneal", "rnean", "rneaning", "rneans",
        "rneantirne", "rneanwhile", "rneasure", "rneat", "rnechanisrn", "rnedical",
        "rnedicine", "rneet", "rneeting", "rnelt", "rnember", "rnembership", "rnemory",
        "rnend", "rnental", "rnention", "rnerchant", "rnercy", "rnere", "rnerely", "rnerry",
        "rnessage", "rnessenger", "rnetal", "rnethod", "rng", "rniddle", "rnight", "rnild",
        "rnile", "rnilitary", "rnilk", "rnill", "rnin", "rnind", "rnine", "rnineral",
        "rninister", "rninistry", "rninute", "rninutes", "rniserable", "rnisery", "rniss",
        "rnistake", "rnix", "rnixture", "rnle", "rnn", "rnodel", "rnoderate", "rnoderation",
        "rnodern", "rnodest", "rnodesty", "rnodule", "rnoney", "rnonkey", "rnonth", "rnoon",
        "rnoonlight", "rnoral", "rnore", "rnoreover", "rnornent", "rnornentary", "rnorning",
        "rnost", "rnother", "rnotherhood", "rnotherly", "rnotion", "rnountain", "rnouse",
        "rnouth", "rnove", "rnovement", "Rnow", "rnral", "rnsh", "rnst", "rnuch", "rnud",
        "rnultiply", "rnurder", "rnuseurn", "rnusic", "rnusician", "rnust", "rny", "rnyself",
        "rnystery", "roh", "rolc", "rongh", "ronnd", "ronte", "rooin", "roorn", "ropc",
        "rottcn", "rotteu", "rougb", "rougli", "routc", "rouud", "roval", "rubbcr", "rudc",
        "ruh", "ruhher", "ruiu", "rulc", "rusb", "rusli", "ruu", "Rven", "Ry", "sacrcd",
        "saddcn", "saddeu", "saddlc", "safc", "safcty", "safetv", "saine", "sainple", "sakc",
        "salarv", "salc", "salesrnan", "samc", "samplc", "sance", "sancer", "sarne",
        "sarnple", "saucc", "sauccr", "saud", "sav", "savc", "sbade", "sbadow", "sbake",
        "sball", "sbame", "sbape", "sbare", "sbarp", "sbave", "Sbc", "Sbe", "sbe", "sbeep",
        "sbeet", "sbelf", "sbell", "sbield", "sbine", "sbip", "sbirt", "sbock", "sboe",
        "Sbonld", "sboot", "sbop", "sbore", "sbort", "sbot", "Sbould", "sbould", "sbout",
        "Sbow", "sbow", "sbower", "sbut", "sca", "scalc", "scarcc", "scarch", "scason",
        "scbeme", "scbool", "scbools", "scc", "Scc", "sccd", "scck", "sccm", "sccnc", "sccnt",
        "sccond", "sccrct", "sccurc", "Sce", "sceue", "sceut", "schcmc", "scheine", "scherne",
        "scizc", "sclcct", "scldom", "sclf", "scliool", "scll", "scnd", "scnior", "scnsc",
        "scom", "scorc", "scoru", "scrapc", "scrccn", "scrcw", "screeu", "scrics", "scrvc",
        "sct", "Sct", "scttlc", "scvcrc", "scw", "searcb", "searcli", "seasou", "secnre",
        "secoud", "seein", "seern", "seldoin", "seldorn", "settlernent", "seud", "seuior",
        "seuse", "shadc", "shaine", "shakc", "shamc", "shapc", "sharc", "sharne", "shavc",
        "shc", "Shc", "shcct", "shclf", "shcll", "shde", "shght", "shicld", "shinc", "shiue",
        "shme", "shnt", "shoc", "shonld", "Shonld", "shont", "shorc", "shouldnt", "showcr",
        "sidc", "sigbt", "siglit", "sigu", "sigual", "siinple", "siinply", "silcnt", "sileut",
        "silvcr", "simplc", "simplv", "sinall", "Sinall", "sincc", "Sincc", "sinell",
        "singlc", "sinile", "sinoke", "sinooth", "sirnilar", "sirnple", "sirnplicity",
        "sirnply", "sistcr", "sitc", "siuce", "Siuce", "siug", "siugle", "siuk", "sizc",
        "skiu", "skm", "skv", "slavc", "slccp", "sliade", "sliake", "sliall", "sliame",
        "sliape", "sliare", "sliarp", "slidc", "Slie", "slie", "slieet", "slielf", "sliell",
        "sligbt", "sliglit", "sliield", "sliine", "sliip", "sliirt", "slioe", "Slionld",
        "slioot", "sliop", "sliore", "sliort", "sliot", "Sliould", "sliould", "sliout",
        "Sliow", "sliow", "sliut", "slopc", "slowlv", "Smce", "smce", "smcll", "smg", "smgle",
        "smilc", "smk", "smokc", "smootb", "smootli", "snakc", "snch", "Snch", "sndden",
        "snffer", "sngar", "snit", "snm", "snmmer", "snn", "snpper", "snpply", "snre",
        "snrely", "snrvey", "softcn", "softeu", "sohd", "Soine", "soine", "solcmn", "soleinn",
        "solemu", "solernn", "solvc", "somc", "Somc", "somcthing", "sometbing", "sonl",
        "sonnd", "sonp", "sonr", "sonrce", "sonth", "soou", "sorc", "Sorne", "sorne",
        "sornebody", "sornehow", "sorneone", "sornething", "sornetirne", "sornetirnes",
        "sornewhat", "sornewhere", "sorrv", "sou", "soug", "sourcc", "soutb", "southem",
        "soutli", "souud", "spacc", "spadc", "sparc", "spcak", "spccch", "spccd", "spcll",
        "spcnd", "speecb", "speecli", "speud", "spht", "spitc", "spiu", "spm", "spoou",
        "sprcad", "spriug", "sprmg", "sqnare", "squarc", "Srnall", "srnall", "srnell",
        "srnile", "srnoke", "srnooth", "stagc", "stainp", "staiu", "starnp", "statc",
        "staternent", "statns", "staud", "Staud", "stav", "stcady", "stcal", "stcam", "stccl",
        "stccp", "stccr", "stcm", "stcp", "steadv", "steain", "stearn", "stiug", "stmg",
        "stndio", "stndy", "stnff", "stnpid", "stonc", "storc", "storin", "stornach",
        "storrn", "storv", "stoue", "stovc", "strcam", "strcct", "streain", "strearn",
        "strikc", "stripc", "striug", "strmg", "strokc", "stroug", "studv", "stvle", "stylc",
        "suake", "sucb", "Sucb", "Sucli", "sucli", "suddcn", "suddeu", "suffcr", "suin",
        "summcr", "suow", "suppcr", "supplv", "surc", "surcly", "surelv", "surn", "surnrner",
        "survcy", "survev", "suu", "svstem", "swcar", "swcat", "swccp", "swcct", "swcll",
        "swiin", "swirn", "switcb", "switcli", "swiug", "swmg", "syrnpathetic", "syrnpathy",
        "systcm", "systein", "systern", "t11e", "tablc", "tahle", "taine", "Takc", "takc",
        "tamc", "tapc", "targct", "tarne", "tastc", "tban", "tbank", "tbanks", "tbat", "Tbat",
        "Tbcre", "Tbe", "tbe", "tbe", "tbeir", "tbem", "tbeme", "tben", "Tben", "tbeory",
        "Tberc", "Tbere", "tbere", "Tbese", "tbese", "tbey", "Tbey", "tbick", "tbief", "tbin",
        "tbing", "tbink", "tbirst", "Tbis", "tbis", "tborn", "Tbose", "tbose", "tbougb",
        "tbread", "tbreat", "tbroat", "Tbrougb", "Tbrough", "tbrow", "tbumb", "tbus", "tca",
        "tcach", "tcam", "tcar", "tcaring", "tcll", "tcmpcr", "tcmplc", "tcmpt", "tcnd",
        "tcndcr", "tcnding", "tcnt", "tcrm", "tcrms", "tcst", "tcxt", "teacb", "teacli",
        "teain", "tearn", "teh", "teinper", "teinple", "teinpt", "terin", "terins", "ternper",
        "ternperature", "ternple", "ternpt", "terrn", "terrns", "teud", "teuder", "teut",
        "thau", "thauk", "thauks", "thc", "thcir", "thcm", "thcmc", "thcn", "Thcn", "thcory",
        "thcrc", "Thcrc", "Thcre", "thcsc", "Thcy", "thcy", "thein", "theine", "theorv",
        "Therc", "thern", "therne", "thernselves", "Thesc", "theu", "Thev", "thev", "theyll",
        "thicf", "thiu", "thiug", "thiuk", "thm", "thmg", "thmk", "thnmb", "thns", "thom",
        "thongh", "thosc", "Thosc", "thougb", "thrcad", "thrcat", "Throngh", "Througb",
        "thuinb", "thumh", "thurnb", "tickct", "tidc", "tidv", "tigbt", "tiglit", "tiine",
        "timc", "timne", "tinv", "tirc", "tirne", "titlc", "tiu", "tiuy", "tlian", "tliank",
        "tlianks", "Tliat", "tliat", "Tlie", "tlie", "tlieir", "tliem", "tlien", "Tlien",
        "Tliere", "tliere", "tliese", "Tliese", "Tliey", "tliey", "tliick", "tliief", "tliin",
        "tliing", "tliink", "tliirst", "Tliis", "tliis", "tliose", "Tliose", "tliread",
        "tlireat", "tlirow", "tlius", "Tm", "tmy", "tnbe", "tnne", "Tnrn", "tnrn", "toc",
        "todav", "togetber", "tonc", "tonch", "tongh", "tongne", "tonguc", "tonr", "tootb",
        "Torn", "tornorrow", "tou", "toucb", "toucli", "toue", "tougb", "tougli", "tougue",
        "tov", "towcl", "towcr", "towu", "toxvard", "tradc", "traiu", "trav", "travcl",
        "trcat", "trcaty", "trcc", "trcnd", "treatrnent", "treatv", "trernble", "treud",
        "tribc", "trihe", "trne", "trnnk", "trnst", "trnth", "truc", "trutb", "trutli",
        "truuk", "trv", "tubc", "tuhe", "tumpike", "tunc", "turu", "Turu", "tuue", "tvpe",
        "twicc", "typc", "uail", "uame", "uarrow", "uatiou", "uative", "uature", "uear",
        "uearly", "ueat", "ueck", "ueed", "ueedle", "uephew", "uest", "uet", "uever", "uew",
        "uews", "uext", "uglv", "uice", "uiece", "uight", "unablc", "unahle", "unc", "unclc",
        "undcr", "Undcr", "undemeath", "unitc", "unitcd", "unitv", "unlcss", "uoble",
        "uobody", "uod", "uoise", "uoou", "uor", "uormal", "uorth", "uose", "uot", "uote",
        "uotice", "uotiou", "uoue", "uow", "upou", "uppcr", "upperrnost", "upsct", "urgc",
        "urgcnt", "urgeut", "Usc", "usc", "uscd", "uscful", "uscr", "uuable", "uucle",
        "uuder", "uuiou", "uuit", "uuite", "uuited", "uuity", "uuless", "uumber", "uurse",
        "uut", "uutil", "vaiu", "vallcy", "vallev", "valne", "valuc", "vam", "vard", "varv",
        "vcil", "vcrb", "vcrsc", "vcry", "Vcry", "vcsscl", "veah", "vear", "vellow", "verv",
        "Verv", "ves", "vho", "victiin", "victirn", "vicw", "vield", "virtne", "virtuc",
        "visiou", "voicc", "volnme", "voluine", "volumc", "volurne", "votc", "vou", "voung",
        "vour", "vouth", "vovage", "vowcl", "voyagc", "waa", "wagc", "waiking", "waitcr",
        "wakc", "wam", "wandcr", "warinth", "warmtb", "warmtli", "warrn", "warrnth", "waru",
        "wasb", "wasli", "wasnt", "wastc", "watcb", "watcli", "watcr", "wauder", "waut",
        "wav", "wavc", "wbat", "Wbat", "wbeat", "wbeel", "wben", "Wben", "Wbere", "wbere",
        "Wbeu", "wbich", "wbile", "Wbile", "wbilst", "wbip", "wbite", "wbo", "Wbo", "wbole",
        "wbom", "wbose", "wby", "Wc", "wc", "wcak", "wcakcn", "wcalth", "wcapon", "wcar",
        "wcavc", "wccd", "wcck", "wcigh", "wcight", "wcll", "wcst", "wct", "weakeu", "wealtb",
        "weapou", "weigb", "weigbt", "welcorne", "westem", "whcat", "whccl", "whcn", "Whcn",
        "Whcrc", "whcrc", "Whcre", "Wherc", "wheu", "Wheu", "whicb", "Whicb", "Whicb",
        "whicli", "whilc", "Whilc", "whitc", "whitcn", "whiteu", "whoin", "wholc", "whorn",
        "whosc", "whv", "wickcd", "widc", "widcly", "widcn", "widelv", "wideu", "widtb",
        "widtli", "wifc", "winc", "winncr", "wintcr", "wipc", "wirc", "wisb", "wisc",
        "wisdoin", "wisdorn", "wisli", "Witb", "witb", "witbin", "witbout", "withiu", "withm",
        "witli", "Witli", "witliin", "wiu", "wiud", "wiudow", "wiue", "wiug", "wiuter",
        "wiuuer", "Wliat", "wliat", "wlien", "Wlien", "Wliere", "wliere", "wliich", "Wliile",
        "wliile", "wliilst", "wliip", "wliite", "Wlio", "wlio", "wliole", "wliom", "wliose",
        "wliy", "wmd", "wmdow", "wme", "wmg", "wmner", "wmter", "wo", "woinan", "womau",
        "wondcr", "wonld", "wonnd", "woodcn", "woodeu", "woolcn", "wooleu", "worin", "workcr",
        "wornan", "worrn", "worrv", "worsc", "wortb", "wortli", "wouder", "wouid", "wouldnt",
        "wouud", "wrcck", "writc", "writcr", "wroug", "ycar", "ycllow", "ycs", "yct", "yicld",
        "yntir", "yonng", "yonr", "yonth", "youtb", "youtli", "youug", "youve", "zcro",
        "stiil", "aword", "nnd", "KEW", "Sonth", "wa", "ou", "aa", "klnd", "tne", "ths"
    ]
    # fmt: on

    # Build scanno dictionary. All words made lower case.

    scanno_dictionary = {}
    for entry in scannos_misspelled:
        scoword = entry.lower()
        # Deal with duplicates.
        if scoword in scanno_dictionary:
            continue
        scanno_dictionary[scoword] = 0

    return scanno_dictionary


##
# PPTXT Main Function
##


def pptxt(project_dict: ProjectDict) -> None:
    """Top-level pptxt function."""
    global checker_dialog
    global book, word_list_map_count, word_list_map_lines, word_list_map_words
    global found_long_doctype_declaration
    global ssq, sdq, csq, cdq
    global longest_line, shortest_line
    global report_limit

    if not tool_save():
        return

    report_limit = 999999 if preferences.get(PrefKey.PPTEXT_VERBOSE) else 5

    found_long_doctype_declaration = False

    # Create the checker dialog to show results
    checker_dialog = PPtxtCheckerDialog.show_dialog(
        rerun_command=lambda: pptxt(project_dict),
    )

    # Get the whole of the file from the main text widget

    text = maintext().get_text()
    input_lines = text.splitlines()

    # Get book lines, list of words on line and word frequency.

    book = []
    word_list_map_words = []
    word_list_map_count = {}
    word_list_map_lines = {}

    # Counters for each quote type
    ssq = 0
    sdq = 0
    csq = 0
    cdq = 0
    longest_line = (0, 0)
    shortest_line = (0, 9999)

    for line_number, line in enumerate(input_lines, start=1):
        line = line.rstrip("\r\n")

        book.append(line)

        if non_text_line(line):
            word_list_map_words.append(
                []
            )  # Needs to correspond to lines, even when ignored
            continue

        line_length = len(line)
        if line_length > longest_line[1]:
            longest_line = (line_number, line_length)
        if 0 < line_length < shortest_line[1]:
            shortest_line = (line_number, line_length)

        # Note types of single/double quotes if present. They are
        # not being counted here, only their presence in the file.
        if "'" in line:
            ssq += 1
        if '"' in line:
            sdq += 1
        if re.search(r"[‘’]", line):
            csq += 1
        if re.search(r"[“”]", line):
            cdq += 1

        # Build a list, 'word_list_map_words', whose entries are themselves
        # a list of words on each line. It is indexed from zero and
        # will have as many entries as there are lines in the book.

        # Build a dictionary, 'word_list_map_count', of words in the book
        # and their frequency.

        # Build a dictionary, 'word_list_map_lines', whose key is a word
        # and its value a list of integer line numbers on which that word
        # appears.

        # Collect a dictionary of hyphenated words as well.

        wol = get_words_on_line(line)
        word_list_map_words.append(wol)
        for word in wol:
            if word in word_list_map_count:
                word_list_map_count[word] += 1
            else:
                word_list_map_count[word] = 1

            if word in word_list_map_lines:
                word_list_map_lines[word].append(line_number)
            else:
                word_list_map_lines[word] = [line_number]

    ###################################################
    # We're done reading the input. Start processing it.
    ###################################################

    if preferences.get(PrefKey.PPTXT_FILE_ANALYSIS_CHECK):
        file_analysis_check()
    if preferences.get(PrefKey.PPTXT_SPACING_CHECK):
        spacing_check()
    if preferences.get(PrefKey.PPTXT_REPEATED_WORDS_CHECK):
        repeated_words_check()
    if preferences.get(PrefKey.PPTXT_ELLIPSIS_CHECK):
        ellipsis_check()
    if preferences.get(PrefKey.PPTXT_CURLY_QUOTE_CHECK):
        curly_quote_check()
    if preferences.get(PrefKey.PPTXT_HYPHENATED_WORDS_CHECK):
        hyphenated_words_check()
    if preferences.get(PrefKey.PPTXT_ADJACENT_SPACES_CHECK):
        adjacent_spaces_check()
    if preferences.get(PrefKey.PPTXT_DASH_REVIEW_CHECK):
        dash_review_check()
    if preferences.get(PrefKey.PPTXT_SCANNO_CHECK):
        scanno_check()
    if preferences.get(PrefKey.PPTXT_WEIRD_CHARACTERS_CHECK):
        weird_characters_check()
    if preferences.get(PrefKey.PPTXT_HTML_CHECK):
        html_check()
    if preferences.get(PrefKey.PPTXT_UNICODE_NUMERIC_CHARACTER_CHECK):
        unicode_numeric_character_check()
    if preferences.get(PrefKey.PPTXT_SPECIALS_CHECK):
        specials_check(project_dict)

    # Add final divider line to dialog.

    checker_dialog.add_footer(f"{'-' * 80}")
    checker_dialog.display_entries()
    # Select first entry (which might not be one with a line number)
    checker_dialog.select_entry_by_index(0)
