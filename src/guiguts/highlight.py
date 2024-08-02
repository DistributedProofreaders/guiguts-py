"""Highlight functionality."""

from enum import auto

from guiguts.maintext import maintext
from guiguts.preferences import preferences, PrefKey
from guiguts.utilities import IndexRange


class Highlight:
    """Global highlight settings."""

    TAG_QUOTEMARK = str(auto())

    # Possible future enhancement:
    #
    # GG1 allowed you to set three colors:
    # - Background color (text areas, text inputs, main editor textarea)
    # - Button highlight color (hover on buttons, checkboxes, radio selects)
    # - Scanno/quote highlight color (which would apply here)
    #
    # Unclear what we should/will do in GG2 with themes & dark mode support.

    # Must be a definition for each available theme
    COLORS_QUOTEMARK = {
        "Light": {"bg": "#a08dfc", "fg": "black"},
        "Dark": {"bg": "#a08dfc", "fg": "white"},
        "Default": {"bg": "#a08dfc", "fg": "black"},
    }

    TAG_SPOTLIGHT = str(auto())

    COLORS_SPOTLIGHT = {
        "Light": {"bg": "orange", "fg": "black"},
        "Dark": {"bg": "orange", "fg": "white"},
        "Default": {"bg": "orange", "fg": "black"},
    }


def highlight_selection(
    pat: str,
    tag_name: str,
    nocase: bool = False,
    regexp: bool = False,
    wholeword: bool = False,
) -> None:
    """Highlight matches in the current selection.
    Args:
        pat: string or regexp to find in the current selection
        tag_name: tkinter tag to apply to matched text region(s)
    Optional keyword args:
        nocase (default False): set True for case-insensitivity
        regexp (default False): whether to assume 's' is a regexp
        wholeword (defalut False): whether to match only whole words
    """

    if not (ranges := maintext().selected_ranges()):
        return

    for _range in ranges:
        matches = maintext().find_matches(
            pat, _range, nocase=nocase, regexp=regexp, wholeword=wholeword
        )
        for match in matches:
            maintext().tag_add(
                tag_name, match.rowcol.index(), match.rowcol.index() + "+1c"
            )


def remove_highlights() -> None:
    """Remove active highlights."""
    maintext().tag_delete(Highlight.TAG_QUOTEMARK)


def highlight_quotemarks(pat: str) -> None:
    """Highlight quote marks in current selection which match a pattern."""
    remove_highlights()
    _highlight_configure_tag(Highlight.TAG_QUOTEMARK, Highlight.COLORS_QUOTEMARK)
    highlight_selection(pat, Highlight.TAG_QUOTEMARK, regexp=True)


def highlight_single_quotes() -> None:
    """Highlight single quotes in current selection.

    ' APOSTROPHE
    ‘’ {LEFT, RIGHT} SINGLE QUOTATION MARK
    ‹› SINGLE {LEFT, RIGHT}-POINTING ANGLE QUOTATION MARK
    ‛‚ SINGLE {HIGH-REVERSED-9, LOW-9} QUOTATION MARK
    """
    highlight_quotemarks("['‘’‹›‛‚]")


def highlight_double_quotes() -> None:
    """Highlight double quotes in current selection.

    " QUOTATION MARK
    “” {LEFT, RIGHT} DOUBLE QUOTATION MARK
    «» {LEFT, RIGHT}-POINTING DOUBLE ANGLE QUOTATION MARK
    ‟„ DOUBLE {HIGH-REVERSED-9, LOW-9} QUOTATION MARK
    """
    highlight_quotemarks('["“”«»‟„]')


def spotlight_range(spot_range: IndexRange) -> None:
    """Highlight the given range in the spotlight color.

    Args:
        spot_range: The range to be spotlighted.
    """
    remove_spotlights()
    _highlight_configure_tag(Highlight.TAG_SPOTLIGHT, Highlight.COLORS_SPOTLIGHT)
    maintext().tag_add(
        Highlight.TAG_SPOTLIGHT, spot_range.start.index(), spot_range.end.index()
    )


def remove_spotlights() -> None:
    """Remove active spotlights"""
    maintext().tag_delete(Highlight.TAG_SPOTLIGHT)


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
