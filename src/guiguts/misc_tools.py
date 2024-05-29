"""Miscellaneous tools."""

from enum import Enum, StrEnum, auto
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

import regex as re

from guiguts.checkers import CheckerDialog, CheckerEntry
from guiguts.file import the_file
from guiguts.maintext import maintext
from guiguts.preferences import PrefKey, PersistentString, preferences
from guiguts.utilities import IndexRowCol, IndexRange, cmd_ctrl_string, is_mac
from guiguts.widgets import ToolTip, ToplevelDialog

logger = logging.getLogger(__package__)

BLOCK_TYPES = "[$*XxFf]"
POEM_TYPES = "[Pp]"
ALL_BLOCKS_REG = f"[{re.escape('#$*FILPXCR')}]"


def tool_save() -> bool:
    """File must be saved before running tool, so check if it has been,
    and if not, check if user wants to save, or cancel the tool run.

    Returns:
        True if OK to continue with intended operation.
    """
    if the_file().filename:
        return True

    save = messagebox.askokcancel(
        title="Save document",
        message="Document must be saved before running tool",
        icon=messagebox.INFO,
    )
    # User could cancel from messagebox or save-as dialog
    return save and bool(the_file().save_file())


def process_fixup(checker_entry: CheckerEntry) -> None:
    """Process the fixup error."""
    if checker_entry.text_range is None:
        return
    entry_type = checker_entry.text.split(":", 1)[0]
    start_mark = CheckerDialog.mark_from_rowcol(checker_entry.text_range.start)
    end_mark = CheckerDialog.mark_from_rowcol(checker_entry.text_range.end)
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


def sort_key_type(
    entry: CheckerEntry,
) -> tuple[int, str, int, int]:
    """Sort key function to sort Fixup entries by text, putting identical upper
        and lower case versions together.

    Differs from default alpha sort in using the text up to the colon
    (the type of error) as the primary sort key. No need to deal with different
    entry types for Fixup, and all entries have a text_range.
    """
    assert entry.text_range is not None
    return (
        entry.section,
        entry.text.split(":")[0],
        entry.text_range.start.row,
        entry.text_range.start.col,
    )


def basic_fixup_check() -> None:
    """Check the currently loaded file for basic fixup errors."""

    if not tool_save():
        return

    checker_dialog = CheckerDialog.show_dialog(
        "Basic Fixup Check Results",
        rerun_command=basic_fixup_check,
        process_command=process_fixup,
        sort_key_alpha=sort_key_type,
    )
    ToolTip(
        checker_dialog.text,
        "\n".join(
            [
                "Left click: Select & find issue",
                "Right click: Remove issue from list",
                f"With {cmd_ctrl_string()} key: Also fix issue",
                "With Shift key: Also remove/fix matching issues",
            ]
        ),
        use_pointer_pos=True,
    )
    checker_dialog.reset()

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
            prefix_len = len(prefix)
            for match in re.finditer(regex, test_line):
                group = 2 if match[1] is None else 1
                checker_dialog.add_entry(
                    prefix + line,
                    IndexRange(
                        IndexRowCol(line_num, match.start(group)),
                        IndexRowCol(line_num, match.end(group)),
                    ),
                    match.start(group) + prefix_len,
                    match.end(group) + prefix_len,
                )
    checker_dialog.display_entries()


class PageSepAutoType(StrEnum):
    """Enum class to store Page Separator sort types."""

    NO_AUTO = auto()
    AUTO_ADVANCE = auto()
    AUTO_FIX = auto()


class PageSeparatorDialog(ToplevelDialog):
    """Dialog for fixing page separators."""

    SEPARATOR_REGEX = r"^-----File: .+"
    BTN_WIDTH = 16

    def __init__(self) -> None:
        """Initialize messagelog dialog."""
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

        self.auto_type = PersistentString(PrefKey.PAGESEP_AUTO_TYPE)
        ttk.Radiobutton(
            self.top_frame,
            text="No Auto",
            command=self.refresh,
            variable=self.auto_type,
            value=PageSepAutoType.NO_AUTO,
            takefocus=False,
        ).grid(column=0, row=1, sticky="NSEW", padx=(20, 2), pady=2)
        ttk.Radiobutton(
            self.top_frame,
            text="Auto Advance",
            command=self.refresh,
            variable=self.auto_type,
            value=PageSepAutoType.AUTO_ADVANCE,
            takefocus=False,
        ).grid(column=1, row=1, sticky="NSEW", padx=2, pady=2)
        ttk.Radiobutton(
            self.top_frame,
            text="Auto Fix",
            command=self.refresh,
            variable=self.auto_type,
            value=PageSepAutoType.AUTO_FIX,
            takefocus=False,
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
            command=self.undo,
            underline=0,
            width=self.BTN_WIDTH,
        )
        undo_button.grid(column=0, row=0, sticky="NSEW")
        self.key_bind("u", undo_button.invoke)
        self.key_bind("Cmd/Ctrl+Z", undo_button.invoke)

        redo_button = ttk.Button(
            end_frame,
            text="Redo",
            command=self.redo,
            underline=1,
            width=self.BTN_WIDTH,
        )
        redo_button.grid(column=1, row=0, sticky="NSEW")
        self.key_bind("e", redo_button.invoke)
        self.key_bind("Cmd+Shift+Z" if is_mac() else "Ctrl+Y", redo_button.invoke)

        refresh_button = ttk.Button(
            end_frame,
            text="Refresh",
            command=self.refresh,
            underline=0,
            width=self.BTN_WIDTH,
        )
        refresh_button.grid(column=2, row=0, sticky="NSEW")
        self.key_bind("r", refresh_button.invoke)

    def do_join(self, keep_hyphen: bool) -> None:
        """Join 2 lines if hyphenated, otherwise just remove separator line.

        Args:
            keep_hyphen: True to keep hyphen when lines are joined.
        """
        if (sep_range := self.find()) is None:
            return

        self.fix_pagebreak_markup(sep_range)
        maintext().delete(sep_range.start.index(), sep_range.end.index())
        prev_eol = f"{sep_range.start.index()} -1l lineend"
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
            next_bol = f"{next_bol}+1c"
        maybe_page2_emdash = maintext().get(next_bol, f"{next_bol}+2c")

        # If word is hyphenated or emdash, join previous end of line to next beg of line
        if maybe_hyphen == "-" or maybe_page2_emdash == "--":
            # Replace space with newline after second half of word
            if space_pos := maintext().search(" ", next_bol, f"{next_bol} lineend"):
                maintext().replace(space_pos, f"{space_pos}+1c", "\n")
            # Delete hyphen, asterisks & newline to join the word
            maintext().delete(prev_eol, next_bol)
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
        self.undo_block_begin()
        self.do_auto()
        self.view()
        self.undo_block_end()

    def join(self, keep_hyphen: bool) -> None:
        """Handle click on Join buttons.

        Args:
            keep_hyphen: True to keep hyphen when lines are joined.
        """
        self.undo_block_begin()
        self.do_join(keep_hyphen)
        self.do_auto()
        self.undo_block_end()

    def delete(self) -> None:
        """Handle click on Delete button."""
        self.undo_block_begin()
        self.do_delete()
        self.do_auto()
        self.undo_block_end()

    def blank(self, num_lines: int) -> None:
        """Handle click on Blank buttons.

        Args:
            num_lines: How many blank lines to use.
        """
        self.undo_block_begin()
        self.do_blank(num_lines)
        self.do_auto()
        self.undo_block_end()

    def undo(self) -> None:
        """Handle click on Undo button, by undoing latest changes and re-viewing
        the first available page separator."""
        maintext().event_generate("<<Undo>>")
        self.view()

    def redo(self) -> None:
        """Handle click on Redo button, by re-doing latest undo and re-viewing
        the first available page separator."""
        maintext().event_generate("<<Redo>>")
        self.view()

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
            IndexRange(maintext().start(), maintext().end()),
            nocase=False,
            regexp=True,
            wholeword=False,
            backwards=False,
        )
        if match is None:
            return None
        end_rowcol = IndexRowCol(match.rowcol.row + 1, match.rowcol.col)
        return IndexRange(match.rowcol, end_rowcol)

    def fix_pagebreak_markup(self, sep_range: IndexRange) -> None:
        """Remove inline close markup, e.g. italics, immediately before page break
        if same markup is reopened immediately afterwards.

        Args:
            sep_range: Range of page separator line.
        """
        markup_prev = maintext().get(
            f"{sep_range.start.index()}-1l lineend -6c",
            f"{sep_range.start.index()}-1l lineend",
        )
        markup_next = maintext().get(
            f"{sep_range.end.index()}",
            f"{sep_range.end.index()} +4c",
        )
        if match := re.search(r"</(i|b|f|g|sc)>([,;*]?)$", markup_prev):
            markup_type = match[1]
            len_markup = len(markup_type)
            len_punc = len(match[2])
            if re.search(rf"^<{markup_type}>", markup_next):
                maintext().delete(
                    f"{sep_range.end.index()}",
                    f"{sep_range.end.index()} +{len_markup+2}c",
                )
                maintext().delete(
                    f"{sep_range.start.index()}-1l lineend -{len_markup+len_punc+3}c",
                    f"{sep_range.start.index()}-1l lineend -{len_punc}c",
                )

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
            self.fix_pagebreak_markup(sep_range)
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
            ):
                # No hyphen before/after page break, so OK to join
                self.do_join(False)
            else:
                break
        self.view()

    def undo_block_begin(self) -> None:
        """Begin a block of changes that will be undone with one undo operation.

        Will be replaced with a method in MainText.
        """
        maintext().config(autoseparators=False)
        maintext().edit_separator()

    def undo_block_end(self) -> None:
        """End a block of changes that will be undone with one undo operation.

        Will be replaced with a method in MainText.
        """
        maintext().edit_separator()
        maintext().config(autoseparators=True)


def page_separator_fixup() -> None:
    """Fix and remove page separator lines."""
    dlg = PageSeparatorDialog.show_dialog()
    dlg.view()


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
        "Unmatched Brackets",
        rerun_command=unmatched_brackets,
        match_reg="[][}{)(]",
        match_pair_func=toggle_bracket,
    )


def unmatched_curly_quotes() -> None:
    """Check for unmatched curly quotes."""

    def toggle_quote(quote_in: str) -> tuple[str, bool]:
        """Get regex that matches open and close quote.

        Args:
            quote_in: Quote - must be one of ‘ ’ “ ”

        Returns:
            Tuple with regex, True if bracket_in was close bracket.
        """
        match quote_in:
            case "‘":
                return "[‘’]", False
            case "’":
                return "[‘’]", True
            case "“":
                return "[“”]", False
            case "”":
                return "[“”]", True
        assert False, f"'{quote_in}' is not a curly quote"

    unmatched_markup_check(
        "Unmatched Curly Quotes",
        rerun_command=unmatched_curly_quotes,
        match_reg="[‘’“”]",
        match_pair_func=toggle_quote,
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
        "Unmatched DP markup",
        rerun_command=unmatched_dp_markup,
        match_reg="<[a-z]+>|</[a-z]+>",
        match_pair_func=matched_pair_dp_markup,
        ignore_reg="<tb>",
        sort_key_alpha=sort_key_dp_markup,
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

    def malformed_block_markup(dialog: CheckerDialog) -> None:
        """Add warnings about malformed block markup to given dialog.

        Args:
            dialog: Checkerdialog to receive error messages.
        """
        search_range = IndexRange(maintext().start(), maintext().end())
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
            # Don't report if open markup preceded by "<", e.g. "</i>"
            if match_str[0] == "/" and maintext().get(f"{match_index}-1c") == "<":
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
            regex = rf"^(/{block_type}(\[\d+)?(\.\d+)?(,\d+)?]?|{block_type}/)$"
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
        "Unmatched Block markup",
        rerun_command=unmatched_block_markup,
        match_reg=f"^(/{ALL_BLOCKS_REG}|{ALL_BLOCKS_REG}/)",
        match_pair_func=match_pair_block_markup,
        nest_reg="/#|#/",
        sort_key_alpha=sort_key_block_markup,
        additional_check_command=malformed_block_markup,
    )


def unmatched_markup_check(
    title: str,
    rerun_command: Callable[[], None],
    match_reg: str,
    match_pair_func: Callable[[str], tuple[str, bool]],
    nest_reg: Optional[str] = None,
    ignore_reg: Optional[str] = None,
    sort_key_alpha: Optional[Callable[[CheckerEntry], tuple]] = None,
    additional_check_command: Optional[Callable[[CheckerDialog], None]] = None,
) -> None:
    """Check the currently loaded file for unmatched markup errors.

    Args:
        title: Title for dialog.
        rerun_command: Function to re-run check.
        match_reg: Regex matching open & close markup.
        nest_reg: Regex matching markup that is allowed to be nested.
        ignore_reg: Regex matching markup that is to be ignored during check.
        sort_key_alpha: Function to provide type/alphabetic sorting
        additional_check_command: Function to perform extra checks
    """

    if not tool_save():
        return

    checker_dialog = CheckerDialog.show_dialog(
        title,
        rerun_command=rerun_command,
        sort_key_alpha=sort_key_alpha,
    )
    ToolTip(
        checker_dialog.text,
        "\n".join(
            [
                "Left click: Select & find issue",
                "Right click: Remove issue from list",
                "Shift-Right click: Remove all matching issues",
            ]
        ),
        use_pointer_pos=True,
    )
    checker_dialog.reset()

    search_range = IndexRange(maintext().start(), maintext().end())
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
        nestable = bool(
            nest_reg and re.fullmatch(nest_reg, match_str, flags=re.IGNORECASE)
        )
        prefix = "Unmatched: "
        # Search for the matching pair to this markup
        if not find_match_pair(
            match_index, match_str, match_pair_reg, reverse, nestable
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
    match_index: str, match_str: str, match_pair_reg: str, reverse: bool, nestable: bool
) -> str:
    """Find the pair to the given match.

    Args:
        match_index: Index of start of match_str in file.
        match_str: String to find the pair of.
        pair_str: The pair string to search for.
        reverse: True to search backwards (i.e. given close, look for open).
        nestable: True if markup is allowed to nest.
    """
    found = ""
    match_len = len(match_str)
    depth = 1
    start = match_index if reverse else maintext().index(f"{match_index}+{match_len}c")
    end = maintext().start() if reverse else maintext().end()
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

        depth += (
            1 if maintext().get_match_text(match).lower() == match_str.lower() else -1
        )
        # Check it's not nested when nesting isn't allowed
        if depth > 1 and not nestable:
            found = ""
            break

        found = match.rowcol.index()
        # Adjust start point for next search
        start = (
            match.rowcol.index()
            if reverse
            else maintext().index(f"{match.rowcol.index()}+{match.count}c")
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
        type: Determines which/how fractions will be converted.
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

    sel_ranges = maintext().selected_ranges()
    if not sel_ranges:
        sel_ranges = [IndexRange(maintext().start(), maintext().end())]

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
            # "B1/2" or "C-1/3" - probably a plate/serial number, but not a fraction
            prefix = maintext().get(f"{match.rowcol.index()}-2c", match.rowcol.index())
            if new_frac and not re.search(r"(\p{L}-|\p{L}$)", prefix):
                len_frac = len(new_frac)
                maintext().insert(match_index, new_frac)
                maintext().delete(
                    f"{match_index}+{len(new_frac)}c",
                    f"{match_index}+{len(new_frac)+len(gmatch[0])-offset}c",
                )
            else:
                len_frac = len(base_frac) - offset

            after_match = maintext().rowcol(f"{match_index}+{len_frac}c")
            search_range = IndexRange(
                after_match, maintext().rowcol("TempEndSelection")
            )
