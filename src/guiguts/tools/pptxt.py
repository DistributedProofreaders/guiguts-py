"""PPtxt tool"""


from guiguts.checkers import CheckerDialog
from guiguts.maintext import maintext
from guiguts.utilities import IndexRowCol, IndexRange

from typing import Dict, Sequence, List
import regex as re

########################################################
# pptxt.py
# Perl author: Roger Franks (DP:rfrank) - 2009
# Go author: Roger Franks (DP:rfrank) - 2020
# Python author: Quentin Campbell (DP:qgc) - 2024
# Last edit: 7-mar-2024
########################################################


def pptxt() -> None:
    ######################################################################
    # Utility functions and variables saved between function calls
    ######################################################################

    found_long_doctype_declaration = False

    def mask_special_cases(match_obj: re.Match) -> str:
        """Obfuscate temporarily special case characters. The replacement will
        be reversed later so obscure Unicode number characters are used that
        are very unlikely to appear in book texts."""
        if match_obj.group(2) == "-":
            repl = "①"
        elif match_obj.group(2) == "’":
            repl = "②"
        elif match_obj.group(2) == "‘":
            repl = "③"
        elif match_obj.group(2) == "'":
            repl = "④"
        elif match_obj.group(2) == ".":
            repl = "⑤"
        elif match_obj.group(2) == "^":
            repl = "⑥"
        elif match_obj.group(2) == "—":
            # Replace emdash with space in this situation
            repl = " "
        else:
            repl = match_obj.group(2)
        return match_obj.group(1) + repl + match_obj.group(3)

    def get_words_on_line(line: str) -> list[str]:
        """Parses the text to find all the 'words' on a line
        and returns them as a (possibly) empty list."""

        if len(line) == 0:
            return []

        # Words may be surrounded by abandoned HTML tags, entities,
        # Unicode numeric character references, etc. Remove these
        # from the line first of all so genuine words are easier to
        # identify.

        # A document starting with a "<!DOCTYPE>" declaration is
        # assumed to be an HTML file. We have to treat this HTML
        # declaration specially as it may overflow onto a second
        # line in the case of older documents (HTML 4 or XHTML).
        # Check for this.

        # Variable 'found_long_doctype_declaration' needs to exist
        # between function calls.
        nonlocal found_long_doctype_declaration

        if found_long_doctype_declaration:
            # Second line of a long <!DOCTYPE> declaration. Toss it.
            found_long_doctype_declaration = False
            return []

        if re.search(r"<!DOCTYPE", line, re.IGNORECASE) and ">" not in line:
            # Looks like a two-line <!DOCTYPE declaration. Toss it
            # and set flag to toss the second line too.
            found_long_doctype_declaration = True
            return []

        # A short HTML 5 <!DOCTYPE> declaration will not be detected
        # by the above tests. However it will be detected as an HTML
        # 'tag' next and removed from line.

        new_line = ""
        while res := re.search(r"<(?=[!\/a-z]).*?(?<=[\"A-Za-z0-9\/]|-)>", line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]
        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace HTML entities (e.g. &amp;) with a space.
        new_line = ""
        while res := re.search(r"(&[a-z0-9]+?;)", line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]
        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace tokens consisting only of digits.
        new_line = ""
        while res := re.search(r"(\b\p{Nd}+\b)", line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]
        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace Unicode numeric character references with a space.
        new_line = ""
        while res := re.search(r"(&#[0-9]{1,4};|&#x[0-9a-fA-F]{1,4};)", line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]
        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace 1/2-style fractions with a space.
        new_line = ""
        while res := re.search(r"[0-9]+?/[0-9]+?", line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]
        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Replace [99]-type footnote anchors with a space.
        new_line = ""
        while res := re.search(r"\[[0-9]+?\]|\[[0-9]+?[a-zA-Z]\]", line):
            new_line += " " + line[0 : res.start(0)]
            line = line[res.start(0) + len(res.group(0)) :]
        if len(line) != 0:
            new_line += " " + line
        line = new_line

        # Remove italic markup (_) before letter and after letter or period (.).
        while res := re.search(r"(.*?)(_(?=\p{L}).*?(?<=\p{L}|\.)_)(.*)", line):
            t = res.group(2)
            t = t.replace("_", " ")
            line = res.group(1) + t + res.group(3)

        # Protect special cases by masking them temporarily:
        # E.g.
        # high-flying, hasn’t, ’tis, Househ^d
        # all stay intact
        # Capitalisation is retained.
        # Additionally, an emdash separating words in, for
        # example, the ToC is replaced by a space.

        # Need these twice to handle alternates
        # E.g. fo’c’s’le

        # Emdash
        line = re.sub(
            r"([\p{L}\p{Nd}\p{P}=])(\—)([\p{L}\p{N}’‘“_\(])",
            mask_special_cases,
            line,
        )
        line = re.sub(
            r"([\p{L}\p{Nd}\p{P}=])(\—)([\p{L}\p{N}’‘“_\(])",
            mask_special_cases,
            line,
        )
        # Minus
        line = re.sub(r"([\p{L}①②③④⑤\.=])(\-)([\p{L}\p{N}])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤\.=])(\-)([\p{L}\p{N}])", mask_special_cases, line)
        # The others.
        line = re.sub(r"([\p{L}①②③④⑤])(’)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(’)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤]|^)(’)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤]|^)(’)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(‘)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(‘)([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(\')([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤])(\')([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤]|^)(\')([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(r"([\p{L}①②③④⑤]|^)(\')([\p{L}①②③④⑤])", mask_special_cases, line)
        line = re.sub(
            r"([\p{L}①②③④⑤])(\.)([\p{L}①②③④⑤\p{P}])", mask_special_cases, line
        )
        line = re.sub(
            r"([\p{L}①②③④⑤])(\.)([\p{L}①②③④⑤\p{P}])", mask_special_cases, line
        )
        line = re.sub(
            r"([\p{L}①②③④⑤])(\^)([\p{L}①②③④⑤\p{P}])", mask_special_cases, line
        )
        line = re.sub(
            r"([\p{L}①②③④⑤])(\^)([\p{L}①②③④⑤\p{P}])", mask_special_cases, line
        )

        s = ""
        indx = 0

        while indx < len(line):
            # Look for 'words', one character at a time.
            if (
                line[indx : indx + 1].isnumeric()
                or line[indx : indx + 1].isalpha()
                or line[indx : indx + 1].isspace()
            ):
                s = s + line[indx : indx + 1]
            else:
                s = s + " "
            indx += 1

        # Use temporary list to hold the split line while we put
        # back the protected characters.
        T = s.split()
        L = []
        for n in range(len(T)):
            # For efficiency!
            Tn = T[n]
            Tn = Tn.replace("①", "-")
            Tn = Tn.replace("②", "’")
            Tn = Tn.replace("③", "‘")
            Tn = Tn.replace("④", "'")
            Tn = Tn.replace("⑤", ".")
            Tn = Tn.replace("⑥", "^")
            L.append(Tn)

        return L

    ######################################################################
    # blank line spacing check
    ######################################################################

    def spacing_check() -> None:
        """Blank line spacing check that flags other than 4121, 421 or 411 spacing."""

        checker_dialog.add_entry(
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
        BL_cnt = 0
        prev_line_was_BL = False
        prev_BL_cnt = 0
        BL_spacing_ISSUES = []
        line_number = 1
        four_line_spacing_found = False
        no_other_spacing_issues = False

        for line in book:
            BL = re.match(r"^ *$", line)
            if BL:
                # Blank line.
                BL_cnt += 1
                prev_line_was_BL = True
            elif not BL and prev_line_was_BL:
                if BL_cnt == 3 or BL_cnt > 4:
                    # i.e. 5..131.., 4..151.., etc, spacing.
                    BL_spacing_ISSUES.append((BL_cnt, line_number))
                elif BL_cnt == 4:
                    four_line_spacing_found = True
                    no_other_spacing_issues = True
                elif BL_cnt == 2:
                    if prev_BL_cnt == 2:
                        # i.e. 4..1221..., etc, spacing.
                        BL_spacing_ISSUES.append((BL_cnt, line_number))
                prev_BL_cnt = BL_cnt
                BL_cnt = 0
                prev_line_was_BL = False
            line_number += 1

        # Output to dialog any line spacing issues found. We have a list
        # of issue tuples: (int: spacing count, int: line number)

        for issue in BL_spacing_ISSUES:
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
            checker_dialog.add_entry("")
            checker_dialog.add_entry(
                "    No 4-line spacing found in book - that's unusual!"
            )
        elif no_other_spacing_issues:
            checker_dialog.add_entry("")
            checker_dialog.add_entry(
                "    Book appears to conform to DP paragraph/block spacing standards."
            )

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # repeated words check
    ######################################################################

    def repeated_words_check() -> None:
        """Repeated words check."""

        checker_dialog.add_entry(
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

        none_found = True
        for rec_num in range(len(book) - 1):
            book_line = book[rec_num]
            words_on_line = word_list_map_words[rec_num]
            # Run through words found on a line looking for possible repeats. This quick
            # and cheap check eliminates most lines from being 'possibles'.
            possibles = False
            for i in range(len(words_on_line) - 1):
                word = words_on_line[i]
                wordn1 = words_on_line[i + 1]
                # Chop apostrophe and following characters of second word.
                # E.g. "Jackey Jackey's". Note that "he had haddock" as a
                # possible from the above will be eliminated by the more
                # precise regex test below.
                if word == wordn1[: len(word)]:
                    possibles = True
            if possibles:
                # For each word on line see if a copy follows separated only
                # by one or more spaces. These are the true repeated words.
                for word in words_on_line:
                    # Build a regex.
                    regx = f"(\\b{word}\\b +\\b{word}\\b)"
                    if res := re.search(regx, book_line):
                        none_found = False
                        repl = " " * len(word)
                        # Obsfucate the first occurence of 'word' on the line so
                        # next re.search can't find it. It's replaced by blanks
                        # to the same length as 'word'.
                        book_line = re.sub(word, repl, book_line, count=1)
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
                        checker_dialog.add_entry(
                            record,
                            IndexRange(start_rowcol, end_rowcol),
                            hilite_start,
                            hilite_end,
                        )

            # We may get here also if current line is a blank line.

            if len(words_on_line) > 0:
                # Completed determinative search of line for possible repeated words.
                # Now look at last word on the line and the first word of the next.
                word = words_on_line[-1]
                # If last word on current line is same as first word on next line then
                # this is also an instance of repeated words.
                regx1 = f"(\\b{word}$)"
                regx2 = f"(^{word}\\b)"
                if (res1 := re.search(regx1, book[rec_num])) and (
                    res2 := re.search(regx2, book[rec_num + 1])
                ):
                    none_found = False
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
                    checker_dialog.add_entry(
                        record,
                        IndexRange(start_rowcol, end_rowcol),
                        hilite_start,
                        hilite_end,
                    )
        # At this point all lines but the last have been searched for repeated words.
        # Do this now for the last line of the book.

        if len(book) > 0:
            last_line = book[-1]
            words_on_line = word_list_map_words[-1]
            for word in words_on_line:
                # Build a regex.
                regx = f"(\\b{word}\\b +\\b{word}\\b)"
                if res := re.search(regx, last_line):
                    none_found = False
                    repl = " " * len(word)
                    # Obsfucate the first occurence of 'word' on the line so
                    # next re.search can't find it. It's replaced by blanks
                    # to the same length as 'word'.
                    last_line = re.sub(word, repl, last_line, count=1)
                    # Get start/end of the repeated words in file.
                    last_line_number = len(book)
                    error_start = str(last_line_number) + "." + str(res.start(0))
                    error_end = str(last_line_number) + "." + str(res.end(0))
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
                    checker_dialog.add_entry(
                        record,
                        IndexRange(start_rowcol, end_rowcol),
                        hilite_start,
                        hilite_end,
                    )

        if none_found:
            checker_dialog.add_entry("")
            checker_dialog.add_entry("    No repeated words found.")

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # hyphenated/non-hyphenated words check
    ######################################################################

    def hyphenated_words_check() -> None:
        """Repeated words check."""

        checker_dialog.add_entry(
            "----- Hyphenated/non-hyphenated words check ------------------------------------"
        )

        first_header = True
        none_found = True
        if len(hyphenated_words_dictionary) != 0:
            for word_with_hyphen in hyphenated_words_dictionary:
                # Make a non-hyphenated version.
                word_with_no_hyphen = re.sub("-", "", word_with_hyphen)
                if word_with_no_hyphen in word_list_map_count:
                    # Here when hyphenated and non-hyphenated version of a word.
                    none_found = False
                    word_count_with_no_hyphen = word_list_map_count[word_with_no_hyphen]
                    word_count_with_hyphen = word_list_map_count[word_with_hyphen]
                    # Make a header with this info and output it to dialog.
                    # E.g. "hyphen-ated (1) <-> hyphenated (3)".
                    record = f"{word_with_hyphen} ({word_count_with_hyphen}) <-> {word_with_no_hyphen} ({word_count_with_no_hyphen})"
                    # Insert a blank line before each header except the first one.
                    if first_header:
                        first_header = False
                    else:
                        checker_dialog.add_entry("")
                    # Add header record to dialog.
                    checker_dialog.add_entry(record)
                    # Under the header add to the dialog every line containing an instance of the word.
                    # If there are multiple instances of a word on a line then the line will appear in
                    # the dialog multiple times, each time highlighting a different instance of word.
                    #
                    # We will do the same with the non-hyphenated version of the word.

                    line_list = word_list_map_lines[word_with_hyphen]
                    prev_line_number = -1
                    regx = f"(\\b{word_with_hyphen}\\b)"
                    for line_number in line_list:
                        # The same line number can appear multiple times in the list if the word in question
                        # appears multiple times on the line. Treat each appearance of the word separately.
                        # We do this using re.finditer() the first time the line number appears in the list
                        # list then ignoring all other appearances of that line number in the list.
                        if line_number == prev_line_number:
                            prev_line_number = line_number
                            continue
                        else:
                            # Use re.finditer() to generate a new dialog line for each time the word appears
                            # on the line.
                            line = book[line_number - 1]
                            IX = re.finditer(regx, line)
                            while True:
                                try:
                                    match_obj = next(IX)
                                except StopIteration:
                                    break
                                # Get start/end of error in file.
                                error_start = (
                                    str(line_number) + "." + str(match_obj.start(1))
                                )
                                error_end = (
                                    str(line_number) + "." + str(match_obj.end(1))
                                )
                                # Store in structure for file row/col positions & ranges.
                                start_rowcol = IndexRowCol(error_start)
                                end_rowcol = IndexRowCol(error_end)
                                # Highlight occurrence of word in the line.
                                hilite_start = match_obj.start(1)
                                hilite_end = match_obj.end(1)
                                # Add record to the dialog.
                                checker_dialog.add_entry(
                                    line,
                                    IndexRange(start_rowcol, end_rowcol),
                                    hilite_start,
                                    hilite_end,
                                )
                        prev_line_number = line_number

                    # We do the same for the non-hyphenated version of the word. Separate this
                    # list of lines from the ones above with a rule.

                    checker_dialog.add_entry("-----")

                    line_list = word_list_map_lines[word_with_no_hyphen]
                    prev_line_number = -1
                    regx = f"(\\b{word_with_no_hyphen}\\b)"
                    for line_number in line_list:
                        # The same line number can appear multiple times in the list if the word in question
                        # appears multiple times on the line. Treat each appearance of the word separately.
                        # We do this using re.finditer() the first time the line number appears in the list
                        # list then ignoring all other appearances of that line number in the list.
                        if line_number == prev_line_number:
                            prev_line_number = line_number
                            continue
                        else:
                            # Use re.finditer() to generate a new dialog line for each time the word appears
                            # on the line.
                            line = book[line_number - 1]
                            IX = re.finditer(regx, line)
                            while True:
                                try:
                                    match_obj = next(IX)
                                except StopIteration:
                                    break
                                # Get start/end of error in file.
                                error_start = (
                                    str(line_number) + "." + str(match_obj.start(1))
                                )
                                error_end = (
                                    str(line_number) + "." + str(match_obj.end(1))
                                )
                                # Store in structure for file row/col positions & ranges.
                                start_rowcol = IndexRowCol(error_start)
                                end_rowcol = IndexRowCol(error_end)
                                # Highlight occurrence of word in the line.
                                hilite_start = match_obj.start(1)
                                hilite_end = match_obj.end(1)
                                # Add record to the dialog.
                                checker_dialog.add_entry(
                                    line,
                                    IndexRange(start_rowcol, end_rowcol),
                                    hilite_start,
                                    hilite_end,
                                )
                        prev_line_number = line_number

        if none_found:
            checker_dialog.add_entry("")
            checker_dialog.add_entry(
                "    No non-hyphenated versions of hyphenated words found."
            )

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # Unusual character check. Collects and reports lines that contain
    # characters ('weirdos') not normally found in an an English text.
    # Each 'weirdo' on a line in the dialog is highlighted.
    ######################################################################

    def weird_characters() -> None:
        """Collects lines containing unusual characters. Lines in the report
        are grouped by unusual character and each instance of the character
        on a report line is highlighted."""

        checker_dialog.add_entry(
            "----- Character checks ---------------------------------------------------------"
        )

        first_header = True
        none_found = True

        weirdos_lines_dictionary: Dict[str, list[int]] = {}
        weirdos_counts_dictionary: Dict[str, int] = {}

        # Build dictionary of unusual characters ('weirdos'). The key is a
        # weirdo and the value a list of line numbers on which that character
        # appears.

        line_number = 1
        for line in book:
            # Get list of weirdos on this line. That means any character NOT in the regex.
            weirdos_list = re.findall(
                r"[^A-Za-z0-9\s.,:;?!\\\-_—–=“”‘’\[\]\(\){}]", line
            )
            # Update dictionary with the weirdos from the line.
            for weirdo in weirdos_list:
                if weirdo in weirdos_lines_dictionary:
                    weirdos_lines_dictionary[weirdo].append(line_number)
                else:
                    weirdos_lines_dictionary[weirdo] = [line_number]

                if weirdo in weirdos_counts_dictionary:
                    weirdos_counts_dictionary[weirdo] += 1
                else:
                    weirdos_counts_dictionary[weirdo] = 1
            line_number += 1

        # If nothing in the dictioary, nothing to do!
        if len(weirdos_lines_dictionary) != 0:
            none_found = False
            for weirdo in weirdos_lines_dictionary:
                count = weirdos_counts_dictionary[weirdo]
                # Make a header with this info and output it to dialog.
                # E.g. "'¢' (3)".
                record = f"'{weirdo}' ({count})"
                # Insert a blank line before each header except the first one.
                if first_header:
                    first_header = False
                else:
                    checker_dialog.add_entry("")
                # Add header record to dialog.
                checker_dialog.add_entry(record)

                # Under the header add to the dialog every line containing an instance of the weirdo.
                # If there are multiple instances of a weirdo on a line then the line will appear in
                # the dialog multiple times, each time highlighting a different instance of it.

                line_list = weirdos_lines_dictionary[weirdo]
                prev_line_number = -1
                regx = f"(\\{weirdo})"
                for line_number in line_list:
                    # The same line number can appear multiple times in the list if the weirdo in question
                    # appears multiple times on the line. Treat each appearance of the weirdo separately.
                    # We do this using re.finditer() the first time the line number appears in the list
                    # list then ignoring all other appearances of that line number in the list.
                    if line_number == prev_line_number:
                        prev_line_number = line_number
                        continue
                    else:
                        # Use re.finditer() to generate a new dialog line for each time the weirdo appears
                        # on the line.
                        line = book[line_number - 1]
                        IX = re.finditer(regx, line)
                        while True:
                            try:
                                match_obj = next(IX)
                            except StopIteration:
                                break
                            # Get start/end of error in file.
                            error_start = (
                                str(line_number) + "." + str(match_obj.start(1))
                            )
                            error_end = str(line_number) + "." + str(match_obj.end(1))
                            # Store in structure for file row/col positions & ranges.
                            start_rowcol = IndexRowCol(error_start)
                            end_rowcol = IndexRowCol(error_end)
                            # Highlight occurrence of word in the line.
                            hilite_start = match_obj.start(1)
                            hilite_end = match_obj.end(1)
                            # Add record to the dialog.
                            checker_dialog.add_entry(
                                line,
                                IndexRange(start_rowcol, end_rowcol),
                                hilite_start,
                                hilite_end,
                            )
                    prev_line_number = line_number

        if none_found:
            checker_dialog.add_entry("")
            checker_dialog.add_entry("    No unusual characters found.")

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # Specials check. Multiple checks done on each line during a single
    # read of book lines.
    ######################################################################

    def specials_check() -> None:
        """A series of textual checks done on a single read of the book lines"""

        checker_dialog.add_entry(
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
            """Helper function for abstraction of processing logic

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
                    # Obscure symbol is a dentistry symbol (Hex 23c0, Dec 9152).
                    line_copy = (
                        line_copy[: res.start(0)]
                        + "⏀" * (res.end(0) - res.start(0))
                        + line[res.end(0) :]
                    )
            # Exceptions on line obscured. Any remaining instances of
            # pattern are to be highlighted.
            # Use re.finditer() to generate a new dialog line for each time the pattern (the issue
            # being checked) appears on the line.
            I = re.finditer(pattern, line_copy)
            while True:
                try:
                    match_obj = next(I)
                except StopIteration:
                    break
                # Get start/end of error in file.
                error_start = str(line_number) + "." + str(match_obj.start(0))
                error_end = str(line_number) + "." + str(match_obj.end(0))
                # Highlight occurrence of word in the line.
                hilite_start = match_obj.start(0)
                hilite_end = match_obj.end(0)
                if heading in specials_report:  # type: ignore[has-type]
                    specials_report[heading].append((line, error_start, error_end, hilite_start, hilite_end))  # type: ignore[has-type]
                else:
                    specials_report[heading] = [(line, error_start, error_end, hilite_start, hilite_end)]  # type: ignore[has-type]

        def process_word(word: str, exceptions: Sequence[str], line: str) -> None:
            """Helper function for abstraction of processing logic

            METHOD
            On the line passed in:
            1. Find the word on the line.
            2. Highlight text in same position on actual line.
            """

            # This function is within the scope of specials_check() function from where it is called.
            line_number = line_index + 1
            something_to_report = True
            for exception in exceptions:
                if re.search(exception, word):
                    # Word matches an exception so nothing to report.
                    something_to_report = False
                    break
            # Report word if it is not an exception/empty exceptions list.
            if something_to_report:
                # Get all occuurences of word on this line and report them.
                regx = f"\\b{word}\\b"
                IX = re.finditer(regx, line)
                while True:
                    try:
                        match_obj = next(IX)
                    except StopIteration:
                        break
                    # Get start/end of error in file.
                    error_start = str(line_number) + "." + str(match_obj.start(0))
                    error_end = str(line_number) + "." + str(match_obj.end(0))
                    # Highlight occurrence of word in the line.
                    hilite_start = match_obj.start(0)
                    hilite_end = match_obj.end(0)
                    if heading in specials_report:  # type: ignore[has-type]
                        specials_report[heading].append((line, error_start, error_end, hilite_start, hilite_end))  # type: ignore[has-type]
                    else:
                        specials_report[heading] = [(line, error_start, error_end, hilite_start, hilite_end)]  # type: ignore[has-type]

        specials_report: Dict[str, list[tuple]] = {}

        ####
        # The following series of checks operate on text of each line.
        ####

        none_found = True

        # NOTE: Count from 0 rather than 1. Actual line number for book
        #       text will be line_index + 1.

        line_index = 0
        for line in book:
            exceptions: List[str] = []
            # Allow Illustrations, Greek, Music or number in '[]'
            heading = (
                "Opening square bracket followed by other than I, G, M, S or digit."
            )
            exceptions.append(r"\[Blank Page\]")
            process_line_with_pattern(r"\[[^IGMS\d]", exceptions, line)
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

            # Ampersand character in line (excluding unicode numeric character references)
            heading = "Ampersand character in line (excluding unicode numeric character references)."
            process_line_with_pattern(r"&(?!#)", exceptions, line)

            # Single character line
            heading = "Single character line."
            process_line_with_pattern(r"^.$", exceptions, line)

            # Broken hyphenation
            heading = "Broken hyphenation."
            process_line_with_pattern(
                r"(\p{L}\- +?\p{L})|(\p{L} +?\-\p{L})", exceptions, line
            )

            # Comma spacing regexes
            heading = "Comma spacing."
            process_line_with_pattern(
                r"\p{L},\p{L}|\p{L},\p{N}|\s,|^,", exceptions, line
            )

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
            process_line_with_pattern(r"\s[\?!:;\.]", exceptions, line)
            # process_line_with_pattern(r"\s\p{P}", exceptions, line)

            # Abbreviation &c without period
            heading = "Abbreviation &c. without period."
            process_line_with_pattern(r"&c([^\.]|$)", exceptions, line)

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
                # Generate dialog tuples only if not an exception.
                heading = "Standalone 0."
                process_line_with_pattern(pattern, exceptions, line)

            # The following check for standalone 1 consists of:
            #
            # GENERAL TEST
            pattern = r"(?<=^|\P{Nd})(1)(?=$|\P{Nd})"
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
                # standalone 1 allowed as "1." (e.g. a numbered list).
                exceptions.append(r"(?<=^|\P{Nd})(1)(?=\.(?!$))")
                # standalone 1 allowed as "1st".
                exceptions.append(r"(?<=^|\P{Nd})(1)st")
                # standalone 1 allowed as a footnote anchors
                exceptions.append(r"\[(1)\]")
                # Generate dialog tuples only if not an exception.
                heading = "Standalone 1."
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
                # Generate dialog tuples only if not an exception.
                heading = "Punctuation after 'the'."
                process_line_with_pattern(pattern, exceptions, line)

            # The following check for double punctuation consists of:
            #
            # GENERAL TEST
            pattern = r",\.|\.,|,,|(?!<\.)\.\.(?!\.)"
            if re.search(pattern, line):
                # Here if possible issue.
                #
                # EXCEPTIONS
                #
                # NB Each regex below returns the pattern in a match
                #    as group(0).
                exceptions = []
                # Ignore contexts such as "etc.,", "&c.,"
                exceptions.append(r"(?i)etc\.,")
                exceptions.append(r"(?i)etc\.{4}(?!\.)")
                exceptions.append(r"(?i)&c\.,")
                # Generate dialog tuples only if not an exception.
                heading = "Queried double punctuation."
                process_line_with_pattern(pattern, exceptions, line)

            # Unexpected comma check. Commas should not occur after these words:
            pattern = (
                r"(?i)\bthe,|\bit’s,|\btheir,|\ban,|\ba,|\bour,|\bthat’s,|\bits,|\bwhose,|\bevery,"
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
                r"|\band\.|\bbut\.|\bas\.|\bif\.|\bthe\.|\bits\.|\bit’s\.|\buntil\.|\bthan\.|\bwhether\.|\bi’ll\."
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

            # Temporary variable until decision on loading 'good words'
            # and/or 'proj dict' is made. It means that...
            in_good_words_list = False
            # ...for the moment we assume any suspect word we want to look
            # up in either collection is not found so will be flagged by
            # the checks. If it had been present in those collections the
            # check would not have reported the word.

            # We already have a list of words for this line.
            already_checked = []
            for word in word_list_map_words[line_index]:
                if word in already_checked:
                    # Word has occurred again on the line but it has
                    # already been reported on. Don't repeat reports.
                    continue

                # Looks for mixed case within word but not if the word is in
                # the good words list or occurs more than once in the book.

                if word_list_map_count[word] == 1 and not in_good_words_list:
                    if re.search(r".\p{Ll}+[-]?\p{Lu}", word):
                        # NB word occurs only once in the book.
                        line = book[line_index]
                        # Generate dialog tuples.
                        heading = "Mixed case in word."
                        process_word(word, [], line)

                # Word start and word endings checks.

                if len(word) > 2:
                    # Check word ending (last 2 characters).
                    last2 = word[len(word) - 2 :]
                    # The following pairs of characters are very rare at word end.
                    if (
                        re.match(
                            "cb|gb|pb|sb|tb|wh|fr|br|qu|tw|gl|fl|sw|gr|sl|cl|iy", last2
                        )
                        and not in_good_words_list
                    ):
                        line = book[line_index]
                        # Generate dialog tuples.
                        heading = f"Query word ending with '{last2}'."
                        process_word(word, [], line)

                    # Check word start (first 2 characters)
                    first2 = word[0:2]

                    # The following pairs of characters are very rare at start of word.
                    if (
                        re.match(
                            "hr|hl|cb|sb|tb|wb|tl|tn|rn|lt|tj", first2, re.IGNORECASE
                        )
                        and not in_good_words_list
                    ):
                        line = book[line_index]
                        # Generate dialog tuples.
                        heading = f"Query word starting with '{first2}'."
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
                    exceptions.append(r"\b\p{Nd}*[02-9]?1st\b")
                    # E.g. 282nd
                    exceptions.append(r"\b\p{Nd}*[02-9]?2nd\b")
                    # E.g. 373rd
                    exceptions.append(r"\b\p{Nd}*[02-9]?3rd\b")
                    # E.g. 373d
                    exceptions.append(r"\b\p{Nd}*[23]d\b")
                    # E.g. 65th
                    exceptions.append(r"\b\p{Nd}*[4567890]th\b")
                    # E.g. 10th
                    exceptions.append(r"\b\p{Nd}*[4567890]th\b")
                    # Generate dialog tuples only if not an exception.
                    heading = "Query mixed letters/digits in word."
                    # NB 'heading' is accessed in the 'process_word' function
                    #    which is in same scope. flake8 complains about it.
                    process_word(word, exceptions, line)

                # If the word occurs again on this line we will not
                # repeat the checks.
                already_checked.append(word)

            line_index += 1

        # Done with specials checks. Report what, if anything, we've found.

        # Produce dialog lines from the dialog tuples generated by
        # the checks above. The specials_report dictionary may be
        # empty in which case there will be no dialog messages.
        first_header = True
        for header_line in specials_report:
            none_found = False
            # Insert a blank line before each header except the first one.
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            # Add header record to dialog.
            checker_dialog.add_entry(header_line)
            tuples_list = specials_report[header_line]
            # Generate the dialog messages
            for tple in tuples_list:
                line = tple[0]
                # Get start/end of error in file.
                error_start = tple[1]
                error_end = tple[2]
                # Store in structure for file row/col positions & ranges.
                start_rowcol = IndexRowCol(error_start)
                end_rowcol = IndexRowCol(error_end)
                # Highlight occurrence of word in the line.
                hilite_start = tple[3]
                hilite_end = tple[4]
                # Add record to the dialog.
                checker_dialog.add_entry(
                    line, IndexRange(start_rowcol, end_rowcol), hilite_start, hilite_end
                )

        if none_found:
            checker_dialog.add_entry("")
            checker_dialog.add_entry("    No special situations reports.")

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # abandoned HTML tag check
    ######################################################################

    def html_check() -> None:
        """Abandoned HTML tag check."""

        checker_dialog.add_entry(
            "----- Abandoned HTML tag check -------------------------------------------------"
        )

        # Courtesy limit if user uploads fpgen source, etc.
        courtesy_limit = 5
        abandoned_HTML_tag_count = 0
        lines_with_HTML_tags = 0

        line_number = 1
        regx = r"<(?=[!\/a-z]).*?(?<=[\"A-Za-z0-9\/]|-)>"
        for line in book:
            if re.findall(regx, line):
                # Use re.finditer() to generate a new dialog line for each match
                # on the line.
                IX = re.finditer(regx, line)
                while True:
                    try:
                        match_obj = next(IX)
                    except StopIteration:
                        break
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
                    abandoned_HTML_tag_count += 1
                lines_with_HTML_tags += 1

            # If abandoned_HTML_tag_count > courtesy_limit then it looks like we are
            # not dealing with a plain text file afterall. Flag this and report the
            # number of HTML tags found so far then exit loop.

            if abandoned_HTML_tag_count > courtesy_limit:
                checker_dialog.add_entry("")
                record = f"Source file not plain text: {lines_with_HTML_tags} book lines with {abandoned_HTML_tag_count} markup instances so far..."
                checker_dialog.add_entry(record)
                checker_dialog.add_entry("...abandoning check.")
                # Don't search any more book lines for HTML tags.
                break

            line_number += 1

        # All book lines scanned or scanning abandoned.
        if abandoned_HTML_tag_count == 0:
            checker_dialog.add_entry("")
            checker_dialog.add_entry("    No abandoned HTML tags found.")

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # Unicode numeric character references check.
    ######################################################################

    def unicode_numeric_character_check() -> None:
        """Unicode numeric character references check."""

        checker_dialog.add_entry(
            "----- Unicode numeric character references check -------------------------------"
        )

        # Courtesy limit if user uploads fpgen source, etc.
        numeric_char_reference_count = 0

        line_number = 1
        regx = r"(&#[0-9]{1,4};|&#x[0-9a-fA-F]{1,4};)"
        for line in book:
            if re.search(regx, line):
                # Use re.finditer() to generate a new dialog line for each match
                # on the line.
                IX = re.finditer(regx, line)
                while True:
                    try:
                        match_obj = next(IX)
                    except StopIteration:
                        break
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
                    numeric_char_reference_count += 1

            line_number += 1

        # All book lines scanned.
        if numeric_char_reference_count == 0:
            checker_dialog.add_entry("")
            checker_dialog.add_entry(
                "    No unicode numeric character references found."
            )

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # Scan book for two or more adjacent spaces on a line that
    # does not start with a space
    ######################################################################

    def adjacent_spaces_check() -> None:
        """Scans text of each book line for adjacent spaces."""

        checker_dialog.add_entry(
            "----- Adjacent spaces check (poetry, block-quotes, etc., are ignored) ----------"
        )

        # If the line starts with one or more spaces (poetry, block-quotes, etc.,
        # adjacent spaced will not be reported.

        no_adjacent_spaces_found = True

        line_number = 1
        for line in book:
            #  Spaced poetry, block-quotes, etc., will fail the 'if' below.

            # If adjacent spaces but no leading spaces then ...
            if re.search(r"\s\s+?", line) and not re.search(r"^\s+?", line):
                no_adjacent_spaces_found = False
                regx = r"\s\s+"
                # Use re.finditer() to generate a new dialog line for each match
                # on the line.
                IX = re.finditer(regx, line)
                while True:
                    try:
                        match_obj = next(IX)
                    except StopIteration:
                        break
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

            line_number += 1

        # All book lines scanned.
        if no_adjacent_spaces_found:
            checker_dialog.add_entry("")
            checker_dialog.add_entry("    No lines with adjacent spaces found.")

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # Scan book for trailing spaces
    ######################################################################

    def trailing_spaces_check() -> None:
        """Scans each book line for trailing spaces."""

        checker_dialog.add_entry(
            "----- Trailing spaces check ----------------------------------------------------"
        )

        no_trailing_spaces_found = True
        line_number = 1
        regx = r" +$"
        for line in book:
            if res := re.search(regx, line):
                # Line has trailing space
                no_trailing_spaces_found = False
                # Get start/end of error in file.
                error_start = str(line_number) + "." + str(res.start(0))
                error_end = str(line_number) + "." + str(res.end(0))
                # Store in structure for file row/col positions & ranges.
                start_rowcol = IndexRowCol(error_start)
                end_rowcol = IndexRowCol(error_end)
                # Highlight occurrence of word in the line.
                hilite_start = res.start(0)
                hilite_end = res.end(0)
                # Add record to the dialog.
                checker_dialog.add_entry(
                    line, IndexRange(start_rowcol, end_rowcol), hilite_start, hilite_end
                )

            line_number += 1

        # All book lines scanned.
        if no_trailing_spaces_found:
            checker_dialog.add_entry("")
            checker_dialog.add_entry("    No lines with trailing spaces found.")

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    ######################################################################
    # dash review
    ######################################################################

    def double_dash_replace(matchobj: re.Match) -> str:
        """Called to replace exactly 2 emdashes by 1 emdash.

        Args:
            matchobj: A regex match object.
        """

        return matchobj.group(1) + "—" + matchobj.group(2)

    def report_all_occurrences_on_line(
        pattern: str, line: str, line_number: int
    ) -> None:
        """Abstraction of dialog code that's used repeatedly for reporting.

        Args:
            pattern - a regex of the pattern to matched and highlighted.
            line - the string on which to match the pattern.
            line_number - the line number of the line in the file.
        """

        IX = re.finditer(pattern, line)
        while True:
            try:
                match_obj = next(IX)
            except StopIteration:
                break
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

    def dash_review() -> None:
        """Hyphen/dashes check."""

        checker_dialog.add_entry(
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
        #                   [\p{Ll}—\p{P}(?=$)] between lower-case letter and closing punctuation
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

                if dbuf[line_index] == "" and re.match(
                    r"\p{Zs}*—", dbuf[line_index + 1]
                ):
                    # Replace only one occurrence; i.e. the prefixing one.
                    dbuf[line_index + 1] = dbuf[line_index + 1].replace("—", "", 1)

            line_index += 1

        # Go through the book line by line again and obfuscate valid occurrences
        # of Unicode dash characters. This is the second of the initial passes.
        #
        # The order of execution of these replacements on a line is important!

        # line number = line_index + 1
        line_index = 0
        while line_index < len(dbuf):
            dbuf[line_index] = dbuf[line_index].replace("_", "")
            # em-dash when 8 or more act as a separator
            dbuf[line_index] = re.sub(r"—{8,}", "", dbuf[line_index])
            # deleted words E.g. "as soon as Mr. —— had left the ship"
            dbuf[line_index] = re.sub(r"\s——\s", " QQ ", dbuf[line_index])
            # consider exactly two em-dashes as one
            dbuf[line_index] = re.sub(
                r"([^—])——([^—])", double_dash_replace, dbuf[line_index]
            )
            # hyphen-minus between two letters. Repeat to deal with lines like:
            #   pur-r-rta-a-a-tu-ur? I b’long to the Twenty-secun’ Nor’ Ka-a-a-li-i-na
            dbuf[line_index] = re.sub(r"\p{L}-\p{L}", "QQ", dbuf[line_index])
            dbuf[line_index] = re.sub(r"\p{L}-\p{L}", "QQ", dbuf[line_index])
            # hyphen between two letters. Repeat to deal with lines like:
            #   pur-r-rta-a-a-tu-ur? I b’long to the Twenty-secun’ Nor’ Ka-a-a-li-i-na
            dbuf[line_index] = re.sub(r"\p{L}‐\p{L}", "QQ", dbuf[line_index])
            dbuf[line_index] = re.sub(r"\p{L}‐\p{L}", "QQ", dbuf[line_index])
            # hyphen-minus when 8 or more act as a separator
            dbuf[line_index] = re.sub(r"-{8,}", "", dbuf[line_index])
            # non-breaking hyphen between two letters
            dbuf[line_index] = re.sub(r"\p{L}‑\p{L}", "", dbuf[line_index])
            # figure dash between two digits
            dbuf[line_index] = re.sub(r"\p{Nd}‒\p{Nd}", "", dbuf[line_index])
            # en-dash between two digits
            dbuf[line_index] = re.sub(r"\p{Nd}–\p{Nd}", "", dbuf[line_index])
            # en-dash with spaces between two digits
            dbuf[line_index] = re.sub(r"\p{Nd}\s–\s\p{Nd}", "", dbuf[line_index])
            # em-dash between letters with no spacing
            dbuf[line_index] = re.sub(r"\p{L}—\p{L}", "", dbuf[line_index])
            # em-dash between lower-case letter or 'I' and final punctuation
            dbuf[line_index] = re.sub(r"[\p{Ll}I]—\p{P}(?=$)", "", dbuf[line_index])
            # lower-case letter, em-dash, space, upper-case letter
            dbuf[line_index] = re.sub(r"\p{Ll}— \p{Lu}", "", dbuf[line_index])
            # em-dash should not end a line - may be exceptions
            dbuf[line_index] = re.sub(r"—\s*$", "", dbuf[line_index])

            line_index += 1

        # FINAL PASS: flag what remains.

        a_h2 = []
        a_hh = []
        a_hm = []
        a_hy = []  # type: ignore  # bug in mypy?
        a_nb = []
        a_fd = []
        a_en = []
        a_em = []
        a_un = []

        dash_suspects_found = False
        line_index = 0
        counth2 = 0

        while line_index < len(dbuf):
            line = dbuf[line_index]

            # Does line contain any dashes?
            if re.search(r"\p{Pd}", line):
                # Line has dashes so generate output records to flag
                # each type of invalid dash types found.

                dash_suspects_found = True
                not_consecutive_dashes = True

                # Look for pairs of hyphen-minus (keyboard "-") possibly being
                # used in place of em-dash. We will check and flag this later.
                if re.search(r"(?<!-)--(?!-)", line):
                    res = re.findall(r"(?<!-)--(?!-)", line)
                    counth2 += len(res)
                    a_h2.append((line_index + 1, book[line_index]))
                    # Delete all the pairs just found.
                    line = re.sub(r"(?<!-)--(?!-)", "", line)
                # Look for other consecutive dashes (of any kind).
                if res := re.search(r"(\p{Pd}\p{Pd}+)", line):  # type: ignore  # bug in mypy?
                    a_hh.append((line_index + 1, book[line_index]))
                    # Delete consecutive dashes just found. Any left at final test are 'unecognised'.
                    line = line.replace(res.group(0), "")  # type: ignore  # see 3 lines up re. bug
                    not_consecutive_dashes = False
                # Look for hyphen-minus
                if ch_hm in line and not_consecutive_dashes:
                    a_hm.append((line_index + 1, book[line_index]))
                    # Delete dash(es) just found. Any left at final test is 'unecognised'.
                    line = line.replace(ch_hm, "")
                # Look for non-breaking hyphen
                if ch_nb in line:
                    a_nb.append((line_index + 1, book[line_index]))
                    # Delete dash(es) just found. Any left at final test is 'unecognised'.
                    line = line.replace(ch_nb, "")
                # Look for figure dash
                if ch_fd in line:
                    a_fd.append((line_index + 1, book[line_index]))
                    # Delete dash(es) just found. Any left at final test is 'unecognised'.
                    line = line.replace(ch_fd, "")
                # Look for endash
                if ch_en in line:
                    a_en.append((line_index + 1, book[line_index]))
                    # Delete dash(es) just found. Any left at final test is 'unecognised'.
                    line = line.replace(ch_en, "")
                # Look for emdash
                if ch_em in line:
                    a_em.append((line_index + 1, book[line_index]))
                    # Delete dash(es) just found. Any left at final test is 'unecognised'.
                    line = line.replace(ch_em, "")
                # If any dashes left on line at this point treat them as unrecognised
                if re.search(r"\p{Pd}", line):
                    a_un.append((line_index + 1, book[line_index]))

            line_index += 1

        # Generate dialog entries about remaining entries.

        first_header = True

        # If many pairs of "--" detected report only the first five.

        if len(a_h2) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry("Pairs of '--' (keyboard '-') found")

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
                checker_dialog.add_entry(output_record)
            if counth2 > 5:
                checker_dialog.add_entry("")
                checker_dialog.add_entry(
                    "    [Book seems to use '--' as em-dash so not reporting these further]"
                )

        # Report other consecutive dashes

        if len(a_hh) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry(
                "Adjacent dashes (at least 8 emdash or keyboard '-' expected as separator)"
            )

            for record in a_hh:
                line_number = record[0]
                line = record[1]
                report_all_occurrences_on_line(r"(\p{Pd}\p{Pd}+)", line, line_number)

        # Report hyphen-minus

        if len(a_hm) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry("Hyphen-minus")
            for record in a_hm:
                line_number = record[0]
                line = record[1]
                report_all_occurrences_on_line(ch_hm, line, line_number)

        # Report hyphen

        if len(a_hy) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry("Hyphen")
            for record in a_hy:
                line_number = record[0]
                line = record[1]
                report_all_occurrences_on_line(ch_hy, line, line_number)

        # Report non-breaking hyphen

        if len(a_nb) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry("Non-breaking hyphen")
            for record in a_nb:
                line_number = record[0]
                line = record[1]
                report_all_occurrences_on_line(ch_nb, line, line_number)

        # Report figure dash

        if len(a_fd) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry("Figure dash")
            for record in a_fd:
                line_number = record[0]
                line = record[1]
                report_all_occurrences_on_line(ch_fd, line, line_number)

        # Report en-dash

        if len(a_en) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry("En-dash")
            for record in a_en:
                line_number = record[0]
                line = record[1]
                report_all_occurrences_on_line(ch_en, line, line_number)

        # Report em-dash

        if len(a_em) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry("Em-dash")
            for record in a_em:
                line_number = record[0]
                line = record[1]
                report_all_occurrences_on_line(ch_em, line, line_number)

        # Report unrecognised dash

        if len(a_un) > 0:
            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            checker_dialog.add_entry("Unrecognised dash")
            for record in a_un:
                line_number = record[0]
                line = record[1]
                report_all_occurrences_on_line(r"\p{Pd}", line, line_number)

        # All book lines scanned.
        if not dash_suspects_found:
            checker_dialog.add_entry("")
            checker_dialog.add_entry("    No dash suspects found.")

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    def scanno_check() -> None:
        """Checks the 'words' on a line against a long list
        of commonly misspelled words."""

        checker_dialog.add_entry(
            "----- Scannos check ------------------------------------------------------------"
        )

        scanno_dictionary = build_scanno_dictionary()
        scanno_outrecs: Dict[str, list[tuple]] = {}
        no_scannos_found = True

        line_index = 0
        for line in book:
            # We have the list of words on the line already in the
            # array 'word_list_map_words]'. It is indexed from zero.

            L = word_list_map_words[line_index]
            previously_found_on_this_line = []

            # Look for scannos among the words on this line.
            for word in L:
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
            line_index += 1

        # We're done looking for scannos on each line. Report what we found.
        # NB 'scanno_outrecs' is a dictionary. The keys are a scanno and the
        #    value is a list of tuples: [(line number, line text), ...]

        first_header = True
        for scanno in scanno_outrecs:
            # The value of each scanno key in scanno_outrecs dictionary
            # is a list of tuples: (line_number, line). For a given scanno
            # only one instance of it on a line has been noted in a tuple.
            # Find and add to dialog other instances that may also be on
            # the line.

            if first_header:
                first_header = False
            else:
                checker_dialog.add_entry("")
            # Header is the scanno.
            checker_dialog.add_entry(scanno)

            tple_list = scanno_outrecs[scanno]
            for tple in tple_list:
                line_number = tple[0]
                line = tple[1]

                # We know that scanno appears at least once on line; it may
                # be repeated, possibly in a different case.
                # Get all occuurences of scanno on line and report them.

                regx = f"\\b{scanno}\\b"
                IX = re.finditer(regx, line, re.IGNORECASE)
                while True:
                    try:
                        match_obj = next(IX)
                    except StopIteration:
                        break
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

        if no_scannos_found:
            checker_dialog.add_entry("")
            checker_dialog.add_entry("    No scannos found.")

        # Add line spacer at end of this checker section.
        checker_dialog.add_entry("")

    def build_scanno_dictionary() -> Dict[str, int]:
        """Builds a dictionary from a list of common misspelled words."""

        # List of common scannos. Add additions to end of the list.
        # Duplicates will be dealt with when building the dictionary.

        s = {}
        scannos_misspelled = []

        s[0] = ["1gth", "1lth", "1oth", "1Oth", "2gth", "2ist", "2lst", "oa", "po"]
        s[1] = ["2Oth", "2OTH", "2oth", "3lst", "3Oth", "3oth", "abead", "ablc"]
        s[2] = ["Abont", "abovc", "abscnt", "abseut", "acadernic", "acbe", "acccpt"]
        s[3] = ["accnse", "accornpany", "accusc", "accustorn", "achc", "aclie"]
        s[4] = ["actiou", "activc", "actnal", "adinire", "adinit", "admirc", "adnlt"]
        s[5] = ["adrnire", "adrnission", "adrnit", "advicc", "advisc", "affcct"]
        s[6] = ["aftcr", "Aftcr", "aftemoon", "agaiu", "Agaiu", "Agaiust", "agam"]
        s[7] = ["Agam", "Agamst", "agc", "agcncy", "agcnt", "agencv", "ageucy", "ageut"]
        s[8] = ["agrcc", "agreernent", "ahcad", "ahke", "ahle", "Ahont", "Ahout"]
        s[9] = ["ahout", "ahove", "ahroad", "ahsent", "ahve", "aiin", "ainong"]
        s[10] = ["ainount", "ainuse", "airn", "A-Iy", "aliead", "alikc", "alinost"]
        s[11] = ["alivc", "aln", "alonc", "alond", "aloue", "aloug", "alrnost"]
        s[12] = ["altbough", "altemative", "alwavs", "amd", "amnse", "amonnt", "amoug"]
        s[13] = ["amouut", "amusc", "ane", "angcr", "anglc", "angrv", "aniinal"]
        s[14] = ["anirnal", "annnal", "annov", "annt", "Anotber", "anotber", "Anothcr"]
        s[15] = ["Anotlier", "answcr", "anthor", "antnmn", "anv", "Anv", "anvhow"]
        s[16] = ["anvone", "anvwav", "anybow", "anyliow", "anyonc", "appcal", "appcar"]
        s[17] = ["applv", "appointrnent", "arca", "arcb", "arcli", "argne", "arguc"]
        s[18] = ["argurnent", "arin", "ariny", "arisc", "armv", "arn", "arnbition"]
        s[19] = ["arnbitious", "arnong", "arnongst", "arnount", "arnuse", "Aronnd"]
        s[20] = ["aronnd", "arouud", "Arouud", "arrangernent", "arrcst", "arrivc"]
        s[21] = ["arrn", "arrny", "asb", "asharned", "asidc", "aslccp", "asli"]
        s[22] = ["aspcct", "asscss", "assct", "assernbly", "assessrnent", "assnme"]
        s[23] = ["assuine", "assumc", "assurne", "assurnption", "atrnosphere", "attacb"]
        s[24] = ["attacli", "attcnd", "atternpt", "atteud", "au", "aud", "Aud", "augle"]
        s[25] = ["augry", "auimal", "Auother", "auswer", "autbor", "autlior", "autuinn"]
        s[26] = ["autumu", "auturnn", "auuoy", "auut", "auuual", "Auv", "Auy", "auy"]
        s[27] = ["auyhow", "auyoue", "auyway", "avenne", "aveuue", "awakc", "awarc"]
        s[28] = ["awav", "babit", "babv", "bair", "bakc", "balf", "bandle", "bappen"]
        s[29] = ["bappy", "barc", "barden", "bardly", "Barly", "barm", "barrcl", "bas"]
        s[30] = ["basc", "basiu", "baskct", "basm", "basten", "batb", "batbe", "bathc"]
        s[31] = ["batli", "batlie", "batred", "battlc", "bauk", "baok", "bav", "bave"]
        s[32] = ["baving", "Bc", "bc", "bcam", "bcan", "bcar", "bcard", "bcast", "bcat"]
        s[33] = ["bcauty", "Bccausc", "bccomc", "bcd", "bcforc", "Bcforc", "Bcfore"]
        s[34] = ["Bcgin", "bcgin", "Bcgiu", "bchavc", "bchind", "bcing", "bclicf"]
        s[35] = ["bcll", "bclong", "bclow", "bclt", "bcnd", "bcrry", "bcsidc", "bcst"]
        s[36] = ["bcttcr", "Bctwccn", "bcyond", "beain", "beal", "bealtb", "beanty"]
        s[37] = ["beap", "bearn", "beart", "beautv", "beaven", "beavy", "bebave"]
        s[38] = ["bebind", "Becanse", "becoine", "becond", "becorne", "bedroorn"]
        s[39] = ["Beforc", "Begiu", "begiu", "Begm", "begm", "behef", "behiud", "behmd"]
        s[40] = ["beigbt", "beiug", "beliave", "beliind", "bello", "beloug", "belp"]
        s[41] = ["belped", "bemg", "bence", "ber", "bere", "berrv", "Betweeu", "beud"]
        s[42] = ["bevond", "beyoud", "bhnd", "bigb", "bigbly", "bim", "bire", "birtb"]
        s[43] = ["birtli", "bis", "bitc", "bittcr", "biud", "bladc", "blaine", "blamc"]
        s[44] = ["blarne", "blccd", "blcss", "bliud", "blmd", "blne", "bloodv", "bluc"]
        s[45] = ["bmd", "bncket", "bndget", "bnild", "bnilt", "bnnch", "bnndle", "Bnow"]
        s[46] = ["bnrn", "bnrst", "bnry", "bns", "bnsh", "bnsy", "bnt", "Bnt", "bntter"]
        s[47] = ["bntton", "bny", "bodv", "bole", "bollow", "boly", "bome", "bomes"]
        s[48] = ["bonest", "bonnd", "bonor", "bope", "bordcr", "borse", "bost", "bot"]
        s[49] = ["botb", "Botb", "botel", "Botli", "botli", "bottlc", "bottoin"]
        s[50] = ["bottorn", "boue", "bour", "bouse", "boused", "bouses", "bouud", "bov"]
        s[51] = ["bowever", "braiu", "brancb", "brancli", "brauch", "bravc", "brcad"]
        s[52] = ["brcak", "brcath", "breatb", "breatli", "bribc", "bricf", "bridgc"]
        s[53] = ["brigbt", "briglit", "brihe", "briug", "brmg", "brnsh", "browu"]
        s[54] = ["brusb", "brusli", "buckct", "buge", "buncb", "buncli", "bundlc"]
        s[55] = ["bunger", "burry", "burt", "buru", "burv", "busb", "busiiicss"]
        s[56] = ["busli", "busv", "buttcr", "buttou", "buuch", "buudle", "buv", "bv"]
        s[57] = ["Bv", "Bven", "cach", "cagc", "cagcr", "cailing", "cainp", "cakc"]
        s[58] = ["calin", "calrn", "canse", "camo", "carc", "carccr", "carly", "carn"]
        s[59] = ["carnp", "carnpaign", "carrv", "carth", "casb", "casc", "casc"]
        s[60] = ["casily", "casli", "castlc", "casy", "catcb", "catcli", "cattlc"]
        s[61] = ["cau", "Cau", "caual", "causc", "cavc", "cbain", "cbair", "cbalk"]
        s[62] = ["cbance", "Cbange", "cbange", "cbarm", "cbeap", "cbeat", "cbeck"]
        s[63] = ["cbeer", "cbeese", "cbest", "cbief", "cbild", "cboice", "cboose"]
        s[64] = ["cburcb", "ccnt", "ccntcr", "ccntrc", "cdgc", "cerernony", "ceut"]
        s[65] = ["ceuter", "ceutre", "cf", "cffcct", "cffort", "chairrnan", "chaiu"]
        s[66] = ["chancc", "changc", "Changc", "CHAPTEE", "chargc", "charrn", "chauce"]
        s[67] = ["chauge", "Chauge", "chcap", "chcck", "chcst", "chent", "chff"]
        s[68] = ["chicf", "chirnney", "chmb", "chnrch", "choicc", "choosc", "circlc"]
        s[69] = ["circurnstance", "cithcr", "cither", "citv", "claas", "claiin"]
        s[70] = ["clairn", "clav", "clcan", "clcar", "clcct", "clcvcr", "cldcr"]
        s[71] = ["cleau", "cliain", "cliair", "clialk", "cliance", "Cliange", "cliange"]
        s[72] = ["cliarge", "cliarm", "clieap", "clieat", "clieck", "clieer", "cliest"]
        s[73] = ["clieut", "cliief", "cliild", "cliinb", "climh", "clioice", "clioose"]
        s[74] = ["clirnb", "clnb", "clond", "Closc", "closc", "clotb", "clotbe"]
        s[75] = ["clothc", "clotli", "clotlie", "clsc", "cluh", "cmcrgc", "cmpirc"]
        s[76] = ["cmploy", "cmpty", "cnablc", "cncmy", "cnd", "cnjoy", "cnough", "cnp"]
        s[77] = ["cnre", "cnrl", "cnrse", "cnrve", "cnstom", "cnsurc", "cnt", "cntcr"]
        s[78] = ["cntirc", "cntry", "cnvy", "coarsc", "coffcc", "coinb", "Coine"]
        s[79] = ["coine", "coiu", "colonr", "colonv", "colouy", "comh", "commou"]
        s[80] = ["concem", "concemed", "confirrn", "congh", "conld", "Conld", "connt"]
        s[81] = ["connty", "conple", "conrse", "conrt", "Considcr", "consin", "coppcr"]
        s[82] = ["copv", "cornb", "cornbination", "cornbine", "corncr", "corne"]
        s[83] = ["Corne", "cornfort", "corning", "cornpanion", "cornpanionship"]
        s[84] = ["cornpany", "cornpare", "cornparison", "cornpete", "cornpetitor"]
        s[85] = ["cornplain", "cornplaint", "cornplete", "cornpletely", "cornpletion"]
        s[86] = ["cornplex", "cornplicate", "cornplication", "cornponent", "cornpose"]
        s[87] = ["cornposition", "coru", "coruer", "cottou", "cou", "cougb", "cougli"]
        s[88] = ["couldnt", "countv", "couplc", "coursc", "Cousider", "cousiu", "couut"]
        s[89] = ["couuty", "covcr", "cqual", "crasb", "crasli", "crcam", "crcatc"]
        s[90] = ["creain", "crearn", "criine", "crimc", "crirne", "crirninal"]
        s[91] = ["criticisrn", "crnel", "crnsh", "crowu", "crror", "crucl", "crusb"]
        s[92] = ["crusli", "crv", "cscapc", "cstatc", "curc", "cursc", "curvc"]
        s[93] = ["custoin", "custorn", "custornary", "custorner", "cvcn", "cvcnt"]
        s[94] = ["cvcr", "cvcry", "cver", "cvil", "cxact", "cxccpt", "cxccss", "cxcitc"]
        s[95] = ["cxcusc", "cxist", "cxpcct", "cxpcrt", "cxtcnd", "cxtcnt", "cxtra"]
        s[96] = ["cyc", "cycd", "dailv", "dainage", "dainp", "damagc", "dancc"]
        s[97] = ["dangcr", "darc", "darkcn", "darkeu", "darnage", "darnp", "datc"]
        s[98] = ["dauce", "dauger", "dav", "davlight", "dc", "dcad", "dcal", "dcar"]
        s[99] = ["dcath"]
        for i in range(len(s)):
            scannos_list = s[i]
            for j in range(len(scannos_list)):
                scannos_misspelled.append(scannos_list[j])
        s = {}
        s[0] = ["dcbatc", "dcbt", "dccadc", "dccay", "dcccit", "dccd", "dccidc", "dccp"]
        s[1] = ["dccpcn", "dccr", "dcfcat", "dcfcnd", "dcfinc", "dcgrcc", "dclay"]
        s[2] = ["dclivcred", "dcmand", "dcny", "dcpcnd", "dcpth", "dcputy", "dcrivc"]
        s[3] = ["dcscrt", "dcsign", "dcsirc", "dcsk", "dctail", "dcvicc", "dcvil"]
        s[4] = ["deatb", "deatli", "decav", "deepeu", "defeud", "defiue", "defme"]
        s[5] = ["dehate", "dehates", "deht", "deinand", "delav", "demaud", "denv"]
        s[6] = ["departrnent", "depeud", "depnty", "deptb", "deptli", "deputv"]
        s[7] = ["dernand", "dernocratic", "dernonstrate", "desigu", "deterrnine"]
        s[8] = ["deuy", "developrnent", "diarnond", "dic", "didnt", "dinc", "dinncr"]
        s[9] = ["dircct", "disb", "discornfort", "disli", "disrniss", "ditcb", "ditcli"]
        s[10] = ["diue", "diuuer", "divc", "dividc", "dme", "dmner", "dnck", "dne"]
        s[11] = ["dnll", "dnring", "Dnring", "dnst", "dnty", "docurnent", "doesnt"]
        s[12] = ["donble", "donbt", "donkev", "dont", "dornestic", "doublc", "douhle"]
        s[13] = ["douht", "dowu", "Dowu", "dozcn", "dozeu", "drawcr", "drcam", "drcss"]
        s[14] = ["dreain", "drearn", "driuk", "drivc", "drivcr", "drmk", "drng", "drnm"]
        s[15] = ["drowu", "druin", "drurn", "drv", "duc", "duriug", "Duriug", "durmg"]
        s[16] = ["Durmg", "dutv", "eacb", "Eacb", "Eack", "Eacli", "eacli", "eam"]
        s[17] = ["eamest", "earlv", "Earlv", "eartb", "eartli", "earu", "easilv"]
        s[18] = ["eastem", "easv", "econornic", "econorny", "Ee", "Eecause", "Eeep"]
        s[19] = ["Eefore", "Eegin", "Eetween", "Eill", "einerge", "einpire", "einploy"]
        s[20] = ["einpty", "eitber", "eitlier", "elernent", "emplov", "emptv", "enahle"]
        s[21] = ["eneiny", "enemv", "energv", "enerny", "enjov", "enongh", "enougb"]
        s[22] = ["enougli", "ensnre", "entrv", "environrnent", "envv", "Eobert", "Eome"]
        s[23] = ["Eoth", "eqnal", "equiprnent", "ernerge", "ernphasis", "ernpire"]
        s[24] = ["ernploy", "ernpty", "establishrnent", "estirnate", "euable", "eud"]
        s[25] = ["euemy", "euergy", "eujoy", "euough", "eusure", "Eut", "euter"]
        s[26] = ["eutire", "eutry", "euvy", "Evcn", "everv", "Eveu", "eveu", "eveut"]
        s[27] = ["exarnination", "exarnine", "exarnple", "excnse", "experirnent"]
        s[28] = ["extemal", "exteud", "exteut", "extrerne", "extrernely", "Ey", "facc"]
        s[29] = ["fadc", "faine", "fainily", "fainous", "fairlv", "faitb", "faitli"]
        s[30] = ["faiut", "famc", "familv", "famons", "famt", "fancv", "fanlt", "farin"]
        s[31] = ["fariner", "farmcr", "farne", "farniliar", "farnily", "farnous"]
        s[32] = ["farrn", "farrner", "fastcn", "fasteu", "fatber", "fatc", "fathcr"]
        s[33] = ["fatlier", "fattcn", "fatteu", "fau", "faucy", "favonr", "fcar"]
        s[34] = ["fcast", "fcc", "fccd", "fccl", "fcllow", "fcncc", "fcvcr", "fcw"]
        s[35] = ["Fcw", "feinale", "fernale", "feuce", "fhght", "ficld", "ficrcc"]
        s[36] = ["figbt", "figlit", "fignre", "figurc", "filc", "filid", "filin"]
        s[37] = ["finc", "fingcr", "finisb", "finisli", "firc", "firin", "firrn"]
        s[38] = ["fisb", "fisli", "fiual", "fiud", "fiue", "fiuger", "fiuish", "flaine"]
        s[39] = ["flamc", "flarne", "flasb", "flasli", "flesb", "flesli", "fligbt"]
        s[40] = ["fliglit", "flonr", "flv", "fmal", "fmd", "fme", "fmger", "fmish"]
        s[41] = ["fnel", "fnll", "fnlly", "fnn", "fnnd", "fnnny", "fnr", "fntnre"]
        s[42] = ["focns", "forcc", "forcst", "forgct", "forhid", "forin", "forinal"]
        s[43] = ["foriner", "formcr", "forrn", "forrnal", "forrner", "fortb", "fortli"]
        s[44] = ["foud", "fraine", "framc", "frarne", "frarnework", "frcc", "frcczc"]
        s[45] = ["frcsh", "freedorn", "freind", "fresb", "fresli", "fricnd", "frieud"]
        s[46] = ["frigbt", "friglit", "frnit", "Froin", "froin", "fromt", "Frorn"]
        s[47] = ["frorn", "frout", "frow", "frv", "fucl", "fullv", "fumish", "fumiture"]
        s[48] = ["funnv", "furtber", "futurc", "fuu", "fuud", "fuuuy", "gaicty"]
        s[49] = ["gaietv", "gaine", "gaiu", "gallou", "gamc", "garagc", "gardcn"]
        s[50] = ["gardeu", "garne", "gatber", "gatc", "gathcr", "gatlier", "gav"]
        s[51] = ["gcntlc", "gct", "gentlernan", "geutle", "givc", "Givc", "glorv"]
        s[52] = ["gnard", "gness", "gnest", "gnide", "gnilt", "gnn", "goldcn", "goldeu"]
        s[53] = ["govcrn", "govem", "govemment", "govemor", "governrnent", "goveru"]
        s[54] = ["gracc", "graiu", "graud", "graut", "grav", "gravc", "grcasc", "grcat"]
        s[55] = ["Grcat", "grccd", "grccn", "grcct", "grcy", "greeu", "grev", "griud"]
        s[56] = ["grmd", "gronnd", "gronp", "grouud", "growtb", "growtli", "gth"]
        s[57] = ["gucss", "gucst", "guidc", "guu", "hahit", "hake", "han", "handlc"]
        s[58] = ["happcn", "happeu", "happv", "har", "hardcn", "hardeu", "hardlv"]
        s[59] = ["harhor", "harin", "harrel", "harrn", "hase", "hasic", "hasin"]
        s[60] = ["hasis", "hasket", "hastc", "hastcn", "hasteu", "hatc", "hathe"]
        s[61] = ["hatrcd", "hattle", "haud", "haudle", "haug", "hav", "havc", "Havc"]
        s[62] = ["Hc", "hc", "hcad", "hcal", "hcalth", "hcap", "hcar", "hcart", "hcat"]
        s[63] = ["hcavcn", "hcavy", "hcight", "hcll", "hcllo", "hclp", "hcncc", "hcr"]
        s[64] = ["hcrc", "hd", "heak", "heam", "hean", "heast", "heauty", "heaveu"]
        s[65] = ["heavv", "hecause", "hecome", "hed", "heen", "hefore", "heg", "hegan"]
        s[66] = ["hegin", "hehave", "hehind", "heid", "heing", "helief", "helieve"]
        s[67] = ["helong", "helow", "helt", "hend", "henefit", "herry", "heside"]
        s[68] = ["hest", "hetter", "hetween", "heuce", "heyond", "hfe", "hft", "hght"]
        s[69] = ["hia", "hidc", "hie", "hig", "higber", "highlv", "hiii", "hiin"]
        s[70] = ["hiln", "hin", "hindcr", "hirc", "hird", "hirn", "hirnself", "hirth"]
        s[71] = ["hite", "hiuder", "hke", "hkely", "hlack", "hlade", "hlame", "hleed"]
        s[72] = ["hless", "hlind", "hlock", "hlood", "hloody", "hlow", "hlue", "hmb"]
        s[73] = ["hmder", "hmit", "hne", "hnge", "hnk", "hnman", "hnmble", "hnnger"]
        s[74] = ["hnnt", "hnrry", "hnrt", "hnt", "hoast", "hoat", "hody", "hoil"]
        s[75] = ["hoine", "holc", "holv", "homc", "honcst", "honr", "honse", "hopc"]
        s[76] = ["horder", "horne", "hornecorning", "hornernade", "hornework", "horrow"]
        s[77] = ["horsc", "hotcl", "hoth", "hottle", "hottom", "houest", "houor"]
        s[78] = ["housc", "Howcvcr", "Howcver", "Howevcr", "hox", "hp", "hquid"]
        s[79] = ["hrain", "hranch", "hrass", "hrave", "hread", "hreak", "hreath"]
        s[80] = ["hrick", "hridge", "hrief", "hright", "hring", "hroad", "hrown"]
        s[81] = ["hrush", "hst", "hsten", "httle", "hucket", "hudget", "hugc", "huild"]
        s[82] = ["huinan", "huinble", "humblc", "humhle", "hundle", "hungcr", "hurn"]
        s[83] = ["hurnan", "hurnble", "hurrv", "hurst", "hury", "hus", "husy", "hutter"]
        s[84] = ["hutton", "huuger", "huut", "huy", "hve", "hving", "hy", "i3th"]
        s[85] = ["i4th", "i5th", "i6th", "i7th", "i8th", "i9th", "ia", "icc", "idca"]
        s[86] = ["idcal", "idlc", "ignorc", "iguore", "iie", "iii", "iiie", "iinage"]
        s[87] = ["iinpact", "iinply", "iinpose", "iiow", "Ile", "Ilim", "I-low"]
        s[88] = ["imagc", "implv", "imposc", "inad", "inadden", "inail", "inain"]
        s[89] = ["inainly", "inajor", "inake", "inanage", "inanner", "inany", "inap"]
        s[90] = ["inarch", "inark", "inarket", "inarry", "inass", "inaster", "inat"]
        s[91] = ["inatch", "inatter", "inay", "inaybe", "incb", "incli", "incoine"]
        s[92] = ["incomc", "incorne", "indccd", "ine", "ineal", "inean", "ineans"]
        s[93] = ["ineat", "ineet", "inelt", "inend", "inental", "inercy", "inere"]
        s[94] = ["inerely", "inerry", "inetal", "inethod", "inforin", "inforrn"]
        s[95] = ["inforrnation", "iniddle", "inight", "inild", "inile", "inilk"]
        s[96] = ["inill", "inind", "inine", "ininute", "inisery", "iniss", "inix"]
        s[97] = ["injnry", "injurv", "inodel", "inodern", "inodest", "inodule"]
        s[98] = ["inoney", "inonth", "inoon", "inoral", "inore", "inost", "inother"]
        s[99] = ["inotion"]
        for i in range(len(s)):
            scannos_list = s[i]
            for j in range(len(scannos_list)):
                scannos_misspelled.append(scannos_list[j])
        s = {}
        s[0] = ["inotor", "inouse", "inouth", "inove", "insidc", "insnlt", "insnre"]
        s[1] = ["instrurnent", "insurc", "intcnd", "intemal", "intemational", "inuch"]
        s[2] = ["inud", "inurder", "inusic", "inust", "investrnent", "invitc", "iny"]
        s[3] = ["inyself", "irnage", "irnaginary", "irnaginative", "irnagine"]
        s[4] = ["irnitate", "irnitation", "irnpact", "irnplication", "irnply"]
        s[5] = ["irnportance", "irnportant", "irnpose", "irnpossible", "irnpression"]
        s[6] = ["irnprove", "irnprovernent", "irou", "islaud", "issne", "issuc", "itcm"]
        s[7] = ["itein", "itern", "itsclf", "iu", "iu", "Iu", "iuch", "iucome"]
        s[8] = ["iudeed", "iudex", "iudoor", "iuform", "iujury", "iuk", "iuside"]
        s[9] = ["iusist", "iusult", "iusure", "iuteud", "Iuto", "iuto", "iuu", "iuveut"]
        s[10] = ["iuvite", "iuward", "jndge", "jnmp", "Jnst", "jnst", "jobn", "joh"]
        s[11] = ["joiu", "joiut", "jom", "jomt", "joumey", "jov", "judgc", "juinp"]
        s[12] = ["jurnp", "Kack", "kccp", "Kccp", "Kcep", "kcy", "Ke", "Kecause"]
        s[13] = ["Kecp", "Kefore", "Ketween", "kev", "kingdorn", "kiud", "kiug", "kmd"]
        s[14] = ["kmg", "kncc", "knccl", "knifc", "Kome", "kuee", "kueel", "kuife"]
        s[15] = ["kuock", "kuot", "Kuow", "kuow", "Kut", "Kven", "l0th", "l1ad", "l1th"]
        s[16] = ["l2th", "l3th", "l4th", "l5th", "l6th", "l7th", "l8th", "l9th"]
        s[17] = ["labonr", "ladv", "lahour", "lainp", "lakc", "langh", "lannch"]
        s[18] = ["largc", "larnp", "latc", "latcly", "latcr", "latelv", "lattcr"]
        s[19] = ["laugb", "launcb", "lauuch", "lav", "lawver", "lawycr", "lazv", "lcad"]
        s[20] = ["lcadcr", "lcaf", "lcaguc", "lcan", "lcarn", "lcast", "lcavc", "lcft"]
        s[21] = ["lcg", "lcgal", "lcnd", "lcngth", "lcss", "lcsscn", "lcsson", "lcttcr"]
        s[22] = ["lcvcl", "leagne", "leam", "learu", "leau", "lengtb", "lengtli"]
        s[23] = ["lesseu", "lessou", "leud", "leugth", "lgth", "liabit", "liair"]
        s[24] = ["lialf", "liall", "liand", "liandle", "liang", "liappen", "liappy"]
        s[25] = ["liarbor", "liard", "liarden", "liardly", "liarm", "lias", "liaste"]
        s[26] = ["liasten", "liat", "liate", "liatred", "liave", "lic", "licll"]
        s[27] = ["liead", "lieal", "lieap", "liear", "lieart", "lieat", "lieaven"]
        s[28] = ["lieavy", "liell", "liello", "lielp", "lience", "liere", "lifc"]
        s[29] = ["ligbt", "liglit", "liide", "liigli", "liill", "liim", "liinb"]
        s[30] = ["liinder", "liinit", "liire", "liis", "liit", "Likc", "likc", "likcly"]
        s[31] = ["likelv", "limh", "linc", "liold", "liole", "liollow", "lioly"]
        s[32] = ["liome", "lionest", "lionor", "liook", "liope", "liorse", "liost"]
        s[33] = ["liot", "liotel", "liour", "liouse", "liow", "liqnid", "lirnb"]
        s[34] = ["lirnit", "lirnited", "listcn", "listeu", "littie", "Littlc", "littlc"]
        s[35] = ["liue", "liuge", "liuk", "liumble", "liunger", "liunt", "liurry"]
        s[36] = ["liurt", "liut", "livc", "liviug", "livmg", "lIy", "llth", "lme"]
        s[37] = ["lmk", "lnck", "lnmp", "lnnch", "lnng", "loau", "localitv", "lodgc"]
        s[38] = ["loncly", "lond", "lonelv", "loosc", "looscn", "looseu", "losc"]
        s[39] = ["louely", "loug", "Loug", "loval", "lovc", "lovcly", "lovelv", "lst"]
        s[40] = ["ltim", "luinp", "luncb", "luncli", "lurnp", "luuch", "luug"]
        s[41] = ["maiiaged", "mainlv", "maiu", "maiuly", "makc", "Makc", "malc"]
        s[42] = ["mamly", "managc", "managernent", "manncr", "manv", "Manv", "marcb"]
        s[43] = ["marcli", "markct", "marrv", "mastcr", "matcb", "matcli", "mattcr"]
        s[44] = ["mau", "mauage", "mauuer", "mauy", "Mauy", "mav", "Mav", "mavbe"]
        s[45] = ["maybc", "mayhe", "mb  ", "mbber", "mc", "mcal", "mcan", "mcans"]
        s[46] = ["mcat", "mcct", "mch", "mclt", "mcmbcr", "mcmory", "mcnd", "mcntal"]
        s[47] = ["mcome", "mcrc", "mcrcly", "mcrcy", "mcrry", "mctal", "mcthod", "mde"]
        s[48] = ["mdeed", "mdex", "mdoor", "meantirne", "meanwbile", "meau", "meaus"]
        s[49] = ["memher", "memhers", "memorv", "mercv", "merelv", "mernber"]
        s[50] = ["mernbership", "mernory", "merrv", "metbod", "metliod", "meud"]
        s[51] = ["meutal", "mform", "middlc", "Migbt", "migbt", "miglit", "Miglit"]
        s[52] = ["milc", "minc", "minnte", "minutc", "miscry", "miserv", "miud", "miue"]
        s[53] = ["miuute", "mjury", "mk", "mle", "mmd", "mme", "mmute", "mn", "mn"]
        s[54] = ["Mncb", "mnch", "Mnch", "mnd", "mnrder", "mnsenm", "mnsic", "mnst"]
        s[55] = ["modcl", "modcrn", "modcst", "modem", "moderu", "modnle", "modulc"]
        s[56] = ["momcnt", "momeut", "moming", "moncy", "monev", "monkev", "monse"]
        s[57] = ["montb", "montli", "moou", "Morc", "morc", "mornent", "mornentary"]
        s[58] = ["motber", "mothcr", "motiou", "motlier", "mouey", "mousc", "moutb"]
        s[59] = ["moutli", "Movc", "movc", "movernent", "mral", "msect", "msh", "mside"]
        s[60] = ["msist", "mst", "msult", "msure", "mtend", "mto", "Mucb", "mucb"]
        s[61] = ["Mucli", "mucli", "murdcr", "museurn", "mv", "mvite", "mvself"]
        s[62] = ["mward", "mysclf", "naine", "namc", "narne", "nativc", "natnre"]
        s[63] = ["naturc", "nc", "ncar", "ncarly", "ncat", "nccd", "ncck", "ncphcw"]
        s[64] = ["ncst", "nct", "Ncvcr", "ncvcr", "Ncver", "ncw", "ncws", "ncxt"]
        s[65] = ["nearlv", "neitber", "ner", "nepbew", "Nevcr", "ngly", "nian", "nicc"]
        s[66] = ["niccc", "nigbt", "niglit", "nlyself", "nnable", "nncle", "nnder"]
        s[67] = ["nnion", "nnit", "nnite", "nnited", "nnity", "nnless", "nnmber"]
        s[68] = ["nnrse", "nnt", "nntil", "noblc", "nobodv", "nohle", "nohody", "noisc"]
        s[69] = ["nonc", "norinal", "norrnal", "norrnally", "nortb", "nortbern"]
        s[70] = ["northem", "nortli", "nosc", "notbing", "notc", "noticc", "np", "npon"]
        s[71] = ["npper", "npset", "nrge", "nrgent", "ns", "nse", "nsed", "nsefnl"]
        s[72] = ["nser", "nsnal", "Nte", "nuinber", "numbcr", "numher", "numhers"]
        s[73] = ["nurnber", "nurnerous", "nursc", "oan", "obcy", "obev", "objcct"]
        s[74] = ["obtaiu", "obtam", "occan", "occnr", "oceau", "offcnd", "offcr"]
        s[75] = ["offeud", "officc", "oftcn", "ofteu", "ohey", "ohject", "ohtain"]
        s[76] = ["oinit", "okav", "om", "omament", "Onc", "onc", "Oncc", "oncc"]
        s[77] = ["onght", "oniy", "Onlv", "onlv", "onnce", "onr", "ont", "Ont"]
        s[78] = ["ontpnt", "opcn", "Opcn", "Opeu", "opeu", "opposc", "optiou", "ordcr"]
        s[79] = ["orgau", "origiu", "origm", "ornarnent", "ornission", "ornit", "Otber"]
        s[80] = ["otber", "otbers", "othcr", "Othcr", "otlier", "Otlier", "Oucc"]
        s[81] = ["Ouce", "ouce", "Oue", "oue", "ougbt", "ouglit", "Oulv", "ouly"]
        s[82] = ["Ouly", "ouncc", "outcorne", "outo", "ouuce", "ovcr", "Ovcr"]
        s[83] = ["overcorne", "owc", "owncr", "owu", "owuer", "pagc", "paiu", "paiut"]
        s[84] = ["palc", "pamt", "pancl", "panse", "papcr", "parccl", "parcnt"]
        s[85] = ["pardou", "pareut", "parliarnent", "partlv", "partv", "pastc"]
        s[86] = ["pastrv", "patb", "patli", "pattem", "pau", "pauel", "pausc", "pav"]
        s[87] = ["payrnent", "pbase", "pbone", "pcacc", "pcarl", "pcn", "pcncil"]
        s[88] = ["pcnny", "Pcoplc", "pcoplc", "Pcople", "pcr", "pcriod", "pcrmit"]
        s[89] = ["pcrson", "pct", "pennv", "Peoplc", "perbaps", "perforrn"]
        s[90] = ["perforrnance", "perinit", "perrnanent", "perrnission", "perrnit"]
        s[91] = ["persou", "peu", "peucil", "peuuy", "phasc", "phonc", "pia", "piccc"]
        s[92] = ["pigcon", "pilc", "pincb", "pincli", "pipc", "pitv", "piu", "piuch"]
        s[93] = ["piuk", "piut", "placc", "plaiu", "plam", "platc", "plau", "plaut"]
        s[94] = ["plav", "plaver", "playcr", "plcasc", "plcnty", "plentv", "pleuty"]
        s[95] = ["pliase", "plnral", "plns", "pmch", "pmk", "pmt", "pnb", "pnblic"]
        s[96] = ["pnll", "pnmp", "pnnish", "pnpil", "pnre", "pnrple", "pnsh", "pnt"]
        s[97] = ["Pnt", "pnzzle", "pockct", "pocm", "poct", "poein", "poern", "pohte"]
        s[98] = ["poisou", "poiut", "policc", "policv", "polisb", "politc", "pomt"]
        s[99] = ["ponnd"]
        for i in range(len(s)):
            scannos_list = s[i]
            for j in range(len(scannos_list)):
                scannos_misspelled.append(scannos_list[j])
        s = {}
        s[0] = ["ponr", "pouud", "powcr", "powdcr", "praisc", "prav", "prcach"]
        s[1] = ["prcfcr", "prcss", "prctty", "preacb", "preacli", "prettv", "pricc"]
        s[2] = ["pricst", "pridc", "priine", "primc", "prirnary", "prirne", "prisou"]
        s[3] = ["priut", "prizc", "prmt", "problern", "prohlem", "prohlems", "proinpt"]
        s[4] = ["prond", "propcr", "prornise", "prornised", "prornote", "prornpt"]
        s[5] = ["provc", "pubhc", "puh", "puhlic", "puinp", "punisb", "punisli", "purc"]
        s[6] = ["purnp", "purplc", "pusb", "pusli", "puuish", "qnart", "qneen", "qnick"]
        s[7] = ["qniet", "qnite", "qttict", "Quc", "quc", "quccn", "queeu", "quict"]
        s[8] = ["quitc", "racc", "rahhit", "raisc", "raiu", "rangc", "rarc", "Rarly"]
        s[9] = ["ratber", "ratc", "rathcr", "ratlier", "rauge", "rauk", "rav", "rcach"]
        s[10] = ["rcad", "rcadcr", "rcady", "rcal", "rcally", "rcason", "rccall"]
        s[11] = ["rcccnt", "rccord", "rcd", "rcddcn", "rcducc", "rcfcr", "rcform"]
        s[12] = ["rcfusc", "rcgard", "rcgion", "rcgrct", "rcjcct", "rclatc", "rclicf"]
        s[13] = ["rcly", "rcmain", "rcmark", "rcmcdy", "rcmind", "rcmovc", "rcnt"]
        s[14] = ["rcpair", "rcpcat", "rcply", "rcport", "rcscuc", "rcsign", "rcsist"]
        s[15] = ["rcst", "rcsult", "rctain", "rctirc", "rcturn", "rcvcal", "rcvicw"]
        s[16] = ["rcward", "reacb", "reacli", "readv", "reallv", "reasou", "Recause"]
        s[17] = ["receut", "reddeu", "rednce", "Reep", "refnse", "Refore", "reforin"]
        s[18] = ["reforrn", "regiou", "rehef", "reinain", "reinark", "reinedy"]
        s[19] = ["reinind", "reinove", "relv", "remaiu", "remam", "remcrnbered"]
        s[20] = ["remedv", "remiud", "remmd", "renlincled", "replv", "requirernent"]
        s[21] = ["rernain", "rernark", "rernedy", "rernernber", "rernind", "rernove"]
        s[22] = ["rescne", "resigu", "resnlt", "retaiu", "retam", "retnrn", "retum"]
        s[23] = ["returu", "Retween", "reut", "ribbou", "ricb", "ricc", "ricli", "ridc"]
        s[24] = ["Rigbt", "rigbt", "riglit", "Riglit", "rihhon", "ripc", "ripcn"]
        s[25] = ["ripeu", "risc", "riug", "rivcr", "rmg", "rnachine", "rnachinery"]
        s[26] = ["rnad", "rnadden", "rnagazine", "rnail", "rnain", "rnainly"]
        s[27] = ["rnaintain", "rnajor", "rnajority", "rnake", "rnale", "rnan"]
        s[28] = ["rnanage", "rnanaged", "rnanagement", "rnanager", "rnankind"]
        s[29] = ["rnanner", "rnany", "rnap", "rnarch", "rnark", "rnarket", "rnarriage"]
        s[30] = ["rnarried", "rnarry", "rnass", "rnaster", "rnat", "rnatch"]
        s[31] = ["rnaterial", "rnatter", "rnay", "rnaybe", "rnb", "rnbber", "rnde"]
        s[32] = ["rne", "rneal", "rnean", "rneaning", "rneans", "rneantirne"]
        s[33] = ["rneanwhile", "rneasure", "rneat", "rnechanisrn", "rnedical"]
        s[34] = ["rnedicine", "rneet", "rneeting", "rnelt", "rnember", "rnembership"]
        s[35] = ["rnemory", "rnend", "rnental", "rnention", "rnerchant", "rnercy"]
        s[36] = ["rnere", "rnerely", "rnerry", "rnessage", "rnessenger", "rnetal"]
        s[37] = ["rnethod", "rng", "rniddle", "rnight", "rnild", "rnile", "rnilitary"]
        s[38] = ["rnilk", "rnill", "rnin", "rnind", "rnine", "rnineral", "rninister"]
        s[39] = ["rninistry", "rninute", "rninutes", "rniserable", "rnisery", "rniss"]
        s[40] = ["rnistake", "rnix", "rnixture", "rnle", "rnn", "rnodel", "rnoderate"]
        s[41] = ["rnoderation", "rnodern", "rnodest", "rnodesty", "rnodule", "rnoney"]
        s[42] = ["rnonkey", "rnonth", "rnoon", "rnoonlight", "rnoral", "rnore"]
        s[43] = ["rnoreover", "rnornent", "rnornentary", "rnorning", "rnost", "rnother"]
        s[44] = ["rnotherhood", "rnotherly", "rnotion", "rnountain", "rnouse", "rnouth"]
        s[45] = ["rnove", "rnovement", "Rnow", "rnral", "rnsh", "rnst", "rnuch", "rnud"]
        s[46] = ["rnultiply", "rnurder", "rnuseurn", "rnusic", "rnusician", "rnust"]
        s[47] = ["rny", "rnyself", "rnystery", "roh", "rolc", "rongh", "ronnd", "ronte"]
        s[48] = ["rooin", "roorn", "ropc", "rottcn", "rotteu", "rougb", "rougli"]
        s[49] = ["routc", "rouud", "roval", "rubbcr", "rudc", "ruh", "ruhher", "ruiu"]
        s[50] = ["rulc", "rusb", "rusli", "ruu", "Rven", "Ry", "sacrcd", "saddcn"]
        s[51] = ["saddeu", "saddlc", "safc", "safcty", "safetv", "saine", "sainple"]
        s[52] = ["sakc", "salarv", "salc", "salesrnan", "samc", "samplc", "sance"]
        s[53] = ["sancer", "sarne", "sarnple", "saucc", "sauccr", "saud", "sav", "savc"]
        s[54] = ["sbade", "sbadow", "sbake", "sball", "sbame", "sbape", "sbare"]
        s[55] = ["sbarp", "sbave", "Sbc", "Sbe", "sbe", "sbeep", "sbeet", "sbelf"]
        s[56] = ["sbell", "sbield", "sbine", "sbip", "sbirt", "sbock", "sboe", "Sbonld"]
        s[57] = ["sboot", "sbop", "sbore", "sbort", "sbot", "Sbould", "sbould", "sbout"]
        s[58] = ["Sbow", "sbow", "sbower", "sbut", "sca", "scalc", "scarcc", "scarch"]
        s[59] = ["scason", "scbeme", "scbool", "scbools", "scc", "Scc", "sccd", "scck"]
        s[60] = ["sccm", "sccnc", "sccnt", "sccond", "sccrct", "sccurc", "Sce", "sceue"]
        s[61] = ["sceut", "schcmc", "scheine", "scherne", "scizc", "sclcct", "scldom"]
        s[62] = ["sclf", "scliool", "scll", "scnd", "scnior", "scnsc", "scom", "scorc"]
        s[63] = ["scoru", "scrapc", "scrccn", "scrcw", "screeu", "scrics", "scrvc"]
        s[64] = ["sct", "Sct", "scttlc", "scvcrc", "scw", "searcb", "searcli", "seasou"]
        s[65] = ["secnre", "secoud", "seein", "seern", "seldoin", "seldorn"]
        s[66] = ["settlernent", "seud", "seuior", "seuse", "shadc", "shaine", "shakc"]
        s[67] = ["shamc", "shapc", "sharc", "sharne", "shavc", "shc", "Shc", "shcct"]
        s[68] = ["shclf", "shcll", "shde", "shght", "shicld", "shinc", "shiue", "shme"]
        s[69] = ["shnt", "shoc", "shonld", "Shonld", "shont", "shorc", "shouldnt"]
        s[70] = ["showcr", "sidc", "sigbt", "siglit", "sigu", "sigual", "siinple"]
        s[71] = ["siinply", "silcnt", "sileut", "silvcr", "simplc", "simplv", "sinall"]
        s[72] = ["Sinall", "sincc", "Sincc", "sinell", "singlc", "sinile", "sinoke"]
        s[73] = ["sinooth", "sirnilar", "sirnple", "sirnplicity", "sirnply", "sistcr"]
        s[74] = ["sitc", "siuce", "Siuce", "siug", "siugle", "siuk", "sizc", "skiu"]
        s[75] = ["skm", "skv", "slavc", "slccp", "sliade", "sliake", "sliall", "sliame"]
        s[76] = ["sliape", "sliare", "sliarp", "slidc", "Slie", "slie", "slieet"]
        s[77] = ["slielf", "sliell", "sligbt", "sliglit", "sliield", "sliine", "sliip"]
        s[78] = ["sliirt", "slioe", "Slionld", "slioot", "sliop", "sliore", "sliort"]
        s[79] = ["sliot", "Sliould", "sliould", "sliout", "Sliow", "sliow", "sliut"]
        s[80] = ["slopc", "slowlv", "Smce", "smce", "smcll", "smg", "smgle", "smilc"]
        s[81] = ["smk", "smokc", "smootb", "smootli", "snakc", "snch", "Snch", "sndden"]
        s[82] = ["snffer", "sngar", "snit", "snm", "snmmer", "snn", "snpper", "snpply"]
        s[83] = ["snre", "snrely", "snrvey", "softcn", "softeu", "sohd", "Soine"]
        s[84] = ["soine", "solcmn", "soleinn", "solemu", "solernn", "solvc", "somc"]
        s[85] = ["Somc", "somcthing", "sometbing", "sonl", "sonnd", "sonp", "sonr"]
        s[86] = ["sonrce", "sonth", "soou", "sorc", "Sorne", "sorne", "sornebody"]
        s[87] = ["sornehow", "sorneone", "sornething", "sornetirne", "sornetirnes"]
        s[88] = ["sornewhat", "sornewhere", "sorrv", "sou", "soug", "sourcc", "soutb"]
        s[89] = ["southem", "soutli", "souud", "spacc", "spadc", "sparc", "spcak"]
        s[90] = ["spccch", "spccd", "spcll", "spcnd", "speecb", "speecli", "speud"]
        s[91] = ["spht", "spitc", "spiu", "spm", "spoou", "sprcad", "spriug", "sprmg"]
        s[92] = ["sqnare", "squarc", "Srnall", "srnall", "srnell", "srnile", "srnoke"]
        s[93] = ["srnooth", "stagc", "stainp", "staiu", "starnp", "statc", "staternent"]
        s[94] = ["statns", "staud", "Staud", "stav", "stcady", "stcal", "stcam"]
        s[95] = ["stccl", "stccp", "stccr", "stcm", "stcp", "steadv", "steain"]
        s[96] = ["stearn", "stiug", "stmg", "stndio", "stndy", "stnff", "stnpid"]
        s[97] = ["stonc", "storc", "storin", "stornach", "storrn", "storv", "stoue"]
        s[98] = ["stovc", "strcam", "strcct", "streain", "strearn", "strikc", "stripc"]
        s[99] = ["striug"]
        for i in range(len(s)):
            scannos_list = s[i]
            for j in range(len(scannos_list)):
                scannos_misspelled.append(scannos_list[j])
        s = {}
        s[0] = ["strmg", "strokc", "stroug", "studv", "stvle", "stylc", "suake", "sucb"]
        s[1] = ["Sucb", "Sucli", "sucli", "suddcn", "suddeu", "suffcr", "suin"]
        s[2] = ["summcr", "suow", "suppcr", "supplv", "surc", "surcly", "surelv"]
        s[3] = ["surn", "surnrner", "survcy", "survev", "suu", "svstem", "swcar"]
        s[4] = ["swcat", "swccp", "swcct", "swcll", "swiin", "swirn", "switcb"]
        s[5] = ["switcli", "swiug", "swmg", "syrnpathetic", "syrnpathy", "systcm"]
        s[6] = ["systein", "systern", "t11e", "tablc", "tahle", "taine", "Takc", "takc"]
        s[7] = ["tamc", "tapc", "targct", "tarne", "tastc", "tban", "tbank", "tbanks"]
        s[8] = ["tbat", "Tbat", "Tbcre", "Tbe", "tbe", "tbe", "tbeir", "tbem", "tbeme"]
        s[9] = ["tben", "Tben", "tbeory", "Tberc", "Tbere", "tbere", "Tbese", "tbese"]
        s[10] = ["tbey", "Tbey", "tbick", "tbief", "tbin", "tbing", "tbink", "tbirst"]
        s[11] = ["Tbis", "tbis", "tborn", "Tbose", "tbose", "tbougb", "tbread"]
        s[12] = ["tbreat", "tbroat", "Tbrougb", "Tbrough", "tbrow", "tbumb", "tbus"]
        s[13] = ["tca", "tcach", "tcam", "tcar", "tcaring", "tcll", "tcmpcr", "tcmplc"]
        s[14] = ["tcmpt", "tcnd", "tcndcr", "tcnding", "tcnt", "tcrm", "tcrms", "tcst"]
        s[15] = ["tcxt", "teacb", "teacli", "teain", "tearn", "teh", "teinper"]
        s[16] = ["teinple", "teinpt", "terin", "terins", "ternper", "ternperature"]
        s[17] = ["ternple", "ternpt", "terrn", "terrns", "teud", "teuder", "teut"]
        s[18] = ["thau", "thauk", "thauks", "thc", "thcir", "thcm", "thcmc", "thcn"]
        s[19] = ["Thcn", "thcory", "thcrc", "Thcrc", "Thcre", "thcsc", "Thcy", "thcy"]
        s[20] = ["thein", "theine", "theorv", "Therc", "thern", "therne", "thernselves"]
        s[21] = ["Thesc", "theu", "Thev", "thev", "theyll", "thicf", "thiu", "thiug"]
        s[22] = ["thiuk", "thm", "thmg", "thmk", "thnmb", "thns", "thom", "thongh"]
        s[23] = ["thosc", "Thosc", "thougb", "thrcad", "thrcat", "Throngh", "Througb"]
        s[24] = ["thuinb", "thumh", "thurnb", "tickct", "tidc", "tidv", "tigbt"]
        s[25] = ["tiglit", "tiine", "timc", "timne", "tinv", "tirc", "tirne", "titlc"]
        s[26] = ["tiu", "tiuy", "tlian", "tliank", "tlianks", "Tliat", "tliat", "Tlie"]
        s[27] = ["tlie", "tlieir", "tliem", "tlien", "Tlien", "Tliere", "tliere"]
        s[28] = ["tliese", "Tliese", "Tliey", "tliey", "tliick", "tliief", "tliin"]
        s[29] = ["tliing", "tliink", "tliirst", "Tliis", "tliis", "tliose", "Tliose"]
        s[30] = ["tliread", "tlireat", "tlirow", "tlius", "Tm", "tmy", "tnbe", "tnne"]
        s[31] = ["Tnrn", "tnrn", "toc", "todav", "togetber", "tonc", "tonch", "tongh"]
        s[32] = ["tongne", "tonguc", "tonr", "tootb", "Torn", "tornorrow", "tou"]
        s[33] = ["toucb", "toucli", "toue", "tougb", "tougli", "tougue", "tov", "towcl"]
        s[34] = ["towcr", "towu", "toxvard", "tradc", "traiu", "trav", "travcl"]
        s[35] = ["trcat", "trcaty", "trcc", "trcnd", "treatrnent", "treatv", "trernble"]
        s[36] = ["treud", "tribc", "trihe", "trne", "trnnk", "trnst", "trnth", "truc"]
        s[37] = ["trutb", "trutli", "truuk", "trv", "tubc", "tuhe", "tumpike", "tunc"]
        s[38] = ["turu", "Turu", "tuue", "tvpe", "twicc", "typc", "uail", "uame"]
        s[39] = ["uarrow", "uatiou", "uative", "uature", "uear", "uearly", "ueat"]
        s[40] = ["ueck", "ueed", "ueedle", "uephew", "uest", "uet", "uever", "uew"]
        s[41] = ["uews", "uext", "uglv", "uice", "uiece", "uight", "unablc", "unahle"]
        s[42] = ["unc", "unclc", "undcr", "Undcr", "undemeath", "unitc", "unitcd"]
        s[43] = ["unitv", "unlcss", "uoble", "uobody", "uod", "uoise", "uoou", "uor"]
        s[44] = ["uormal", "uorth", "uose", "uot", "uote", "uotice", "uotiou", "uoue"]
        s[45] = ["uow", "upou", "uppcr", "upperrnost", "upsct", "urgc", "urgcnt"]
        s[46] = ["urgeut", "Usc", "usc", "uscd", "uscful", "uscr", "uuable", "uucle"]
        s[47] = ["uuder", "uuiou", "uuit", "uuite", "uuited", "uuity", "uuless"]
        s[48] = ["uumber", "uurse", "uut", "uutil", "vaiu", "vallcy", "vallev", "valne"]
        s[49] = ["valuc", "vam", "vard", "varv", "vcil", "vcrb", "vcrsc", "vcry"]
        s[50] = ["Vcry", "vcsscl", "veah", "vear", "vellow", "verv", "Verv", "ves"]
        s[51] = ["vho", "victiin", "victirn", "vicw", "vield", "virtne", "virtuc"]
        s[52] = ["visiou", "voicc", "volnme", "voluine", "volumc", "volurne", "votc"]
        s[53] = ["vou", "voung", "vour", "vouth", "vovage", "vowcl", "voyagc", "waa"]
        s[54] = ["wagc", "waiking", "waitcr", "wakc", "wam", "wandcr", "warinth"]
        s[55] = ["warmtb", "warmtli", "warrn", "warrnth", "waru", "wasb", "wasli"]
        s[56] = ["wasnt", "wastc", "watcb", "watcli", "watcr", "wauder", "waut", "wav"]
        s[57] = ["wavc", "wbat", "Wbat", "wbeat", "wbeel", "wben", "Wben", "Wbere"]
        s[58] = ["wbere", "Wbeu", "wbich", "wbile", "Wbile", "wbilst", "wbip", "wbite"]
        s[59] = ["wbo", "Wbo", "wbole", "wbom", "wbose", "wby", "Wc", "wc", "wcak"]
        s[60] = ["wcakcn", "wcalth", "wcapon", "wcar", "wcavc", "wccd", "wcck", "wcigh"]
        s[61] = ["wcight", "wcll", "wcst", "wct", "weakeu", "wealtb", "weapou", "weigb"]
        s[62] = ["weigbt", "welcorne", "westem", "whcat", "whccl", "whcn", "Whcn"]
        s[63] = ["Whcrc", "whcrc", "Whcre", "Wherc", "wheu", "Wheu", "whicb", "Whicb"]
        s[64] = ["Whicb", "whicli", "whilc", "Whilc", "whitc", "whitcn", "whiteu"]
        s[65] = ["whoin", "wholc", "whorn", "whosc", "whv", "wickcd", "widc", "widcly"]
        s[66] = ["widcn", "widelv", "wideu", "widtb", "widtli", "wifc", "winc"]
        s[67] = ["winncr", "wintcr", "wipc", "wirc", "wisb", "wisc", "wisdoin"]
        s[68] = ["wisdorn", "wisli", "Witb", "witb", "witbin", "witbout", "withiu"]
        s[69] = ["withm", "witli", "Witli", "witliin", "wiu", "wiud", "wiudow", "wiue"]
        s[70] = ["wiug", "wiuter", "wiuuer", "Wliat", "wliat", "wlien", "Wlien"]
        s[71] = ["Wliere", "wliere", "wliich", "Wliile", "wliile", "wliilst", "wliip"]
        s[72] = ["wliite", "Wlio", "wlio", "wliole", "wliom", "wliose", "wliy", "wmd"]
        s[73] = ["wmdow", "wme", "wmg", "wmner", "wmter", "wo", "woinan", "womau"]
        s[74] = ["wondcr", "wonld", "wonnd", "woodcn", "woodeu", "woolcn", "wooleu"]
        s[75] = ["worin", "workcr", "wornan", "worrn", "worrv", "worsc", "wortb"]
        s[76] = ["wortli", "wouder", "wouid", "wouldnt", "wouud", "wrcck", "writc"]
        s[77] = ["writcr", "wroug", "ycar", "ycllow", "ycs", "yct", "yicld", "yntir"]
        s[78] = ["yonng", "yonr", "yonth", "youtb", "youtli", "youug", "youve", "zcro"]
        s[79] = ["stiil", "aword", "nnd", "KEW", "Sonth", "wa", "ou", "aa", "klnd"]
        s[80] = ["tne", "ths"]
        for i in range(len(s)):
            scannos_list = s[i]
            for j in range(len(scannos_list)):
                scannos_misspelled.append(scannos_list[j])
        s = {}

        # Can add new entries above. Maintain the same code structure with no line longer
        # than 88 characters and no dictionary index greater than 99. Note the 's = {}'
        # line above is superfluous there but is REQUIRED if new dictionary entries are
        # added after loop-code (see above) that appends dictionary entries to the list
        # misspelled_scannos.

        scanno_dictionary = {}

        # Build scanno dictionary. All words made lower case.

        for entry in scannos_misspelled:
            scoword = entry.lower()
            # Deal with duplicates.
            if scoword in scanno_dictionary:
                continue
            scanno_dictionary[scoword] = 0

        return scanno_dictionary

    ##
    # PPTXT Main section
    ##

    # Create the checker dialog to show results
    checker_dialog = CheckerDialog.show_dialog("PPtxt Results", pptxt)
    checker_dialog.reset()

    # Get the whole of the file from the main text widget

    # text = maintext().get_text()
    text = maintext().get_text()
    input = text.splitlines()

    # Get book lines, list of words on line and word frequency.

    book = []
    word_list_map_words = []
    word_list_map_count: Dict[str, int] = {}
    word_list_map_lines: Dict[str, list[int]] = {}
    hyphenated_words_dictionary: Dict[str, int] = {}

    line_number = 1
    for line in input:
        line = line.rstrip("\r\n")

        book.append(line)

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

            # Build dictionary of hyphenated words and their frequency.
            if re.search(r"-", word):
                if word in hyphenated_words_dictionary:
                    hyphenated_words_dictionary[word] += 1
                else:
                    hyphenated_words_dictionary[word] = 1
        line_number += 1

    ###################################################
    # We're done reading the input. Start processing it.
    ###################################################

    # The checks are run in the following order...

    trailing_spaces_check()
    spacing_check()
    repeated_words_check()
    hyphenated_words_check()
    adjacent_spaces_check()
    dash_review()
    scanno_check()
    weird_characters()
    html_check()
    unicode_numeric_character_check()
    # This final one does multiple checks.
    specials_check()

    # Add final divider line to dialog.

    checker_dialog.add_entry(f"{'-' * 80}")
