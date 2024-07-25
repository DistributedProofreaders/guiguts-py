# Changelog


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