# https://tkdocs.com/tutorial/text.html
#
# https://stackoverflow.com/a/3781773
# The basic concept is, you assign properties to tags, and you apply tags to
# ranges of text in the widget. You can use the text widget's search command to
# find strings that match your pattern, which will return you enough information
# apply a tag to the range that matched.
#
# https://stackoverflow.com/a/3781773
# This answer seems to have a way to do a search/match with a regex? Also Nigel
# probably has done a lot of work here that can be used as an example of even
# re-used.
#
# Relevant tickets (all from GG1 search menu):
#
# Highlight Character, String or Regex #41 - https://github.com/DistributedProofreaders/guiguts-py/issues/41
# Behavior:
# - opens a dialog
# - accepts a string input
# - has either "exact" or "regex" mode - a toggle
# - works on a selection if present; or else lets you choose "prev selection" or else "select whole file"
# - and then "apply highlights" or "remove highlight"

# Highlight surrounding quotes/brackets #42 - https://github.com/DistributedProofreaders/guiguts-py/issues/42
# Behavior:
# - Wherever the cursor is place, surrounding markers are highlighted
# - it can match left to right brackets i think but quotes just any pair.
# - it doesn't necessarily do only the innermost like for ({foo bar}) it would
#   highlight both of the bracket pairs ... have to analyze what it's doing in GG1
# - colors:
#       - gray for ' ‘’ (single quote)
#       - green for " “ ” (double quote)
#       - pink for ( )
#       - purple for [ ]
#       - blue for { }
#       - it doesn't seem to match < >
#       - not sure about guillemet
#       - check what guiguts1 does.

# Highlight Alignment Column #43 - https://github.com/DistributedProofreaders/guiguts-py/issues/43
# Behavior:
# - identify column at cursor
# - find all characters at the column PRIOR, so to left of the bar cursor position
# - highlight that character
# - so if cursor is at column 3, highlight any character in column 2 on any line
# - it only can highlight lines with a character; lines with no char in that column
#   get no highlight there
# - THIS COLUMN DOESN'T MOVE but as the text may move or change, on each change,
#   or maybe firing on some timer, it re-highlights so that even if text change,
#   the highlight column stays in the same location.
# - this seems to be something that has to be done on each redraw / cursor position move?
#   is there a central hook to hang that on? In GG1 it can lag, which makes me think it is
#   firing on 250ms timer or something instead of "on each change" ? have to investigate.

# Other things, not ticketed, but related:
# Search -> Highlight single quotes in selection
# Search -> Highlight double quotes in selection

# These are all defined in GG1 in MenuStructure.pm lines 337+

# Order of these by how easy they seem:
# 1. Highlight surrounding quotes/brackets #42
#           this is a CheckButton which then has a command tied to it...
#           Highlight.pm :: highlight_quotbrac()
# 2. Highlight Alignment Column #43 (must be done on each redraw...)
#           Highlight.pm :: it calls a lambda that runs hilite_alignment_{start,stop}()
#           this is a CheckButton
# 3. Highlight Character, String or Regex #41 (needs a dialog)
#           Highlight.pm :: hilitepopup()
# 4. Search -> Highlight single quotes in selection
#           Highlight.pm :: hilitesinglequotes() -> calls hilite()
# 5. Search -> Highlight double quotes in selection
#           Highlight.pm :: hilitedoublequotes() -> calls hilite()

        # [
        #     'command', 'Highlight ~Double Quotes in Selection',
        #     -accelerator => 'Ctrl+.',
        #     -command     => \&::hilitedoublequotes,
        # ],
        # [
        #     'command', 'Highlight ~Single Quotes in Selection',
        #     -accelerator => 'Ctrl+,',
        #     -command     => \&::hilitesinglequotes,
        # ],
        # [
        #     'command', '~Highlight Character, String or Regex...',
        #     -accelerator => "Ctrl+$::altkeyname+h",
        #     -command     => \&::hilitepopup,
        # ],
        # [
        #     Checkbutton  => 'Highlight S~urrounding Quotes & Brackets',
        #     -variable    => \$::nohighlights,
        #     -onvalue     => 1,
        #     -offvalue    => 0,
        #     -accelerator => "Ctrl+;",
        #     -command     => \&::highlight_quotbrac
        # ],
        # [
        #     Checkbutton  => 'Highlight Al~ignment Column',
        #     -accelerator => 'Ctrl+Shift+a',
        #     -variable    => \$::lglobal{highlightalignment},
        #     -onvalue     => 1,
        #     -offvalue    => 0,
        #     -command     => sub {
        #         if ( $::lglobal{highlightalignment} ) {
        #             ::hilite_alignment_start();
        #         } else {
        #             ::hilite_alignment_stop();
        #         }
        #         $textwindow->focus;
        #     }
        # ],
        # [
        #     'command', 'Re~move Highlights',
        #     -accelerator => 'Ctrl+0',
        #     -command     => \&::hiliteremove,
        # ],

# Things I need to work out:
#
# - these two are menu items in the Search menu. seems like it's just a "take this action" thing.
# - look at GG1 "highlight single quotes in selection" algorithm
# - look at GG1 "highlight double quotes in selection" algorithm
# - make a function to highlight quotes (either kind) to use for both of the above 2
#
# - Search menu - this is a checkbox / toggle thing. as you move the cursor it CHANGES the surround that's highlighted.
#     - so this is another thing that is on every cursor move / redraw? have to re-evaluate it
# - look at GG1 "highlight surrounding quote/bracket" algorithm
# - look at the colors used by the different things and map it in that function
# - make generic function to highlight surrounding (anything) to use for the above
#
# - Search menu - this is a checkbox / toggle thing. as you move cursor if changes with every redraw.
# - make a function to highlight the alignment column
# - look to see if there's an "every change" function that can be used for "on redraw" already
# - implement that if it's not already there. ask nigel first to be sure.
#
# - create dialog box for the char/str/re function
# - work on the implementation(s) behind that
