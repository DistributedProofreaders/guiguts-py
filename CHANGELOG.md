# Changelog


## Version 2.0.0-alpha.14

- When using the Search dialog to search for a string, all occurrences
  of the string are highlighted faintly, in addition to the first occurrence
  being selected as previously. These faint highlights are removes when
  the user begins a new search or closes the Search dialog
- The bookloupe tool has been added. Although it is not identical in 
  behavior to the old external tool, it essentially does the same checks
  and reports issues in a similar way. Most of the differences relate to
  changes in DP/PG texts since the forerunner of bookloupe (gutcheck) was
  first written, such as use of non-ASCII characters.
- When using Save As, GG2 now adds an appropriate extension, which is
  `.txt` unless the file has an HTML header, in which case it is `.html`.
  Also, if there is no filename, Save As suggests `untitled.txt`
- Illo/Sidenote Fixup now automatically select the first message when run
- HTML Autogeneration now reports more specific errors it discovers while
  running, and allows user to re-load the previous backup to fix them

### Bug fixes

- Orange spotlights could be hidden by selected text
- Could get warnings if preferences were removed in a previous release
- Asterisk thoughtbreaks were broken by rewrapping
- The first page number in HTML could get inserted before the HTML header
- Swap/delete space functions in curly quote check didn't always work
- Using undo/redo did not cause Sidenote/Illo Fixup to recalculate positions
- The final footnote in the file could cause an error during HTML generation
- HTML Autogeneration didn't show the "busy" cursor to indicate it was working
- HTML Autogeneration didn't consider the last line of the file
- HTML Autogeneration didn't fail gracefully if the final chapter heading did
  not have 2 blank lines after it
- Rapidly cancelling the Search dialog with the Escape key while it was still
  working caused an error to occur


## Version 2.0.0-alpha.13

- HTML Autogeneration has been added. This performs basic conversion to HTML
  in a similar way to GG1. Other features such as image and table conversion
  are not included. To customize the HTML header, the user has two choices.
  The recommended method is to leave the default header as it is in
  `data/html/html_header.txt`, and create a new `html_header.txt` in their
  GGprefs folder which only contains CSS to override or add to the defaults.
  When the HTML file is generated, the default header will be inserted at
  the top of the file, and the user's header will be inserted at the bottom
  of the CSS, just before the closing `</style>` so that the user's CSS
  will override the earlier default settings. This method has the advantage
  that when future releases are made with adjustments to the default header,
  you will not usually need to edit your customized header text.
  The alternative method, which does not have this advantage, is to
  copy the file `html_header.txt` from the `data/html` folder in the
  release into their GGprefs folder and edit it there. That file will be
  used as the complete header for generated HTML files. If the default
  header is altered in a future release, you would need to either copy across
  any new changes into your header, or copy the whole file across and make
  your customizing edits again.
- There is a manual page for all the features currently in GG2. The top level
  of the manual is https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_2_Manual
- Pressing the F1 function key in any dialog brings up the manual page for
  that dialog
- Checker dialogs, e.g. Jeebies, now have a Copy Results button which copies
  all the messages from the dialog to the clipboard, so the user can paste
  them elsewhere to help with reporting issues or to analyze results
- Regex Cheat Sheet link added to Help menu
- Search dialog now has a First (or Last) button. This finds the first
  occurrence of the search term in the file (or last if Reverse searching).
  This is equivalent to Start at Beginning, followed by Search in GG1
- Each checker dialog, e.g. Jeebies and Spell check, now has its own settings
  for sorting the messages, either by line/column or by type/alphabetic
- PPtext now reports occurrences of multiple spaces/dashes once per line
  rather than every occurrence. The number of occurrences on the line
  is displayed in the error message 
- Detection of mid-paragraph illustrations/sidenotes has been improved
- Pressing "R&S" in the Search dialog after pressing Replace now does
  a Search
- Highlight colors have been adjusted for dark themes.

### Bug Fixes

- Ditto marks were not recognized if they appeared at the beginning or end
  of the line during curly quote conversion
- Blank lines at page breaks could be lost during rewrap
- Case changes required several Undo clicks to undo the changes made
- The text window could fail to scroll correctly when the mouse was clicked
  and dragged outside the window. Also other column-selection bugs.
- Multi-paragraph footnotes didn't "move to paragraph" correctly
- Illustration/Sidenote Fixup could move the wrong lines if the file had been
  edited since the tool was first run
- When selecting text to make an edit within an orange spotlighted piece of
  text, the selection was not visible
- Word Frequency and Search's ideas of what constitutes a word were
  inconsistent meaning that some "words" found by WF could not be found by
  searching
- Some ellipses were reported as "double punctuation" by PPtext
- Using Ctrl/Cmd+0 to fit the image to the image viewer window crashed if
  the image viewer was hidden at the time.


## Version 2.0.0-alpha.12

- There are no additional features - the primary reason for this release is
  to support macOS installation via `pip`

### Bug Fixes

- MacOS installation via `pip` failed due to out-of-date Levenshtein module
- Column selection failed in the lower of the split view windows
- Blank lines in indexes caused an error when rewrapped
- Dragging the cursor outside the window when scrolling failed on Macs
- The lower split view window colors didn't always match the theme
- Fractions with decimal points were converted wrongly



## Version 2.0.0-alpha.11

- Footnote Fixup dialog can now be used to fixup the majority of footnote
  situations, including setting up and moving footnotes to landing zones,
  or moving footnotes to the end of the paragraph. Mixed style footnotes
  are not yet supported.
- Text Markup dialog allows user to convert italic and other markup
- Clean Up Rewrap Markers removes rewrap markup from text file
- Stealth Scannos feature added
- Column numbers (horizontal ruler) can now be displayed
- Highlight Quotes & Brackets feature added
- Highlight Alignment column feature added
- Current line is now given a subtle background highlight
- Convert to Curly Quotes and Check Curly Quotes features added
- Image viewer background now adapts better to dark/light themes
- Insert cursor is now hidden when there is a selection
- Home/End keys (Cmd+Up/Down on Macs) go to start/end of checker dialogs,
  and Page Label Config dialog
- New shortcuts for Search/Replace: Cmd/Ctrl+Enter does Replace & Search;
  Shift+Cmd/Ctrl+Enter does Replace & Search in reverse direction
- Tooltips & labels improved in Preferences dialog

### Bug Fixes

- Double-clicking Re-run in checker dialogs caused an error
- Search/replace text fields were sometimes not tall enough to show character
- Show/hide line numbers now works properly in Split Window mode
- Some keystrokes, e.g. Ctrl+D, caused unwanted edits
- Word pairs followed by punctuation were not flagged in WF hyphen check
- Using cut/copy when macOS clipboard contained an image caused an error
- Illegal language codes were not handled well
- Fractions containing decimal points were wrongly converted
- Typing over a column selection gave unexpected results
- The page labels dialog could become desynchronized from the display


## Version 2.0.0-alpha.10

- Checker dialogs now use the same font as the text window
- Do not jump to position in main window when user uses the first-letter
  shortcut in Word Frequency
- Line.column displays in checker dialogs and Word Frequency are now padded
  and aligned 
- All features are now accessible via the menus (and hence by keyboard)
- Find Asterisks w/o Slashes feature added
- Words reported by spell checker can be added to global user dictionary
- Installation notes mention that either Python 3.11 or 3.12 can be used

### Bug Fixes

- Pasting didn't overwrite existing selection on Linux
- WF count and search did not handle word boundaries consistently
- Highlighting of spelling errors preceded by a single quote was wrong
- Fit-to-height sometimes failed in image viewer
- Double clicking Re-run button in checker dialogs caused an error


## Version 2.0.0-alpha.9

- Word Frequency Italic/Bold check is much faster, and when sorted
  alphabetically puts the marked up and non-marked up duplicates together
- Illustration Fixup tool added to facilitate moving illustrations to required
  location in file
- Sidenote Fixup tool added - similar to Illustration fixup
- Improvements to Image viewer including zoom, fit-to-width/height, dock and
  close buttons (shortcuts Cmd/Ctrl-plus, Cmd/Ctrl-minus and Cmd/Ctrl-zero);
  better zoomed image quality; ability to invert scan colors for dark themes;
  viewer size and position are remembered
- "Save a Copy As" button added to File menu
- Find Proofer Comments feature added
- Remove (unnecessary) Byte Order Mark from top of files

### Bug Fixes

- Word Frequency Hyphen check did not find suspects correctly
- Traceback occurred on Linux when Menu bar was selected - related to Split
  Text window code
- Keyboard shortcuts for Undo and Redo text edits did not work if the focus
  was in a checker tool dialog


## Version 2.0.0-alpha.8

- Split Text Window now available via the View menu
- Multi-replace now available in the Search/Replace dialog to show three
  independent replace fields with associated buttons
- Minor wording improvements to Preferences dialog
- Suspects Only checkbox in Word Frequency is now hidden when not relevant

### Known bugs discovered pre-testing alpha.8 (also in previous versions)

- Some false positives in Word Frequency hyphens check
- Some false positives in Ital/Bold/SC/etc check


## Version 2.0.0-alpha.7

- Unicode Search dialog added
- Unicode block list updated to include more recently defined blocks
- Warn user in Unicode dialogs if character is "recently added" to Unicode

### Bug Fixes

- Using `$` and `^` in regexes did not match end/start of line
- Some regex matches overlapped with the previous match
- Searching forward/backward did not always find the same matches - now does
  so, except in very rare case.
- `\C...\E` to execute bad Python code caused a traceback - now errors tidily


## Version 2.0.0-alpha.6

- Unicode & Commonly Used Characters dialog added
- Find All results improved for multiline matches
- Bad regexes in S/R dialog turn red as user types them

### Bug Fixes

- `Ctrl-left-click` in Basic Fixup caused an error
- S/R dialog kept resetting to a narrow width on Macs
- Searching for the next match in S/R didn't highlight correctly
- S/R regex count with backreferences didn't count correctly
- Replace All didn't work for all regexes
- Searching backwards for regex with backreference didn't work
- `^` didn't match beginning of all lines correctly
- Find Next/Previous key bindings (`F3`/`Cmd+g`) were executed twice
- Trying to use a bad regex caused an error - error now reported correctly
- Dock/Undock Image Window caused an error
- Compose sequence failed to insert some characters, e.g. non-breaking space
- Trailing hyphen appeared in title bar when there was no filename


## Version 2.0.0-alpha.5

- "Join Footnote to Previous" added to Footnote Fixup
- Status bar "current character" box now shows the selected character if
  exactly one character is selected, and nothing if more than one is
- Windows and Chromebook user installation notes added to README
- Navigation in Word Frequency dialog improved: Home & End keys go to
  start/end of list (Cmd Up/Down on Macs), Arrows and Page Up/Down
  scroll list, and typing a character jumps to the first word that 
  starts with that character, similar to GG1
- Levenshtein-based "Word Distance Check" added
- Search/Replace fields use same font & size as main window
- View-->Full Screen mode added (except on Macs)
- More powerful regex search/replace 
- `\C...\E` allows Python code to be run in regex replace
- Improved positioning of page breaks during multi-line regex replacements

### Bug Fixes

- Cursor wasn't placed consistently if user pressed left/right arrow while
  some text was selected. Now cursor goes to left/right of selection
- Footnote not processed correctly if not at start of line, e.g. after
  proofer's note
- Jeebies paranoia level radio buttons unexpectedly re-ran the tool
- Line number of current line wasn't always highlighted if a search
  changed line but didn't cause a scroll
- Compose sequence inserts didn't remove currently selected characters first
- Search dialog could get popped but without focus in the Search field,
  making it awkward to copy/paste the search string
- Lookahead and use of word boundary caused search strings not to be replaced


## Version 2.0.0-alpha.4

- Command line argument `--nohome` added which does not load the prefs file.
  This is primarily for testing purposes.
- Highlighted text in checker dialogs now uses the same colors as selected
  text in the main window.
- Text spotlighted in the main window by clicking on an error in a checker
  dialog is now highlighted in orange, rather than using selection colors
- Unmatched DP Markup now only checks for `i|b|u|g|f|sc`
- After fraction conversion, the cursor is placed after the last fraction
  converted, so it is clearer to the user what has happened
- The Spelling checker now supports spellcheck within selected text only
- The Spelling checker now has a threshold - if a word appears more times
  than the threshold, it is assumed to be good
- Unmatched Brackets and Curly Quotes now have a checkbutton to allow or
  disallow nesting
- A "working" label appears in checker dialogs when a tool is re-run, rather
  than showing "0 Entries"
- In the line numbers on the left, the number corresponding to the cursor's
  current location is highlighted 

### Bug Fixes

- Default scan directory `projectID0123456789abc_images` was not supported
- Errors occurred saving preferences if user's Documents directory was not
  in their home folder on Windows
- Page Separator Fixup started auto-fixing immediately if user changed
  radio buttons to Auto instead of waiting for user to click Refresh
- Additional blank lines were added during rewrapping
- After rewrapping a selection, the wrong range was selected


## Version 2.0.0-alpha.3

- Page Marker Flags now include the necessary information to generate the
  page labels, to improve transfer between GG2 and GG1 (v1.6.3 and above)
- Improved text rewrapping using Knuth-Plass algorithm (like Guiguts 1)
- Go to Img number no longer requires leading zeros
- A "Working" label and, on some platforms, a "busy" cursor now indicate
  when Guiguts is busy working on a long task.
- When user selects an entry in the Page Label Config dialog, the cursor
  jumps to the beginning of that page. If Auto Img is turned on, this will
  also show the scan image for that page
- If the full path to the text file is very long, its display in the title
  bar is truncated so that the name of the file is still visible

### Bug Fixes

- Cursor was not always visible after pasting text
- Word Frequency Ligature report included words that were not suspects
- Word Frequency Ital/Bold report is now sorted the same way as Guiguts 1
- Word Frequency Hyphens only reported the non-hyphenated form as suspect, 
  rather than both forms
- Unmatched quote check included some single quotes that were clearly
  apostrophes
- PPtxt was over-sensitive when reporting words appearing in hyphenated form
- Page Separator Fixup was leaving the page mark mid-word when a hyphenated
  word was joined
- Large files took far too long to load due to Page Marker Flags code


## Version 2.0.0-alpha.2

- Font family and size selection in Preferences (Edit menu)
- Highlight quotes in selection (Search menu)
- Additional Compose Sequences added (Cmd+I/Ctrl+I) such as curly quotes, 
  degrees, super/subscripts, fractions, Greek, etc. List of Sequences
  (Help Menu) allows clicking to insert character. 

### Bug Fixes

- Ignore Case in Word Frequency stopped options such as ALL CAPS from working
- Main window size and position didn't work well with maximized windows


## Version 2.0.0-alpha.1

First alpha release, containing the following features:
- Status bar with line/col, Img, Prev/See/Next Img, Lbl, selection, language,
  and current character display buttons
- Go to line, image, label (click in status bar)
- Restore previous selection (click in status bar)
- Change language (click in status bar)
- Line numbers (shift-click line/col in status bar)
- Normal and column selection supported for most operations
- Configure page labels (shift-click Lbl in status bar)
- Built-in basic image viewer (View menu)
- Auto Img (shift-click See Img in status bar)
- Recent documents (File menu)
- Change case features (Edit menu)
- Preferences (Edit menu, or Python menu on Macs) for theme, margins, etc
- Search & Replace (Search menu) with regex, match case, etc. Also, limit
  search/replace to current selection
- Count and Find All search features
- Bookmarks (Search menu, and via shortcuts)
- Basic Fixup (Tools menu)
- Word Frequency (Tools menu)
- Spell Check (Tools menu)
- PPtxt  (Tools menu)
- Jeebies (Tools menu)
- Fixup Page Separators (Tools menu)
- Fixup Footnotes (Tools menu) - begun but not complete
- Rewrap (Tools menu) - using "greedy" algorithm
- Unmatched Markup features  (Tools menu)
- Convert Fractions (Tools menu)
- Normalize Characters (Tools menu)
- Add/Remove Page Marker Flags (File-->Project menu) for transfer between
  editors
- Compose Sequences (Tools menu, and via Cmd+I/Ctrl+I shortcut) - only
  accented characters and Unicode ordinals. List of sequences (Help Menu)
- Message log (View menu)
- Command line arguments: 
    - `-h`, `--help`: show help on command line arguments
    - `-r1 (or 2...9)`, `--recent 1 (or 2...9)`: load most recent
      (or 2nd...9th most recent) file
    - `-d`: debug mode, mostly for developer use