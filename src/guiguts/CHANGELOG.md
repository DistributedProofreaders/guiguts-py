# Changelog


## Version 2.0.14

- "Match Case" is turned on in S/R dialog when launched from Stealth Scannos
or Regex Library
- Jeebies no longer reports "he’s", "he’d", etc., as suspects
- PPtxt no longer reports certain number/letter combinations, e.g. "12th",
nor mixed-case hyphenated words, e.g. "Mary-Anne"
- Bookloupe no longer reports standalone 1 for "£1" or "$1" or "[1]" , nor
certain combinations of letters, punctuation, and apostrophe, e.g. "C.’".
- Word Frequency Hyphens check has been upgraded to deal with asterisks,
e.g. "to-*day": such words are always reported as Suspects; they are also
passed correctly to the Google Ngrams viewer
- Stealth Scanno checks relating to uppercase characters following commas,
and lowercase characters following periods have been updated to select the
whole of the word, thus improving alphabetical sorting
- Auto-Illustrations and HTML Images dialogs are now separate dialogs,
allowing both to be visible at the same time
- Version number in this Changelog is not checked for pre-releases, which
is useful for developers and bug-fixing

### Bug fixes

- The orange border round the Internal Image Viewer sometimes flashed even
when Auto Img was turned off
- Especially on Windows, filenames could end up appearing twice in the dropdown
menus in Stealth Scannos and Regex Library
- Keyboard navigation did not store selection anchor positions correctly,
meaning Shift-Click did not select all the expected text
- External Image Viewer was run twice for every image if Fit-to-Height/Width
was turned on in the Internal Viewer
- IrfanView on Windows would not work as an External Image Viewer due to a
conflict between forward- and back-slashes


## Version 2.0.13

- HTML Image dialog now has "Decorative only" checkbox which adds
  `data-role="presentation"` to the illustration HTML
- Toolbar icon size can now be changed in the settings dialog
- Image Prev/Next buttons in the image viewer are now available via the
  Command Palette, and can thus have shortcut keys assigned
- PPhtml tests that fail are now highlighted in red
- Default CSS for the `center` class now forces `text-indent` to zero
- Check if user wants to proceed if the current Fix/Remove action in a dialog
  would affect over 1000 messages
- Curly Quote Check now only reports one error per quote

### Bug fixes

- Unicode Fraction Convert changed `7/8` to `⅝`
- Poetry lines ending with double-hyphen emdashes could be wrongly joined
  across page boundaries
- Title-casing words with apostrophes did not work correctly
- Auto-Illustration would add an extra `<p>` to right-aligned captions
- Pressing Return/Enter in Command Palette sometimes did nothing or gave
  an exception


## Version 2.0.12

- Spelling check suggestions are displayed much more quickly
- Spelling check suggestions can be turned off in Settings, Advanced tab
- Newlines are preserved in HTML source after using Auto-Table 

### Bug fixes

- Goto Page and similar small dialogs interpreted leading-zero numbers as
  octal. and didn't respect GG theme on some platforms


## Version 2.0.11

- Content Providing Dehyphenation tool automatically flags with asterisk if
hyphen(s) appear at start of page, in addition to end-of-page hyphen(s)  

### Bug fixes

- Selecting blank lines beyond the end of a table caused HTML AutoTable to
duplicate some of the lines of the table
- Line spacing setting was not used correctly when drawing line numbers,
meaning they could become misaligned with text
- Busy cursor and "Working" label were left showing when last message was
removed from a checker dialog
- PPtext could give an exception if a line consisted solely of numbers


## Version 2.0.10

- View Menu now has Soft Wrap (Word) button which wraps the lines in the
  file at a word boundary so that the whole line is visible - not related
  to standard text wrapping
- The Hide All button in the Find All dialog now hides all matching
  occurrences of the match, rather than only matching lines 
- PPtext now has a verbose flag, which doesn't restrict the number of reports
  to 5 with a "more..." message
- Astral plane characters (i.e. not in the Unicode Basic Multilingual Plane)
  now get a warning icon in the Unicode dialogs
- Content Providing, Olde Englifh dialog now has "swap" buttons to make it
  easier to fix ambiguous or unknown cases
- Script added to update GG2 manual index page (developer use only)

### Bug fixes

- When there were multiple anchors for a footnote, reindexing could corrupt
  the footnote number with duplicate strings
- Duplicate Roman footnote anchors were not detected correctly
- Masking a footnote type could interfere with subscript markup - now uses
  double curly braces
- Unmatched HTML Tag check did not cope if there was a line break inside
  the open tag
- Hide All button didn't show "working" label

## Version 2.0.9

- Spellings dialog now suggests corrections for bad spellings. User can Fix
  one occurrence, Fix All, or Fix & Hide (All) to fix the spelling(s) and
  remove from the list
- The Spellings dialog now resizes in such a way that buttons remain visible
- Search/Replace dialog tooltips added to inform user about Shift-clicking 
  buttons to search in opposite direction, and replace identical matches only
- Shift-clicking Highlight All in Search/Replace dialog removes previously
  added highlighting
- When using File-->Include File, `.css` files are shown in the load dialog
  as well as text and html files
- The load file button icon in the image viewer has been improved 

### Bug fixes

- Word Frequency reporting of the number of hyphen and accent suspects was
  inconsistent
- A lookbehind followed by a space in a regex caused replacements based on
  that regex to fail
- The tooltip in the Content Providing Filter dialog was incorrect
- On some Mac systems, the Image dialog was truncated - now resizable
- Debugging using VSCode with Python 3.13/3.14 gave an error 


## Version 2.0.8

- Spelling dialog now supports Sort by Frequency
- Support for Google Books Ngram Viewer moved from Custom Menu to Tools menu,
  with support for additional parameters, and automatic inclusion of
  non-hyphenated version if hyphenated word is selected
- Parameters to pass to Google Ngrams, such as language or corpus selection,
  can be entered in the Settings Dialog, Advanced tab
- Support for Google Books Ngram Viewer added to Word Frequency with inclusion
  of hyphenation variants: use Shift-Cmd-Click or Shift-Ctrl-Click
- CP English Scannos now displays changes that will be made giving user chance
  to review/remove unwanted changes before fixing remainder
- CP Header/Footer tool allows multiple fixes to the same page to support
  removal of multi-line headers/footers
- CP Filter changes now reported in more detail, either as a summary or in
  verbose mode listing every changed line
- CP List Good Words feature added to support easy word entry at DP
- CP Filter now runs about 5 times faster
- PPtext now runs about 25% faster
- PPhtml now warns if the `h1` and `<title>` forms of the title text differ
- Improve masking support for nested footnotes of differing styles
- Soft Hyphen added to Commonly Used Characters dialog
- No longer report all numeric "words" as hyphenation suspects in WF
- Documentation updated to describe use of icons in Windows user installation
- Documentation updated for CachyOS developer installation 

### Bug fixes

- Cmd/Ctrl-clicking a word in Spelling dialog could add wrong word to project
  dictionary
- Regex library `italic_semantic` `cite` markup had a trailing space
- GG2 occasionally displayed an exception when program was quit
- GG2 did not install cleanly under Python 3.14 on Windows systems


## Version 2.0.7

- Guiguts can now be run under Python versions from 3.11 to 3.14
- Footnotes can now be reindexed beginning at 1 for each landing zone
  (typically restarting for each chapter)
- Footnote Fixup now detects if there are multiple anchors for the same
  footnote, displaying them in the dialog and reindexing them correctly
- New checkbox in Settings, Advanced tab, causes footnote anchor and footnote
  text to be displayed in the two windows when Split Text Window is on
- Support for multiple footnote styles in a file added, e.g. Numbered and
  Roman: Mask/Unmask Footnote Styles submenu allows "masking" of one style
  while another style is processed with Footnote Fixup (by changing the open
  square bracket to curly); unmasking does the reverse
- More than one class can now be entered in fields in HTML Markup
- A new `--resetgeometry` command line argument has been added, which resets
  the size and position of the main window and all dialogs to their default
  values - primarily intended for when on-off use of multiple screens ends up
  with dialogs being displayed "off-screen"

### Bug fixes

- Where two mid-paragraph illos followed one another, they were sometimes not
  flagged as mid-paragraph, or the first of two illos might be flagged as
  mid-paragraph when it wasn't
- HTML Markup didn't add quotes round a single class name
- PPhtml reported errors in CSS that was within comments
- Control-clicking to fix quotes in Curly Quote check was broken


## Version 2.0.6

- Word Frequency now has a Mixed Script check that will report errors such as
a word with Latin characters that also contains a Greek character
- The headings in the Command Palette list of commands can now be clicked to
sort the commands by Command name, Shortcut, or Menu - this could be useful to
check which shortcuts have not been assigned yet
- When a tooltip is shown, after a 7 second delay it is hidden again
- Some Stealth Scanno regexes have been improved
- Auto-Illustration now finds the first `[Illustration]` tag following the
cursor, and `Find Next` finds the next tag following the cursor

### Bug fixes

- Footnotes were not indexed correctly if a proofer note preceded the footnote
- Some compose sequences for accented Greek letters with breathing were wrong
- `/*`, `/c`, and `/r` markup in a chapter heading caused HTML auto-generation
to give an incorrect error
- When AutoSave was turned on, the "Working" label sometimes changed to red,
and didn't return to white
- Auto-illustration did not detect `[Illustration]` markup if it was enclosed
in `<div>` markup


## Version 2.0.5

- Fix installation problem relating to `packaging` module


## Version 2.0.4 (Faulty)

- Display a "Did You Know...?" tip when Guiguts starts. Can be configured to
  show once a day, once a week, or never - also accessible via Help menu
- Display Release Notes when a new release of Guiguts is first started - also
  accessible via Help menu
- Multiple replacements can now be added for a regex in Regex Library - these
  will be shown in the S/R dialog when Regex Library's Replace is Shift-clicked
- Default directory when selecting the project's scan directory is now the
  project directory
- Regex handling defaults to permit advanced features such as character set
  differences, e.g. `[a-z--c-t]`
- Order of Content Providing menu switched to better match process order
- Content Providing Dehyphenation has color coded Keep/Remove label
- Dehyphenating number ranges Keeps rather than Removing hyphen
- Content Providing header/footer detection improved to catch the case of a
  page number and book/chapter title
- Footnote anchors can now be escaped with backslash, e.g. `\[1928]`
- Curly Quote Fixup buttons made narrower to fit better into dialog
- Unmatched HTML Tags check has been sped up
- Instructions for installation on Fedora Linux were added to the README

### Bug fixes

- Mid-paragraph illos were not detected when the text after the illo began
  with a lower case letter
- Re-run with Suspects in Illo/SN fixup did not re-select the correct message
- Word Frequency Diacritics check did not spot suspects if the accented
  character was `ä`, `ö`, or `ü`
- Whole Word regexes involving `|` for alternation sometimes failed
- Column ruler was not precisely aligned
- `Preserve Illo's Page Number` setting was inadvertently being applied to
  Sidenote Fixup
- `View HTML in Browser` in Custom Menu had an incorrect command for some
  flavors of Linux
- On macOS, "border" icon in Settings-->Colors tab was a filled square instead
  of a square border
- Editing a Custom Menu entry could cause an exception
- Slow footnote operations did not show the "Working" alert
- `Text-->Convert <sc> Manually` sometimes did not set the number of
  replacement fields correctly in the S/R dialog
- Reindexing when there were unpaired footnote anchors could cause an exception
- Some menu buttons were missing `...` to indicate that additional input is
  required before the operation can be completed
- Hotzones of some checkboxes were too wide
- Block Rewrap Selection didn't respect blockquote right margin
- Missing Scanno/Regex Library file caused dialog to be lost behind main window


## Version 2.0.3

- Manage Character Suites in the Content Providing menu allows the user
  to select which DP char suites are used in the project
- Highlight WF Chars not in Selected Suites in the Content Providing menu
  highlights characters in the WF Character Count display if they are not
  in selected character suites
- CP Renumbering has been improved
- CP Header/Footer reports are more detailed
- "All⇒Remove" and "All⇒Keep" buttons have been added to Dehyphenation
- CP Fix Common Scannos is now labelled "Fix Common English Scannos"
- Several CP features now report how many changes were made
- Ctrl+Delete/Backspace (Option+Delete on Macs) deletes a word
- Replace [::] With Incremental Counter (like GG1) added to Search menu
- Optionally, `h3` markup can be added to section headings during HTML
  autogeneration
- "/L[3]", for example, is now accepted as list markup during HTML conversion
- Block Rewrap Selection has been added to Tools menu
- Directory used to load/save files or choose directories is remembered
  between uses of the load/save/choose dialog
- PPhtml now reports unconverted italic words in underscores
- Bookloupe no longer reports missing punctuation at end of quotes if there
  is punctuation immediately following the close quote
- Ebookmaker (API) timeout has been increased to give large books time to
  be processed

### Bug fixes

- CP Dehyphenation used some tests that were specific to English, even when
  English was not one of the project languages
- Using "Undo" after Dehyphenation Fix All, only undid one at a time 
- Import Prep Text Files gave an exception if files were Latin1-encoded
- Drag selected text got confused if NumLock was turned on
- Alt+drag did not work for column select on Linux (replaced with Ctrl+drag)
- Ctrl+A did not work in some text entry fields on Linux
- Using Redo after rewrapping moved the cursor to the start of the file
- Rewrapping an index multiple times caused cumulative indentation
- Find Next/Previous did not respect the "Reverse" flag in the SR dialog
- Word Frequency did not search correctly for italic words in underscores
- Some combinations of accented words were not reported correctly as suspects
  by Word Frequency Diacritics check
- Some text entry widgets did not follow the Dark/Light theme setting if the
  OS theme was different
- Automatic theme changing to match the OS theme was broken
- If Find All was re-run with S/R dialog not shown an exception occurred
- If an internal error gave an exception, the busy cursor remained on
- IDs on h2/h3 headings were not necessarily unique


## Version 2.0.2

- A Content-Providing menu supplies functionality equivalent to that provided
  by the Perl guiprep tool.
- Add `viewport` meta tag to default HTML header to improve rendering of
  books on narrow-screen devices. Add option to HTML AutoTable to wrap
  wide tables in a div with `overflow-x: auto`
- Tear-off menus are now available on all computers: previously they were not
  supported on Macs, but "Custom Tear-Offs" work on all systems
- Empty paragraphs are removed from Autogenerated HTML
- Double blank lines are retained during HTML Autogeneration to make it easier
  to locate section headings

### Bug fixes

- Illos could sometimes be marked as mid-paragraph when they were not, or not
  identified as mid-paragraph when they were
- Commands sometimes experienced a delay when run on macOS systems, especially
  if run via the Command Palette
- The Recent Files menu was not correctly updated if there were not already
  10 filenames listed
- On some platforms, e.g. some Linux systems, typing to jump to a message in
  Word Frequency and checker dialogs did not work with NumLock or ScrollLock 
- Page Up and Page Down moved a different number of lines
- The "comma, UPPERCASE" regex scanno did not sort correctly alphabetically
- Using a bookmark when there was a selection did not clear the selection,
  leading to the cursor position being incorrect
- Long lines had inter-word spaces removed when it was centered
- Copies of original table lines could be left behind after Multiline Autotable
- PPhtml sometimes incorrectly reported the location of a defined-not-used
  class
- Combining word boundary and non-greedy capture in a regex could cause the
  replacement to fail
- Checker Re-run buttons did not show the "Working" label
- If the ebookmaker directory was incorrect, the dialog was hidden behind the
  main window, making it difficult to find 
- In an index, pagenum spans were sometimes placed illegally
- Home key did not cause window to scroll to the start of the line
 

## Version 2.0.1

- A message bar at the bottom of the main window displays the latest message
  for several seconds. An example is a message reporting how many fixes were
  made using Fix All in a checker dialog.
- A toolbar containing common buttons appears next to the message bar. The
  toolbar contains Load, Save, Undo, Redo, Cut, Copy, Paste, Search/Replace,
  Go Back, Go Forward (see below), and Help.
- Go Back and Go Forward have been added to the Search menu. These are similar
  to the back/forward buttons in a browser, going back to previous locations
  in the file. Each time the cursor is moved via a search, or by clicking on 
  a checker message, the current location is saved into the list that is used.
- A regex library has been added. This works in a similar way to scannos, using
  a file of regexes and replacements, but can be used for any replacements,
  not just scannos. One file is supplied, `dashes.json`, which helps with
  conversion of hyphens to more specific dashes. Users may add their own files
  to the library.
- "Search" within Word Frequency has been improved and extended to all checker
  dialogs. Instead of just being able to type a single character, e.g. "G" to
  jump to the first entry in the list beginning with "G", you can now type
  part or all of a word, in a similar way to Windows File Explorer or macOS
  Finder. If several characters are typed with no delay, they are treated as
  a search term. After a delay, the search term is reset. In checker dialogs,
  the default is to search the beginning of the message, or by enabling
  "Full Search", to search anywhere in the message. Example: run pptext, then
  type "ellipsis" in the dialog to jump to the ellipsis test results.
- A similar feature has been added to the Unicode Block dialog. The string
  typed can be the beginning of any word in the block's title. Alternatively,
  if you type the start of a 4-digit Unicode codepoint, it will jump to the
  block that contains that character, e.g. knowing that open single quote
  is `U+2018`, typing `201` will jump to General Punctuation, which has the
  range `2000-206f`. 
- Shift-clicking the Replace All button in the S/R dialog replaces all 
  "identical" matches to the current match. An example would be to search for
  words in italic markup, then if a LOTE word is found, all occurrences of
  that LOTE word can have a `lang` attribute added.
- Shift-clicking the Replace button in the Scannos dialog pops the S/R dialog
  pre-populated with the search and replace fields.
- View Options has been upgraded to make it easier to view messages one type
  at a time. Using Next Option will select the next available view option,
  and display messages of that type. Previous Option goes to the previous
  view option. Next/Previous respect the setting of "Grey out options with
  no matches".
- Illustration Fixup has a new button to "Preserve Illo's Page Number". If
  enabled, when moving an illo would take it across a page boundary, the
  page break locations are adjusted to keep the illo's page number the same.
  This is equivalent to keeping the illo where it was and moving the text
  around it. 
- Fix, Fix All, Hide, and Hide All buttons have been added to Scannos dialog.
- Selected text can now be dragged to another location in the file. If an 
  attempt is made to drag outside the screen, the selection may look incorrect
  until the text is dropped at the current mouse location. It is not possible
  to drag between the two split text windows.
- Holding one of Ctrl/Cmd/Shift modifier keys while dragging will copy
  selected text instead of moving. Dragging can be cancelled with Escape key.
- Any dialog may be "pinned", meaning that it will remain in front of the main
  window (not available on Linux). When pinned, a pin is shown in the title
  of the dialog. The current dialog may be pinned using Pin/Unpin Dialog in
  the View menu, or by right-clicking the dialog in an area where right-click
  is not normally used, i.e. most of the dialog except a list of messages.
  When you unpin a dialog, the title bar will say that it will be unpinned
  when it is next closed. Pinned dialogs are linked to the main window, so
  are raised, lowered, or iconized with the main window.
- Vowels with macros and vowels with breves have been added to the Common
  Characters dialog.
- "Include File" has been added to the file menu to insert a file at the
  current location.
- Footnotes ending in `...]*` are now marked as "CONTINUED" in Footnote Fixup.
- Regexes now support `\N` which converts a matched Roman numeral string
  (optionally including spaces) to a regular, Arabic number. This is to
  support adding `abbr` markup, e.g. `<abbr title="8">VIII</abbr>`.
- Support for curly quote conversion in HTML files has been added via Protect
  and Restore HTML Straight Quotes, which protect straight quotes used within
  HTML elements by replacing them with an obscure character, like the online
  ppsmq tool. Normal curly quote conversion can then be run, and the quotes
  restored once this is complete.
- Compose Help dialog can now be sorted by clicking in the header of any
  column. Clicking again reverses the sort.
- The verbosity of more sections of the pptext report has been reduced.
- HTML tags are now stripped from the selected text passed to a Custom command
  with the `$t` token.
- The `blockquote` element is used for blockquotes instead of a `div`.
- Chapter `h2` markup is closed if poetry is detected in header.
- Pressing Home or Cmd-Left already moved the insert cursor to the start of
  the current line. Pressing it again will now move to the first non-space
  character.
- PPhtml checks music files in a similar way to image files.
- PPhtml no longer reports `www.w3.org` links in the HTML header.
- Shadow command for "delete next character" added to Command Palette.
- "Highlight Surrounding Quotes & Brackets" now ignores apostrophes that are
  surrounded by letters.
- Default CSS for gesperrt has been improved, including a fallback for epub2.

### Bug fixes

- Using the Recent Files menu, and possibly other methods of loading a file,
  could make Guiguts crash instantly and silently.
- Music files were not zipped up to send to ebookmaker.
- If the user ignored the red "bad regex" indication in the S/R dialog and
  searched for the regex, an exception occurred.
- Block markup around the book title could cause an error during HTML
  generation.
- The default HTML header had a minor incorrect indentation


## Version 2.0.0

### Bug fixes

- Unicode Block dialog characters were displayed in the wrong font
- Hebrew paste feature always pasted into main text window
- One-line sidenotes were converted incorrectly to HTML
- Png filenames containing hyphens caused a Page Separator Fixup exception
- PPhtml gave incorrect locations for some unused CSS classes
- PPhtml reported multiple links to an id as a failure, not a warning
- Block markup around book title was handled badly by HTML autogeneration
- HTML autogeneration did not add chapter div when block markup preceded
  by 4 blank lines 
- Undoing Replace All from the S/R dialog only worked one change at a time


## Version 2.0.0-beta.3

- Font used for labels, buttons, etc., can now be configured - Mac users
  need to restart Guiguts to see the full benefit
- HTML Links, Anchors and Images can now be added via the HTML menu
- Auto-List added to HTML menu
- Search/Replace dialog can now have up to 10 replacement fields
- Bookmarks now save and restore the current selection
- Replace Match added to Search menu
- Revert/Reload from Disk added to File menu
- CSS classes listed by PPhtml are now sorted
- Fix/Hide All in Basic Fixup now fixes/hides all errors of that type
- Up/Down buttons added to checker dialogs and related commands added to
  Command Palette
- Convert & Find Next button added to Auto-Illustration dialog
- PPtxt has been made significantly less verbose, not reporting several
  things that PPers do not require
- Size grips added to bottom right of checkers and similar dialogs, for
  easier resizing
- Switch Text Window command added to Command Palette
- Recent Files 1, 2 & 3 added to Command Palette
- Delete To End Of Line added to Command Palette
- TIA Abbyy import added to Content Providing menu
- Movement of Illustrations/Sidenotes is now more flexible
- Dutch, Portuguese & Spanish language dictionaries added to release
- Custom commands on Windows that do not use the "start" command will now
  display their results in a command window
- PPtxt no longer reports straight quotes if all quotes are straight
- HTML link checker no longer reports page breaks as unused anchors
- Less strict option for Curly Quote conversion added
- Footnote anchors tied to previous word with Word Joiner character
- Stealth Scanno buttons reorganized for ease of use
- HTML generator uses the dialog's title field to facilitate h1 markup
- HTML generation of chapter headings improved, including dialog option
- Footnote sorting using Alpha/Type has been improved
- Different methods to add words to project/global dictionaries now all
  work the same as one another
- Highlight All highlights are now removed when S/R dialog is closed
- Generated HTML is indented to improve ease of reading
- To reduce cross-platform differences, File-->Exit is named Quit, and
  Preferences is named Settings at the bottom of the Edit menu
- Use of paragraph markup in illustration captions is now optional
- Word Distance entries separated more clearly
- WF Diacritics label clarified
- Curly Quote messages have been shortened for ease of reading
- Checker dialog header layout adjusted to reduce required width
- Unnamed files can no longer be converted to HTML
- If a non-UTF8 file, or one containing a BOM, is loaded, an error is reported
- Installation notes improved and clarified

### Bug fixes

- Deleting a proofer comment could delete a previous fix
- Deleting a proofer comment could leave a double space behind
- Jeebies erroneously reported he/be occurrences that were not lowercase
- HTML autogen used paragraph markup for pagenums within list markup
- Nested square bracket within footnote was not reported, confusing Fixup
- Apply Surround Selection command did not work if dialog was dismissed
- Word Frequency failed to find locations of some "words"
- Word Frequency did not allow some keyboard shortcuts to work
- Pre-existing HTML markup was broken during HTML generation
- Unpaired footnote anchors were not reported
- WF and checkers could cause exception if closed while in progress
- Custom dialog had incorrect example for $s
- Nested footnotes could cause re-indexing problems
- Default command to open a URL did not work on all Linux systems


## Version 2.0.0-beta.2

- Almost all colors used by GG can now be customized by the user via the
  Preferences dialog; colors may be set for the dark theme or light theme
- Alignment options added to Text menu: Center, Right Align, and
  Right Align Numbers
- GG-specific extended regexes added: `\U` uppercases, `\L` lowercases, 
  `\T` titlecases, `\A` creates a hyperlink, `\R` converts to Roman numerals
- GG2 now has the ability to store (using cset) and retrieve (using cget)
  persistent variables when using `\C...\E` to execute python code, similar
  to the use of `lglobal` in GG1
- HTML markup dialog added to HTML menu
- `Convert <sc> Manually` added to Text menu
- Basic Fixup now has View Options so that messages of one type can be
  hidden or shown
- New `Content Providing` submenu of File menu has three functions:
  Export as Prep Text Files, Import Prep Text Files, CP Character Substitution  
- Browse button in image viewer allows user to load any image file
- Scrolling during select-and-drag operations and within image viewer is now
  smoother, particularly on Macs
- In Page Labels configuration dialog, user can now click in the Img and Label
  columns to select the label and jump to the page break in the text file
- Image viewer can now be docked on the left or right of the text window
- View Options dialogs have checkboxes spread evenly across columns
- The busy cursor and "working" label now show during file saving operations
- Spellcheck, Bookloupe and PPtext now ignore page separator lines, ppgen
  command lines, and ppgen comment lines
- Illustration/Sidenote fixups now sound the bell if an attempt is made to
  move an illo/sidenote past another one
- Focus ring around the currently-focused button or other user interface
  control made more visible, especially in dark mode
- Mac installation instructions improved
- Some minor improvments to the wording and case of labels and buttons
- Running `guiguts --version` prints the current Guiguts version number
- New test suite auto-runs some tools and checks the results

### Bug fixes

- Prev/Next Footnote buttons did not work if an anchor line was selected
  in the dialog rather than a footnote line
- HTML autotable sometimes mis-selected the table causing a line to be lost
  or duplicated
- During HTML generation, `<p>` markup was wrongly added around `pagenum`
  spans inside poetry
- Scan images that were stored as palettized or RGB files were never inverted
  in the image viewer
- Illustration Fixup sometimes corrupted Illustration markup when attempting
  to move an illo upwards past an illo block containing blank lines
- HTML generation exited with a fatal error if the file began with `/#` markup
- Mousewheel scrolling in image viewer was broken for Mac users
- PPhtml reported double hyphens in comments in the CSS style block
- PPhtml did not recognize valid DOCTYPE declarations if case was unexpected
- On Linux, Shift-tab did not work correctly to change which user interface
  control had focus
- Some checkboxes in the S/R dialog were wider than needed, so users might
  click them in error, thinking they were clicking in some empty space


## Version 2.0.0-beta.1

- Indent +1/-1/+4 Spaces added to Text menu
- Commonly Used Characters added to Unicode menu - also available using
  Shift+Left-click on status bar character button, with Shift+Right-click
  opening the Unicode Block dialog
- Search/Replace dialog now has "Highlight All" button, which is a more
  powerful version of GG1's "Highlight Char, String & Regex"
- Unicode and Commonly Used Characters display the name of the character
  being hovered overin the dialog, plus a large copy of the character
- Image scroll and zoom commands added to Command Palette so user can
  define keyboard shortcuts
- Tab and Shift+Tab can now be used to navigate to any button or checkbox
  within the main window and all dialogs, to improve accessibility, meaning
  almost everything within Guiguts can be accessed via the keyboard
- Shift+Return operates the Apply button in OK/Apply/Cancel dialogs
- Applying the contents of the "Surround Selection With" dialog is now in
  the Command Palette so can be assigned a keyboard shortcut
- Word Distance Check can now be configured to ignore words with digits
- A few improvements to Stealth Scanno regexes
- Word Frequency navigation resets to start of file after last match is
  found (like GG1); Shift-clicking navigates backwards through
  word occurrences
- Word Frequency Hyphens check, "Two Word" matches are now optional
- PPtxt reports multiple repeated words on one line with just one message
- Proofer comment markup added to "Surround Selection With" Autofill button 
- The Curly Quote check exception to ignore a missing close quote if the
  following paragraph begins with an open quote has been made optional
- When running ebookmaker, user can now control whether they want to create
  EPUB2 files or not
- Small changes to support use of Python 3.13, and README updated to warn
  Mac users about Homebrew-installed Python 3.12 or later
- Touchpad scrolling support for Tk9 added 
- `-p` or `--prefsfile` command line argument can be used to give the basename
  of a preferences file instead of `GGprefs` - for development/testing
- File-save check is omitted in debug mode - for development/testing

### Bug fixes

- User was not warned about using Alt+key as a user-defined shortcut when that
  combination opened a menu on Windows/Linux, e.g. Alt+F for the File menu 
- Bookloupe reported `123.png` as a word containing a digit
- In Word Frequency, clicking on a "word" that began with a non-word character
  but ended with a word character, e.g. `*--the` didn't display the word
- WF reported `Joseph-Marie`, `MacDonald`, `E.g.`, etc. as Mixed Case words
- WF did not ignore ppgen page break commands or comments
- PPhtml failed to spot the charset definition in non-HTML5 files
- Theme queries failed when using Tk9
- OK/Apply buttons in Configure Page Labels did not show whether there were any
  changes to apply
- If Undo/Redo were used from the Edit menu while use Page Separator Fixup, the
  current separator was not re-highlighted
- Adjusting the indent of an ASCII table did not work correctly if the "Rewrap"
  setting was enabled
- Illustration Fixup failed to handle proofer comments inside illo markup
- Bookloupe did not report lower case after period in quotes
- PPtxt did not report a repeated word across a line break in indented text
- PPtxt reported multiple repeated words incorrectly
- PPtxt reported close curly quotes being used as ditto marks as "spaced"
- PPtxt sometimes reported `0` and `1` in decimal numbers as "standalone"
- PPtxt didn't report a potential hyphenated/unhyphenated error if the hyphen
  was at the start or end of the word
- PPhtml reported a cover image over 1MB as an error, not a warning

## Version 2.0.0-alpha.20

### Bug fixes

- Command Palette Edit button gave an exception error message


## Version 2.0.0-alpha.19

- User can define keyboard shortcuts for any menu command as well as several
  other commands that are not in menus. Use Help-->Command Palette, then 
  Edit Shortcut. 
- Ebookmaker can now be run via API without installing it on local computer,
  thus always running latest version installed at PG
- Scan images can now be rotated in the image viewer, with the rotation saved
  permanently per image rotated
- Several improvements to Stealth Scannos: auto-starts immediately; 
  auto-advance checkbox added; search/replace fields are editable; button
  to swap search/replace terms; bad regexes are trapped and reported;
  current and total scanno number displayed; Replace All button fixes all
  issues in the list
- "Surround Selection With" feature added to Edit menu, including autofill
  for closing markup
- Current image name is now displayed in the internal image viewer
- Error messages triggered during file saving are more helpful
- Unmatched Curly Quotes removed due to duplication of features, with its
  unique features added to the Curly Quotes Check
- WF emdash check now includes Unicode emdash characters as well as double
  hyphens, and now ignores intervening punctuation correctly
- PPhtml no longer reports landscape covers with warnings
- Checker dialog no longer forces focus to main window on Windows/Linux

### Bug fixes

- High Contrast label was missing from Preferences dialog
- Page Separator Fixup attempted to join pages with trailing footnotes, but
  failed to do it correctly
- It was not possible to select a leading vertical table line in column 0
- Proofer comment undo also undid user's edits
- WF Hyphen check didn't respect the "case" flag
- Bookloupe wasn't splitting words joined by emdash correctly
- ASCII tables didn't highlight correctly if at top of file
- Closing block markup was sometimes not detected at page breaks
- Superfluous `<br>` and `<p></p>` were sometimes output by HTML generator
- PPgen files were marked as edited when loaded, due to page number commands
- Footnotes were not wrapped when tidied
- Known bugs relating to Tk version 9 have been fixed
- When a bookmark was set/changed, the file was not flagged as needing saving
- Some complex regexes can take a very long time - a timeout now warns the user
- Extending a column selection as the first operation caused an exception


## Version 2.0.0-alpha.18

### Bug fixes

- Cmd/Ctrl-clicking a spell check error removed 2 errors instead of one


## Version 2.0.0-alpha.17

- ASCII Table Effects dialog, similar to GG1, has been added
- HTML Auto-table dialog, similar to section of GG1's HTML Markup dialog,
  has been added
- Backup file now saved when user saves file, with extension `.bak`. Can be
  disabled in Prefs dialog
- Autosave can now be enabled in Prefs dialog, which saves the current file
  every 5 minutes (configurable in Prefs dialog) 
- The Prefs file (where settings are saved) is now backed up so that a "day-"
  and "week-old" version should be retained in the same directory, which can
  be restored if the original becomes corrupted. Now that many settings,
  including Custom menu entries, are saved in the Prefs file, it would be
  more disruptive if Pref file's contents were lost. Procedure: quit Guiguts;
  rename `GGprefs.json` to `GGprefs_corrupt.json`; rename `GGprefs_day.json`
  to `GGprefs.json`; restart Guiguts; if problem not resolved, repeat the
  above, but restoring `GGprefs_week.json`
- Custom Menu added, similar to GG1, but read help in dialog or manual page
  for more details, including how to link to source scans at IA or Hathi Trust
- IMPORTANT note for users upgrading from earlier alpha versions: the location
  of the ebookmaker directory/folder must be re-selected - it is now where
  the `pipenv install ebookmaker` command was run, rather than the ebookmaker
  script in the virtual environment.
- If ebookmaker is installed on user's computer, it can be run from within
  GG on all platforms. Normally runs in verbose mode, but "Verbose" checkbox
  enables further verbosity (mostly for debugging)
- Ebookmaker messages can be sorted by severity; "Suspects only" can be used
  to filter out debug/information messages.
- Command Palette has been added, accessible via the Help menu, or using
  Cmd/Ctrl+Shift+P: it lists all the commands available, and user can type
  part of the command to filter the list, then run the command with the "Run"
  button, or the "Enter/Return" key or double clicking the command. In addition
  to being a feature in its own right, it is intended to use this work to
  support the addition of user-defined shortcut keys in a future release
- Proofer comments can now be deleted, via button or Cmd/Ctrl-clicking in
  Proofer Comments dialog
- Highlighting of current cursor line can be disabled via Prefs dialog
- Display of tooltips can be disabled via Prefs dialog
- End-of-page blank lines, and end-of-line spaces are deleted automatically
  when file is saved
- Pathnames, e.g. scannos filename, are displayed right-aligned in comboboxes
  so the filename is more visible, and a tooltip displays the full pathname
- Link to PPWB is not in Tools menu, and a few button labels have been changed
- Show/Hide Image Viewer menu buttons replaced with Image Viewer checkbox
- All checker dialogs now output "Check complete" at the bottom of the list
- Dialog Manual in the Help menu performs the same task as the F1 key, i.e.
  displays the manual page for the dialog that was most recently used
- When Unicode Search dialog is popped, if there is a character displayed in
  the status bar (i.e. single character selected, or character after cursor)
  the information on that character is displayed

### Bug fixes

- Autoset Chap LZ in Footnote Fixup caused an infinite refreshing loop
- A few PPtxt false positives have been fixed
- PPhtml failed to detect `id="my_id"` when split across a line break
- PPhtml sometimes output a leading comma in the list of defined classes
- PPhtml split classnames containing hyphens into two classes
- HTML & CSS validator dialogs did not link to their manual pages
- Cmd/Ctrl-clicking a spelling error didn't remove it from the list
- Search-->Count, Find All & Replace All with "In selection" checked did not
  work correctly in column selections.
- Line number and column number highlighting foreground color could be wrong
- The CSS validator failed with CSS blocks over 400 lines long
- The current cursor line displayed oddly in combination with split window -
  a known issue is that the cursor line from the other half of the split
  will be displayed (faintly) in the split window
- Footnote reindexing could give incorrect output where multiple footnote
  anchors were on the same line of text
- WF treated underscores as word characters in an inconsistent manner
- Very small image viewer scale factors could cause a traceback


## Version 2.0.0-alpha.16

- The user can now use an external viewer to display scan files, instead of,
  or in addition to, the internal viewer. If the user does not specify a
  particular viewer, the computer's default viewer for PNG files will be used.
  Typically, this is the viewer that would open a PNG file when the operating
  system is asked to "open" or "view" the file, or it is double-clicked when
  using Windows. Alternatively the user can choose a specific viewer, such as
  `XnView` on Windows, `Pixea` on macOS, or `eog -w` on Linux, which will then
  be used instead of the computer's default viewer.
- Help->About Guiguts now reports version numbers and is easier to copy
  when reporting a bug
- A High Contrast preference option increases the contrast of the main text
  window and internal image viewer, i.e. black on white or white on black
- Highlight HTML Tags in the Search menu displays HTML tags in color to make
  it easier to edit HTML files
- Image Viewer now has auto fit-to-height and fit-to-width buttons
- CSS Validator in the HTML menu uses the online W3C validator to validate
  (CSS2.1 or CSS3) and report on the CSS block at the top of the file
- All checker dialogs now have buttons to hide (and fix if appropriate) the
  selected message, instead of requiring use of Cmd/Ctrl with mouse clicks
- The "Default" theme is now dark or light depending on the current operating
  system setting - the user can still choose Dark or Light explicitly
- Clicking (and dragging) in the line numbers on the left now selects whole
  lines of text. Although it is not possible to drag beyond the height of
  the window, large sections of text can be selected by clicking to select
  the first line, scrolling down, then Shift-clicking to select the last
  line. Shift-clicking and dragging extends/reduces the selection in a similar
  way to the behavior in the main text window. The mouse scroll wheel should
  also scroll the text window even when the mouse is in the line numbers
- Checker View Options (e.g. Bookloupe) now mean "show" when checked, rather
  than "hide"
- Checker View Options now have a checkbox to allow the graying out of view
  options that do not match any messages in the checker dialog - in addition
  the number of matching messages is shown next to each view option 
- Curly Quotes now has View Options to allow hide/show of single/double quote
  queries independently
- PPhtml check has been added, based on a combination of the PPWB tool and the
  tool bundled with Guiguts 1 
- A link to the online Post-Processors' Workbench is now in the HTML menu
- The Preferences dialog now has tabs to split the different preferences into
  sections
- A new Advanced tab in the Preferences dialog has settings for line spacing
  which increases the vertical spacing between lines of text, and for cursor
  width which can be increased to make it more visible
- A few small improvements have been made to PPtxt's report
- Spell check does not highlight all the spelling queries in blue
- Ebookmaker check has been added to the HTML menu. Checkboxes determine which
  formats will be created in the project directory. The user must first 
  install ebookmaker according to the instructions here:
  https://github.com/gutenbergtools/ebookmaker/blob/master/README.md
  So far, this has been tested successfully  on Windows, but not on macOS or
  Linux. Feedback would be welcomed.
- An experimental feature to improve the display of Hebrew and Arabic text,
  which is displayed right to left (RTL), attempts to display the text in the
  correct direction. To paste Hebrew text on Windows, or Hebrew and Arabic
  text on Linux, use the new Edit Paste Hebrew/Arabic Text button. This
  reverses the text in a platform appropriate manner, and also adjusts it
  when the file is saved and reloaded. Do not attempt to paste a mixture of
  RTL and LTR text. As with all previous versions of Guiguts 1 and 2, if you
  position the insert cursor within the RTL text, characters may jump around
  unexpectedly, but will be restored when the cursor is moved away. Feedback
  would be welcomed.

### Bug fixes

- Footnote anchors were accidentally included in the autogenerated ToC
- Auto-illustration sometimes failed to spot the end of illo markup
- Sometimes when the window scrolled to show the latest search match, the
  match would be at the very edge of the screen making it hard to spot
- Math fractions like `100/length` were reported by Unmatched Block Markup
- Mac mousewheel/trackpad image scrolling was not smooth


## Version 2.0.0-alpha.15

- HTML Auto Illustrations feature has been added
- Unmatched HTML tag check has been added 
- HTML Validator added using the Nu validator: https://validator.w3.org/nu/
- HTML Link Checker added
- Bookloupe now has a View Options dialog to control which messages are shown
- Image viewer buttons improved, including ability to page through the files
  in the images folder without moving the current text position
- Proofer notes are now optionally highlighted
- A `misspelled.json` stealth scannos file has been added to the release
- Mouse pointer in checker dialogs is now the normal cursor arrow
- Spell Check dialog has shortcut keys using Cmd/Ctrl plus a letter, like GG1:
  A - Add to global dictionary, P - add to Project dictionary, S - Skip,
  I - skIp all
- Search match highlighting speed has been improved
- Previous/next image buttons in the status bar now move to the next image
  even if the text position does not move
- Curly Quote checker reports open quotes preceded by punctuation
- Some Bookloupe false positive reports have been removed, and the wording
  of some messages improved
- Some repeated PPtxt messages removed
- Search dialog shows "No matches found" in addition to sounding the bell
- "Invert Image" has been added to the View menu
- README updated to include changes due to Poetry version 2

### Bug fixes

- Bookloupe could crash when processing a text table using `=` for borders
- Insert cursor wasn't hidden in text split window when a selection was made
- Split text window's column ruler did not always follow the theme color
- Footnotes LZ heading could have 4 blank lines before, but only 1 after  
- Orange spotlights could be left behind when WF or other dialogs closed
- An exception could happen if GG exited while certain dialogs were visible
- Footnotes "Move to paragraphs" could fail due to editing side effect
- HTML Autogen could wrap the book title in both `<h1>` and `<p>` markup


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

- Orange spotlights were hidden when doing Find All within a selection
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