"""Highlight functionality"""

from enum import auto

from guiguts.maintext import maintext
from guiguts.preferences import preferences, PrefKey


class Highlight:
    """Global highlight settings"""

    TAG_QUOTEMARK = auto()

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


def get_active_theme() -> str:
    """Return the current theme name"""
    return preferences.get(PrefKey.THEME_NAME)


def remove_highlights() -> None:
    """Remove acvite highlights"""
    maintext().tag_delete(str(Highlight.TAG_QUOTEMARK))


def highlight_quotemarks(pat: str) -> None:
    """Highlight quote marks in current selection which match a pattern"""
    theme = get_active_theme()
    remove_highlights()
    maintext().tag_configure(
        str(Highlight.TAG_QUOTEMARK),
        background=Highlight.COLORS_QUOTEMARK[theme]["bg"],
        foreground=Highlight.COLORS_QUOTEMARK[theme]["fg"],
    )
    highlight_selection(pat, str(Highlight.TAG_QUOTEMARK), regexp=True)


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
