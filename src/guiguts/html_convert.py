"""Functions to convert from text to HTML."""

import logging
import tkinter as tk
from tkinter import ttk

import regex as re

from guiguts.file import the_file
from guiguts.maintext import maintext
from guiguts.utilities import IndexRange
from guiguts.widgets import ToplevelDialog

logger = logging.getLogger(__package__)

css_indents: dict[int, bool] = {}


class HTMLGeneratorDialog(ToplevelDialog):
    """Dialog for converting text file to HTML."""

    def __init__(self) -> None:
        """Initialize HTML Generator dialog."""
        super().__init__("HTML Auto-generator", resize_x=False, resize_y=False)

        ttk.Button(
            self.top_frame, text="Auto-generate HTML", command=html_autogenerate
        ).grid(column=0, row=0, pady=2, sticky="NSEW")


def html_autogenerate() -> None:
    """Autogenerate HTML from text file."""
    global css_indents
    css_indents = {}

    fn = re.sub(r"\.[^\.]*$", "-htmlbak.txt", the_file().filename)
    the_file().save_copy(fn)

    maintext().undo_block_begin()
    remove_trailing_spaces()
    html_convert_amp_lt_gt()
    # html_convert_footnotes() - waiting for footnote code
    try:
        html_convert_body()
    except SyntaxError as exc:
        logger.error(exc)


def remove_trailing_spaces() -> None:
    """Remove trailing spaces from every line."""
    maintext().replace_all(" +$", "", regexp=True)


def html_convert_amp_lt_gt() -> None:
    """Replace occurrences of ampersand, less & greater than characters
    with HTML entities, except for things like `<i>`."""
    maintext().replace_all("&", "&amp;")

    # Find all < and > characters
    search_range = IndexRange(maintext().start(), maintext().end())
    while match := maintext().find_match("(<|>)", search_range, regexp=True):
        match_index = match.rowcol.index()
        match_text = maintext().get(match_index, f"{match_index} lineend")
        # Check if it's a DP tag, like `<i>` or `</sc>`
        check_match = re.match("</?(i|b|f|g|sc|tb)>", match_text)
        if check_match is None:
            maintext().replace(
                match_index,
                f"{match_index}+1c",
                "&lt;" if match_text[0] == "<" else "&gt;",
            )
            advance = 4
        else:
            advance = len(check_match[0])  # Skip whole of DP tag
        search_range = IndexRange(
            maintext().rowcol(f"{match_index}+{advance}c"), maintext().end()
        )


def html_convert_body() -> None:
    """Convert body of text to HTML one line at a time."""
    next_step = 1
    contents_start = None
    in_para = False
    in_front_para = False
    in_stanza = False
    pre_flag = False
    front_flag = False
    poetry_flag = False
    list_flag = False
    index_flag = False
    dollar_nowrap_flag = False
    asterisk_nowrap_flag = False
    center_nowrap_flag = False
    right_nowrap_flag = False
    right_block_line_num = 0
    poetry_indent = 0
    blockquote_level = 0
    right_line_lengths: list[int] = []
    ibs_dict = {
        "i": False,
        "b": False,
        "sc": False,
    }  # Flags to track open inline markup across lines

    def check_illegal_nesting() -> None:
        """Raise exception if already inside block markup."""
        if (
            pre_flag  # pylint: disable=too-many-boolean-expressions
            or front_flag
            or poetry_flag
            or list_flag
            or dollar_nowrap_flag
            or asterisk_nowrap_flag
            or center_nowrap_flag
            or right_nowrap_flag
            or index_flag
        ):
            raise SyntaxError(f"Line {step}: Illegally nested block markup")

    def reset_ibs_dict() -> None:
        """Set the italic/bold/smcap flags to False when starting a new block."""
        for key in ibs_dict:
            ibs_dict[key] = False

    while next_step < maintext().end().row:
        step = next_step
        next_step += 1
        line_start = f"{step}.0"
        line_end = f"{step}.end"
        selection = maintext().get(line_start, line_end)
        selection_lower = selection.lower()
        n_spaces = len(selection) - len(selection.lstrip())

        # Remove trailing spaces first
        if n_trail := len(selection) - len(selection.rstrip()):
            maintext().delete(f"{line_end}-{n_trail}c", line_end)

        # Note start of table of contents (English-only atm)
        if step < 300 and contents_start is None and "contents" in selection_lower:
            contents_start = line_end

        selection = html_convert_sub_super(selection, line_start, line_end)
        if html_convert_tb(selection, line_start, line_end):
            continue

        # "/x" is replaced with "<pre>", then leave lines unchanged until "/x"-->"</pre>"
        if selection.lower() == "/x":  # open
            maintext().replace(line_start, line_end, "<pre>")
            pre_flag = True
            continue
        if pre_flag:
            if selection.lower() == "x/":  # close
                maintext().replace(line_start, line_end, "</pre>")
                pre_flag = False
            continue

        # Remove leading spaces now "pre" is dealt with.
        # n_spaces stores the number of spaces if needed later.
        maintext().delete(line_start, f"{line_start}+{n_spaces}c")

        # "/f" --> center all paragraphs until we get "f/"
        if selection.lower() == "/f":  # open
            maintext().delete(line_start, line_end)
            front_flag = True
            in_front_para = False
            continue
        if front_flag:
            if selection.lower() == "f/":  # close
                if in_front_para:
                    maintext().insert(f"{line_start} -1l lineend", "</p>")
                maintext().delete(line_start, line_end)
                front_flag = False
            elif selection:
                if not in_front_para:  # start of paragraph
                    maintext().insert(line_start, '<p class="center">')
                    in_front_para = True
            elif in_front_para:  # blank line - end of paragraph
                maintext().insert(f"{line_start} -1l lineend", "</p>")
                in_front_para = False
            continue

        # "/p" --> poetry until we get "p/"
        if selection.lower() == "/p":  # open
            maintext().replace(
                line_start,
                line_end,
                '<div class="poetry-container"><div class="poetry">',
            )
            poetry_flag = True
            in_stanza = False
            poetry_end = maintext().search(
                "^p/$", line_end, tk.END, regexp=True, nocase=True
            )
            if not poetry_end:
                raise SyntaxError(f"Line {step}: Unclosed poetry")
            poetry_indent = poetry_indentation(
                maintext().get(f"{line_start}+1l", poetry_end)
            )
            reset_ibs_dict()
            continue
        if poetry_flag:
            if selection.lower() == "p/":  # close
                if in_stanza:
                    maintext().insert(f"{line_start} -1l lineend", "</div>")
                maintext().replace(line_start, line_end, "</div></div>")
                poetry_flag = False
            elif selection:
                # Handle line numbers (at least 2 spaces plus digits at end of line)
                # Remove line number prior to handling per-line bold/ital/smcap
                # then add marked up line number afterwards.
                replacement = ""
                if linenum_match := re.search(r" {2,}(\d+) *$", selection):
                    linenum_len = len(linenum_match[0])
                    replacement = f'<span class="linenum">{linenum_match[1]}</span>'
                    maintext().delete(f"{line_end}-{linenum_len}c", line_end)
                do_per_line_markup(selection, line_start, line_end, ibs_dict)
                # Now safe to add indent markup and line number markup
                indent = n_spaces - poetry_indent
                maintext().insert(
                    line_start,
                    f'<div class="verse indent{indent}">',
                )
                maintext().insert(line_end, replacement + "</div>")
                add_indent_to_css(indent)
                if not in_stanza:  # start of stanza
                    maintext().insert(line_start, '<div class="stanza">')
                    in_stanza = True
            elif in_stanza:  # blank line - end of stanza
                maintext().insert(f"{line_start} -1l lineend", "</div>")
                in_stanza = False
            continue

        # "/l" --> list until we get "l/"
        if selection_lower == "/l":  # open
            maintext().replace(
                line_start,
                line_end,
                "<ul>",
            )
            list_flag = True
            reset_ibs_dict()
            continue
        if list_flag:
            if selection_lower == "l/":  # close
                maintext().replace(line_start, line_end, "</ul>")
                list_flag = False
            elif selection:
                do_per_line_markup(selection, line_start, line_end, ibs_dict)
                # Now safe to add list markup
                maintext().insert(line_start, "<li>")
                maintext().insert(line_end, "</li>")
            continue

        # "/#" --> enter new level of blockquote until we get "p/"
        if selection.startswith("/#"):  # open
            blockquote_level += 1
            maintext().replace(
                line_start,
                line_end,
                '<div class="blockquot">',
            )
            continue
        if selection == "#/":  # close
            if blockquote_level > 0:
                blockquote_level -= 1
                maintext().replace(
                    line_start,
                    line_end,
                    "</div>",
                )
            else:
                raise SyntaxError(f"Line {step}: Unmatched close blockquote (#/)")
            continue

        # "/$" --> nowrap until we get "$/"
        if selection == "/$":  # open
            check_illegal_nesting()
            dollar_nowrap_flag = True
            maintext().replace(
                line_start,
                line_end,
                "<p>",
            )
            reset_ibs_dict()
            continue
        if dollar_nowrap_flag and selection == "$/":  # close
            dollar_nowrap_flag = False
            maintext().replace(
                line_start,
                line_end,
                "</p>",
            )
            continue
        # "/*" --> nowrap until we get "*/"
        if selection == "/*":  # open
            check_illegal_nesting()
            asterisk_nowrap_flag = True
            maintext().replace(
                line_start,
                line_end,
                "<p>",
            )
            reset_ibs_dict()
            continue
        if asterisk_nowrap_flag and selection == "*/":  # close
            asterisk_nowrap_flag = False
            maintext().replace(
                line_start,
                line_end,
                "</p>",
            )
            continue
        # lines within "/$" or "/*" markup
        if dollar_nowrap_flag or asterisk_nowrap_flag:
            do_per_line_markup(selection, line_start, line_end, ibs_dict)
            # Add 0.5em margin per space character
            if n_spaces > 0:
                maintext().insert(
                    line_start,
                    f'<span style="margin-left: {n_spaces * 0.5}em;">',
                )
                maintext().insert(line_end, "</span>")
            maintext().insert(line_end, "<br>")
            continue

        # "/i" --> index until we get "i/"
        if selection_lower == "/i":  # open
            check_illegal_nesting()
            index_flag = True
            maintext().replace(
                line_start,
                line_end,
                '<ul class="index">',
            )
            reset_ibs_dict()
            index_blank_lines = 2  # Force first entry to be start of section
            continue
        if index_flag:
            if selection_lower == "i/":  # close
                index_flag = False
                maintext().replace(
                    line_start,
                    line_end,
                    "</ul>",
                )
                continue
            if selection == "":
                index_blank_lines += 1
                continue
            if index_blank_lines >= 2:  # Section start
                classname = "ifrst"
            elif index_blank_lines == 1:  # Top-level entry
                classname = "indx"
            else:
                classname = f"isub{int((n_spaces+1)/2)}"
            maintext().insert(
                line_start,
                f'<li class="{classname}">',
            )
            maintext().insert(line_end, "</li>")
            index_blank_lines = 0
            continue

        # "/c" --> center until we get "c/"
        if selection_lower == "/c":  # open
            check_illegal_nesting()
            center_nowrap_flag = True
            maintext().replace(
                line_start,
                line_end,
                '<p class="center">',
            )
            reset_ibs_dict()
            continue
        if center_nowrap_flag:
            if selection_lower == "c/":  # close
                center_nowrap_flag = False
                maintext().replace(
                    line_start,
                    line_end,
                    "</p>",
                )
            else:  # lines within "/c" markup
                do_per_line_markup(selection, line_start, line_end, ibs_dict)
                maintext().insert(line_end, "<br>")
            continue

        # "/r" --> right-align block until we get "r/"
        if selection_lower == "/r":  # open
            check_illegal_nesting()
            right_nowrap_flag = True
            maintext().replace(
                line_start,
                line_end,
                '<p class="right">',
            )
            reset_ibs_dict()
            # Begin list of line lengths in order to add right-margin indents later
            right_line_lengths = []
            right_block_line_num = maintext().rowcol(line_start).row
            continue
        if right_nowrap_flag:
            if selection_lower == "r/":  # close
                right_nowrap_flag = False
                maintext().replace(
                    line_start,
                    line_end,
                    "</p>",
                )
                # Add the right-margin indents calculated from line lengths
                # Attempt to preserve shape of right margin (0.5em per character)
                max_len = max(right_line_lengths)
                for line_len in right_line_lengths:
                    right_block_line_num += 1
                    right_pad = max_len - line_len
                    if line_len > 0 and right_pad > 0:
                        maintext().insert(
                            f"{right_block_line_num}.0",
                            f'<span style="margin-left: {right_pad * 0.5}em;">',
                        )
                        maintext().insert(f"{right_block_line_num}.end", "</span>")
                    maintext().insert(f"{right_block_line_num}.end", "<br>")
            else:  # lines within "/r" markup
                # Store original line length for later right-margin calculations
                right_line_lengths.append(len(selection))
                do_per_line_markup(selection, line_start, line_end, ibs_dict)
            continue

        if selection:
            if not in_para:  # start of paragraph
                maintext().insert(line_start, "<p>")
                in_para = True
        elif in_para:  # blank line - end of paragraph
            maintext().insert(f"{line_start} -1l lineend", "</p>")
            in_para = False

    # May hit end of file without a final blank line
    if in_para:
        maintext().insert(tk.END, "</p>")

    if pre_flag:
        raise SyntaxError("Pre-formatted (/x) markup not closed by end of file")
    if front_flag:
        raise SyntaxError("Frontmatter (/f) markup not closed by end of file")
    if poetry_flag:
        raise SyntaxError("Poetry (/p) markup not closed by end of file")
    if list_flag:
        raise SyntaxError("List (/l) markup not closed by end of file")
    if dollar_nowrap_flag:
        raise SyntaxError("List (/$) markup not closed by end of file")
    if asterisk_nowrap_flag:
        raise SyntaxError("List (/*) markup not closed by end of file")
    if index_flag:
        raise SyntaxError("List (/i) markup not closed by end of file")
    if blockquote_level > 0:
        raise SyntaxError("Blockquote (/#) not closed by end of file")


def do_per_line_markup(
    selection: str,
    line_start: str,
    line_end: str,
    ibs_flags: dict[str, bool],
) -> None:
    """Add <i>, <b>, <sc> markup to this line if needed.

    Some constructions, e.g. poetry, use divs/spans for each line, which
    means that italic, bold or smcap cannot span line breaks, even if
    it was marked up that way at DP. Therefore need to stop/restart these
    inline markups on every line.

    Args:
        selection: Text of the line currently being worked on.
        line_start: Index of start of line.
        line_end: Index of end of line.
        ibs_flags: Global dictionary of flags keeping track of which markups are active.
    """
    if not selection:
        return
    for ch in ibs_flags.keys():
        # Add open at start if already in markup when we got to this line
        if ibs_flags[ch]:
            maintext().insert(line_start, f"<{ch}>")
        # Check status at end of line
        open_idx = selection.rfind(f"<{ch}>")
        close_idx = selection.rfind(f"</{ch}>")
        if open_idx > close_idx:
            ibs_flags[ch] = True  # Markup was left open
        if close_idx > open_idx:
            ibs_flags[ch] = False  # Markup was left closed
        # Add close at end of line if markup was left open
        if ibs_flags[ch]:
            maintext().insert(line_end, f"</{ch}>")


def add_indent_to_css(indent: int) -> None:
    """Add CSS for indent to CSS."""
    css_indents[indent] = True


def poetry_indentation(poem: str) -> int:
    """Return how much whole poem is already indented by."""
    min_indent = 1000
    for line in poem.splitlines():
        if strip_line := line.lstrip():
            min_indent = min(min_indent, len(line) - len(strip_line))
            if min_indent == 0:
                break
    return min_indent


def html_convert_sub_super(selection: str, line_start: str, line_end: str) -> str:
    """Convert all sub/superscripts in given line & return
    the modified line for later processing.

    Supports `_{subscript}`, `^{superscript}`, and `^x` (single char superscript).

    Args:
        selection: The text of one line.
        line_start: Index of start of line.
        line_end: Index of end of line.

    Returns:
        The modified text of the line.
    """
    selection, nsubs = re.subn(r"_\{(.+?)\}", r"<sub>\1</sub>", selection)
    selection, nsups1 = re.subn(r"\^{(.+?)\}", r"<sup>\1</sup>", selection)
    selection, nsups2 = re.subn(r"\^(.)", r"<sup>\1</sup>", selection)
    if nsubs or nsups1 or nsups2:
        maintext().replace(line_start, line_end, selection)
    return selection


def html_convert_tb(selection: str, line_start: str, line_end: str) -> int:
    """Convert asterisk or <tb> thoughtbreak markup to <hr>.

    Args:
        selection: The text of one line.
        line_start: Index of start of line.
        line_end: Index of end of line.

    Returns:
        True if line was a thoughtbreak.
    """
    selection, nsubs = re.subn(r"^(       \*){5}$", '<hr class="tb">', selection)
    if nsubs:
        maintext().replace(line_start, line_end, selection)
    else:
        selection, nsubs = re.subn("<tb>", '<hr class="tb">', selection)
        if nsubs:
            maintext().replace(line_start, line_end, selection)
    return nsubs
