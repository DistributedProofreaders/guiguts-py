"""Miscellaneous tools."""

from enum import Enum, StrEnum, auto
import importlib.resources
import logging
import operator
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional, Any, TypeVar
import unicodedata

import regex as re

from guiguts.checkers import (
    CheckerDialog,
    CheckerEntry,
    CheckerFilterErrorPrefix,
    CheckerViewOptionsDialog,
    CheckerMatchType,
)
from guiguts.data import scannos
from guiguts.file import the_file
from guiguts.maintext import maintext, menubar_metadata
from guiguts.preferences import (
    PrefKey,
    PersistentString,
    preferences,
    PersistentBoolean,
)
from guiguts.search import (
    get_regex_replacement,
    message_from_regex_exception,
    SearchDialog,
)
from guiguts.utilities import (
    IndexRowCol,
    IndexRange,
    cmd_ctrl_string,
    is_mac,
    sound_bell,
    load_dict_from_json,
    is_debug,
)
from guiguts.widgets import (
    ToplevelDialog,
    PathnameCombobox,
    insert_in_focus_widget,
    ToolTip,
)

logger = logging.getLogger(__package__)

BLOCK_TYPES = "[$*XxFf]"
POEM_TYPES = "[Pp]"
ALL_BLOCKS_REG = f"[{re.escape('#$*FILPXCR')}]"
NEVER_MATCH_REG = "NEVER"
ALWAYS_MATCH_REG = "ALWAYS"
DEFAULT_SCANNOS_DIR = importlib.resources.files(scannos)
DEFAULT_REGEX_SCANNOS = "regex.json"
DEFAULT_STEALTH_SCANNOS = "en-common.json"
DEFAULT_MISSPELLED_SCANNOS = "misspelled.json"

CURLY_QUOTES_CHECKER_FILTERS = [
    CheckerFilterErrorPrefix("Double quote not converted", "DQ not converted: "),
    CheckerFilterErrorPrefix(
        "Other double quote errors", "(Open|Close) DQ.*|DQ not closed: "
    ),
    CheckerFilterErrorPrefix("Single quote not converted", "SQ not converted: "),
    CheckerFilterErrorPrefix(
        "Other single open quote errors", "Open SQ.*|SQ not closed: "
    ),
    CheckerFilterErrorPrefix(
        "Other single close quote errors (may be apostrophes)", "Close SQ.*"
    ),
]


def tool_save() -> bool:
    """File must be saved before running tool, so check if it has been,
    and if not, check if user wants to save, or cancel the tool run.

    Returns:
        True if OK to continue with intended operation.
    """
    if the_file().filename or is_debug():
        return True

    save = messagebox.askokcancel(
        title="Save document",
        message="Document must be saved before running tool",
        icon=messagebox.INFO,
    )
    # User could cancel from messagebox or save-as dialog
    return save and bool(the_file().save_file())


BASIC_FIXUP_CHECKER_FILTERS = [
    CheckerFilterErrorPrefix("Multiple spaces: ", "Multiple spaces: "),
    CheckerFilterErrorPrefix("Spaced hyphen: ", "Spaced hyphen: "),
    CheckerFilterErrorPrefix("Spaced period: ", "Spaced period: "),
    CheckerFilterErrorPrefix("Spaced exclamation mark: ", "Spaced exclamation mark: "),
    CheckerFilterErrorPrefix("Spaced question mark: ", "Spaced question mark: "),
    CheckerFilterErrorPrefix("Spaced comma: ", "Spaced comma: "),
    CheckerFilterErrorPrefix("Spaced colon: ", "Spaced colon: "),
    CheckerFilterErrorPrefix("Spaced semicolon: ", "Spaced semicolon: "),
    CheckerFilterErrorPrefix("Spaced open quote: ", "Spaced open quote: "),
    CheckerFilterErrorPrefix("Spaced close quote: ", "Spaced close quote: "),
    CheckerFilterErrorPrefix("Spaced open bracket: ", "Spaced open bracket: "),
    CheckerFilterErrorPrefix("Spaced close bracket: ", "Spaced close bracket: "),
    CheckerFilterErrorPrefix("Trailing spaces: ", "Trailing spaces: "),
    CheckerFilterErrorPrefix("Thought break: ", "Thought break: "),
    CheckerFilterErrorPrefix("1/l scanno: ", "1/l scanno: "),
    CheckerFilterErrorPrefix("Ellipsis spacing: ", "Ellipsis spacing: "),
    CheckerFilterErrorPrefix("Spaced guillemet: ", "Spaced guillemet: "),
]


class BasicFixupCheckerViewOptionsDialog(CheckerViewOptionsDialog):
    """Minimal class to identify dialog type."""

    manual_page = "Tools_Menu#Basic_Fixup"


class BasicFixupCheckerDialog(CheckerDialog):
    """Basic Fixup dialog."""

    manual_page = "Tools_Menu#Basic_Fixup"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Basic Fixup dialog."""
        super().__init__(
            "Basic Fixup Check Results",
            tooltip="\n".join(
                [
                    "Left click: Select & find issue",
                    "Right click: Hide issue",
                    f"With {cmd_ctrl_string()} key: Also fix issue",
                    "With Shift key: Also hide/fix all issues of this type",
                ]
            ),
            match_on_highlight=CheckerMatchType.ERROR_PREFIX,
            **kwargs,
        )


class BasicFixup:
    """Run Basic Fixup check and allows user to fix errors."""

    def __init__(self) -> None:
        """Initialize HTML Validator."""
        self.dialog = BasicFixupCheckerDialog.show_dialog(
            rerun_command=self.run,
            process_command=self.process_fixup,
            view_options_dialog_class=BasicFixupCheckerViewOptionsDialog,
            view_options_filters=BASIC_FIXUP_CHECKER_FILTERS,
        )

    def run(self) -> None:
        """Check the currently loaded file for basic fixup errors."""

        if not tool_save():
            return

        self.dialog.reset()

        # Check lines that aren't in block markup
        in_block = in_poem = False
        for line, line_num in maintext().get_lines():
            # Ignore lines within block markup
            if re.match(rf"/{BLOCK_TYPES}", line):
                in_block = True
            elif re.match(rf"{BLOCK_TYPES}/", line):
                in_block = False
            if in_block:
                continue

            # Ignore any poem line number (with preceding/trailing spaces)
            if re.match(rf"/{POEM_TYPES}", line):
                in_poem = True
            elif re.match(rf"{POEM_TYPES}/", line):
                in_poem = False
            test_line = line
            if in_poem and (match := re.search(r"\s{2,}\d+\s*$", line)):
                test_line = line[: match.start(0)]

            # Dictionary of regexes:
            # One or two capture groups in each regex, with the characters being checked
            # captured by one of them - these will be highlighted in error message.
            #
            # Multiple spaces between non-space characters
            # Space around single hyphen (not at start of line)
            # Space before single period (not at start of line and not decimal point)
            # Space before exclamation mark, question mark, comma, colon, or semicolon
            # Space before close or after open quotes (where unambiguous)
            # Space before close or after open brackets
            # Trailing spaces
            # Thought break (possibly poorly formed)
            # 1/l scanno, e.g. llth
            fixup_regexes = {
                "Multiple spaces: ": r"(\S\s{2,})(?=\S)",  # Capture character before too
                "Spaced hyphen: ": r"\S( +- *)(?!-)|(?<!-)( *- +)",
                "Spaced period: ": r"\S( +\.)(?![\d\.])",
                "Spaced exclamation mark: ": r"( +!)",
                "Spaced question mark: ": r"( +\?)",
                "Spaced comma: ": r"( +,)",
                "Spaced colon: ": r"( +:)",
                "Spaced semicolon: ": r"( +;)",
                "Spaced open quote: ": r'(^" +|[‘“] +)',
                "Spaced close quote: ": r'( +"$| +”)',
                "Spaced open bracket: ": r"([[({] )",
                "Spaced close bracket: ": r"( [])}])",
                "Trailing spaces: ": r"(.? +$)",
                "Thought break: ": r"^(\s*(\*\s*){4,})$",
                "1/l scanno: ": r"(?<!\p{Letter})(lst|llth)\b",
                "Ellipsis spacing: ": r"(?<=[^\.\!\? \"'‘“])(\.{3})(?![\.\!\?])",
                "Spaced guillemet: ": r"(«\s+|\s+»)",
            }
            # Some languages use inward pointing guillemets - catch most of them.
            # Do inward check if first language is one of these, or English with one of these.
            inward_langs = r"(de|hr|cs|da|hu|pl|sr|sk|sl|sv)"
            languages = maintext().get_language_list()
            if re.match(inward_langs, languages[0]) or (
                re.match("en", languages[0])
                and any(re.match(inward_langs, lang) for lang in languages)
            ):
                fixup_regexes["Spaced guillemet: "] = r"(»\s+|\s+«)"

            for prefix, regex in fixup_regexes.items():
                for match in re.finditer(regex, test_line):
                    group = 2 if match[1] is None else 1
                    self.dialog.add_entry(
                        line,
                        IndexRange(
                            IndexRowCol(line_num, match.start(group)),
                            IndexRowCol(line_num, match.end(group)),
                        ),
                        match.start(group),
                        match.end(group),
                        error_prefix=prefix,
                    )
        self.dialog.display_entries()

    def process_fixup(self, checker_entry: CheckerEntry) -> None:
        """Process the fixup error."""
        if checker_entry.text_range is None:
            return
        entry_type = checker_entry.error_prefix.removesuffix(": ")
        start_mark = BasicFixupCheckerDialog.mark_from_rowcol(
            checker_entry.text_range.start
        )
        end_mark = BasicFixupCheckerDialog.mark_from_rowcol(
            checker_entry.text_range.end
        )
        match_text = maintext().get(start_mark, end_mark)
        # Several fixup errors are "Spaced ..." and need spaces removing.
        if entry_type.startswith("Spaced "):
            replacement_text = match_text.replace(" ", "")
            maintext().replace(start_mark, end_mark, replacement_text)
        elif entry_type == "Trailing spaces":
            replacement_text = match_text.replace(" ", "")
            maintext().replace(start_mark, end_mark, replacement_text)
        elif entry_type == "Multiple spaces":
            # Leave the non-space and first space alone
            replacement_text = match_text[2:].replace(" ", "")
            maintext().replace(f"{start_mark} + 2c", end_mark, replacement_text)
        elif entry_type == "Thought break":
            maintext().replace(start_mark, end_mark, "<tb>")
        elif entry_type == "1/l scanno":
            replacement_text = match_text.replace("llth", "11th").replace("lst", "1st")
            maintext().replace(start_mark, end_mark, replacement_text)
        elif entry_type == "Ellipsis spacing":
            maintext().replace(start_mark, end_mark, " ...")
        else:
            return


class PageSepAutoType(StrEnum):
    """Enum class to store Page Separator sort types."""

    NO_AUTO = auto()
    AUTO_ADVANCE = auto()
    AUTO_FIX = auto()


class PageSeparatorDialog(ToplevelDialog):
    """Dialog for fixing page separators."""

    manual_page = "Tools_Menu#Page_Separator_Fixup"
    SEPARATOR_REGEX = r"^-----File: .+"
    BTN_WIDTH = 16

    def __init__(self) -> None:
        """Initialize page separator dialog."""
        super().__init__("Page Separator Fixup", resize_x=False, resize_y=False)
        for col in range(0, 3):
            self.top_frame.columnconfigure(col, pad=2, weight=1)

        btn_frame = ttk.Frame(
            self.top_frame, borderwidth=1, relief=tk.GROOVE, padding=5
        )
        btn_frame.grid(column=0, row=0, columnspan=3, sticky="NSEW")

        for row in range(0, 3):
            btn_frame.rowconfigure(row, pad=2)
        for col in range(0, 3):
            btn_frame.columnconfigure(col, pad=2, weight=1)
        join_button = ttk.Button(
            btn_frame,
            text="Join",
            underline=0,
            command=lambda: self.join(False),
            width=self.BTN_WIDTH,
        )
        join_button.grid(column=0, row=0, sticky="NSEW")
        self.key_bind("j", join_button.invoke)

        keep_button = ttk.Button(
            btn_frame,
            text="Join, Keep Hyphen",
            underline=6,
            command=lambda: self.join(True),
            width=self.BTN_WIDTH,
        )
        keep_button.grid(column=1, row=0, sticky="NSEW")
        self.key_bind("k", keep_button.invoke)

        delete_button = ttk.Button(
            btn_frame,
            text="Delete",
            underline=0,
            command=self.delete,
            width=self.BTN_WIDTH,
        )
        delete_button.grid(column=2, row=0, sticky="NSEW")
        self.key_bind("d", delete_button.invoke)

        blank_button = ttk.Button(
            btn_frame,
            text="Blank (1 line)",
            underline=0,
            command=lambda: self.blank(1),
            width=self.BTN_WIDTH,
        )
        blank_button.grid(column=0, row=1, sticky="NSEW")
        self.key_bind("b", blank_button.invoke)
        self.key_bind("Key-1", blank_button.invoke)

        section_button = ttk.Button(
            btn_frame,
            underline=0,
            text="Section (2 lines)",
            command=lambda: self.blank(2),
            width=self.BTN_WIDTH,
        )
        section_button.grid(column=1, row=1, sticky="NSEW")
        self.key_bind("s", section_button.invoke)
        self.key_bind("Key-2", section_button.invoke)

        chapter_button = ttk.Button(
            btn_frame,
            underline=0,
            text="Chapter (4 lines)",
            command=lambda: self.blank(4),
            width=self.BTN_WIDTH,
        )
        chapter_button.grid(column=2, row=1, sticky="NSEW")
        self.key_bind("c", chapter_button.invoke)
        self.key_bind("Key-4", chapter_button.invoke)

        auto_type = PersistentString(PrefKey.PAGESEP_AUTO_TYPE)
        ttk.Radiobutton(
            self.top_frame,
            text="No Auto",
            command=self.view,
            variable=auto_type,
            value=PageSepAutoType.NO_AUTO,
        ).grid(column=0, row=1, sticky="NSEW", padx=(20, 2), pady=2)
        ttk.Radiobutton(
            self.top_frame,
            text="Auto Advance",
            command=self.view,
            variable=auto_type,
            value=PageSepAutoType.AUTO_ADVANCE,
        ).grid(column=1, row=1, sticky="NSEW", padx=2, pady=2)
        ttk.Radiobutton(
            self.top_frame,
            text="Auto Fix",
            command=self.view,
            variable=auto_type,
            value=PageSepAutoType.AUTO_FIX,
        ).grid(column=2, row=1, sticky="NSEW", padx=2, pady=2)

        end_frame = ttk.Frame(
            self.top_frame, borderwidth=1, relief=tk.GROOVE, padding=5
        )
        end_frame.grid(column=0, row=2, columnspan=3, sticky="NSEW")
        for col in range(0, 3):
            end_frame.columnconfigure(col, pad=2, weight=1)

        undo_button = ttk.Button(
            end_frame,
            text="Undo",
            command=lambda: maintext().event_generate("<<Undo>>"),
            underline=0,
            width=self.BTN_WIDTH,
        )
        undo_button.grid(column=0, row=0, sticky="NSEW")
        self.key_bind("u", lambda: maintext().event_generate("<<Undo>>"))
        self.key_bind("Cmd/Ctrl+Z", lambda: maintext().event_generate("<<Undo>>"))

        redo_button = ttk.Button(
            end_frame,
            text="Redo",
            command=lambda: maintext().event_generate("<<Redo>>"),
            underline=1,
            width=self.BTN_WIDTH,
        )
        redo_button.grid(column=1, row=0, sticky="NSEW")
        self.key_bind("e", lambda: maintext().event_generate("<<Redo>>"))
        self.key_bind(
            "Cmd+Shift+Z" if is_mac() else "Ctrl+Y",
            lambda: maintext().event_generate("<<Redo>>"),
        )

        refresh_button = ttk.Button(
            end_frame,
            text="Refresh",
            command=self.refresh,
            underline=0,
            width=self.BTN_WIDTH,
        )
        refresh_button.grid(column=2, row=0, sticky="NSEW")
        self.key_bind("r", refresh_button.invoke)

        # If user does undo/redo, we want to re-view the active page separator
        maintext().add_undo_redo_callback(self.get_dlg_name(), self.view)

    def on_destroy(self) -> None:
        """Tidy up when the dialog is destroyed - remove undo/redo callback."""
        maintext().remove_undo_redo_callback(self.get_dlg_name())
        super().on_destroy()

    def do_join(self, keep_hyphen: bool) -> None:
        """Join 2 lines if hyphenated, otherwise just remove separator line(s).

        Args:
            keep_hyphen: True to keep hyphen when lines are joined.
        """
        if (sep_range := self.find()) is None:
            return

        # Don't try to join if page ends with "]" or "]*" because that probably means
        # there's a possible mid-para footnote/sidenote/illo at the page end
        start_index = sep_range.start.index()
        mid_para_check = maintext().get(f"{start_index}-2l", f"{start_index}-1c")
        if mid_para_check.endswith("]") or mid_para_check.endswith("]*"):
            return

        sep_range = self.fix_pagebreak_markup(sep_range)
        maintext().delete(start_index, sep_range.end.index())
        prev_eol = f"{start_index} -1l lineend"
        maybe_hyphen = maintext().get(f"{prev_eol}-1c", prev_eol)
        # If "*" at end of line, check previous character for "-"
        if maybe_hyphen == "*":
            prev_eol = f"{prev_eol} -1c"
            maybe_hyphen = maintext().get(f"{prev_eol}-1c", prev_eol)
        # Check for emdash (double-hyphen)
        maybe_second_hyphen = ""
        if maybe_hyphen == "-":
            maybe_second_hyphen = maintext().get(f"{prev_eol}-2c", f"{prev_eol} -1c")
        # Adjust effective end of line position depending if hyphen is being kept
        # (always keep emdash)
        if not keep_hyphen and maybe_hyphen == "-" and maybe_second_hyphen != "-":
            prev_eol = f"{prev_eol} -1c"
        # If emdash at start of second page, also want to join,
        # even if no hyphen at end of first page.
        next_bol = f"{sep_range.start.index()} linestart"
        # Omit any "*" at beginning of next line
        if maintext().get(next_bol, f"{next_bol}+1c") == "*":
            maintext().delete(next_bol)
        maybe_page2_emdash = maintext().get(next_bol, f"{next_bol}+2c")

        # If word is hyphenated or emdash, move second part of word to end of first part
        if maybe_hyphen == "-" or maybe_page2_emdash == "--":
            word_end = maintext().search(" ", next_bol, f"{next_bol} lineend")
            if not word_end:
                word_end = maintext().index(f"{next_bol} lineend")
            # Delete one character (space or newline) after second part of word
            maintext().delete(word_end)
            second_part = maintext().get(next_bol, word_end)
            maintext().delete(next_bol, word_end)
            # Delete maybe hyphen, & asterisks at end of prev line
            maintext().delete(prev_eol, f"{prev_eol} lineend")
            # Insert second part of word at end of prev line
            maintext().insert(f"{prev_eol} lineend", second_part)
        maintext().set_insert_index(sep_range.start, focus=False)

    def do_delete(self) -> None:
        """Just remove separator line."""
        if (sep_range := self.find()) is None:
            return
        maintext().delete(sep_range.start.index(), sep_range.end.index())
        maintext().set_insert_index(sep_range.start, focus=False)

    def do_blank(self, num_lines: int) -> None:
        """Replace separator & adjacent blank lines with given number of blank lines.

        Args:
            num_lines: How many blank lines to use.
        """
        if (sep_range := self.find()) is None:
            return
        # Find previous end and next start of non-whitespace, to replace with given number of blank lines
        end_prev = maintext().search(
            r"\S",
            sep_range.start.index(),
            "1.0",
            backwards=True,
            regexp=True,
        )
        end_prev = f"{end_prev}+1l linestart" if end_prev else "1.0"
        beg_next = maintext().search(r"\S", sep_range.end.index(), tk.END, regexp=True)
        beg_next = f"{beg_next} linestart" if beg_next else tk.END
        maintext().replace(end_prev, beg_next, num_lines * "\n")
        maintext().set_insert_index(sep_range.start, focus=False)

    def refresh(self) -> None:
        """Refresh to show the first available page separator."""
        maintext().undo_block_begin()
        self.do_auto()
        self.view()

    def join(self, keep_hyphen: bool) -> None:
        """Handle click on Join buttons.

        Args:
            keep_hyphen: True to keep hyphen when lines are joined.
        """
        maintext().undo_block_begin()
        self.do_join(keep_hyphen)
        self.do_auto()

    def delete(self) -> None:
        """Handle click on Delete button."""
        maintext().undo_block_begin()
        self.do_delete()
        self.do_auto()

    def blank(self, num_lines: int) -> None:
        """Handle click on Blank buttons.

        Args:
            num_lines: How many blank lines to use.
        """
        maintext().undo_block_begin()
        self.do_blank(num_lines)
        self.do_auto()

    def view(self) -> None:
        """Show the first available separator line to be processed."""
        if (sep_range := self.find()) is None:
            return
        maintext().do_select(sep_range)
        maintext().set_insert_index(sep_range.start, focus=False)

    def find(self) -> Optional[IndexRange]:
        """Find the first available separator line.

        Returns:
            IndexRange containing start & end of separator, or None.
        """
        match = maintext().find_match(
            PageSeparatorDialog.SEPARATOR_REGEX,
            maintext().start_to_end(),
            nocase=False,
            regexp=True,
            backwards=False,
        )
        if match is None:
            return None
        end_rowcol = IndexRowCol(match.rowcol.row + 1, match.rowcol.col)
        return IndexRange(match.rowcol, end_rowcol)

    def fix_pagebreak_markup(self, sep_range: IndexRange) -> IndexRange:
        """Remove markup, e.g. italics or blockquote, if closed immediately before
        page break and same markup is reopened immediately afterwards.

        Args:
            sep_range: Range of page separator line.

        Returns:
            Updated page separator range (removal of markup may have affected page sep line number)
        """
        # Remove all but one page sep lines at this location. As each is deleted
        # the next will be move up to lie at the same location.
        line = ""
        while True:
            del_range = self.find()
            if del_range is None or del_range.start != sep_range.start:
                break
            line = maintext().get(sep_range.start.index(), sep_range.end.index())
            maintext().delete(sep_range.start.index(), sep_range.end.index())
        # Add last one back
        maintext().insert(sep_range.start.index(), line)
        ps_start = sep_range.start.index()
        ps_end = sep_range.end.index()
        maybe_more_to_remove = True
        while maybe_more_to_remove:
            maybe_more_to_remove = False
            markup_prev = maintext().get(
                f"{ps_start}-1l lineend -6c",
                f"{ps_start}-1l lineend",
            )
            markup_next = maintext().get(
                f"{ps_end}",
                f"{ps_end} +4c",
            )
            # Remove blockquote or nowrap markup
            if match := re.search(r"(\*|#)/$", markup_prev):
                markup_type = re.escape(match[1])
                if re.search(rf"^/{markup_type}", markup_next):
                    maintext().delete(
                        ps_end,
                        f"{ps_end} +1l",
                    )
                    maintext().delete(
                        f"{ps_start}-1l",
                        ps_start,
                    )
                    # Compensate for having deleted a line before the page separator
                    ps_start = maintext().index(f"{ps_start}-1l")
                    ps_end = maintext().index(f"{ps_end}-1l")
                    maybe_more_to_remove = True
            # Remove inline markup
            elif match := re.search(r"</(i|b|f|g|sc)>([,;*]?)$", markup_prev):
                markup_type = match[1]
                len_markup = len(markup_type)
                len_punc = len(match[2])
                if re.search(rf"^<{markup_type}>", markup_next):
                    maintext().delete(
                        f"{ps_end}",
                        f"{ps_end} +{len_markup + 2}c",
                    )
                    maintext().delete(
                        f"{ps_start}-1l lineend -{len_markup + len_punc + 3}c",
                        f"{ps_start}-1l lineend -{len_punc}c",
                    )
                    maybe_more_to_remove = True
        return IndexRange(ps_start, ps_end)

    def do_auto(self) -> None:
        """Do auto page separator fixing if allowed by settings."""
        if preferences.get(PrefKey.PAGESEP_AUTO_TYPE) == PageSepAutoType.NO_AUTO:
            return
        if preferences.get(PrefKey.PAGESEP_AUTO_TYPE) == PageSepAutoType.AUTO_ADVANCE:
            self.view()
            return

        # Auto-fix: Loop through page separators, fixing them if possible
        while sep_range := self.find():
            # Fix markup across page break, even though the join function would fix it later,
            # because otherwise it would interfere with check for automated joining below.
            sep_range = self.fix_pagebreak_markup(sep_range)
            line_prev = maintext().get(
                f"{sep_range.start.index()}-1l lineend -10c",
                f"{sep_range.start.index()}-1l lineend",
            )
            line_next = maintext().get(
                f"{sep_range.end.index()}",
                f"{sep_range.end.index()}+10c",
            )
            if line_next.startswith(4 * "\n"):
                self.do_blank(4)
            elif line_next.startswith(2 * "\n"):
                self.do_blank(2)
            elif line_next.startswith(1 * "\n"):
                self.do_blank(1)
            elif line_next.startswith("-----File:"):
                self.do_delete()
            elif not (
                re.search(r"^\*?-(?!-)", line_next)
                or re.search(r"(?<!-)-\*?$", line_prev)
                or line_prev.endswith("]")
                or line_prev.endswith("]*")
            ):
                # No hyphen before/after page break and no mid-para
                # footnote, sidenote or illo, so OK to join
                self.do_join(False)
            else:
                break
        self.view()


def page_separator_fixup() -> None:
    """Fix and remove page separator lines."""
    dlg = PageSeparatorDialog.show_dialog()
    dlg.view()


UnMatchedChkDlg = TypeVar("UnMatchedChkDlg", bound="UnmatchedCheckerDialog")


class UnmatchedCheckerDialog(CheckerDialog):
    """Unmatched Pairs Checker dialog."""

    manual_page = 'Tools_Menu#"Unmatched"_Submenu'

    def __init__(self, title: str, **kwargs: Any) -> None:
        """Initialize Unmatched Pairs Checker dialog."""
        super().__init__(
            title,
            tooltip="\n".join(
                [
                    "Left click: Select & find issue",
                    "Right click: Hide issue",
                    "Shift-Right click: Also hide all matching issues",
                ]
            ),
            **kwargs,
        )


class UnmatchedBracketDialog(UnmatchedCheckerDialog):
    """Unmatched Bracket Markup dialog."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Unmatched Bracket Markup dialog."""
        super().__init__("Unmatched Bracket markup", **kwargs)


class UnmatchedDPMarkupDialog(UnmatchedCheckerDialog):
    """Unmatched DP Markup dialog."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Unmatched DP Markup dialog."""
        super().__init__("Unmatched DP markup", **kwargs)


class UnmatchedHTMLTagDialog(UnmatchedCheckerDialog):
    """Unmatched HTML Tag dialog."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Unmatched HTML Tag dialog."""
        super().__init__("Unmatched HTML tags", **kwargs)


class UnmatchedBlockMarkupDialog(UnmatchedCheckerDialog):
    """Unmatched Block Markup dialog."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Unmatched Block Markup dialog."""
        super().__init__("Unmatched Block markup", **kwargs)


def unmatched_brackets() -> None:
    """Check for unmatched brackets."""

    def toggle_bracket(bracket_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close bracket.

        Args:
            bracket_in: Bracket - must be one of ( [ { ) ] }

        Returns:
            Tuple with regex, True if bracket_in was close bracket.
        """
        match bracket_in:
            case "(":
                return "[)(]", False
            case ")":
                return "[)(]", True
            case "{":
                return "[}{]", False
            case "}":
                return "[}{]", True
            case "[":
                return "[][]", False
            case "]":
                return "[][]", True
        assert False, f"'{bracket_in}' is not a bracket character"

    unmatched_markup_check(
        UnmatchedBracketDialog,
        rerun_command=unmatched_brackets,
        match_reg="[][}{)(]",
        match_pair_func=toggle_bracket,
    )


def unmatched_dp_markup() -> None:
    """Check for unmatched DP markup."""

    def matched_pair_dp_markup(markup_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close DP markup.

        Args:
            markup_in: Markup string - must be "<i>", "</b>", "<sc>", etc.

        Returns:
            Tuple with regex, True if markup_in was close markup.
        """
        if markup_in[1] == "/":
            return f"(<{markup_in[2:-1]}>|{markup_in})", True
        return f"({markup_in}|</{markup_in[1:-1]}>)", False

    def sort_key_dp_markup(
        entry: CheckerEntry,
    ) -> tuple[str, bool, int, int]:
        """Sort key function to sort bad DP  entries by casefolded text.

        Order is type of markup (e.g. b, i, sc), open/close, row, col.
        """
        assert entry.text_range is not None
        text = entry.text[entry.hilite_start : entry.hilite_end]
        type_lower = text.lower().replace("/", "")[1:-1]
        return (
            type_lower,
            "/" in text,
            entry.text_range.start.row,
            entry.text_range.start.col,
        )

    unmatched_markup_check(
        UnmatchedDPMarkupDialog,
        rerun_command=unmatched_dp_markup,
        match_reg="<(i|b|u|g|f|sc)>|</(i|b|u|g|f|sc)>",
        match_pair_func=matched_pair_dp_markup,
        nest_reg=NEVER_MATCH_REG,
        ignore_reg="<tb>",
        sort_key_alpha=sort_key_dp_markup,
    )


def unmatched_html_markup() -> None:
    """Check for unmatched HTML markup."""

    open_regex = "<([[:alnum:]]+)( [^>\n]+)?>"
    close_regex = "</([[:alnum:]]+)>"

    def get_tag_type_regex(markup_in: str) -> str:
        """Get the type of the given tag, e.g. "<div class='abc'>" gives "div".

        Escaped so suitable for use in a regex.
        """
        return re.escape(re.sub(open_regex, r"\1", markup_in.replace("/", "")))

    def matched_pair_html_markup(markup_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close HTML markup.

        Args:
            markup_in: Markup string - must be "<i>", "</b>", "<div class='...'>", etc.

        Returns:
            Tuple with regex, True if markup_in was close markup.
        """
        mtype = get_tag_type_regex(markup_in)
        return f"(<{mtype}( [^>\n]+)?>|</{mtype}>)", (markup_in[1] == "/")

    def sort_key_html_markup(
        entry: CheckerEntry,
    ) -> tuple[str, bool, int, int]:
        """Sort key function to sort bad HTML tags.

        Order is type of markup (e.g. b, div, span), open/close, row, col.
        """
        assert entry.text_range is not None
        text = entry.text[entry.hilite_start : entry.hilite_end]
        mtype = get_tag_type_regex(text)
        return (
            mtype,
            "/" in text,
            entry.text_range.start.row,
            entry.text_range.start.col,
        )

    def equiv_func(s1: str, s2: str) -> bool:
        """Check if two html tags are equivalent, i.e. the same type of tag,
        and both opening or both closing. This is to make `<p class="center">`
        match `<p>`, for example, which simple equality would not.
        """
        s1 = re.sub(open_regex, r"<\1>", s1)
        s2 = re.sub(open_regex, r"<\1>", s2)
        return s1 == s2

    unmatched_markup_check(
        UnmatchedHTMLTagDialog,
        rerun_command=unmatched_html_markup,
        match_reg=f"{open_regex}|{close_regex}",
        match_pair_func=matched_pair_html_markup,
        nest_reg=ALWAYS_MATCH_REG,
        ignore_reg="<(area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr).*?>",
        sort_key_alpha=sort_key_html_markup,
        equiv_func=equiv_func,
    )


def unmatched_block_markup() -> None:
    """Check for unmatched block markup."""

    def match_pair_block_markup(markup_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close block markup.

        Args:
            markup_in: Markup string - must be "/#", "/*", "C/", etc.

        Returns:
            Tuple with regex, True if markup_in was close markup.
        """
        close = markup_in[1] == "/"
        block_type = markup_in[0] if close else markup_in[1]
        block_type = re.escape(block_type)
        return rf"^(/{block_type}(\[\d+)?(\.\d+)?(,\d+)?]?|{block_type}/)$", close

    def malformed_block_markup(dialog: UnmatchedCheckerDialog) -> None:
        """Add warnings about malformed block markup to given dialog.

        Args:
            dialog: UnmatchedCheckerDialog to receive error messages.
        """
        search_range = maintext().start_to_end()
        prefix = "Badly formed markup: "
        while match := maintext().find_match(
            f"(/{ALL_BLOCKS_REG}|{ALL_BLOCKS_REG}/)",
            search_range,
            regexp=True,
            nocase=True,
        ):
            match_index = match.rowcol.index()
            after_match = maintext().index(f"{match_index}+{match.count}c")
            search_range = IndexRange(after_match, maintext().end())
            match_str = maintext().get_match_text(match)
            # Don't report if open markup preceded by non-space, e.g. "</i>"(markup) or "z/l"(math)
            if (
                match_str[0] == "/"
                and not maintext().get(f"{match_index}-1c").isspace()
            ):
                continue
            # Nor if close markup followed by word character, e.g. "i/j"(math)
            if match_str[1] == "/" and re.match(
                r"\w", maintext().get(f"{match_index}+2c")
            ):
                continue
            # Now check if markup is malformed - get whole line and check against regex
            line = maintext().get(f"{match_index} linestart", f"{match_index} lineend")
            try:
                idx_start = len(prefix) + line.index(match_str)
                idx_end = idx_start + len(match_str)
            except ValueError:
                idx_start = None
                idx_end = None
            block_type = re.escape(match_str.replace("/", ""))
            regex = rf"^(/{block_type}(\[(\d+)?(\.\d+)?(,\d+)?])?|{block_type}/)$"
            if not re.fullmatch(regex, line):
                dialog.add_entry(
                    f"{prefix}{line}",
                    IndexRange(match_index, after_match),
                    idx_start,
                    idx_end,
                )

    def sort_key_block_markup(
        entry: CheckerEntry,
    ) -> tuple[str, str, int, int, int]:
        """Sort key function to sort bad markup entries by casefolded text.

        Order is type of error (badly formed or unmatched), type of markup (e.g. #, *, P),
        open/close markup, row, col.
        """
        assert entry.text_range is not None
        text = entry.text[entry.hilite_start : entry.hilite_end]
        type_lower = text.lower().replace("/", "")
        open_close_index = text.index("/")
        return (
            entry.text.split(":")[0],
            type_lower,
            open_close_index,
            entry.text_range.start.row,
            entry.text_range.start.col,
        )

    unmatched_markup_check(
        UnmatchedBlockMarkupDialog,
        rerun_command=unmatched_block_markup,
        match_reg=f"^(/{ALL_BLOCKS_REG}|{ALL_BLOCKS_REG}/)",
        match_pair_func=match_pair_block_markup,
        nest_reg="/#|#/",
        sort_key_alpha=sort_key_block_markup,
        additional_check_command=malformed_block_markup,
    )


def unmatched_markup_check(
    dlg_type: type[UnMatchedChkDlg],
    rerun_command: Callable[[], None],
    match_reg: str,
    match_pair_func: Callable[[str], tuple[str, bool]],
    nest_reg: Optional[str] = None,
    ignore_reg: Optional[str] = None,
    sort_key_alpha: Optional[Callable[[CheckerEntry], tuple]] = None,
    additional_check_command: Optional[Callable[[UnmatchedCheckerDialog], None]] = None,
    equiv_func: Optional[Callable[[str, str], bool]] = None,
) -> None:
    """Check the currently loaded file for unmatched markup errors.

    Args:
        dlg_type: Dialog type to display results in.
        rerun_command: Function to re-run check.
        match_reg: Regex matching open & close markup.
        nest_reg: Regex matching markup that is allowed to be nested.
            None means user-controlled via Pref.
        ignore_reg: Regex matching markup that is to be ignored during check.
        sort_key_alpha: Function to provide type/alphabetic sorting
        additional_check_command: Function to perform extra checks
        equiv_func: Function to check if items are equivalent - defaults to `==`
    """

    if not tool_save():
        return

    checker_dialog = dlg_type.show_dialog(
        rerun_command=rerun_command,
        sort_key_alpha=sort_key_alpha,
    )

    # User can control nestability of some unmatched check types
    if nest_reg is None:
        frame = ttk.Frame(checker_dialog.custom_frame)
        frame.grid(column=0, row=1, sticky="NSEW")
        ttk.Checkbutton(
            frame,
            text="Allow nesting",
            variable=PersistentBoolean(PrefKey.UNMATCHED_NESTABLE),
        ).grid(row=0, column=0, sticky="NSEW")

    search_range = maintext().start_to_end()
    # Find each piece of markup that matches the regex
    while match := maintext().find_match(
        match_reg, search_range, regexp=True, nocase=True
    ):
        match_index = match.rowcol.index()
        after_match = maintext().index(f"{match_index}+{match.count}c")
        search_range = IndexRange(after_match, maintext().end())
        match_str = maintext().get_match_text(match)
        # Ignore if it matches the ignore regex
        if ignore_reg and re.fullmatch(ignore_reg, match_str, flags=re.IGNORECASE):
            continue
        # Get a regex that will find the match and the pair( e.g. "(<i>|</i>)")
        match_pair_reg, reverse = match_pair_func(match_str)
        # Is this markup permitted to nest?
        if nest_reg is None:
            nestable = preferences.get(PrefKey.UNMATCHED_NESTABLE)
        elif nest_reg == NEVER_MATCH_REG:
            nestable = False
        elif nest_reg == ALWAYS_MATCH_REG:
            nestable = True
        else:
            nestable = bool(re.fullmatch(nest_reg, match_str, flags=re.IGNORECASE))
        prefix = "Unmatched: "
        # Search for the matching pair to this markup
        if not find_match_pair(
            match_index,
            match_str,
            match_pair_reg,
            reverse,
            nestable,
            equiv_func=equiv_func,
        ):
            checker_dialog.add_entry(
                f"{prefix}{match_str}",
                IndexRange(match_index, after_match),
                len(prefix),
                len(prefix) + match.count,
            )

    if additional_check_command:
        additional_check_command(checker_dialog)
    checker_dialog.display_entries()


def find_match_pair(
    match_index: str,
    match_str: str,
    match_pair_reg: str,
    reverse: bool,
    nestable: bool,
    ignore_func: Optional[Callable[[str], bool]] = None,
    equiv_func: Optional[Callable[[str, str], bool]] = None,
) -> str:
    """Find the pair to the given match.

    Args:
        match_index: Index of start of match_str in file.
        match_str: String to find the pair of.
        pair_str: The pair string to search for.
        reverse: True to search backwards (i.e. given close, look for open).
        nestable: True if markup is allowed to nest.
        ignore_func: Optional function that returns whether to ignore a potential match.
    """
    found = ""
    match_len = len(match_str)
    depth = 1
    start = match_index if reverse else maintext().index(f"{match_index}+{match_len}c")
    end = maintext().start() if reverse else maintext().end()

    if equiv_func is None:
        equiv_func = operator.eq
    # Keep searching until we find the markup that brings us back
    # to the same depth as the given markup (or until there's an error)
    while depth > 0:
        # Search for the given markup and its pair in order to spot nesting
        match = maintext().find_match(
            match_pair_reg,
            IndexRange(start, end),
            regexp=True,
            backwards=reverse,
            nocase=True,
        )
        if match is None:
            found = ""
            break

        # If match shouldn't be ignored, adjust depth and check if nesting is allowed
        match_index = match.rowcol.index()
        if ignore_func is None or not ignore_func(match_index):
            depth += (
                1
                if equiv_func(
                    maintext().get_match_text(match).lower(), match_str.lower()
                )
                else -1
            )
            # Check it's not nested when nesting isn't allowed
            if depth > 1 and not nestable:
                found = ""
                break
            found = match_index

        # Adjust start point for next search
        start = (
            match_index
            if reverse
            else maintext().index(f"{match_index}+{match.count}c")
        )
    return found


class FractionConvertType(Enum):
    """Enum class to store fraction conversion types."""

    UNICODE = auto()  # convert only those that have a Unicode fraction
    MIXED = auto()  # convert to Unicode if possible, otherwise super/subscript
    SUPSUB = auto()  # convert all to super/subscript form


def fraction_convert(conversion_type: FractionConvertType) -> None:
    """Convert fractions in selection or whole file, e.g. 1/2 --> ½

    Args:
        conversion_type: Determines which/how fractions will be converted.
    """

    unicode_fractions = {
        "1/4": "¼",
        "1/2": "½",
        "3/4": "¾",
        "1/7": "⅐",
        "1/9": "⅑",
        "1/10": "⅒",
        "1/3": "⅓",
        "2/3": "⅔",
        "1/5": "⅕",
        "2/5": "⅖",
        "3/5": "⅗",
        "4/5": "⅘",
        "1/6": "⅙",
        "5/6": "⅚",
        "1/8": "⅛",
        "3/8": "⅜",
        "5/8": "⅝",
        "7/8": "⅝",
    }
    superscripts = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    subscripts = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

    maintext().undo_block_begin()
    maintext().selection_ranges_store_with_marks()

    sel_ranges = maintext().selected_ranges()
    if not sel_ranges:
        sel_ranges = [maintext().start_to_end()]

    last_match = ""
    frac_slash = "⁄"
    any_slash = f"[/{frac_slash}]"
    for sel_range in sel_ranges:
        # Use mark for the end of the range, since end index can move as changes are made
        maintext().set_mark_position("TempEndSelection", sel_range.end)

        search_range = IndexRange(
            sel_range.start, maintext().rowcol("TempEndSelection")
        )
        match_regex = rf"(\d-)?(\d+){any_slash}(\d+)(?!\d*,\d)"
        while match := maintext().find_match(match_regex, search_range, regexp=True):
            match_str = maintext().get_match_text(match)
            gmatch = re.fullmatch(match_regex, match_str)
            assert gmatch is not None  # Has to match because we used the same regex

            # Allow for matching the "1-" in "1-2/3"
            # match_index is start of section being replaced, i.e. "-2/3"
            offset = 0 if gmatch[1] is None else 1
            match_index = f"{match.rowcol.index()}+{offset}c"

            base_frac = f"{gmatch[2]}/{gmatch[3]}"
            new_frac = ""
            if (
                base_frac in unicode_fractions
                and conversion_type != FractionConvertType.SUPSUB
            ):
                new_frac = unicode_fractions[base_frac]
            elif conversion_type != FractionConvertType.UNICODE:
                new_frac = f"{gmatch[2].translate(superscripts)}{frac_slash}{gmatch[3].translate(subscripts)}"
            # Only convert if we found one that should be converted. Don't convert strings like
            # "B1/2" or "C-1/3" - probably a plate/serial number, but not a fraction.
            # Also don't convert ".2/18" - probably "4.2/18.6" and converting the "2/18" would be wrong.
            prefix = maintext().get(
                f"{match.rowcol.index()} linestart", match.rowcol.index()
            )
            if (
                new_frac
                and not re.search(r"\p{L}-?$", prefix)
                and not prefix.endswith(".")
            ):
                len_frac = len(new_frac)
                maintext().insert(match_index, new_frac)
                maintext().delete(
                    f"{match_index}+{len(new_frac)}c",
                    f"{match_index}+{len(new_frac) + len(gmatch[0]) - offset}c",
                )
                last_match = f"{match_index}+{len(new_frac)}c"
            else:
                len_frac = len(base_frac) - offset

            after_match = maintext().rowcol(f"{match_index}+{len_frac}c")
            search_range = IndexRange(
                after_match, maintext().rowcol("TempEndSelection")
            )
    maintext().selection_ranges_restore_from_marks()
    if last_match:
        maintext().set_insert_index(IndexRowCol(maintext().index(last_match)))


def unicode_normalize() -> None:
    """Normalize selected characters into Unicode Normalization Form C.

    Replaces one line at a time to avoid page marker drift.
    """
    sel_ranges = maintext().selected_ranges()
    if not sel_ranges:
        return

    for sel_range in sel_ranges:
        for row in range(sel_range.start.row, sel_range.end.row + 1):
            # Set start/end columns of first/last rows, else normalize whole line
            if row == sel_range.start.row:
                start_idx = f"{row}.{sel_range.start.col}"
            else:
                start_idx = f"{row}.0"
            if row == sel_range.end.row:
                end_idx = f"{row}.{sel_range.end.col}"
            else:
                end_idx = f"{row}.end"
            text = maintext().get(start_idx, end_idx)
            if not unicodedata.is_normalized("NFC", text):
                normalized_text = unicodedata.normalize("NFC", text)
                maintext().replace(start_idx, end_idx, normalized_text)


class ProoferCommentCheckerDialog(CheckerDialog):
    """Proofer Comment Checker dialog."""

    manual_page = "Search_Menu#Find_Proofer_Comments_(_[**_notes]_)"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Proofer Comment dialog."""
        super().__init__(
            "Proofer Comments",
            tooltip="\n".join(
                [
                    "Left click: Select & find comment",
                    "Right click: Hide comment",
                    "Shift Right click: Also hide all matching comments",
                    f"With {cmd_ctrl_string()} key: Also delete the commment(s)",
                ]
            ),
            **kwargs,
        )


class ProoferCommentChecker:
    """Proofer Comment checker."""

    def __init__(self) -> None:
        """Initialize Proofer Comment checker."""

        self.dialog = ProoferCommentCheckerDialog.show_dialog(
            rerun_command=self.run,
            process_command=self.delete_comment,
            match_on_highlight=CheckerMatchType.HIGHLIGHT,
            show_process_buttons=False,
            reverse_mark_gravities=True,
        )
        # Taken from CheckerDialog
        fix_btn = ttk.Button(
            self.dialog.message_controls_frame,
            text="Delete",
            command=lambda: self.dialog.process_entry_current(all_matching=False),
        )
        fix_btn.grid(row=0, column=2, sticky="NSEW")
        ToolTip(fix_btn, f"Delete selected comment ({cmd_ctrl_string()} left-click)")
        fixall_btn = ttk.Button(
            self.dialog.message_controls_frame,
            text="Delete Matching",
            command=lambda: self.dialog.process_entry_current(all_matching=True),
        )
        fixall_btn.grid(row=0, column=3, sticky="NSEW")
        ToolTip(
            fixall_btn,
            f"Delete all identical comments matching selected one (Shift {cmd_ctrl_string()} left-click)",
        )
        fixrem_btn = ttk.Button(
            self.dialog.message_controls_frame,
            text="Delete&Hide",
            command=lambda: self.dialog.process_remove_entry_current(
                all_matching=False
            ),
        )
        fixrem_btn.grid(row=0, column=4, sticky="NSEW")
        ToolTip(
            fixrem_btn,
            f"Delete selected comment & hide message ({cmd_ctrl_string()} right-click)",
        )
        fixremall_btn = ttk.Button(
            self.dialog.message_controls_frame,
            text="Delete&Hide Matching",
            command=lambda: self.dialog.process_remove_entry_current(all_matching=True),
        )
        fixremall_btn.grid(row=0, column=5, sticky="NSEW")
        ToolTip(
            fixremall_btn,
            f"Delete and hide all identical comments matching selected one (Shift {cmd_ctrl_string()} right-click)",
        )

    def run(self) -> None:
        """Do the actual check and add messages to the dialog."""
        self.dialog.reset()

        matches = maintext().find_matches(
            r"\[\*\*([^]]|\n)*]",
            maintext().start_to_end(),
            nocase=False,
            regexp=True,
        )

        for match in matches:
            line = maintext().get(
                f"{match.rowcol.index()} linestart",
                f"{match.rowcol.index()}+{match.count}c lineend",
            )
            end_rowcol = IndexRowCol(
                maintext().index(match.rowcol.index() + f"+{match.count}c")
            )
            self.dialog.add_entry(
                line,
                IndexRange(match.rowcol, end_rowcol),
                match.rowcol.col,
                end_rowcol.col,
            )
        self.dialog.display_entries()

    def delete_comment(self, checker_entry: CheckerEntry) -> None:
        """Delete the given proofer comment."""
        if checker_entry.text_range is None:
            return
        start_mark = ProoferCommentCheckerDialog.mark_from_rowcol(
            checker_entry.text_range.start
        )
        end_mark = ProoferCommentCheckerDialog.mark_from_rowcol(
            checker_entry.text_range.end
        )
        maintext().undo_block_begin()
        maintext().delete(start_mark, end_mark)
        # If this leaves exactly a double space, remove one of them
        if re.fullmatch(
            "[^ ]  [^ ]", maintext().get(f"{start_mark}-2c", f"{end_mark}+2c")
        ):
            maintext().delete(start_mark)


def asterisk_check() -> None:
    """Find all asterisks without slashes."""

    # Match single or multiple asterisks including when separated by spaces, e.g. thought break
    matches = maintext().find_matches(
        r"\*( *\*)*",
        maintext().start_to_end(),
        nocase=False,
        regexp=True,
    )

    class AsteriskCheckerDialog(CheckerDialog):
        """Asterisk Checker Dialog."""

        manual_page = "Search_Menu#Find_Asterisks_w/o_Slash"

        def __init__(self, **kwargs: Any) -> None:
            """Initialize Asterisk Checker dialog."""
            super().__init__(
                "Asterisk Check",
                tooltip="\n".join(
                    [
                        "Left click: Select & find occurrence of asterisk",
                        "Right click: Hide message",
                        "Shift Right click: Also hide all matching message",
                    ]
                ),
                **kwargs,
            )

    checker_dialog = AsteriskCheckerDialog.show_dialog(
        rerun_command=asterisk_check,
    )
    for match in matches:
        line = maintext().get(
            f"{match.rowcol.index()} linestart",
            f"{match.rowcol.index()} lineend",
        )
        # Skip block markup
        if match.count == 1 and (
            (match.rowcol.col > 0 and line[match.rowcol.col - 1] == "/")
            or (match.rowcol.col < len(line) - 1 and line[match.rowcol.col + 1] == "/")
        ):
            continue
        end_rowcol = IndexRowCol(
            maintext().index(match.rowcol.index() + f"+{match.count}c")
        )
        checker_dialog.add_entry(
            line, IndexRange(match.rowcol, end_rowcol), match.rowcol.col, end_rowcol.col
        )
    checker_dialog.display_entries()


class TextMarkupConvertorDialog(ToplevelDialog):
    """Dialog for converting DP markup to text markup."""

    manual_page = "Text_Menu#Convert_Markup"

    def __init__(self) -> None:
        """Initialize text markup convertor dialog."""
        super().__init__("Text Markup Convertor", resize_x=False, resize_y=False)

        def add_row(row: int, markup: str, prefkey: PrefKey) -> None:
            ttk.Label(
                self.top_frame, text=f"<{markup}>...</{markup}>", anchor=tk.CENTER
            ).grid(column=0, row=row, sticky="NSEW")
            ttk.Button(
                self.top_frame,
                text="Convert ⟹",
                command=lambda: self.convert(
                    rf"</?{markup}>", preferences.get(prefkey)
                ),
            ).grid(
                column=1,
                row=row,
                pady=2,
                sticky="NSEW",
            )
            ttk.Entry(
                self.top_frame,
                width=2,
                textvariable=PersistentString(prefkey),
            ).grid(column=2, row=row, padx=5, pady=2, sticky="NSEW")

        add_row(0, "i", PrefKey.TEXT_MARKUP_ITALIC)
        add_row(1, "b", PrefKey.TEXT_MARKUP_BOLD)
        ttk.Label(self.top_frame, text="<sc>...</sc>", anchor=tk.CENTER).grid(
            column=0, row=2, sticky="NSEW"
        )
        ttk.Button(
            self.top_frame, text="Convert ⟹", command=self.convert_smallcaps_to_allcaps
        ).grid(column=1, row=2, pady=2, sticky="NSEW")
        ttk.Label(self.top_frame, text="ALLCAPS").grid(
            column=2, row=2, padx=5, sticky="NSEW"
        )
        add_row(3, "sc", PrefKey.TEXT_MARKUP_SMALLCAPS)
        add_row(4, "g", PrefKey.TEXT_MARKUP_GESPERRT)
        add_row(5, "f", PrefKey.TEXT_MARKUP_FONT)
        ttk.Label(self.top_frame, text="<tb>", anchor=tk.CENTER).grid(
            column=0, row=6, sticky="NSEW"
        )
        ttk.Button(
            self.top_frame,
            text="Convert ⟹",
            command=lambda: self.convert(r"<tb>", "       *" * 5),
        ).grid(column=1, row=6, pady=2, sticky="NSEW")
        ttk.Label(self.top_frame, text="Asterisks").grid(
            column=2, row=6, padx=5, sticky="NSEW"
        )

    def convert(self, regex: str, replacement: str) -> None:
        """Convert one type of DP markup to text markup.

        Args:
            regex: Regex that matches open/close markup.
            replacement: String to replace markup with.
        """
        found = False
        maintext().undo_block_begin()
        search_range = maintext().start_to_end()
        # Find each piece of markup that matches the regex
        while match := maintext().find_match(
            regex, search_range, regexp=True, nocase=True
        ):
            match_index = match.rowcol.index()
            maintext().replace(
                match_index, f"{match_index}+{match.count}c", replacement
            )
            search_range = IndexRange(
                maintext().index(f"{match_index}+1c"), maintext().end()
            )
            found = True
        if not found:
            sound_bell()

    def convert_smallcaps_to_allcaps(self) -> None:
        """Convert text marked up with <sc> to ALLCAPS."""
        found = False
        maintext().undo_block_begin()
        search_range = maintext().start_to_end()
        # Find start of each smallcap markup
        while match := maintext().find_match(
            "<sc>", search_range, regexp=False, nocase=True
        ):
            match_index = match.rowcol.index()
            search_range = IndexRange(
                maintext().index(f"{match_index}+4c"), maintext().end()
            )
            end_match = maintext().find_match(
                "</sc>", search_range, regexp=False, nocase=True
            )
            if end_match is None:
                logger.error(f"Unclosed <sc> markup on line {match.rowcol.row}")
                maintext().set_insert_index(match.rowcol, focus_widget=maintext())
                return
            end_match_index = end_match.rowcol.index()
            replacement = maintext().get(f"{match_index}+4c", end_match_index).upper()
            maintext().replace(match_index, f"{end_match_index}+5c", replacement)
            found = True
        if not found:
            sound_bell()

    @classmethod
    def manual_sc(cls) -> None:
        """Pop S/R dialog pre-populated to help user convert `<sc>` markup."""
        preferences.set(PrefKey.SEARCHDIALOG_MULTI_REPLACE, True)
        if preferences.get(PrefKey.SEARCHDIALOG_MULTI_ROWS) < 3:
            preferences.set(PrefKey.SEARCHDIALOG_MULTI_ROWS, 3)
        preferences.set(PrefKey.SEARCHDIALOG_REGEX, True)
        preferences.set(PrefKey.SEARCHDIALOG_MATCH_CASE, False)
        preferences.set(PrefKey.SEARCHDIALOG_WHOLE_WORD, False)
        dlg = SearchDialog.show_dialog()
        dlg.search_box.set(r"<sc>([^<]+)</sc>")
        dlg.replace_box[0].set(r"\1")
        dlg.replace_box[1].set(r"\U\1\E")
        dlg.replace_box[2].set(r"+\1+")


class Scanno(dict):
    """Dictionary to hold info about one scanno type.

    Implemented as a dictionary to aid load from JSON file."""

    MATCH = "match"
    REPLACEMENT = "replacement"
    HINT = "hint"

    def __init__(self, match: str, replacement: str, hint: str) -> None:
        self[Scanno.MATCH] = match
        self[Scanno.REPLACEMENT] = replacement
        self[Scanno.HINT] = hint


class ScannoCheckerDialog(CheckerDialog):
    """Dialog to handle stealth scanno checks."""

    manual_page = "Tools_Menu#Stealth_Scannos"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize scanno checker dialog."""
        super().__init__(
            "Stealth Scanno Results",
            tooltip="\n".join(
                [
                    "Left click: Select & find occurrence of scanno",
                    "Right click: Hide occurrence of scanno in list",
                    f"{cmd_ctrl_string()} left click: Fix this occurrence of scanno",
                    f"{cmd_ctrl_string()} right click: Fix this occurrence and remove from list",
                    f"Shift {cmd_ctrl_string()} left click: Fix all occurrences of scanno",
                    f"Shift {cmd_ctrl_string()} right click: Fix all occurrences and remove from list",
                ]
            ),
            **kwargs,
        )

        frame = ttk.Frame(self.custom_frame, padding=2)
        frame.grid(column=0, row=1, sticky="NSEW")
        self.custom_frame.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        for row in range(4):
            frame.rowconfigure(row, uniform="equal height")

        self.file_combo = PathnameCombobox(
            frame,
            PrefKey.SCANNOS_HISTORY,
            PrefKey.SCANNOS_FILENAME,
        )
        self.file_combo.grid(column=0, row=0, sticky="NSEW", pady=2)
        self.file_combo["state"] = "readonly"
        self.file_combo.bind("<<ComboboxSelected>>", lambda _e: self.select_file())
        ttk.Button(frame, text="Load File", command=self.choose_file).grid(
            column=1, row=0, sticky="NSEW", padx=(5, 0), pady=2
        )
        self.auto_checkbtn = ttk.Checkbutton(
            frame,
            text="Auto Adv.",
            variable=PersistentBoolean(PrefKey.SCANNOS_AUTO_ADVANCE),
        )
        self.auto_checkbtn.grid(column=2, row=0, sticky="NSEW", padx=(3, 0), pady=2)

        self.scanno_textvariable = tk.StringVar(self, "")
        search = ttk.Entry(
            frame,
            textvariable=self.scanno_textvariable,
            font=maintext().font,
        )
        search.grid(column=0, row=1, sticky="NSEW", pady=2)
        search.bind("<Return>", lambda _: self.list_scannos(update_fields=False))
        self.prev_btn = ttk.Button(
            frame,
            text="Prev. Scanno",
            command=lambda: self.prev_next_scanno(prev=True),
        )
        self.prev_btn.grid(column=1, row=1, sticky="NSEW", padx=(5, 0), pady=2)
        self.next_btn = ttk.Button(
            frame,
            text="Next Scanno",
            command=lambda: self.prev_next_scanno(prev=False),
        )
        self.next_btn.grid(column=2, row=1, sticky="NSEW", padx=(3, 0), pady=2)

        self.replacement_textvariable = tk.StringVar(self, "")
        replace = ttk.Entry(
            frame,
            textvariable=self.replacement_textvariable,
            font=maintext().font,
        )
        replace.grid(column=0, row=2, sticky="NSEW", pady=2)
        replace.bind("<Return>", lambda _: self.list_scannos(update_fields=False))
        ttk.Button(
            frame,
            text="Replace",
            command=lambda: self.process_entry_current(all_matching=False),
        ).grid(column=1, row=2, sticky="NSEW", padx=(5, 0), pady=2)
        ttk.Button(
            frame,
            text="Replace All",
            command=lambda: self.process_entry_current(all_matching=True),
        ).grid(column=2, row=2, sticky="NSEW", padx=(3, 0), pady=2)

        self.hint_textvariable = tk.StringVar(self, "Hint: ")
        ttk.Entry(frame, textvariable=self.hint_textvariable, state="readonly").grid(
            column=0, row=3, sticky="NSEW", pady=2
        )
        ttk.Button(
            frame,
            text="Swap Terms",
            command=self.swap_terms,
        ).grid(column=1, row=3, sticky="NSEW", padx=(5, 0), pady=2)
        self.count_textvariable = tk.StringVar(self, "")
        ttk.Label(
            frame,
            textvariable=self.count_textvariable,
        ).grid(column=2, row=3, sticky="NS", padx=(3, 0), pady=2)

        self.scanno_list: list[Scanno] = []
        self.whole_word = False
        self.scanno_number = 0

    @classmethod
    def add_orphan_commands(cls) -> None:
        """Add orphan commands to command palette."""

        menubar_metadata().add_checkbutton_orphan(
            "Stealth Scannos, Auto Advance", PrefKey.SCANNOS_AUTO_ADVANCE
        )
        menubar_metadata().add_button_orphan(
            "Stealth Scannos, Previous Scanno",
            cls.orphan_wrapper("prev_next_scanno", prev=True),
        )
        menubar_metadata().add_button_orphan(
            "Stealth Scannos, Next Scanno",
            cls.orphan_wrapper("prev_next_scanno", prev=False),
        )
        menubar_metadata().add_button_orphan(
            "Stealth Scannos, Swap Terms", cls.orphan_wrapper("swap_terms")
        )
        menubar_metadata().add_button_orphan(
            "Stealth Scannos, Replace",
            cls.orphan_wrapper("process_entry_current", all_matching=False),
        )
        menubar_metadata().add_button_orphan(
            "Stealth Scannos, Replace All",
            cls.orphan_wrapper("process_entry_current", all_matching=True),
        )

    def choose_file(self) -> None:
        """Choose & load a scannos file."""
        filename = filedialog.askopenfilename(
            filetypes=(
                ("Scannos files", "*.json"),
                ("All files", "*.*"),
            )
        )
        if filename:
            self.focus()
            preferences.set(PrefKey.SCANNOS_FILENAME, filename)
            self.load_scannos()

    def select_file(self) -> None:
        """Handle selection of a scannos file."""
        self.load_scannos()

    def load_scannos(self) -> None:
        """Load a scannos file."""
        path = preferences.get(PrefKey.SCANNOS_FILENAME)
        self.file_combo.add_to_history(path)
        scanno_dict = load_dict_from_json(path)
        if scanno_dict is None:
            logger.error(f"Unable to load scannos file {path}")
            return
        # Some scannos files require whole-word searching
        try:
            self.whole_word = scanno_dict["wholeword"]
        except KeyError:
            self.whole_word = False
        try:
            self.scanno_list = scanno_dict["scannos"]
        except KeyError:
            logger.error("Error in scannos file - no 'scannos' array")
            return
        # Validate scannos - must have a match, but replacement and/or hint can
        # be omitted, and default to empty strings
        for scanno in self.scanno_list:
            try:
                scanno[Scanno.MATCH]
            except KeyError:
                logger.error("Error in scannos file - entry with no 'match' string")
                self.scanno_list = []
                return
            try:
                scanno[Scanno.REPLACEMENT]
            except KeyError:
                scanno[Scanno.REPLACEMENT] = ""
            try:
                scanno[Scanno.HINT]
            except KeyError:
                scanno[Scanno.HINT] = ""

        self.scanno_number = 0
        self.prev_next_scanno(None)

    def prev_next_scanno(self, prev: Optional[bool]) -> None:
        """Display previous/next scanno & list of results.

        Auto-advances until it finds a scanno that has some results.

        Args:
            prev: True for Previous, False for Next, None for neither, i.e. display current scanno
        """
        slurp_text = maintext().get_text()
        find_range = IndexRange(maintext().start().index(), maintext().end().index())
        while (prev and self.scanno_number > 0) or (
            not prev and self.scanno_number < len(self.scanno_list) - 1
        ):
            # First time through, "None" means use current scanno,
            # but after that behave like "Next"
            if prev is None:
                prev = False
            else:
                self.scanno_number += -1 if prev else 1
            if self.any_matches(slurp_text, find_range) or not preferences.get(
                PrefKey.SCANNOS_AUTO_ADVANCE
            ):
                self.list_scannos()
                return
        # No matches found, so display first/last scanno
        self.scanno_number = 0 if prev else len(self.scanno_list) - 1
        self.list_scannos()

    def any_matches(self, slurp_text: str, find_range: IndexRange) -> bool:
        """Return quickly whether there are any matches for current scanno.

        Args:
            slurp_text: Whole text of file (to avoid multiple slurping)
            find_range: Whole range of file

        Returns:
            True if there is at least 1 match for the current scanno."""

        match, _ = maintext().find_match_in_range(
            self.scanno_list[self.scanno_number][Scanno.MATCH],
            slurp_text,
            find_range,
            nocase=False,
            regexp=True,
            wholeword=self.whole_word,
            backwards=False,
        )
        return bool(match)

    def list_scannos(self, update_fields: bool = True) -> None:
        """Display current scanno and list of results.

        Args:
            update_fields: Set to False if fields should not be updated.
        """
        self.reset()
        if not self.scanno_list:
            self.display_entries(complete_msg=False)
            return
        if update_fields:
            scanno = self.scanno_list[self.scanno_number]
            self.scanno_textvariable.set(scanno[Scanno.MATCH])
            self.replacement_textvariable.set(scanno[Scanno.REPLACEMENT])
            self.hint_textvariable.set(f"Hint: {scanno[Scanno.HINT]}")
            self.count_textvariable.set(
                f"{self.scanno_number + 1} / {len(self.scanno_list)}"
            )

        find_range = IndexRange(maintext().start().index(), maintext().end().index())
        slurp_text = maintext().get_text()
        slice_start = 0

        while True:
            try:
                match, match_start = maintext().find_match_in_range(
                    self.scanno_textvariable.get(),
                    slurp_text[slice_start:],
                    find_range,
                    nocase=False,
                    regexp=True,
                    wholeword=self.whole_word,
                    backwards=False,
                )
            except re.error as e:
                logger.error(
                    f"Scanno regex {self.scanno_number + 1} has an error:\n{message_from_regex_exception(e)}"
                )
                self.display_entries(complete_msg=False)
                self.lift()
                return

            if match is None:
                break
            line = maintext().get(
                f"{match.rowcol.index()} linestart",
                f"{match.rowcol.index()}+{match.count}c lineend",
            )
            end_rowcol = IndexRowCol(
                maintext().index(match.rowcol.index() + f"+{match.count}c")
            )
            hilite_start = match.rowcol.col

            # If multiline, lines will be concatenated, so adjust end hilite point
            if end_rowcol.row > match.rowcol.row:
                not_matched = maintext().get(
                    f"{match.rowcol.index()}+{match.count}c",
                    f"{match.rowcol.index()}+{match.count}c lineend",
                )
                hilite_end = len(line) - len(not_matched)
            else:
                hilite_end = end_rowcol.col
            self.add_entry(
                line, IndexRange(match.rowcol, end_rowcol), hilite_start, hilite_end
            )

            # Adjust start of slice of slurped text, and where that point is in the file
            advance = max(match.count, 1)
            slice_start += match_start + advance
            if slice_start >= len(slurp_text):  # No text left to match
                break
            slurp_start = IndexRowCol(
                maintext().index(f"{match.rowcol.index()}+{advance}c")
            )
            find_range = IndexRange(slurp_start, find_range.end)

        # Disable prev/next scanno buttons if at start/end of list
        self.prev_btn["state"] = tk.DISABLED if self.scanno_number <= 0 else tk.NORMAL
        self.next_btn["state"] = (
            tk.DISABLED
            if self.scanno_number >= len(self.scanno_list) - 1
            else tk.NORMAL
        )

        self.display_entries(
            complete_msg=(self.scanno_number >= len(self.scanno_list) - 1)
        )

    def swap_terms(self) -> None:
        """Swap search & replace terms in dialog."""
        tempstr = self.scanno_textvariable.get()
        self.scanno_textvariable.set(self.replacement_textvariable.get())
        self.replacement_textvariable.set(tempstr)
        self.list_scannos(update_fields=False)


_the_stealth_scannos_dialog: Optional[ScannoCheckerDialog] = None


def do_replace_scanno(checker_entry: CheckerEntry) -> None:
    """Process the scanno by replacing with the replacement regex/string."""
    assert _the_stealth_scannos_dialog is not None
    if checker_entry.text_range:
        search_string = _the_stealth_scannos_dialog.scanno_textvariable.get()
        replace_string = _the_stealth_scannos_dialog.replacement_textvariable.get()
        start = _the_stealth_scannos_dialog.mark_from_rowcol(
            checker_entry.text_range.start
        )
        end = _the_stealth_scannos_dialog.mark_from_rowcol(checker_entry.text_range.end)
        match_text = maintext().get(start, end)
        replacement = get_regex_replacement(
            search_string, replace_string, match_text, flags=0
        )
        maintext().replace(start, end, replacement)


def stealth_scannos() -> None:
    """Report potential stealth scannos in file."""
    global _the_stealth_scannos_dialog

    if not tool_save():
        return

    _the_stealth_scannos_dialog = ScannoCheckerDialog.show_dialog(
        rerun_command=stealth_scannos,
        process_command=do_replace_scanno,
        show_all_buttons=False,
        match_on_highlight=CheckerMatchType.ALL_MESSAGES,
    )
    _the_stealth_scannos_dialog.load_scannos()


DQUOTES = "“”"
SQUOTES = "‘’"
INIT_APOS_WORDS = (
    "'em",
    "'Tis",
    "'Tisn't",
    "'Tweren't",
    "'Twere",
    "'Twould",
    "'Twouldn't",
    "'Twas",
    "'Im",
    "'Twixt",
    "'Til",
    "'Scuse",
    "'Gainst",
    "'Twon't",
    "'Tain't",
)
SAFE_APOS_RQUOTE_REGEXES = (
    r"(?<=\w)'(?=\w)",  # surrounded by letters
    r"(?<=[\.,\w])'",  # preceded by period, comma or letter
    r"(?<=\w)'(?=\.)",  # between letter & period
    r"'$",  # end of line
    rf"'(?=[ {DQUOTES[1]}])",  # followed by space or close double quote
)


def convert_to_curly_quotes() -> None:
    """Convert straight quotes to curly in whole file, and display list of queries.

    Adapted from https://github.com/DistributedProofreaders/ppwb/blob/master/bin/ppsmq.py
    """
    maintext().undo_block_begin()
    end_line = maintext().end().row
    dqtype = 0
    for line_num in range(1, end_line + 1):
        edited = False
        lstart = f"{line_num}.0"
        lend = f"{line_num}.end"
        line = maintext().get(lstart, lend)
        if line == "":
            dqtype = 0  # Reset double quotes at paragraph break
            continue
        start_line_dqtype = dqtype  # Needed for single quote conversion later

        # Apart from special cases, alternate open/close double quotes through each paragraph
        # Ditto marks first - surrounded by double-space. Also permit 0/1 space
        # before ditto if at start of line, or 0/1 space after ditto if at end of line.
        line, count = re.subn('(?<=  )"(?=  )', DQUOTES[1], line)
        if count:
            edited = True
        line, count = re.subn('(?<=^ ?)"(?=  )', DQUOTES[1], line)
        if count:
            edited = True
        line, count = re.subn('(?<=  )"(?= ?$)', DQUOTES[1], line)
        if count:
            edited = True
        # Start of line, must be open quotes
        line, count = re.subn('^"', DQUOTES[0], line)
        if count:
            edited = True
            dqtype = 1
        # Mid-line, alternate open/close quotes
        while True:
            line, count = re.subn('"(?!$)', DQUOTES[dqtype], line, count=1)
            if count:
                edited = True
                dqtype = 0 if dqtype == 1 else 1
            else:
                break
        # End of line must be close quotes
        line, count = re.subn('"$', DQUOTES[1], line)
        if count:
            edited = True
            dqtype = 0

        # Convert apostrophes in specific words
        for straight_word in INIT_APOS_WORDS:
            curly_word = straight_word.replace("'", "’")
            line, count = re.subn(rf"(?!<\w){straight_word}(?!\w)", curly_word, line)
            if count:
                edited = True
            line, count = re.subn(
                rf"(?!<\w){straight_word.lower()}(?!\w)", curly_word.lower(), line
            )
            if count:
                edited = True
        # Now convert specific safe cases to close single quote/apostrophe
        for regex in SAFE_APOS_RQUOTE_REGEXES:
            line, count = re.subn(regex, SQUOTES[1], line)
            if count:
                edited = True
        # If PPer has enabled it, convert straight quote at start of word to
        # apostrophe if it's inside double quotes
        if not preferences.get(PrefKey.CURLY_SINGLE_QUOTE_STRICT) and "'" in line:
            chars = list(line)
            # Begin with situation at start of line
            in_double_quotes = bool(start_line_dqtype)
            for idx, ch in enumerate(chars):
                if ch == "“":
                    in_double_quotes = True
                elif ch == "”":
                    in_double_quotes = False
                elif in_double_quotes and ch == "'":
                    # If single quote at start of line or start of word, assume it is an apostrophe
                    if (idx == 0 or chars[idx - 1] in " “>") and (
                        idx + 1 < len(chars) and chars[idx + 1].isalpha()
                    ):
                        chars[idx] = "’"
                        edited = True
            line = "".join(chars)

        if edited:
            maintext().replace(lstart, lend, line)

    check_curly_quotes()


class CurlyQuotesViewOptionsDialog(CheckerViewOptionsDialog):
    """Minimal class to identify dialog type."""

    manual_page = "Tools_Menu#Convert_to_Curly_Quotes"


class CurlyQuotesDialog(CheckerDialog):
    """Dialog to handle curly quotes checks."""

    manual_page = "Tools_Menu#Convert_to_Curly_Quotes"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize curly quotes checker dialog."""
        super().__init__(
            "Curly Quotes Check",
            tooltip="\n".join(
                [
                    "Left click: Select & find curly quote warning",
                    "Right click: Hide warning",
                    "Shift Right click: Hide all matching warnings",
                    f"With {cmd_ctrl_string()} key: Convert straight to curly, or swap open⇔close",
                ]
            ),
            **kwargs,
        )

        self.custom_frame.columnconfigure(0, weight=1)
        frame = ttk.Frame(self.custom_frame)
        frame.grid(column=0, row=1, sticky="NSEW", pady=5)
        frame.columnconfigure(3, weight=1)
        ttk.Button(
            frame,
            text="Open⇔Close",
            command=self.swap_open_close,
        ).grid(column=0, row=0, sticky="NSW")
        ttk.Button(
            frame,
            text="Straight⇔Curly",
            command=self.swap_straight_curly,
        ).grid(column=1, row=0, sticky="NSW")
        ttk.Button(
            frame,
            text="Swap Quote/Space",
            command=self.swap_quote_space,
        ).grid(column=2, row=0, sticky="NSW")
        ttk.Button(
            frame,
            text="Delete Space",
            command=lambda: self.swap_quote_space(delete=True),
        ).grid(column=3, row=0, sticky="NSW")
        ttk.Label(
            frame,
            text="Insert:",
        ).grid(column=4, row=0, sticky="NSE")
        ttk.Button(
            frame,
            text=DQUOTES[0],
            command=lambda: insert_in_focus_widget(DQUOTES[0]),
        ).grid(column=5, row=0, sticky="NSE")
        ttk.Button(
            frame,
            text=DQUOTES[1],
            command=lambda: insert_in_focus_widget(DQUOTES[1]),
        ).grid(column=6, row=0, sticky="NSE")
        ttk.Button(
            frame,
            text=SQUOTES[0],
            command=lambda: insert_in_focus_widget(SQUOTES[0]),
        ).grid(column=7, row=0, sticky="NSE")
        ttk.Button(
            frame,
            text=SQUOTES[1],
            command=lambda: insert_in_focus_widget(SQUOTES[1]),
        ).grid(column=8, row=0, sticky="NSE")
        ttk.Checkbutton(
            frame,
            text='Allow "Next paragraph begins with quotes" exception',
            variable=PersistentBoolean(PrefKey.CURLY_DOUBLE_QUOTE_EXCEPTION),
        ).grid(column=0, row=1, columnspan=9, sticky="NSW", pady=(5, 0))

    def populate(self) -> None:
        """Populate list with suspect curly quotes."""
        self.reset()
        dqtype = 0
        sqtype = 0
        search_start = maintext().start()
        search_end = maintext().index(tk.END)
        last_open_double_idx = ""
        last_open_single_idx = ""
        punctuation = ".,;:!?"
        while match := maintext().find_match(
            rf"^$|[{DQUOTES}{SQUOTES}\"']",
            IndexRange(search_start, search_end),
            regexp=True,
        ):
            search_start = maintext().rowcol(f"{match.rowcol.index()}+1c")
            line_num = match.rowcol.row
            match_text = maintext().get_match_text(match)
            linebeg = f"{line_num}.0"
            lineend = maintext().index(f"{line_num}.end")

            def add_quote_entry(prefix: str) -> None:
                """Add entry highlighting matched quote.

                Args:
                    prefix: Message prefix.
                """
                self.add_entry(
                    maintext().get(linebeg, lineend),
                    IndexRange(
                        match.rowcol,
                        IndexRowCol(match.rowcol.row, match.rowcol.col + 1),
                    ),
                    hilite_start=match.rowcol.col,
                    hilite_end=match.rowcol.col + 1,
                    error_prefix=prefix,
                )

            if match_text == DQUOTES[0]:  # Open double
                context = maintext().get(
                    f"{match.rowcol.index()}-1c", f"{match.rowcol.index()}+2c"
                )
                if dqtype == 1:
                    add_quote_entry("Open DQ unexpected: ")
                elif len(context) > 2 and context[2] == "\n":
                    add_quote_entry("Open DQ at line end: ")
                elif len(context) > 2 and context[2] == " ":
                    add_quote_entry("Open DQ before space: ")
                elif context[0].isalnum():
                    add_quote_entry("Open DQ after letter: ")
                elif context[0] in punctuation:
                    add_quote_entry("Open DQ after punct: ")
                dqtype = 1
                last_open_double_idx = match.rowcol.index()
            elif match_text == DQUOTES[1]:  # Close double
                # If surrounded by double-spaces or beg/end of line (with optional single space), it's ditto mark, so OK
                context = maintext().get(
                    f"{match.rowcol.index()}-2c", f"{match.rowcol.index()}+3c"
                )
                if (
                    len(context) < 5
                    or re.fullmatch(
                        rf"([\n ] {DQUOTES[1]}  |  {DQUOTES[1]} \n)", context
                    )
                    or context[1:] == f"\n{DQUOTES[1]}  "
                    or context[:4] == f"  {DQUOTES[1]}\n"
                ):
                    continue
                if dqtype == 0:
                    add_quote_entry("Close DQ unexpected: ")
                elif context[1] == "\n":
                    add_quote_entry("Close DQ at line start: ")
                elif context[1] == " ":
                    add_quote_entry("Close DQ after space: ")
                elif context[3].isalnum():
                    add_quote_entry("Close DQ before letter: ")
                dqtype = 0
            elif match_text == SQUOTES[0]:  # Open single
                context = maintext().get(
                    f"{match.rowcol.index()}-1c", f"{match.rowcol.index()}+2c"
                )
                if len(context) < 3:
                    continue
                if sqtype == 1:
                    add_quote_entry("Open SQ unexpected: ")
                elif len(context) > 2 and context[2] == "\n":
                    add_quote_entry("Open SQ at line end: ")
                elif len(context) > 2 and context[2] == " ":
                    add_quote_entry("Open SQ before space: ")
                elif context[0].isalnum():
                    add_quote_entry("Open SQ after letter: ")
                elif context[0] in punctuation:
                    add_quote_entry("Open SQ after punct: ")
                sqtype = 1
                last_open_single_idx = match.rowcol.index()
            elif match_text == SQUOTES[1]:  # Close single
                context = maintext().get(
                    f"{match.rowcol.index()}-2c", f"{match.rowcol.index()}+3c"
                )
                # If letters both sides, it's an apostrophe, so ignore
                if len(context) < 5 or context[1].isalpha() and context[3].isalpha():
                    continue
                if sqtype == 0:
                    add_quote_entry("Close SQ unexpected (apos?): ")
                elif context[1] == "\n":
                    add_quote_entry("Close SQ at line start (apos?): ")
                elif context[1] == " ":
                    add_quote_entry("Close SQ after space (apos?): ")
                elif context[3].isalnum():
                    add_quote_entry("Close SQ before letter (apos?): ")
                sqtype = 0
            elif match_text == '"':  # Straight double
                add_quote_entry("DQ not converted: ")
            elif match_text == "'":  # Straight single
                add_quote_entry("SQ not converted: ")
            elif match_text == "":  # Blank line
                # Expect dqtype == 0 unless next line starts with open double quote
                # AND user has enabled that exception
                if dqtype == 1 and (
                    maintext().get(f"{linebeg} +1l") != DQUOTES[0]
                    or not preferences.get(PrefKey.CURLY_DOUBLE_QUOTE_EXCEPTION)
                ):
                    hilite_start = IndexRowCol(last_open_double_idx).col
                    self.add_entry(
                        maintext().get(
                            f"{last_open_double_idx} linestart",
                            f"{last_open_double_idx} lineend",
                        ),
                        IndexRange(
                            last_open_double_idx,
                            maintext().rowcol(f"{last_open_double_idx}+1c"),
                        ),
                        hilite_start=hilite_start,
                        hilite_end=hilite_start + 1,
                        error_prefix="DQ not closed: ",
                    )
                dqtype = 0
                # Expect sqtype == 0 unless next line starts with open single quote
                if sqtype == 1 and maintext().get(f"{linebeg} +1l") != SQUOTES[0]:
                    hilite_start = IndexRowCol(last_open_single_idx).col
                    self.add_entry(
                        maintext().get(
                            f"{last_open_single_idx} linestart",
                            f"{last_open_single_idx} lineend",
                        ),
                        IndexRange(
                            last_open_single_idx,
                            maintext().rowcol(f"{last_open_single_idx}+1c"),
                        ),
                        hilite_start=hilite_start,
                        hilite_end=hilite_start + 1,
                        error_prefix="SQ not closed: ",
                    )
                sqtype = 0
        self.display_entries()

    def swap_open_close(self) -> None:
        """Swap current quote open<-->close."""
        entry_index = self.current_entry_index()
        if entry_index is None:
            return
        do_swap_open_close(self.entries[entry_index])

    def swap_quote_space(self, delete: bool = False) -> None:
        """Swap current quote with adjacent space, or just delete it.

        Args:
            delete: True to just delete space instead of swapping.
        """
        entry_index = self.current_entry_index()
        if entry_index is None:
            return
        checker_entry = self.entries[entry_index]
        if checker_entry.text_range:
            start_mark = self.mark_from_rowcol(checker_entry.text_range.start)
            end_mark = self.mark_from_rowcol(checker_entry.text_range.end)
            start = maintext().index(f"{start_mark}-1c")
            end = maintext().index(f"{start_mark}+2c")
            match_text = maintext().get(start, end)
            if match_text[1] not in "“”‘’":
                return
            maintext().undo_block_begin()
            # Temporarily change mark gravities so moved space ends up outside marks
            maintext().mark_gravity(start_mark, tk.RIGHT)
            maintext().mark_gravity(end_mark, tk.LEFT)
            # If only space before, or space both sides and it's close quote, swap/delete space before
            if match_text[0] == " " and (match_text[2] != " " or match_text[1] in "”’"):
                maintext().delete(start)
                if not delete:
                    maintext().insert(f"{start}+1c", " ")
            # If only space after, or space both sides and it's open quote, swap/delete space after
            elif (match_text[0] != " " or match_text[1] in "“‘") and match_text[
                2
            ] == " ":
                maintext().delete(f"{start}+2c")
                if not delete:
                    maintext().insert(f"{start}+1c", " ")
            maintext().mark_gravity(start_mark, tk.LEFT)
            maintext().mark_gravity(end_mark, tk.RIGHT)

    def swap_straight_curly(self) -> None:
        """Swap current quote with straight/curly(open) equivalent."""
        entry_index = self.current_entry_index()
        if entry_index is None:
            return
        do_swap_straight_curly(self.entries[entry_index])


_the_curly_quotes_dialog: Optional[CurlyQuotesDialog] = None


def do_fix_quote(checker_entry: CheckerEntry) -> None:
    """Fix the quote problem."""
    assert _the_curly_quotes_dialog is not None
    assert checker_entry.text_range is not None
    if (
        checker_entry.error_prefix
        in (
            "DOUBLE QUOTE NOT CONVERTED: ",
            "SINGLE QUOTE NOT CONVERTED: ",
        )
        and maintext().get(
            _the_curly_quotes_dialog.mark_from_rowcol(checker_entry.text_range.start),
            _the_curly_quotes_dialog.mark_from_rowcol(checker_entry.text_range.end),
        )
        in "'\""
    ):
        do_swap_straight_curly(checker_entry)
    else:
        do_swap_open_close(checker_entry)


def do_swap_straight_curly(checker_entry: CheckerEntry) -> None:
    """Process given entry by swapping straight/curly quotes."""
    do_process_with_dict(
        checker_entry, {'"': "“", "'": "‘", "“": '"', "”": '"', "‘": "'", "’": "'"}
    )


def do_swap_open_close(checker_entry: CheckerEntry) -> None:
    """Process given entry by swapping the quote open<-->close."""
    do_process_with_dict(checker_entry, {"“": "”", "”": "“", "‘": "’", "’": "‘"})


def do_process_with_dict(
    checker_entry: CheckerEntry, swap_dict: dict[str, str]
) -> None:
    """Process given entry by swapping the selected character for the one in the dict.

    Args:
        swap_dict: Dictionary of which character to swap for which.
    """
    assert _the_curly_quotes_dialog is not None
    if not checker_entry.text_range:
        return
    start = _the_curly_quotes_dialog.mark_from_rowcol(checker_entry.text_range.start)
    end = _the_curly_quotes_dialog.mark_from_rowcol(checker_entry.text_range.end)
    match_text = maintext().get(start, end)
    maintext().undo_block_begin()
    try:
        maintext().replace(start, end, swap_dict[match_text])
    except KeyError:
        pass  # User has edited since tool was run
    # Reselect to refresh highlighting
    if cur_idx := _the_curly_quotes_dialog.current_entry_index():
        _the_curly_quotes_dialog.select_entry_by_index(cur_idx)


def sort_key_error(
    entry: CheckerEntry,
) -> tuple[int, str, int, int]:
    """Sort key function to sort Curly Quote entries by text, putting identical upper
        and lower case versions together.

    Differs from default alpha sort in using the error prefix text (the type of error)
    as the primary text sort key.
    No need to deal with different entry types and all entries have a text_range.
    """
    assert entry.text_range is not None
    return (
        entry.section,
        entry.error_prefix,
        entry.text_range.start.row,
        entry.text_range.start.col,
    )


def check_curly_quotes() -> None:
    """Check for suspect curly quotes."""
    global _the_curly_quotes_dialog

    if not tool_save():
        return

    _the_curly_quotes_dialog = CurlyQuotesDialog.show_dialog(
        rerun_command=check_curly_quotes,
        process_command=do_fix_quote,
        sort_key_alpha=sort_key_error,
        show_process_buttons=False,
        view_options_dialog_class=CurlyQuotesViewOptionsDialog,
        view_options_filters=CURLY_QUOTES_CHECKER_FILTERS,
    )
    _the_curly_quotes_dialog.populate()


def indent_selection(indent: int) -> None:
    """Indent selected lines of text.

    Args:
        indent: How many spaces to indent.
    """

    def do_indent(line: int) -> None:
        """Indent given line by adding/removing `indent` space(s)."""
        if indent < 0:
            text = maintext().get(f"{line}.0", f"{line}.end")
            # Don't try to remove more leading spaces than exist
            n_space = min(-indent, len(text) - len(text.lstrip()))
            maintext().delete(f"{line}.0", f"{line}.{n_space}")
        elif indent > 0:
            maintext().insert(f"{line}.0", " " * indent)

    align_indent(do_indent)


def align_selection(center: bool) -> None:
    """Align selected lines of text.

    Args:
        center: True to center, False to right-align.
    """

    right = preferences.get(PrefKey.WRAP_RIGHT_MARGIN)

    def do_align(line: int) -> None:
        """Align given line by adding/removing space(s)."""
        text = maintext().get(f"{line}.0", f"{line}.end").strip()
        text_len = len(text)
        if text_len > 0:
            n_spaces = right - text_len
            if center:
                n_spaces = int(n_spaces / 2)
            n_spaces = max(n_spaces, 0)
            maintext().replace(f"{line}.0", f"{line}.end", f"{n_spaces * ' '}{text}")

    align_indent(do_align)


def right_align_numbers() -> None:
    """Right align numbers in selection, e.g. ToC."""

    right = preferences.get(PrefKey.WRAP_RIGHT_MARGIN)

    def number_align(line: int) -> None:
        """Align numbers at end of given line by adding/removing space(s)."""
        text = maintext().get(f"{line}.0", f"{line}.end").rstrip()
        if match := re.fullmatch(r"^(.*?)  +(\d+([,-–] *\d+)*\.?)", text):
            pre = match[1]
            post = match[2]
            n_spaces = right - len(pre) - len(post)
            n_spaces = max(n_spaces, 2)
            maintext().replace(
                f"{line}.0", f"{line}.end", f"{pre}{n_spaces * ' '}{post}"
            )

    align_indent(number_align)


def align_indent(do_func: Callable[[int], None]) -> None:
    """Call given function on each selected (or current) line.

    Args:
        do_func: Function to do the aligning/indenting.
    """
    maintext().undo_block_begin()

    ranges = maintext().selected_ranges()
    if ranges:
        for sel_range in ranges:
            start = sel_range.start.row
            # End point is end of prev line if sel range ends at line start
            end = maintext().rowcol(f"{sel_range.end.index()}-1c").row
            for line in range(start, end + 1):
                do_func(line)
        # When normal selection, first inserted spaces go before the
        # start of the sel tag and don't appear selected, so re-select
        if len(ranges) == 1 and ranges[0].start.col == 0:
            maintext().do_select(ranges[0])
    else:
        do_func(maintext().get_insert_index().row)
