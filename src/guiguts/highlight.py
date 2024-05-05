"""Highlighter functionality"""

import logging
import time

from guiguts.preferences import preferences, PrefKey
from guiguts.root import root

logger = logging.getLogger(__package__)

def highlight_quotbrac_on() -> None:
    """Turn on highlighting for quotes and brackets"""
    preferences.set(PrefKey.HIGHLIGHT_QUOTBRAC, True)
    print("Turn quote/bracket highlighting on.")
    highlight_quotbrac()

def highlight_quotbrac_off() -> None:
    """Turn off highlighting for quotes and brackets"""
    preferences.set(PrefKey.HIGHLIGHT_QUOTBRAC, False)
    print("Turn quote/bracket highlighting off.")

def highlight_quotbrac(state=None) -> None:
    """Action routine to highlight quotes/brackets that surround the cursor"""
    print(f"CALL update_quotbrac() {time.time()}")
    print(f"arg[state]={state}")

    if preferences.get(PrefKey.HIGHLIGHT_QUOTBRAC):
        print("Pref passes test, it is true")
        root().after(2000, highlight_quotbrac)

# -------------------------------------
# The rest of this file is a PoC for how to highlight text, can be ignored for now.
#
# def poc_highlighter(word="", disable=False) -> None:
#     """Only a proof-of-concept for now. Figuring out how to highlight text."""
#
#     # a tag name for our highlight thingamajig
#     tag_name = "dmlhighlightword"
#
#     if disable:
#         maintext().tag_delete(tag_name)
#         return
#
#     # TODO: either augment the search dialog with a button for
#     # this, or else create a new dialog? See how the GG1 flow works.
#     search_string = word
#
#     # Configure what this tag will look like
#     # TODO: eventually let user control the colors in a pref or something
#     maintext().tag_configure(tag_name, background="OliveDrab1", foreground="black")
#
#     # TODO: improve on this with differing cases; see
#     # search.py : SearchDialog.findall_clicked for examples
#
#     # hack for now
#     find_range = IndexRange(maintext().start(), maintext().end())
#     # find_range = (the_range, "in entire file")
#
#     matches = maintext().find_matches(
#         search_string,
#         find_range,  # what is this??
#         nocase=False,  # figure out how to handle this
#         regexp=False,  # um handle later
#         wholeword=False,  # handle later
#     )
#     count = len(matches)
#     print(f"Found {count} things to highlight")
#
#     # Example of how to do highlight
#     # matches should contain an array of FindMatch
#     # so match.rowcol.index() should return the start position like 'x.y'
#     # match.rowcol.count should return the length
#     # and this code shows how to find from an index to +x chars:
#     # rowcol_end = maintext().rowcol(match.rowcol.index() + f"+{match.count}c")
#
#     # TODO: This doesn't currently behave in the way that GG1 behaves.
#     # In GG1 if you highlight quotes they stay (unless overwritten.)
#     # If you highlight a word/match it will highlight but if you insert anything
#     # in the middle of a word it will split and NOT highlight that word anymore.
#     # do I need to highlight each individual character to mimic that behavior??
#     # And if you highlight the alignment column, then it will re-highlight if you
#     # insert, delete, or overwrite text involving that column. It must be in the
#     # main loop checking on each redraw.
#
#     # GG1 references:
#     # The popup when you run "Highlight Chars, ..." is in Highlight.pm, sub hilitepopup
#     # There is a search history here. And a whole dialog.
#     # The "highlight surrounding brackets" menu item calls Highlight.pm sub highlight_quotbrac
#     # The "highlight alignment column" menu item calls code in Highlight.pm:
#     #    to start: hilite_alignment_start, to stop: hilite_alignment_stop
#     #    it's all keyed off a global value, a bool `highlightalignment`. menu is a checkbox item.
#     #    (?) can menus in macos act as toggles too? (i think so) - does it work in tkinter?
#     #        and if so does it also work in linux?
#     #    the funcs note they are called every 200ms
#     #    in hilite_alignment_start, a repeating function is started that handles this.
#     #    $::lglobal{align_id}           = $::top->repeat( 200, \&hilite_alignment );
#     #    later on this is called with ->cancel to stop the repeating routine
#     #    so it just calls the actual hilight_alignment routine every 200ms
#
#     for match in matches:
#         for n in range(match.count):
#             if n % 2 == 0:
#                 continue
#             # maintext().tag_add(tag_name, match.rowcol.index(), match.rowcol.index() + f"+{match.count}c")
#             __mystart = match.rowcol.index()  # + f"+{n}c"
#             __myend = match.rowcol.index() + f"+{n+1}c"
#             print(f"Highlighter: from {__mystart} to {__myend}")
#             maintext().tag_add(tag_name, __mystart, __myend)
#
#     # Can I get from the above thing, a FindMatch, to somehow an IndexRange?
#     # An IndexRange would have
#     # _range.start.index(), _range.end.index()
