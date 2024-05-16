"""Miscellaneous tools."""

import logging
from tkinter import messagebox
from typing import Callable, Optional

import regex as re

from guiguts.checkers import CheckerDialog, CheckerEntry
from guiguts.file import the_file
from guiguts.maintext import maintext
from guiguts.utilities import IndexRowCol, IndexRange, cmd_ctrl_string
from guiguts.widgets import ToolTip

logger = logging.getLogger(__package__)

BLOCK_TYPES = "[$*XxFf]"
POEM_TYPES = "[Pp]"
ALL_BLOCKS_REG = f"[{re.escape('#$*FILPXCR')}]"


def tool_save() -> bool:
    """File must be saved before running tool, so check if it has been,
    and if not, check if user wants to save, or cancel the tool run.

    Returns:
        True if OK to continue with intended operation.
    """
    if the_file().filename:
        return True

    save = messagebox.askokcancel(
        title="Save document",
        message="Document must be saved before running tool",
        icon=messagebox.INFO,
    )
    # User could cancel from messagebox or save-as dialog
    return save and bool(the_file().save_file())


def process_fixup(checker_entry: CheckerEntry) -> None:
    """Process the fixup error."""
    if checker_entry.text_range is None:
        return
    entry_type = checker_entry.text.split(":", 1)[0]
    start_mark = CheckerDialog.mark_from_rowcol(checker_entry.text_range.start)
    end_mark = CheckerDialog.mark_from_rowcol(checker_entry.text_range.end)
    match_text = maintext().get(start_mark, end_mark)
    # Several fixup errors are "Spaced ..." and need spaces removing.
    if entry_type.startswith("Spaced "):
        replacement_text = match_text.replace(" ", "")
        maintext().replace(start_mark, end_mark, replacement_text)
    elif entry_type == "Trailing spaces":
        replacement_text = match_text.replace(" ", "")
        maintext().replace(start_mark, end_mark, replacement_text)
    elif entry_type == "Multiple spaces":
        # Leave the non-space and first space alone
        replacement_text = match_text[2:].replace(" ", "")
        maintext().replace(f"{start_mark} + 2c", end_mark, replacement_text)
    elif entry_type == "Thought break":
        maintext().replace(start_mark, end_mark, "<tb>")
    elif entry_type == "1/l scanno":
        replacement_text = match_text.replace("llth", "11th").replace("lst", "1st")
        maintext().replace(start_mark, end_mark, replacement_text)
    elif entry_type == "Ellipsis spacing":
        maintext().replace(start_mark, end_mark, " ...")
    else:
        return


def sort_key_type(
    entry: CheckerEntry,
) -> tuple[int, str, int, int]:
    """Sort key function to sort Fixup entries by text, putting identical upper
        and lower case versions together.

    Differs from default alpha sort in using the text up to the colon
    (the type of error) as the primary sort key. No need to deal with different
    entry types for Fixup, and all entries have a text_range.
    """
    assert entry.text_range is not None
    return (
        entry.section,
        entry.text.split(":")[0],
        entry.text_range.start.row,
        entry.text_range.start.col,
    )


def basic_fixup_check() -> None:
    """Check the currently loaded file for basic fixup errors."""

    if not tool_save():
        return

    checker_dialog = CheckerDialog.show_dialog(
        "Basic Fixup Check Results",
        rerun_command=basic_fixup_check,
        process_command=process_fixup,
        sort_key_alpha=sort_key_type,
    )
    ToolTip(
        checker_dialog.text,
        "\n".join(
            [
                "Left click: Select & find issue",
                "Right click: Remove issue from list",
                f"With {cmd_ctrl_string()} key: Also fix issue",
                "With Shift key: Also remove/fix matching issues",
            ]
        ),
        use_pointer_pos=True,
    )
    checker_dialog.reset()

    # Check lines that aren't in block markup
    in_block = in_poem = False
    for line, line_num in maintext().get_lines():
        # Ignore lines within block markup
        if re.match(rf"/{BLOCK_TYPES}", line):
            in_block = True
        elif re.match(rf"{BLOCK_TYPES}/", line):
            in_block = False
        if in_block:
            continue

        # Ignore any poem line number (with preceding/trailing spaces)
        if re.match(rf"/{POEM_TYPES}", line):
            in_poem = True
        elif re.match(rf"{POEM_TYPES}/", line):
            in_poem = False
        test_line = line
        if in_poem and (match := re.search(r"\s{2,}\d+\s*$", line)):
            test_line = line[: match.start(0)]

        # Dictionary of regexes:
        # One or two capture groups in each regex, with the characters being checked
        # captured by one of them - these will be highlighted in error message.
        #
        # Multiple spaces between non-space characters
        # Space around single hyphen (not at start of line)
        # Space before single period (not at start of line and not decimal point)
        # Space before exclamation mark, question mark, comma, colon, or semicolon
        # Space before close or after open quotes (where unambiguous)
        # Space before close or after open brackets
        # Trailing spaces
        # Thought break (possibly poorly formed)
        # 1/l scanno, e.g. llth
        fixup_regexes = {
            "Multiple spaces: ": r"(\S\s{2,})(?=\S)",  # Capture character before too
            "Spaced hyphen: ": r"\S( +- *)(?!-)|(?<!-)( *- +)",
            "Spaced period: ": r"\S( +\.)(?![\d\.])",
            "Spaced exclamation mark: ": r"( +!)",
            "Spaced question mark: ": r"( +\?)",
            "Spaced comma: ": r"( +,)",
            "Spaced colon: ": r"( +:)",
            "Spaced semicolon: ": r"( +;)",
            "Spaced open quote: ": r'(^" +|[‘“] +)',
            "Spaced close quote: ": r'( +"$| +”)',
            "Spaced open bracket: ": r"([[({] )",
            "Spaced close bracket: ": r"( [])}])",
            "Trailing spaces: ": r"(.? +$)",
            "Thought break: ": r"^(\s*(\*\s*){4,})$",
            "1/l scanno: ": r"(?<!\p{Letter})(lst|llth)\b",
            "Ellipsis spacing: ": r"(?<=[^\.\!\? \"'‘“])(\.{3})(?![\.\!\?])",
            "Spaced guillemet: ": r"(«\s+|\s+»)",
        }
        # Some languages use inward pointing guillemets - catch most of them.
        # Do inward check if first language is one of these, or English with one of these.
        inward_langs = r"(de|hr|cs|da|hu|pl|sr|sk|sl|sv)"
        languages = maintext().get_language_list()
        if re.match(inward_langs, languages[0]) or (
            re.match("en", languages[0])
            and any(re.match(inward_langs, lang) for lang in languages)
        ):
            fixup_regexes["Spaced guillemet: "] = r"(»\s+|\s+«)"

        for prefix, regex in fixup_regexes.items():
            prefix_len = len(prefix)
            for match in re.finditer(regex, test_line):
                group = 2 if match[1] is None else 1
                checker_dialog.add_entry(
                    prefix + line,
                    IndexRange(
                        IndexRowCol(line_num, match.start(group)),
                        IndexRowCol(line_num, match.end(group)),
                    ),
                    match.start(group) + prefix_len,
                    match.end(group) + prefix_len,
                )
    checker_dialog.display_entries()


def unmatched_brackets() -> None:
    """Check for unmatched brackets."""

    def toggle_bracket(bracket_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close bracket.

        Args:
            bracket_in: Bracket - must be one of ( [ { ) ] }

        Returns:
            Tuple with regex, True if bracket_in was close bracket.
        """
        match bracket_in:
            case "(":
                return "[)(]", False
            case ")":
                return "[)(]", True
            case "{":
                return "[}{]", False
            case "}":
                return "[}{]", True
            case "[":
                return "[][]", False
            case "]":
                return "[][]", True
        assert False, f"'{bracket_in}' is not a bracket character"

    unmatched_markup_check(
        "Unmatched Brackets",
        rerun_command=unmatched_brackets,
        match_reg="[][}{)(]",
        match_pair_func=toggle_bracket,
    )


def unmatched_curly_quotes() -> None:
    """Check for unmatched curly quotes."""

    def toggle_quote(quote_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close quote.

        Args:
            quote_in: Quote - must be one of ‘ ’ “ ”

        Returns:
            Tuple with regex, True if bracket_in was close bracket.
        """
        match quote_in:
            case "‘":
                return "[‘’]", False
            case "’":
                return "[‘’]", True
            case "“":
                return "[“”]", False
            case "”":
                return "[“”]", True
        assert False, f"'{quote_in}' is not a curly quote"

    unmatched_markup_check(
        "Unmatched Curly Quotes",
        rerun_command=unmatched_curly_quotes,
        match_reg="[‘’“”]",
        match_pair_func=toggle_quote,
    )


def unmatched_dp_markup() -> None:
    """Check for unmatched DP markup."""

    def matched_pair_dp_markup(markup_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close DP markup.

        Args:
            markup_in: Markup string - must be "<i>", "</b>", "<sc>", etc.

        Returns:
            Tuple with regex, True if markup_in was close markup.
        """
        if markup_in[1] == "/":
            return markup_in[:1] + markup_in[2:], True
        return markup_in[:1] + "/" + markup_in[1:], False

    unmatched_markup_check(
        "Unmatched DP markup",
        rerun_command=unmatched_dp_markup,
        match_reg="<[a-z]+>|</[a-z]+>",
        match_pair_func=matched_pair_dp_markup,
        ignore_reg="<tb>",
    )


def unmatched_block_markup() -> None:
    """Check for unmatched block markup."""

    def match_pair_block_markup(markup_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close block markup.

        Args:
            markup_in: Markup string - must be "/#", "/*", "C/", etc.

        Returns:
            Tuple with regex, True if markup_in was close markup.
        """
        close = markup_in[1] == "/"
        block_type = markup_in[0] if close else markup_in[1]
        block_type = re.escape(block_type)
        return rf"^(/{block_type}(\[\d+)?(\.\d+)?(,\d+)?]?|{block_type}/)$", close

    unmatched_markup_check(
        "Unmatched Block markup",
        rerun_command=unmatched_block_markup,
        match_reg=f"^(/{ALL_BLOCKS_REG}|{ALL_BLOCKS_REG}/)",
        match_pair_func=match_pair_block_markup,
        nest_reg="/#|#/",
    )


def unmatched_markup_check(
    title: str,
    rerun_command: Callable[[], None],
    match_reg: str,
    match_pair_func: Callable[[str], tuple[str, bool]],
    nest_reg: Optional[str] = None,
    ignore_reg: Optional[str] = None,
) -> None:
    """Check the currently loaded file for unmatched markup errors."""

    if not tool_save():
        return

    checker_dialog = CheckerDialog.show_dialog(
        title,
        rerun_command=rerun_command,
    )
    ToolTip(
        checker_dialog.text,
        "\n".join(
            [
                "Left click: Select & find issue",
                "Right click: Remove issue from list",
                "Shift-Right click: Remove all matching issues",
            ]
        ),
        use_pointer_pos=True,
    )
    checker_dialog.reset()

    search_range = IndexRange(maintext().start(), maintext().end())
    # Find each piece of markup that matches the regex
    while match := maintext().find_match(
        match_reg, search_range, regexp=True, nocase=True
    ):
        match_index = match.rowcol.index()
        after_match = maintext().index(f"{match_index}+{match.count}c")
        search_range = IndexRange(after_match, maintext().end())
        match_str = maintext().get_match_text(match)
        # Ignore if it matches the ignore regex
        if ignore_reg and re.fullmatch(ignore_reg, match_str, flags=re.IGNORECASE):
            continue
        # Get a regex that will find the match and the pair( e.g. "(<i>|</i>)")
        match_pair_reg, reverse = match_pair_func(match_str)
        # Is this markup permitted to nest?
        nestable = bool(
            nest_reg and re.fullmatch(nest_reg, match_str, flags=re.IGNORECASE)
        )
        prefix = "Unmatched "
        # Search for the matching pair to this markup
        if not find_match_pair(
            match_index, match_str, match_pair_reg, reverse, nestable
        ):
            checker_dialog.add_entry(
                f"{prefix}{match_str}",
                IndexRange(match_index, after_match),
                len(prefix),
                len(prefix) + match.count,
            )
    checker_dialog.display_entries()


def find_match_pair(
    match_index: str, match_str: str, match_pair_reg: str, reverse: bool, nestable: bool
) -> str:
    """Find the pair to the given match.

    Args:
        match_index: Index of start of match_str in file.
        match_str: String to find the pair of.
        pair_str: The pair string to search for.
        reverse: True to search backwards (i.e. given close, look for open).
        nestable: True if markup is allowed to nest.
    """
    found = ""
    match_len = len(match_str)
    depth = 1
    start = match_index if reverse else maintext().index(f"{match_index}+{match_len}c")
    end = maintext().start() if reverse else maintext().end()
    # Keep searching until we find the markup that brings us back
    # to the same depth as the given markup (or until there's an error)
    while depth > 0:
        # Search for the given markup and its pair in order to spot nesting
        match = maintext().find_match(
            match_pair_reg,
            IndexRange(start, end),
            regexp=True,
            backwards=reverse,
            nocase=True,
        )
        if match is None:
            found = ""
            break

        depth += (
            1 if maintext().get_match_text(match).lower() == match_str.lower() else -1
        )
        # Check it's not nested when nesting isn't allowed
        if depth > 1 and not nestable:
            found = ""
            break

        found = match.rowcol.index()
        # Adjust start point for next search
        start = (
            match.rowcol.index()
            if reverse
            else maintext().index(f"{match.rowcol.index()}+{match.count}c")
        )
    return found
