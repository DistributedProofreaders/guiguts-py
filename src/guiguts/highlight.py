"""Highlight functionality."""

from enum import auto, StrEnum
from tkinter import Text

from guiguts.maintext import maintext
from guiguts.preferences import preferences, PrefKey
from guiguts.root import root
from guiguts.utilities import IndexRange


class HighlightTag(StrEnum):
    """Global highlight tag settings."""

    QUOTEMARK = auto()
    SPOTLIGHT = auto()
    PAREN = auto()
    CURLY_BRACKET = auto()
    SQUARE_BRACKET = auto()
    STRAIGHT_DOUBLE_QUOTE = auto()
    CURLY_DOUBLE_QUOTE = auto()
    STRAIGHT_SINGLE_QUOTE = auto()
    CURLY_SINGLE_QUOTE = auto()
    ALIGNCOL = auto()


class HighlightColors:
    """Global highlight color settings."""

    # Possible future enhancement:
    #
    # GG1 allowed you to set three colors:
    # - Background color (text areas, text inputs, main editor textarea)
    # - Button highlight color (hover on buttons, checkboxes, radio selects)
    # - Scanno/quote highlight color (which would apply here)
    #
    # Unclear what we should/will do in GG2 with themes & dark mode support.

    # Must be a definition for each available theme
    QUOTEMARK = {
        "Light": {"bg": "#a08dfc", "fg": "black"},
        "Dark": {"bg": "#a08dfc", "fg": "white"},
        "Default": {"bg": "#a08dfc", "fg": "black"},
    }

    SPOTLIGHT = {
        "Light": {"bg": "orange", "fg": "black"},
        "Dark": {"bg": "orange", "fg": "white"},
        "Default": {"bg": "orange", "fg": "black"},
    }

    PAREN = {
        "Light": {"bg": "violet", "fg": "white"},
        "Dark": {"bg": "violet", "fg": "white"},
        "Default": {"bg": "violet", "fg": "white"},
    }

    CURLY_BRACKET = {
        "Light": {"bg": "blue", "fg": "white"},
        "Dark": {"bg": "blue", "fg": "white"},
        "Default": {"bg": "blue", "fg": "white"},
    }

    SQUARE_BRACKET = {
        "Light": {"bg": "purple", "fg": "white"},
        "Dark": {"bg": "purple", "fg": "white"},
        "Default": {"bg": "purple", "fg": "white"},
    }

    STRAIGHT_DOUBLE_QUOTE = {
        "Light": {"bg": "green", "fg": "white"},
        "Dark": {"bg": "green", "fg": "white"},
        "Default": {"bg": "green", "fg": "white"},
    }

    CURLY_DOUBLE_QUOTE = {
        "Light": {"bg": "limegreen", "fg": "white"},
        "Dark": {"bg": "limegreen", "fg": "white"},
        "Default": {"bg": "limegreen", "fg": "white"},
    }

    STRAIGHT_SINGLE_QUOTE = {
        "Light": {"bg": "grey", "fg": "white"},
        "Dark": {"bg": "grey", "fg": "white"},
        "Default": {"bg": "grey", "fg": "white"},
    }

    CURLY_SINGLE_QUOTE = {
        "Light": {"bg": "dodgerblue", "fg": "white"},
        "Dark": {"bg": "dodgerblue", "fg": "white"},
        "Default": {"bg": "dodgerblue", "fg": "white"},
    }

    ALIGNCOL = {
        "Light": {"bg": "greenyellow", "fg": "black"},
        "Dark": {"bg": "#577a32", "fg": "white"},
        "Default": {"bg": "greenyellow", "fg": "black"},
    }


def highlight_selection(
    pat: str,
    tag_name: str,
    nocase: bool = False,
    regexp: bool = False,
) -> None:
    """Highlight matches in the current selection.
    Args:
        pat: string or regexp to find in the current selection
        tag_name: tkinter tag to apply to matched text region(s)
    Optional keyword args:
        nocase (default False): set True for case-insensitivity
        regexp (default False): whether to assume 's' is a regexp
    """

    if not (ranges := maintext().selected_ranges()):
        return

    for _range in ranges:
        matches = maintext().find_matches(pat, _range, nocase=nocase, regexp=regexp)
        for match in matches:
            maintext().tag_add(
                tag_name, match.rowcol.index(), match.rowcol.index() + "+1c"
            )


def remove_highlights() -> None:
    """Remove active highlights."""
    maintext().tag_delete(HighlightTag.QUOTEMARK)


def highlight_quotemarks(pat: str) -> None:
    """Highlight quote marks in current selection which match a pattern."""
    remove_highlights()
    _highlight_configure_tag(HighlightTag.QUOTEMARK, HighlightColors.QUOTEMARK)
    highlight_selection(pat, HighlightTag.QUOTEMARK, regexp=True)


def highlight_single_quotes() -> None:
    """Highlight single quotes (straight or curly) in current selection."""
    highlight_quotemarks("['‘’]")


def highlight_double_quotes() -> None:
    """Highlight double quotes (straight or curly) in current selection."""
    highlight_quotemarks('["“”]')


def spotlight_range(spot_range: IndexRange) -> None:
    """Highlight the given range in the spotlight color.

    Args:
        spot_range: The range to be spotlighted.
    """
    remove_spotlights()
    _highlight_configure_tag(HighlightTag.SPOTLIGHT, HighlightColors.SPOTLIGHT)
    maintext().tag_add(
        HighlightTag.SPOTLIGHT, spot_range.start.index(), spot_range.end.index()
    )


def remove_spotlights() -> None:
    """Remove active spotlights"""
    maintext().tag_delete(HighlightTag.SPOTLIGHT)


def _highlight_configure_tag(
    tag_name: str, tag_colors: dict[str, dict[str, str]]
) -> None:
    """Configure highlighting tag colors to match the theme.

    Args:
        tag_name: Tag to be configured.
        tag_colors: Dictionary of fg/bg colors for each theme.
    """
    theme = preferences.get(PrefKey.THEME_NAME)
    maintext().tag_configure(
        tag_name,
        background=tag_colors[theme]["bg"],
        foreground=tag_colors[theme]["fg"],
    )


def highlight_single_pair_bracketing_cursor(
    startchar: str,
    endchar: str,
    tag_name: str,
    tag_colors: dict[str, dict[str, str]],
    *,
    charpair: str = "",
) -> None:
    """
    Search for a pair of matching characters that bracket the cursor and tag
    them with the given tagname. If charpair is not specified, a default regex
    of f"[{startchar}{endchar}]" will be used.

    Args:
        startchar: opening char of pair (e.g. '(')
        endchar: closing chair of pair (e.g. ')')
        tag_name: name of tag for highlighting (class HighlightTag)
        tag_colors: dict of color information (class HighlightColors)
        charpair: optional regex override for matching the pair (e.g. '[][]')
    """
    maintext().tag_delete(tag_name)
    _highlight_configure_tag(tag_name, tag_colors)
    cursor = maintext().get_insert_index().index()

    (top_index, bot_index) = get_screen_window_coordinates(
        maintext().focus_widget(), 80
    )

    # search backward for the startchar
    startindex = search_for_base_character_in_pair(
        top_index,
        cursor,
        bot_index,
        startchar,
        endchar,
        charpair=charpair,
        backwards=True,
    )
    if not startindex:
        return

    # search forward for the endchar
    endindex = search_for_base_character_in_pair(
        top_index, cursor, bot_index, startchar, endchar, charpair=charpair
    )

    if not (startindex and endindex):
        return

    maintext().tag_add(tag_name, startindex, maintext().index(f"{startindex}+1c"))
    maintext().tag_add(tag_name, endindex, maintext().index(f"{endindex}+1c"))


def get_screen_window_coordinates(
    viewport: Text, offscreen_lines: int = 5
) -> tuple[str, str]:
    """
    Find start and end coordinates for a viewport (with a margin of offscreen
    text added for padding).

    Args:
        viewport: the viewport to inspect
        offscreen_lines: optional count of offscreen lines to inspect (default: 5)
    """
    (top_frac, bot_frac) = viewport.yview()
    # use maintext() here, not view - there is no TextPeer.rowcol()
    end_index = maintext().rowcol("end")

    # Don't try to go beyond the boundaries of the document.
    #
    # {top,bot}_frac contain a fractional number representing a percentage into
    # the document; do some math to calculate what the top or bottom row in the
    # viewport should be, then use min/max to make sure that value isn't less
    # than 0 or more than the total row count.
    top_line = max(int((top_frac * end_index.row) - offscreen_lines), 0)
    bot_line = min(int((bot_frac * end_index.row) + offscreen_lines), end_index.row)

    return (f"{top_line}.0", f"{bot_line}.0")


def search_for_base_character_in_pair(
    top_index: str,
    searchfromindex: str,
    bot_index: str,
    startchar: str,
    endchar: str,
    *,
    backwards: bool = False,
    charpair: str = "",
) -> str:
    """
    If searching backward, count characters (e.g. parenthesis) until finding a
    startchar which does not have a forward matching endchar.

    (<= search backward will return this index
    ()
    START X HERE
    ( (  )  () )
    )<== search forward will return this index

    If searching forward, count characters until finding an endchar which does
    not have a rearward matching startchar.

    Default search direction is forward.

    If charpair is not specified, a default regex is constructed from startchar,
    endchar using f"[{startchar}{endchar}]". For example,

    startchar='(', endchar=')' results in: charpar='[()]'
    """

    forwards = True
    if backwards:
        forwards = False

    if not charpair:
        if startchar == endchar:
            charpair = startchar
        else:
            charpair = f"[{startchar}{endchar}]"

    if forwards:
        plus_one_char = endchar
        search_end_index = bot_index
        index_offset = " +1c"
        done_index = maintext().index("end")
    else:
        plus_one_char = startchar
        search_end_index = top_index
        index_offset = ""
        done_index = "1.0"

    at_done_index = False
    count = 0

    while True:
        searchfromindex = maintext().search(
            charpair,
            searchfromindex,
            search_end_index,
            backwards=backwards,
            forwards=forwards,
            regexp=True,
        )

        if not searchfromindex:
            break

        # get one character at the identified index
        char = maintext().get(searchfromindex)
        if char == plus_one_char:
            count += 1
        else:
            count -= 1

        if count == 1:
            break

        # boundary condition exists when first char in widget is the match char
        # need to be able to determine if search tried to go past index '1.0'
        # if so, set index to undef and return.
        if at_done_index:
            searchfromindex = ""
            break

        if searchfromindex == done_index:
            at_done_index = True

        searchfromindex = maintext().index(f"{searchfromindex}{index_offset}")

    return searchfromindex


def highlight_parens_around_cursor() -> None:
    """Highlight pair of parens that most closely brackets the cursor."""
    highlight_single_pair_bracketing_cursor(
        "(",
        ")",
        HighlightTag.PAREN,
        HighlightColors.PAREN,
    )


def highlight_curly_brackets_around_cursor() -> None:
    """Highlight pair of curly brackets that most closely brackets the cursor."""
    highlight_single_pair_bracketing_cursor(
        "{",
        "}",
        HighlightTag.CURLY_BRACKET,
        HighlightColors.CURLY_BRACKET,
    )


def highlight_square_brackets_around_cursor() -> None:
    """Highlight pair of square brackets that most closely brackets the cursor."""
    highlight_single_pair_bracketing_cursor(
        "[",
        "]",
        HighlightTag.SQUARE_BRACKET,
        HighlightColors.SQUARE_BRACKET,
        charpair="[][]",
    )


def highlight_double_quotes_around_cursor() -> None:
    """Highlight pair of double quotes that most closely brackets the cursor."""
    highlight_single_pair_bracketing_cursor(
        '"',
        '"',
        HighlightTag.STRAIGHT_DOUBLE_QUOTE,
        HighlightColors.STRAIGHT_DOUBLE_QUOTE,
    )
    highlight_single_pair_bracketing_cursor(
        "“",
        "”",
        HighlightTag.CURLY_DOUBLE_QUOTE,
        HighlightColors.CURLY_DOUBLE_QUOTE,
    )


def highlight_single_quotes_around_cursor() -> None:
    """Highlight pair of single quotes that most closely brackets the cursor."""
    highlight_single_pair_bracketing_cursor(
        "'",
        "'",
        HighlightTag.STRAIGHT_SINGLE_QUOTE,
        HighlightColors.STRAIGHT_SINGLE_QUOTE,
    )
    highlight_single_pair_bracketing_cursor(
        "‘",
        "’",
        HighlightTag.CURLY_SINGLE_QUOTE,
        HighlightColors.CURLY_SINGLE_QUOTE,
    )


def highlight_quotbrac_callback(value: bool) -> None:
    """Callback when highlight_quotbrac preference is changed."""
    if value:
        highlight_quotbrac()
    else:
        remove_highlights_quotbrac()


def highlight_quotbrac() -> None:
    """Highlight all the character pairs that most closely bracket the cursor."""
    if preferences.get(PrefKey.HIGHLIGHT_QUOTBRAC):
        highlight_parens_around_cursor()
        highlight_curly_brackets_around_cursor()
        highlight_square_brackets_around_cursor()
        highlight_double_quotes_around_cursor()
        highlight_single_quotes_around_cursor()


def remove_highlights_quotbrac() -> None:
    """Remove highlights for quotes & brackets"""
    for tag in (
        HighlightTag.PAREN,
        HighlightTag.CURLY_BRACKET,
        HighlightTag.SQUARE_BRACKET,
        HighlightTag.STRAIGHT_DOUBLE_QUOTE,
        HighlightTag.CURLY_DOUBLE_QUOTE,
        HighlightTag.STRAIGHT_SINGLE_QUOTE,
        HighlightTag.CURLY_SINGLE_QUOTE,
    ):
        maintext().tag_delete(tag)


def highlight_aligncol_callback(value: bool) -> None:
    """Callback when highlight_aligncol active state is changed."""
    if value:
        root().aligncol = maintext().get_insert_index().col
        highlight_aligncol()
    else:
        remove_highlights_aligncol()


def highlight_aligncol() -> None:
    """Add a highlight to all characters in the alignment column."""
    if root().highlight_aligncol.get():
        maintext().tag_delete(HighlightTag.ALIGNCOL)
        _highlight_configure_tag(HighlightTag.ALIGNCOL, HighlightColors.ALIGNCOL)

        highlight_aligncol_in_viewport(maintext())
        if PrefKey.SPLIT_TEXT_WINDOW:
            highlight_aligncol_in_viewport(maintext().peer)


def highlight_aligncol_in_viewport(viewport: Text):
    """Do highlighting of the alignment column in a single viewport."""
    (top_index, bot_index) = get_screen_window_coordinates(viewport)

    col = root().aligncol
    row = int(top_index.split(".")[0])
    end_row = int(bot_index.split(".")[0])

    while row <= end_row:
        # find length of row; don't highlight if row is too short to contain col
        rowlen = int(maintext().index(f"{row}.0 lineend").split(".")[1])
        if 0 < col < rowlen:
            maintext().tag_add(HighlightTag.ALIGNCOL, f"{row}.{col}")
        row += 1


def remove_highlights_aligncol() -> None:
    """Remove highlights for alignment column"""
    maintext().tag_delete(HighlightTag.ALIGNCOL)
