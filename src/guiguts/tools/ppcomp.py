"""
As far as possible, this file remains the same as ppcomp.py as used by the PP Workbench in
January 2026 (https://github.com/DistributedProofreaders/ppcomp/blob/master/ppcomp/ppcomp.py).
Thus there are unused sections of code. The purpose is to make it easier to port any later
changes between the two versions.

ppcomp.py - compare text from 2 files, ignoring html and formatting differences, for use by users
of Distributed Proofreaders (https://www.pgdp.net)

Applies various transformations according to program options before passing the files to the Linux
program dwdiff.

Copyright (C) 2012-2013, 2021 bibimbop at pgdp

Modified March 2022 by Robert Tonsing, per GPL section 5

Originally written as the standalone program comp_pp.py by bibimbop at PGDP as part of his PPTOOLS
program. It is used as part of the PP Workbench with permission.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import argparse
from dataclasses import dataclass
import difflib
import logging
import os
import subprocess
import tempfile
import tkinter as tk
from tkinter import ttk, font
from typing import Optional, Any, cast
import warnings

import cssselect
import regex as re
from lxml import etree
from lxml.html import html5parser

from guiguts.checkers import CheckerDialog
from guiguts.file import the_file
from guiguts.maintext import HighlightTag, maintext
from guiguts.preferences import (
    PrefKey,
    PersistentBoolean,
    preferences,
)
from guiguts.utilities import is_windows, IndexRowCol, IndexRange
from guiguts.widgets import ToolTip, Busy, PathnameCombobox, FileDialog

logger = logging.getLogger(__package__)

###############################################################

FLAG_CH_HTML_L = "⦓"
FLAG_CH_HTML_R = "⦔"
FLAG_CH_TEXT_L = "⦕"
FLAG_CH_TEXT_R = "⦖"
NO_SPACE_BEFORE = "])}.,:;!?"
NO_SPACE_AFTER = "[({"


class PPcompCheckerDialog(CheckerDialog):
    """PPcomp dialog."""

    manual_page = "Tools_Menu#PPcomp"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize PPcomp dialog."""
        super().__init__(
            "PPcomp Results",
            tooltip="\n".join(
                [
                    "Left click: Select & find issue",
                    "Right click: Hide issue",
                ]
            ),
            **kwargs,
        )

        self.rerun_button["text"] = "Compare"
        self.custom_frame.columnconfigure(0, weight=1)
        fn_frame = ttk.Frame(self.custom_frame)
        fn_frame.grid(row=0, column=0, sticky="NSEW")
        fn_frame.columnconfigure(0, weight=1)
        self.html_combo = PathnameCombobox(
            fn_frame, PrefKey.PPCOMP_HTML_FILE_HISTORY, PrefKey.PPCOMP_HTML_FILE
        )
        self.html_combo.grid(row=0, column=0, sticky="EW")
        ttk.Button(
            fn_frame,
            text="Choose HTML File",
            command=lambda: self.choose_file(html=True),
        ).grid(row=0, column=1, sticky="EW", padx=(5, 0))
        self.text_combo = PathnameCombobox(
            fn_frame, PrefKey.PPCOMP_TEXT_FILE_HISTORY, PrefKey.PPCOMP_TEXT_FILE
        )
        self.text_combo.grid(row=1, column=0, sticky="EW")
        ttk.Button(
            fn_frame,
            text="Choose Text File",
            command=lambda: self.choose_file(html=False),
        ).grid(row=1, column=1, sticky="EW", padx=(5, 0))

        frame = ttk.Frame(self.custom_frame)
        frame.grid(row=1, column=0, sticky="NSEW")
        frame.columnconfigure(2, weight=1)

        frame_g = ttk.LabelFrame(frame, text="General")
        frame_g.grid(row=0, column=0, sticky="NSEW")
        for cnt, (prefkey, (label, tooltip)) in enumerate(
            {
                PrefKey.PPCOMP_IGNORE_CASE: (
                    "Ignore Case",
                    "Ignore case when comparing",
                ),
                PrefKey.PPCOMP_EXTRACT_FOOTNOTES: (
                    "Extract Footnotes",
                    "Extract and process footnotes separately\n"
                    "May cause line numbers to be incorrect",
                ),
            }.items()
        ):
            btn = ttk.Checkbutton(
                frame_g, variable=PersistentBoolean(prefkey), text=label
            )
            btn.grid(row=cnt, column=0, sticky="NSW")
            ToolTip(btn, tooltip)

        frame_t = ttk.LabelFrame(frame, text="Text")
        frame_t.grid(row=1, column=0, sticky="NSEW")
        for cnt, (prefkey, (label, tooltip)) in enumerate(
            {
                PrefKey.PPCOMP_SUPPRESS_FOOTNOTES: (
                    "Suppress Footnote Tags",
                    'TXT: Suppress "[Footnote #:" marks',
                ),
                PrefKey.PPCOMP_SUPPRESS_ILLOS: (
                    "Suppress Illo Tags",
                    'TXT: Suppress "[Illustration:" marks',
                ),
                PrefKey.PPCOMP_SUPPRESS_SIDENOTES: (
                    "Suppress Sidenote Tags",
                    'TXT: Suppress "[Sidenote:" marks',
                ),
            }.items()
        ):
            btn = ttk.Checkbutton(
                frame_t, variable=PersistentBoolean(prefkey), text=label
            )
            btn.grid(row=cnt, column=0, sticky="NSW")
            ToolTip(btn, tooltip)

        frame_h = ttk.LabelFrame(frame, text="HTML")
        frame_h.grid(row=0, column=1, sticky="NSEW", rowspan=2, padx=5)
        for cnt, (prefkey, (label, tooltip)) in enumerate(
            {
                PrefKey.PPCOMP_CSS_ADD_ILLOS: (
                    "Add Illo Tags",
                    "HTML: Add [Illustration ] tag",
                ),
                PrefKey.PPCOMP_CSS_ADD_SIDENOTES: (
                    "Add Sidenote Tags",
                    "HTML: Add [Sidenote: ...]",
                ),
                PrefKey.PPCOMP_SUPPRESS_NBSP: (
                    "Suppress &nbsp; In Nos.",
                    "HTML: Suppress non-breakable spaces between numbers",
                ),
                PrefKey.PPCOMP_SUPPRESS_WJ: (
                    "Suppress Word Joiner",
                    "HTML: Suppress Word join (&NoBreak;/&#x2060;)",
                ),
                PrefKey.PPCOMP_CSS_SMCAP: (
                    "Smallcap ⇒ UPPERCASE",
                    "HTML: Transform small caps into uppercase",
                ),
            }.items()
        ):
            frame_h.rowconfigure(cnt, weight=1)
            btn = ttk.Checkbutton(
                frame_h, variable=PersistentBoolean(prefkey), text=label
            )
            btn.grid(row=cnt, column=0, sticky="NSW")
            ToolTip(btn, tooltip)

        frame_c = ttk.LabelFrame(frame, text="CSS")
        frame_c.grid(row=0, column=2, sticky="NSEW", rowspan=2)
        for cnt, (prefkey, (label, tooltip)) in enumerate(
            {
                PrefKey.PPCOMP_CSS_NO_DEFAULT: (
                    "Do Not Use Default CSS",
                    "HTML: Do not use default transformation CSS",
                ),
                PrefKey.PPCOMP_CSS_CUSTOM: (
                    "Add Custom CSS",
                    "HTML: Add custom transformation CSS",
                ),
            }.items()
        ):
            frame_c.columnconfigure(cnt, weight=1)
            btn = ttk.Checkbutton(
                frame_c, variable=PersistentBoolean(prefkey), text=label
            )
            btn.grid(row=0, column=cnt, sticky="NSW")
            ToolTip(btn, tooltip)

        mono = font.nametofont("TkFixedFont")

        text_frame = ttk.Frame(frame_c)
        text_frame.grid(row=2, column=0, columnspan=2, sticky="NSEW")
        frame_c.rowconfigure(2, weight=1)

        text = tk.Text(
            text_frame,
            height=5,  # about 5 lines
            width=40,  # in characters
            background=maintext()["background"],
            foreground=maintext()["foreground"],
            insertbackground=maintext()["insertbackground"],
            wrap="none",  # so horizontal scrollbar makes sense
            relief=tk.SUNKEN,
            font=mono,
        )
        text.grid(row=0, column=0, sticky="NSEW")
        text.insert(tk.END, preferences.get(PrefKey.PPCOMP_CSS_CUSTOM_VALUE))

        def on_text_focus_out(event: tk.Event):
            widget = cast(tk.Text, event.widget)
            contents = widget.get("1.0", "end-1c")
            preferences.set(PrefKey.PPCOMP_CSS_CUSTOM_VALUE, contents)

        text.bind("<FocusOut>", on_text_focus_out)

        vscroll = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        vscroll.grid(row=0, column=1, sticky="ns")

        hscroll = ttk.Scrollbar(text_frame, orient="horizontal", command=text.xview)
        hscroll.grid(row=1, column=0, sticky="ew")

        text.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        # Make the text expand if the frame grows
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.update_count_label(False)
        Busy.unbusy()

    def choose_file(self, html: bool) -> None:
        """Choose an HTML or text file."""
        if html:
            filename = FileDialog.askopenfilename(
                filetypes=(
                    ("HTML files", "*.html *.htm *.xhtml"),
                    ("All files", "*.*"),
                )
            )
        else:
            filename = FileDialog.askopenfilename(
                filetypes=(
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                )
            )
        if filename:
            if is_windows():
                filename = filename.replace("\\", "/")
            self.focus()
            if html:
                preferences.set(PrefKey.PPCOMP_HTML_FILE, filename)
                self.html_combo.add_to_history(filename)
            else:
                preferences.set(PrefKey.PPCOMP_TEXT_FILE, filename)
                self.text_combo.add_to_history(filename)


class PPcompChecker:
    """PPcomp checker."""

    files: list["PgdpFile"] = []

    def __init__(self) -> None:
        """Initialize PPcomp checker."""
        self.dialog = PPcompCheckerDialog.show_dialog(rerun_command=self.run)

    def run(self) -> None:
        """Run PPcomp."""
        empty_args: list[str] = []
        PPcompChecker.files = []
        PPcompChecker.files.append(PgdpFileHtml(empty_args))
        PPcompChecker.files.append(PgdpFileText(empty_args))
        fname = preferences.get(PrefKey.PPCOMP_HTML_FILE)
        if not (fname and os.path.isfile(fname)):
            return
        try:
            PPcompChecker.files[0].load(fname)
        except (FileNotFoundError, SyntaxError) as exc:
            logger.error(exc)
            return
        fname = preferences.get(PrefKey.PPCOMP_TEXT_FILE)
        if not (fname and os.path.isfile(fname)):
            return
        PPcompChecker.files[1].load(fname)
        for f in PPcompChecker.files:
            f.cleanup()
            # perform common cleanup for both files
            PPComp.check_characters(PPcompChecker.files)

        self.dialog.reset()
        render_marked_diff(
            self.dialog,
            PPcompChecker.files[0].text,
            PPcompChecker.files[1].text,
            PPcompChecker.files[0].start_line,
        )
        if preferences.get(PrefKey.PPCOMP_EXTRACT_FOOTNOTES):
            render_marked_diff(
                self.dialog,
                PPcompChecker.files[0].footnotes,
                PPcompChecker.files[1].footnotes,
                0,
            )

        self.dialog.display_entries()

        # ---- Convert flag characters into Tk tags ----
        for left, right, tag in [
            (FLAG_CH_HTML_L, FLAG_CH_HTML_R, HighlightTag.PPCOMP_HTML),
            (FLAG_CH_TEXT_L, FLAG_CH_TEXT_R, HighlightTag.PPCOMP_TEXT),
        ]:
            start = "1.0"
            while True:
                start_idx = self.dialog.text.search(left, start, tk.END)
                if not start_idx:
                    break
                end_idx = self.dialog.text.search(right, f"{start_idx}+1c", tk.END)
                if not end_idx:
                    break

                self.dialog.text.tag_add(tag, f"{start_idx}+1c", end_idx)
                self.dialog.text.delete(end_idx, f"{end_idx}+1c")
                self.dialog.text.delete(start_idx, f"{start_idx}+1c")

                start = end_idx


# ------------------------------------------------------------
# Token model
# ------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    """Token consisting of text and its line number"""

    text: str
    line: int


# Words + punctuation (keeps _italic_, em-dashes, quotes, etc)
TOKEN_RE = re.compile(r"[\p{L}\p{M}\p{N}]+|_|[^\p{L}\p{N}\s]")


# ------------------------------------------------------------
# Tokenisation with line provenance
# ------------------------------------------------------------


def tokenize_with_lines(text: str) -> list[Token]:
    """
    Convert text into a flat list of Tokens.
    Each token knows which line it came from.
    """
    tokens: list[Token] = []

    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in TOKEN_RE.finditer(line):
            tokens.append(Token(m.group(), lineno))

    return tokens


def token_span_to_lines(
    tokens: list[Token], i1: int, i2: int, offset: int
) -> Optional[tuple[int, int]]:
    """Map token spans back to line numbers."""
    if i1 == i2:
        return None

    lines = {t.line for t in tokens[i1:i2]}
    return min(lines) + offset, max(lines) + offset


def aligned_tokens(tok_list_a: list[Token], tok_list_b: list[Token]):
    """Check type of change and yield tokens."""
    sm = difflib.SequenceMatcher(
        a=[t.text for t in tok_list_a], b=[t.text for t in tok_list_b], autojunk=False
    )

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                yield tok_list_a[i1 + k], tok_list_b[j1 + k]

        elif tag == "replace":
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                yield (
                    tok_list_a[i1 + k] if i1 + k < i2 else None,
                    tok_list_b[j1 + k] if j1 + k < j2 else None,
                )

        elif tag == "delete":
            for k in range(i1, i2):
                yield tok_list_a[k], None

        elif tag == "insert":
            for k in range(j1, j2):
                yield None, tok_list_b[k]


def aligned_words_with_lines(a_text, b_text):
    """Yield matched tokens and their line numbers."""
    tok_list_a = tokenize_with_lines(a_text)
    tok_list_b = tokenize_with_lines(b_text)

    case_ins = preferences.get(PrefKey.PPCOMP_IGNORE_CASE)

    def norm(s: str) -> str:
        if case_ins:
            return s.lower() if s else ""
        return s

    for a_tok, b_tok in aligned_tokens(tok_list_a, tok_list_b):
        yield {
            "a_word": a_tok.text if a_tok else "",
            "a_line": a_tok.line if a_tok else None,
            "b_word": b_tok.text if b_tok else "",
            "b_line": b_tok.line if b_tok else None,
            "changed": (a_tok and b_tok and norm(a_tok.text) != norm(b_tok.text))
            or (a_tok is None)
            or (b_tok is None),
        }


def join_tokens(tokens: list[str]) -> str:
    """Join tokens, but sticking punctuation to left/right as appropriate."""
    out: list[str] = []
    for tok in tokens:
        if not out:
            out.append(tok)
            continue

        # punctuation sticks to previous token or next token
        # otherwise, space between tokens
        if tok in NO_SPACE_BEFORE or out[-1][-1] in NO_SPACE_AFTER:
            out.append(tok)
        else:
            out.append(f" {tok}")

    return "".join(out)


def render_marked_diff(
    dialog: PPcompCheckerDialog, a_text: str, b_text: str, html_file_start: int
) -> None:
    """Render the diffs to the dialog."""
    rows = aligned_words_with_lines(a_text, b_text)

    lines: list[tuple[str, tuple[int, int] | None]] = []  # (text, a_line, b_line)
    cur_line: list[str] = []

    old_buf: list[str] = []
    new_buf: list[str] = []

    last_a = last_b = None
    cur_linenum: tuple[int, int] | None = None

    def flush_changes():
        if new_buf:
            cur_line.append(f"{FLAG_CH_TEXT_L}{join_tokens(new_buf)}{FLAG_CH_TEXT_R}")
        if old_buf:
            cur_line.append(f"{FLAG_CH_HTML_L}{join_tokens(old_buf)}{FLAG_CH_HTML_R}")
        old_buf.clear()
        new_buf.clear()

    html_ln = os.path.splitext(the_file().filename)[1].lower() in (
        ".htm",
        ".html",
        "xhtml",
    )
    line_has_change = False
    a_line = html_file_start + 1
    b_line = 1
    for r in rows:
        if r["a_line"] is not None:
            a_line = r["a_line"] + html_file_start
        if r["b_line"] is not None:
            b_line = r["b_line"]

        # New source line → flush current output line
        if (a_line, b_line) != (last_a, last_b):
            flush_changes()
            if cur_line and line_has_change:
                lines.append((join_tokens(cur_line), cur_linenum))
                line_has_change = False
            cur_line = []
            cur_linenum = None

        last_a, last_b = a_line, b_line

        # Remember the HTML and Text line numbers for this output line
        if cur_linenum is None and a_line or b_line:
            cur_linenum = (a_line, b_line)

        if r["changed"]:
            if r["b_word"]:
                new_buf.append(r["b_word"])
            if r["a_word"]:
                old_buf.append(r["a_word"])
            line_has_change = True
        else:
            flush_changes()
            if r["a_word"]:
                cur_line.append(r["a_word"])

    flush_changes()
    if cur_line and line_has_change:
        lines.append((join_tokens(cur_line), cur_linenum))

    # ---- Send to the dialog ----
    for text, line_pair in lines:
        if line_pair is None:
            continue
        a_line, b_line = line_pair
        if html_ln:
            if a_line is not None:
                index = IndexRange(IndexRowCol(a_line, 0), IndexRowCol(a_line, 0))
            else:
                index = None
            sub_line = f"{b_line}.0: " if b_line else ""
        else:
            if b_line is not None:
                index = IndexRange(IndexRowCol(b_line, 0), IndexRowCol(b_line, 0))
            else:
                index = None
            sub_line = f"{a_line}.0: " if a_line else ""

        dialog.add_entry(f"{sub_line}{text}", index)


###############################################################

PG_EBOOK_START = "*** START OF"
PG_EBOOK_END = "*** END OF"
DEFAULT_TRANSFORM_CSS = """
  /* Italics */
  i::before, cite::before, em::before,
  i::after, cite::after, em::after { content: "_"; }

  /* Add spaces around td tags */
  td::before, td::after { content: " "; }

  /* Remove thought breaks */
  .tb { display: none; }

  /* Add space before br tags */
  br::before { content: " "; }

  /* Remove page numbers. It seems every PP has a different way. */
  span[class^="pagenum"],
  p[class^="pagenum"],
  div[class^="pagenum"],
  span[class^="pageno"],
  p[class^="pageno"],
  div[class^="pageno"],
  p[class^="page"],
  span[class^="pgnum"],
  div[id^="Page_"] { display: none }

  /* Superscripts, subscripts */
  sup { text-transform:superscript; }
  sub { text-transform:subscript; }
"""
# CSS used to display the diffs
DIFF_CSS = """
body {
  margin-left: 5%;
  margin-right: 5%;
}
ins, del {
  text-decoration: none;
  border: 1px solid black;
  background-color: whitesmoke;
  font-size: larger;
}
ins, .second { color: green; }
del, .first { color: purple; }
.lineno { margin-right: 1em; }
.bbox {
  margin-left: auto;
  margin-right: auto;
  border: 1px dashed;
  padding: 0 1em;
  background-color: lightcyan;
  width: 90%;
  max-width: 50em;
}
h1, .center { text-align: center; }
/* Use a CSS counter to number each diff. */
body { counter-reset: diff; } /* set diff counter to 0 */
hr::before {
  counter-increment: diff; /* inc the diff counter ... */
  content: "Diff " counter(diff) ": "; /* ... and display it */
}
.error-border {
  border-style: double;
  border-color: red;
  border-width: 15px;
}
"""
"""Note that 'º' and 'ª' are ordinals, assume they would be entered as-is, not superscript"""
SUPERSCRIPTS = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "a": "ᵃ",
    "b": "ᵇ",
    "c": "ᶜ",
    "d": "ᵈ",
    "e": "ᵉ",
    "f": "ᶠ",
    "g": "ᵍ",
    "h": "ʰ",
    "i": "ⁱ",
    "j": "ʲ",
    "k": "ᵏ",
    "l": "ˡ",
    "m": "ᵐ",
    "n": "ⁿ",
    "o": "ᵒ",
    "p": "ᵖ",
    "r": "ʳ",
    "s": "ˢ",
    "t": "ᵗ",
    "u": "ᵘ",
    "v": "ᵛ",
    "w": "ʷ",
    "x": "ˣ",
    "y": "ʸ",
    "z": "ᶻ",
    "A": "ᴬ",
    "B": "ᴮ",
    "D": "ᴰ",
    "E": "ᴱ",
    "G": "ᴳ",
    "H": "ᴴ",
    "I": "ᴵ",
    "J": "ᴶ",
    "K": "ᴷ",
    "L": "ᴸ",
    "M": "ᴹ",
    "N": "ᴺ",
    "O": "ᴼ",
    "P": "ᴾ",
    "R": "ᴿ",
    "T": "ᵀ",
    "U": "ᵁ",
    "V": "ⱽ",
    "W": "ᵂ",
    "Æ": "ᴭ",
    "œ": "ꟹ",
}
SUBSCRIPTS = {
    "0": "₀",
    "1": "₁",
    "2": "₂",
    "3": "₃",
    "4": "₄",
    "5": "₅",
    "6": "₆",
    "7": "₇",
    "8": "₈",
    "9": "₉",
    "a": "ₐ",
    "e": "ₑ",
    "h": "ₕ",
    "i": "ᵢ",
    "j": "ⱼ",
    "k": "ₖ",
    "l": "ₗ",
    "m": "ₘ",
    "n": "ₙ",
    "o": "ₒ",
    "p": "ₚ",
    "r": "ᵣ",
    "s": "ₛ",
    "t": "ₜ",
    "u": "ᵤ",
    "v": "ᵥ",
    "x": "ₓ",
}

# mypy: disallow-untyped-defs=False


def to_superscript(text):
    """Convert to unicode superscripts"""
    result = ""
    for char in text:
        try:
            result += SUPERSCRIPTS[char]
        except KeyError:
            return text  # can't convert, just leave it
    return result


def to_subscript(text):
    """Convert to unicode subscripts"""
    result = ""
    for char in text:
        try:
            result += SUBSCRIPTS[char]
        except KeyError:
            return text  # can't convert, just leave it
    return result


class PgdpFile:
    """Base class: Store and process a DP text or html file"""

    def __init__(self, args):
        self.args = args
        self.basename = ""
        self.text = ""  # file text
        self.start_line = (
            0  # line text started, before stripping boilerplate and/or head
        )
        self.footnotes = ""  # footnotes text, if extracted

    def load(self, filename):
        """Load a file (text or html)
        Args:
            filename: file pathname
        Vars:
            self.text = contents of file
            self.basename = file base name
        Raises:
            IOError: unable to open file
            SyntaxError: file too short
        """
        self.basename = os.path.basename(filename)
        try:
            with open(filename, "r", encoding="utf-8") as file:
                self.text = file.read()
                # remove BOM on first line if present
                t = ":".join(f"{ord(c):x}" for c in self.text[0])
                if t[0:4] == "feff":
                    self.text = self.text[1:]
        except UnicodeError:
            with open(filename, "r", encoding="latin-1") as file:
                self.text = file.read()
        except FileNotFoundError as ex:
            raise FileNotFoundError("Cannot load file: " + filename) from ex
        if len(self.text) < 10:
            raise SyntaxError("File is too short: " + filename)

    def strip_pg_boilerplate(self):
        """Remove the PG header and footer from the text if present."""
        raise NotImplementedError("Override this method")

    def cleanup(self):
        """Remove tags from the file"""
        raise NotImplementedError("Override this method")


class PgdpFileText(PgdpFile):
    """Store and process a DP text file"""

    def __init__(self, args):
        super().__init__(args)
        self.from_pgdp_rounds = False  # THIS file is from proofing rounds

    def load(self, filename):
        """Load the file"""
        if not filename.lower().endswith(".txt"):
            raise SyntaxError("Not a text file: " + filename)
        super().load(filename)

    def strip_pg_boilerplate(self):
        """Remove the PG header and footer from the text if present."""
        new_text = []
        start_found = False
        for lineno, line in enumerate(self.text.splitlines(), start=1):
            # Find the markers. Unfortunately PG lacks consistency
            if line.startswith(PG_EBOOK_START):
                start_found = True
            if start_found and line.endswith("***"):  # may take multiple lines
                new_text = []  # PG found, remove previous lines
                self.start_line = lineno + 1
                start_found = False
            elif line.startswith(PG_EBOOK_END):
                break  # ignore following lines
            else:
                new_text.append(line)
        self.text = "\n".join(new_text)

    def remove_paging(self):
        """Remove page markers & blank pages"""
        self.text = re.sub(r"-----File: \w+.png.*", "", self.text)
        self.text = self.text.replace("[Blank Page]", "")

    def remove_block_markup(self):
        """Remove block markup"""
        for markup in ["/*", "*/", "/#", "#/", "/P", "P/", "/F", "F/", "/X", "X/"]:
            self.text = self.text.replace("\n" + markup + "\n", "\n\n")

    def remove_formatting(self):
        """Ignore or replace italics and bold tags in file from rounds"""
        if self.args.ignore_format:
            for tag in ["<i>", "</i>", "<b>", "</b>"]:
                self.text = self.text.replace(tag, "")
        else:
            for tag in ["<i>", "</i>"]:
                self.text = self.text.replace(tag, "_")
            for tag in ["<b>", "</b>"]:
                self.text = self.text.replace(tag, self.args.css_bold)
        # remove other markup
        self.text = re.sub("<.*?>", "", self.text)

    def suppress_proofers_notes(self):
        """suppress proofers notes in file from rounds"""
        if self.args.suppress_proofers_notes:
            self.text = re.sub(r"\[\*\*[^]]*?]", "", self.text)

    def regroup_split_words(self):
        """Regroup split words, must run remove page markers 1st"""
        if self.args.regroup_split_words:
            word_splits = {
                r"(\w+)-\*(\n+)\*": r"\n\1",  # followed by 0 or more blank lines
                r"(\w+)-\*(\w+)": r"\1\2",
            }  # same line
            for key, value in word_splits.items():
                self.text = re.sub(key, value, self.text)

    def ignore_format(self):
        """Remove italics and bold markers in proofed file"""
        # if self.args.ignore_format:
        #     self.text = re.sub(r"_((.|\n)+?)_", r"\1", self.text)
        #     self.text = re.sub(r"=((.|\n)+?)=", r"\1", self.text)

    def remove_thought_breaks(self):
        """Remove thought breaks (4 or more spaced asterisks or dots)"""
        self.text = re.sub(r"\n(?:[ \t]+[*•]){4,}", "\n", self.text)

    def suppress_footnote_tags(self):
        """Remove footnote tags"""
        if preferences.get(PrefKey.PPCOMP_SUPPRESS_FOOTNOTES):
            self.text = re.sub(
                r"[\[]*Footnote ([\d\w]+):\s([^]]*?)[\]]*",
                r"\1 \2",
                self.text,
                flags=re.MULTILINE,
            )
            self.text = re.sub(
                r"\*\[Footnote:\s([^]]*?)]", r"\1", self.text, flags=re.MULTILINE
            )

    def suppress_illustration_tags(self):
        """Remove illustration tags"""
        if preferences.get(PrefKey.PPCOMP_SUPPRESS_ILLOS):
            self.text = re.sub(
                r"\[Illustration?:([^]]*?)]", r"\1", self.text, flags=re.MULTILINE
            )
            self.text = self.text.replace("[Illustration]", "")

    def suppress_sidenote_tags(self):
        """Remove sidenote tags"""
        if preferences.get(PrefKey.PPCOMP_SUPPRESS_SIDENOTES):
            self.text = re.sub(
                r"\[Sidenote:([^]]*?)]", r"\1", self.text, flags=re.MULTILINE
            )

    @staticmethod
    def match_to_superscript(match):
        """Convert regex match to subscript"""
        return to_superscript(match.group(1))

    def superscripts(self):
        """Convert ^{} tagged text"""
        self.text = re.sub(
            r"\^{?([\w\d]+)}?", PgdpFileText.match_to_superscript, self.text
        )

    @staticmethod
    def match_to_subscript(match):
        """Convert regex match to subscript"""
        return to_subscript(match.group(1))

    def subscripts(self):
        """Convert _{} tagged text"""
        self.text = re.sub(r"_{([\w\d]+)}", PgdpFileText.match_to_subscript, self.text)

    def cleanup(self):
        """Perform cleanup for this type of file"""
        if self.from_pgdp_rounds:
            # if self.args.txt_cleanup_type == "n":  # none
            #     return
            # remove page markers & blank pages
            self.remove_paging()
            # if self.args.txt_cleanup_type == "p":  # proofers, all done
            #     return
            # else 'b' best effort
            self.remove_block_markup()
            self.remove_formatting()
            self.suppress_proofers_notes()
            self.regroup_split_words()
        else:  # processed text file
            self.strip_pg_boilerplate()
            self.ignore_format()
            self.remove_thought_breaks()

        # all text files
        if preferences.get(PrefKey.PPCOMP_EXTRACT_FOOTNOTES):
            if self.from_pgdp_rounds:  # always [Footnote 1: text]
                self.extract_footnotes_pgdp()
            else:  # probably [1] text
                self.extract_footnotes_pp()
        else:
            self.suppress_footnote_tags()
        self.suppress_illustration_tags()
        self.suppress_sidenote_tags()
        self.superscripts()
        self.subscripts()

    def extract_footnotes_pgdp(self):
        """Extract the footnotes from an F round text file
        Start with [Footnote #: and finish with ] at the end of a line
        """
        in_footnote = False  # currently processing a footnote
        text = []  # new text without footnotes
        footnotes = []

        for line in self.text.splitlines():
            if "[Footnote" in line:  # New footnote?
                in_footnote = True
                if "*[Footnote" not in line:  # Join to previous?
                    footnotes.append("")  # start new footnote
                line = re.sub(r"\*?\[Footnote\s?[\w\d]*:\s?", "", line)
            if in_footnote:  # Inside a footnote?
                footnotes[-1] = "\n".join([footnotes[-1], line])
                if line.endswith("]"):  # End of footnote?
                    footnotes[-1] = footnotes[-1][:-1]
                    in_footnote = False
                elif line.endswith("]*"):  # Footnote continuation
                    footnotes[-1] = footnotes[-1][:-2]
                    in_footnote = False
            else:
                text.append(line)

        self.text = "\n".join(text)  # Rebuild text, now without footnotes
        self.footnotes = "\n".join(footnotes)

    def extract_footnotes_pp(self):
        """Extract footnotes from a PP text file. Text is iterable. Updates the text without the
        footnotes, and adds the footnotes to the footnotes string. Empty lines are added to
        maintain the line numbers. regexes is a list of (regex, fn_type) that identify the
        beginning and end of a footnote. The fn_type is 2 when a ] terminates it, or 1 when a new
        block terminates it.
        """
        # Pick the regex with the most matches
        regexes = [
            (r"\s*\[([\w-]{1,4})\]( .*|$)", 1),
            (r"\s*Footnote (\d+):( .*|$)", 1),
            (r"\s*\[Footnote (\d+):( .*|$)", 2),
            (r"\s*Note (\d+):( .*|$)", 1),
            (r"\s*\[Note (\d+):( .*|$)", 2),
            (r"\s*([⁰¹²³⁴⁵⁶⁷⁸⁹]+)( .*|$)", 1),
        ]
        match_counts = [0] * len(regexes)  # i.e. [0, 0, 0]
        for text_block, _ in self.get_block():
            if text_block:
                for i, (regex, _) in enumerate(regexes):
                    if re.match(regex, text_block[0]):
                        match_counts[i] += 1
                        break
        footnote_count = max(match_counts)
        regex, fn_type = [regexes[match_counts.index(footnote_count)]][0]

        current_fn_type = 0  # 0 means not in footnote.
        footnotes, new_text = [], []
        current_block = None

        for new_block, empty_lines in self.get_block():
            next_fn_type = 0
            if new_block:
                # Is the block a new footnote?
                matches = re.match(regex, new_block[0])
                if matches:
                    next_fn_type = fn_type
                    new_block[0] = matches.group(2)  # remove footnote tag

            if current_fn_type:  # in current footnote?
                if next_fn_type:
                    # New block is footnote, so it ends the previous footnote
                    footnotes += current_block + [""]
                    new_text += [""] * (len(current_block) + 1)
                    current_fn_type = next_fn_type
                elif new_block[0].startswith(""):
                    # new block is indented continuation, merge in current block
                    new_block = current_block + [""] + new_block
                else:  # new footnote or unindented block, end current footnote, add to footnotes
                    footnotes += current_block + [""]
                    new_text += [""] * (len(current_block) + 1)
                    current_fn_type = 0  # no longer in footnote
            if not current_fn_type and next_fn_type:
                # Account for new footnote
                current_fn_type = next_fn_type
            if current_fn_type and (
                empty_lines >= 2
                or (current_fn_type == 2 and new_block[-1].endswith("]"))
            ):
                if current_fn_type == 2 and new_block[-1].endswith("]"):
                    new_block[-1] = new_block[-1][:-1]  # Remove terminal bracket

                footnotes += new_block
                new_text += [""] * len(new_block)
                current_fn_type = 0  # no longer in fn
                new_block = None
            if not current_fn_type:
                # Add to text, with white lines
                new_text += (new_block or []) + [""] * empty_lines
                footnotes += [""] * (len(new_block or []) + empty_lines)

            current_block = new_block

        # Rebuild text, now without footnotes
        self.text = "\n".join(new_text)
        self.footnotes = "\n".join(footnotes)

        return footnote_count

    def get_block(self):
        """Generator to get a block of text, followed by the number of empty lines."""
        text_lines = self.text.splitlines()
        empty_lines = 0
        block = []
        for line in text_lines:
            if len(line):
                if empty_lines:  # one or more empty lines will stop a block
                    yield block, empty_lines
                    block = []
                    empty_lines = 0
                block += [line]
            else:
                empty_lines += 1
        yield block, empty_lines


class PgdpFileHtml(PgdpFile):
    """Store and process a DP html file."""

    def __init__(self, args):
        super().__init__(args)
        self.tree = None
        self.mycss = ""

    def parse_html5(self):
        """Parse an HTML5 doc"""
        # don't include namespace in elements
        # suppress stderr printed warnings - we report failure to parse via exception
        myparser = html5parser.HTMLParser(namespaceHTMLElements=False, strict=True)
        # without parser this works for all html, but we have to remove namespace
        # & don't get the errors list
        tree = html5parser.document_fromstring(self.text, parser=myparser)
        return tree.getroottree(), myparser.errors

    def parse_html(self):
        """Parse a non-HTML5 doc"""
        myparser = etree.HTMLParser()
        tree = etree.fromstring(self.text, parser=myparser)
        # HTML parser rejects tags with both id and name: (513 == DTD_ID_REDEFINED)
        # even though https://www.w3.org/TR/html4/struct/links.html#edef-A says it is OK
        errors = [
            x for x in list(myparser.error_log) if x.type != 513
        ]  # windymilla edited
        return tree.getroottree(), errors

    def load(self, filename):
        """Load the file. If parsing succeeded, then self.tree is set, and parser.errors is []"""
        if not filename.lower().endswith((".html", ".htm", ".xhtml")):
            raise SyntaxError("Not an html file: " + filename)
        super().load(filename)
        try:
            if 0 <= self.text.find("<!DOCTYPE html>", 0, 100):  # limit search
                self.tree, errors = self.parse_html5()
            else:
                self.tree, errors = self.parse_html()
        except Exception as ex:
            raise SyntaxError("File cannot be parsed: " + filename) from ex
        if errors:
            for error in errors:
                print(error)
            raise SyntaxError("Parsing errors in document: " + filename)

        # save line number of <body> tag - actual text start
        # html5parser does not fill in the source line number
        for lineno, line in enumerate(self.text.splitlines(), start=-1):
            if "<body" in line:
                self.start_line = lineno + 1
                break

        # remove the head - we only want the body
        head = self.tree.find("head")
        if head is not None:
            head.getparent().remove(head)

    def strip_pg_boilerplate(self):
        """Remove the PG header and footer from the text if present."""
        if -1 == self.text.find(PG_EBOOK_START):
            return
        # start: from <body to <div>*** START OF THE ...</div>
        # end: from <div>*** END OF THE ...</div> to </body
        start_found = False
        end_found = False
        for node in self.tree.find("body").iter():
            if node.tag == "div" and node.text and node.text.startswith(PG_EBOOK_START):
                start_found = True
                node.text = ""
                node.tail = ""
            elif node.tag == "div" and node.text and node.text.startswith(PG_EBOOK_END):
                end_found = True
            if end_found or not start_found:
                node.text = ""
                node.tail = ""
        # we need the start line, html5parser does not save source line
        for lineno, line in enumerate(self.text.splitlines(), start=1):
            if PG_EBOOK_START in line:
                self.start_line = lineno + 1
                break

    def css_smallcaps(self):
        """Transform small caps"""
        transforms = {"U": "uppercase", "L": "lowercase", "T": "capitalize"}
        # PPWB only has option for uppercase
        smcap_type = "U" if preferences.get(PrefKey.PPCOMP_CSS_SMCAP) else "N"
        if smcap_type in transforms:
            self.mycss += f".smcap {{ text-transform:{transforms[smcap_type]}; }}"

    def css_bold(self):
        """Surround bold strings with this string"""
        bold_str = "="  # PPWB has no checkbox to change this
        self.mycss += 'b::before, b::after { content: "' + bold_str + '"; }'

    def css_illustration(self):
        """Add [Illustration: ...] markup"""
        if preferences.get(PrefKey.PPCOMP_CSS_ADD_ILLOS):
            for figclass in ["figcenter", "figleft", "figright"]:
                self.mycss += (
                    "." + figclass + '::before { content: "[Illustration: "; }'
                )
                self.mycss += "." + figclass + '::after { content: "]"; }'

    def css_sidenote(self):
        """Add [Sidenote: ...] markup"""
        if preferences.get(PrefKey.PPCOMP_CSS_ADD_SIDENOTES):
            self.mycss += '.sidenote::before { content: "[Sidenote: "; }'
            self.mycss += '.sidenote::after { content: "]"; }'

    def css_greek_title_plus(self):
        """Greek: if there is a title, use it to replace the (grc=ancient) Greek."""
        # if preferences.get(PrefKey.PPCOMP_CSS_GREEK_TITLE):
        #     self.mycss += '*[lang=grc] { content: "+" attr(title) "+"; }'

    def css_custom_css(self):
        """--css can be present multiple times, so it's a list"""
        if not preferences.get(PrefKey.PPCOMP_CSS_CUSTOM):
            return
        custom = [preferences.get(PrefKey.PPCOMP_CSS_CUSTOM_VALUE)]
        for css in custom:
            self.mycss += css

    def remove_nbspaces(self):
        """Remove non-breakable spaces between numbers. For instance, a
        text file could have 250000, and the html could have 250 000.
        """
        if preferences.get(PrefKey.PPCOMP_SUPPRESS_NBSP):
            self.text = re.sub(r"(\d)\u00A0(\d)", r"\1\2", self.text)

    def remove_wordjoin(self):
        """Remove word join (NoBreak) (U+2060)."""
        if preferences.get(PrefKey.PPCOMP_SUPPRESS_WJ):
            self.text = re.sub(r"\u2060", r"", self.text)

    def remove_soft_hyphen(self):
        """Suppress shy (soft hyphen)"""
        self.text = re.sub(r"\u00AD", r"", self.text)

    def cleanup(self):
        """Perform cleanup for this type of file - build up a list of CSS transform rules,
        process them against tree, then convert to text.
        """
        self.strip_pg_boilerplate()
        # load default CSS for transformations
        if not preferences.get(PrefKey.PPCOMP_CSS_NO_DEFAULT):
            self.mycss = DEFAULT_TRANSFORM_CSS
        self.css_smallcaps()
        self.css_bold()
        self.css_illustration()
        self.css_sidenote()
        self.css_custom_css()
        self.process_css()  # process transformations

        self.extract_footnotes()

        # Transform html into text for character search.
        self.text = etree.XPath("string(/)")(self.tree)

        self.remove_nbspaces()
        self.remove_soft_hyphen()
        self.remove_wordjoin()

    @staticmethod
    def _text_transform(val, errors: list):
        """Transform smcaps"""
        if len(val.value) != 1:
            errors += [(val.line, val.column, val.name + " takes 1 argument")]
        else:
            value = val.value[0].value
            if value == "uppercase":
                return lambda x: x.upper()
            if value == "lowercase":
                return lambda x: x.lower()
            if value == "capitalize":
                return lambda x: x.title()
            if value == "superscript":
                return to_superscript
            if value == "subscript":
                return to_subscript
            errors += [
                (
                    val.line,
                    val.column,
                    val.name + " accepts only 'uppercase', 'lowercase', 'capitalize',"
                    " 'superscript', or 'subscript'",
                )
            ]
        return None

    @staticmethod
    def _text_replace(val, errors: list):
        """Skip S (spaces) tokens"""
        values = [v for v in val.value if v.type != "S"]
        if len(values) != 2:
            errors += [(val.line, val.column, val.name + " takes 2 string arguments")]
            return None
        return lambda x: x.replace(values[0].value, values[1].value)

    @staticmethod
    def _text_move(val, errors: list):
        """Move a node"""
        values = [v for v in val.value if v.type != "S"]
        if len(values) < 1:
            errors += [
                (val.line, val.column, val.name + " takes at least one argument")
            ]
            return None
        f_move = []
        for value in values:
            if value.value == "parent":
                f_move.append(lambda el: el.getparent())
            elif value.value == "prev-sib":
                f_move.append(lambda el: el.getprevious())
            elif value.value == "next-sib":
                f_move.append(lambda el: el.getnext())
            else:
                errors += [
                    (val.line, val.column, val.name + " invalid value " + value.value)
                ]
                return None
        return f_move

    def process_css(self):
        """Process each rule from our transformation CSS"""
        # tinycss is not maintained, so needs warnings filtering
        warnings.filterwarnings(
            "ignore", category=SyntaxWarning, module=r"tinycss(\.|$)"
        )
        import tinycss  # type: ignore[import-untyped] # pylint: disable=import-outside-toplevel

        stylesheet = tinycss.make_parser().parse_stylesheet(self.mycss)
        property_errors = []

        def _move_element(elem, move_list):
            """Move elem in tree"""
            parent = elem.getparent()
            new = elem
            for item in move_list:
                new = item(new)
            # move the tail to the sibling or the parent
            if elem.tail:
                sibling = elem.getprevious()
                if sibling:
                    sibling.tail = (sibling.tail or "") + elem.tail
                else:
                    parent.text = (parent.text or "") + elem.tail
                elem.tail = None
            # prune and graft
            parent.remove(elem)
            new.append(elem)

        def _process_element(elem, val):
            """replace text with content of an attribute."""
            if val.name == "content":
                v_content = self.new_content(elem, val)
                if selector.pseudo_element == "before":
                    elem.text = v_content + (elem.text or "")  # opening tag
                elif selector.pseudo_element == "after":
                    elem.tail = v_content + (elem.tail or "")  # closing tag
                else:  # replace all content
                    elem.text = self.new_content(elem, val)
            elif f_replace_with_attr:
                elem.text = f_replace_with_attr(elem)
            elif f_transform:
                self.text_apply(elem, f_transform)
            elif f_element_func:
                f_element_func(elem)
            elif f_move:
                _move_element(elem, f_move)

        for rule in stylesheet.rules:
            # extract values we care about
            f_transform = None
            f_replace_with_attr = None
            f_element_func = None
            f_move = []

            for value in rule.declarations:
                if value.name == "content":
                    pass  # result depends on element and pseudo elements
                elif value.name == "text-transform":
                    f_transform = self._text_transform(value, property_errors)
                elif value.name == "text-replace":
                    f_transform = self._text_replace(value, property_errors)
                elif value.name == "_replace_with_attr":
                    attr_name = value.value[0].value

                    def _replace(elem, attr=attr_name):
                        return elem.attrib[attr]

                    f_replace_with_attr = _replace

                elif value.name == "display":
                    # support display none only. So ignore "none" argument
                    f_element_func = PgdpFileHtml.clear_element
                elif value.name == "_graft":
                    f_move = self._text_move(value, property_errors)
                else:
                    property_errors += [
                        (value.line, value.column, "Unsupported property " + value.name)
                    ]
                    continue

                # iterate through each selector in the rule
                for selector in cssselect.parse(rule.selector.as_css()):
                    xpath = cssselect.HTMLTranslator().selector_to_xpath(selector)
                    find = etree.XPath(xpath)
                    # find each matching elem in the HTML document
                    for element in find(self.tree):
                        _process_element(element, value)

        return self.css_errors(stylesheet.errors, property_errors)

    def css_errors(self, stylesheet_errors, property_errors):
        """Collect transformation CSS errors"""
        css_errors = ""
        if stylesheet_errors or property_errors:
            css_errors = (
                "<div class='error-border bbox'><p>Error(s) in the"
                "  transformation CSS:</p><ul>"
            )
            i = 0
            # if the default css is included, take the offset into account
            if not preferences.get(PrefKey.PPCOMP_CSS_NO_DEFAULT):
                i = DEFAULT_TRANSFORM_CSS.count("\n")
            for err in stylesheet_errors:
                css_errors += f"<li>{err.line - i},{err.column}: {err.reason}</li>"
            for err in property_errors:
                css_errors += f"<li>{err[0] - i},{err[1]}: {err[2]}</li>"
            css_errors += "</ul>"
        return css_errors

    @staticmethod
    def new_content(elem, val):
        """Process the "content:" property"""

        def _escaped_unicode(element):
            try:
                return bytes(element.group(0), "utf8").decode("unicode-escape")
            except UnicodeDecodeError:
                return element.group(0)

        escaped_unicode_re = re.compile(r"\\u[0-9a-fA-F]{4}")
        result = ""
        for token in val.value:
            if token.type == "STRING":  # e.g. { content: "xyz" }
                result += escaped_unicode_re.sub(_escaped_unicode, token.value)
            elif token.type == "FUNCTION":
                if token.function_name == "attr":  # e.g. { content: attr(title) }
                    result += elem.attrib.get(token.content[0].value, "")
            elif token.type == "IDENT":
                if token.value == "content":  # identity, e.g. { content: content }
                    result += elem.text
        return result

    @staticmethod
    def text_apply(tree_elem, func):
        """Apply a function to every sub-element's .text and .tail, and element's .text"""
        if tree_elem.text:
            tree_elem.text = func(tree_elem.text)
        for sub in tree_elem.iter():
            if sub == tree_elem:
                continue
            if sub.text:
                sub.text = func(sub.text)
            if sub.tail:
                sub.tail = func(sub.tail)

    @staticmethod
    def clear_element(element):
        """In an XHTML tree, remove all sub-elements of a given element"""
        tail = element.tail
        element.clear()
        element.tail = tail

    def extract_footnotes(self):
        """Extract the footnotes"""

        def strip_note_tag(string):
            """Remove note tag and number. "Note 123: lorem ipsum" becomes "lorem ipsum"."""
            for regex in [
                r"\s*\[([\w-]+)\](.*)",
                r"\s*([\d]+)\s+(.*)",
                r"\s*([\d]+):(.*)",
                r"\s*Note ([\d]+):\s+(.*)",
            ]:
                match = re.match(regex, string, re.DOTALL)
                if match:
                    return match.group(2)
            return string  # That may be bad

        if not preferences.get(PrefKey.PPCOMP_EXTRACT_FOOTNOTES):
            return
        footnotes = []
        # Special case for PPers who do not keep the marking around
        # the whole footnote. They only mark the first paragraph.
        elements = etree.XPath("//div[@class='footnote']")(self.tree)
        if len(elements) == 1:
            # remove footnote number & remove footnote from main document
            footnotes += [strip_note_tag(elements[0].xpath("string()"))]
            elements[0].getparent().remove(elements[0])
        else:
            for find in [
                "//div[@class='footnote']",
                "//div[@id[starts-with(.,'FN_')]]",
                "//p[a[@id[starts-with(.,'Footnote_')]]]",
                "//div/p[span/a[@id[starts-with(.,'Footnote_')]]]",
                "//p[@class='footnote']",
            ]:
                for element in etree.XPath(find)(self.tree):
                    # remove footnote number & remove footnote from main document
                    footnotes += [strip_note_tag(element.xpath("string()"))]
                    element.getparent().remove(element)
                if footnotes:  # found them, stop now
                    break
        self.footnotes = "\n".join(footnotes)  # save as text string


class PPComp:
    """Compare two files."""

    def __init__(self, args):
        self.args = args

    def do_process(self):
        """Main routine: load & process the files"""
        # files = [None, None]
        # for i, fname in enumerate(self.args.filename):
        #     if fname.lower().endswith((".html", ".htm", ".xhtml")):
        #         files[i] = PgdpFileHtml(self.args)
        #     else:
        #         files[i] = PgdpFileText(self.args)
        #     files[i].load(fname)
        #     files[i].cleanup()  # perform cleanup for each type of file

        # # perform common cleanup for both files
        # self.check_characters(files)

        # # Compare the two versions
        # main_diff = self.compare_texts(files[0].text, files[1].text)
        # if self.args.extract_footnotes:
        #     fnotes_diff = self.compare_texts(files[0].footnotes, files[1].footnotes)
        # else:
        #     fnotes_diff = ""
        # html_content = self.create_html(files, main_diff, fnotes_diff)
        # return html_content, files[0].basename, files[1].basename
        return "", "", ""

    def compare_texts(self, text1, text2):
        """Compare two sources, using dwdiff"""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8"
        ) as temp1, tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as temp2:
            temp1.write(text1)
            temp1.flush()
            temp2.write(text2)
            temp2.flush()
            repo_dir = os.environ.get("OPENSHIFT_DATA_DIR", "")
            if repo_dir:
                dwdiff_path = os.path.join(repo_dir, "bin", "dwdiff")
            else:
                dwdiff_path = "dwdiff"

            # -P Use punctuation characters as delimiters.
            # -R Repeat the begin and end markers at the start and end of line if a change crosses
            #    a newline.
            # -C 2 Show <num> lines of context before and after each changes.
            # -L Show line numbers at the start of each line.
            cmd = [
                dwdiff_path,
                "-P",
                "-R",
                "-C 2",
                "-L",
                "-w ]COMPPP_START_DEL[",
                "-x ]COMPPP_STOP_DEL[",
                "-y ]COMPPP_START_INS[",
                "-z ]COMPPP_STOP_INS[",
            ]
            if self.args.ignore_case:
                cmd += ["--ignore-case"]
            cmd += [temp1.name, temp2.name]
            with subprocess.Popen(cmd, stdout=subprocess.PIPE) as process:
                return process.stdout.read().decode("utf-8")

    def create_html(self, files, text, footnotes):
        """Create the output html file"""

        def massage_input(txt, start0, start1):
            # Massage the input
            replacements = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                "]COMPPP_START_DEL[": "<del>",
                "]COMPPP_STOP_DEL[": "</del>",
                "]COMPPP_START_INS[": "<ins>",
                "]COMPPP_STOP_INS[": "</ins>",
            }
            newtext = txt
            for key, value in replacements.items():
                newtext = newtext.replace(key, value)
            if newtext:
                newtext = "<hr /><pre>\n" + newtext
            newtext = newtext.replace("\n--\n", "\n</pre><hr /><pre>\n")
            newtext = re.sub(
                r"^\s*(\d+):(\d+)",
                lambda m: f"<span class='lineno'>{int(m.group(1)) + start0}"
                f" : {int(m.group(2)) + start1}</span>",
                newtext,
                flags=re.MULTILINE,
            )
            if newtext:
                newtext += "</pre>\n"
            return newtext

        # Find the number of diff sections
        diffs_text = 0
        if text:
            diffs_text = len(re.findall("\n--\n", text)) + 1
            # Text, with correct (?) line numbers
            text = massage_input(text, files[0].start_line, files[1].start_line)
        html_content = "<div>"
        if diffs_text == 0:
            html_content += "<p>There is no diff section in the main text.</p>"
        elif diffs_text == 1:
            html_content += "<p>There is 1 diff section in the main text.</p>"
        else:
            html_content += (
                f"<p>There are <b>{diffs_text}</b> diff sections in the main text.</p>"
            )

        if footnotes:
            diffs_footnotes = len(re.findall("\n--\n", footnotes or "")) + 1
            # Footnotes - line numbers are meaningless right now. We could fix that.
            footnotes = massage_input(footnotes, 0, 0)
            html_content += (
                "<p>Footnotes are diff'ed separately <a href='#footnotes'>here</a></p>"
            )
            if diffs_footnotes == 0:
                html_content += "<p>There is no diff section in the footnotes.</p>"
            elif diffs_footnotes == 1:
                html_content += "<p>There is 1 diff section in the footnotes.</p>"
            else:
                html_content += (
                    f"<p>There are {diffs_footnotes}"
                    " diff sections in the footnotes.</p>"
                )
        else:
            if self.args.extract_footnotes:
                html_content += "<p>There is no diff section in the footnotes.</p>"

        if diffs_text:
            html_content += "<h2>Main text</h2>"
            html_content += text
        if footnotes:
            html_content += "<h2 id='footnotes'>Footnotes</h2>"
            html_content += "<pre>" + footnotes + "</pre>"
        html_content += "</div>"
        return html_content

    def simple_html(self):
        """Debugging only, transform the html and print the text output"""
        if not self.args.filename[0].lower().endswith((".html", ".htm")):
            print("Error: 1st file must be an html file")
            return
        html_file = PgdpFileHtml(self.args)
        html_file.load(self.args.filename[0])
        html_file.cleanup()
        print(html_file.text)
        with open("outhtml.txt", "w", encoding="utf-8") as file:
            file.write(html_file.text)

    @staticmethod
    def check_characters(files):
        """Check whether each file has the 'best' character. If not, convert.
        This is used for instance if one version uses curly quotes while the other uses straight.
        In that case, we need to convert one into the other, to get a smaller diff.
        """
        character_checks = {
            "’": "'",  # close curly single quote to straight
            "‘": "'",  # open curly single quote to straight
            "”": '"',  # close curly double quote to straight
            "“": '"',  # open curly double quote to straight
            "–": "-",  # en dash to hyphen
            "—": "--",  # em dash to double hyphen
            "⁄": "/",  # fraction slash
            "′": "'",  # prime
            "″": "''",  # double prime
            "‴": "'''",  # triple prime
            "½": "-1/2",
            "¼": "-1/4",
            "¾": "-3/4",
        }
        for char_best, char_other in character_checks.items():
            finds_0 = files[0].text.find(char_best)
            finds_1 = files[1].text.find(char_best)
            if finds_0 >= 0 and finds_1 >= 0:  # Both have it
                continue
            if finds_0 == -1 and finds_1 == -1:  # Neither has it
                continue
            # Downgrade one version
            if finds_0 >= 0:
                files[0].text = files[0].text.replace(char_best, char_other)
            else:
                files[1].text = files[1].text.replace(char_best, char_other)
        if files[0].footnotes and files[1].footnotes:
            for char_best, char_other in character_checks.items():
                finds_0 = files[0].footnotes.find(char_best)
                finds_1 = files[1].footnotes.find(char_best)
                if finds_0 >= 0 and finds_1 >= 0:  # Both have it
                    continue
                if finds_0 == -1 and finds_1 == -1:  # Neither has it
                    continue
                if finds_0 >= 0:
                    files[0].footnotes = files[0].footnotes.replace(
                        char_best, char_other
                    )
                else:
                    files[1].footnotes = files[1].footnotes.replace(
                        char_best, char_other
                    )


# noinspection PyPep8
def html_usage(filename1, filename2):
    """Describe how to use the diffs"""
    # noinspection PyPep8
    return f"""
    <div class="bbox">
      <p class="center">— Note —</p>
      <p>The first number is the line number in the first file (<b>{filename1}</b>)<br />
        The second number is the line number in the second file (<b>{filename2}</b>)<br />
        Line numbers can sometimes be very approximate.</p>
      <p>Deleted words that were in the first file but not in the second will appear <del>like
         this</del>.<br />
        Inserted words that were in the second file but not in the first will appear <ins>like
         this</ins>.</p>
    </div>
    """


def output_html(html_content, filename1, filename2, css):
    """Outputs a complete HTML file"""
    print(
        """
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Compare """
        + filename1
        + " and "
        + filename2
        + """</title>
  <style type="text/css">
"""
    )
    print(DIFF_CSS)
    print(
        """
  </style>
</head>
<body>
"""
    )
    print(
        f'<h1>Diff of <span class="first">{filename1}</span> and'
        f' <span class="second">{filename2}</span></h1>'
    )
    print(html_usage(filename1, filename2))
    if css:
        print("<p>Custom CSS added on command line: " + " ".join(css) + "</p>")
    print(html_content)
    print(
        """
</body>
</html>
"""
    )


def main():
    """Main program"""
    parser = argparse.ArgumentParser(
        description="Diff text/HTML documents for PGDP" " Post-Processors."
    )
    parser.add_argument(
        "filename", metavar="FILENAME", type=str, help="input files", nargs=2
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        default=False,
        help="Ignore case when comparing",
    )
    parser.add_argument(
        "--extract-footnotes",
        action="store_true",
        default=False,
        help="Extract and process footnotes separately",
    )
    parser.add_argument(
        "--suppress-footnote-tags",
        action="store_true",
        default=False,
        help='TXT: Suppress "[Footnote #:" marks',
    )
    parser.add_argument(
        "--suppress-illustration-tags",
        action="store_true",
        default=False,
        help='TXT: Suppress "[Illustration:" marks',
    )
    parser.add_argument(
        "--suppress-sidenote-tags",
        action="store_true",
        default=False,
        help='TXT: Suppress "[Sidenote:" marks',
    )
    parser.add_argument(
        "--ignore-format",
        action="store_true",
        default=False,
        help="In Px/Fx versions, silence formatting differences",
    )
    parser.add_argument(
        "--suppress-proofers-notes",
        action="store_true",
        default=False,
        help="In Px/Fx versions, remove [**proofreaders notes]",
    )
    parser.add_argument(
        "--regroup-split-words",
        action="store_true",
        default=False,
        help="In Px/Fx versions, regroup split wo-* *rds",
    )
    parser.add_argument(
        "--txt-cleanup-type",
        type=str,
        default="b",
        help="TXT: In Px/Fx versions, type of text cleaning -- (b)est effort,"
        " (n)one, (p)roofers",
    )
    parser.add_argument(
        "--css-add-illustration",
        action="store_true",
        default=False,
        help="HTML: add [Illustration ] tag",
    )
    parser.add_argument(
        "--css-add-sidenote",
        action="store_true",
        default=False,
        help="HTML: add [Sidenote: ...]",
    )
    parser.add_argument(
        "--css-smcap",
        type=str,
        default=None,
        help="HTML: Transform small caps into uppercase (U), lowercase (L) or"
        " title case (T)",
    )
    parser.add_argument(
        "--css-bold",
        type=str,
        default="=",
        help="HTML: Surround bold strings with this string",
    )
    parser.add_argument(
        "--css",
        type=str,
        default=[],
        action="append",
        help="HTML: Insert transformation CSS",
    )
    parser.add_argument(
        "--css-no-default",
        action="store_true",
        default=False,
        help="HTML: do not use default transformation CSS",
    )
    parser.add_argument(
        "--suppress-nbsp-num",
        action="store_true",
        default=False,
        help="HTML: Suppress non-breakable spaces between numbers",
    )
    parser.add_argument(
        "--suppress-word-join",
        action="store_true",
        default=False,
        help="HTML: Suppress word join (NoBreak) (U+2060)",
    )
    parser.add_argument(
        "--ignore-0-space",
        action="store_true",
        default=False,
        help="HTML: suppress zero width space (U+200b)",
    )
    parser.add_argument(
        "--css-greek-title-plus",
        action="store_true",
        default=False,
        help="HTML: use greek transliteration in title attribute",
    )
    parser.add_argument(
        "--simple-html",
        action="store_true",
        default=False,
        help="HTML: Process just the html file and print the output (debug)",
    )
    args = parser.parse_args()

    if args.extract_footnotes and args.suppress_footnote_tags:
        raise SyntaxError(
            "Cannot use both --extract-footnotes and --suppress-footnote-tags"
        )

    compare = PPComp(args)
    if args.simple_html:
        compare.simple_html()
    else:
        html_content, file1, file2 = compare.do_process()
        output_html(html_content, file1, file2, args.css)


def dumptree(tree):
    """Save tree for debug"""
    with open("tmptree.txt", "w", encoding="utf-8") as file:
        for node in tree.iter():
            if node.text:
                file.write(node.tag + ": " + node.text + "\n")
            else:
                file.write(node.tag + "\n")


if __name__ == "__main__":
    main()
