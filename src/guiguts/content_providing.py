"""Functionality to support content providers."""

import gzip
import importlib.resources
import logging
from pathlib import Path
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any, Final

from PIL import Image, UnidentifiedImageError
import regex as re

from guiguts.checkers import (
    CheckerDialog,
    CheckerEntry,
    CheckerMatchType,
    CheckerEntrySeverity,
)
from guiguts.data import cp_files
from guiguts.file import the_file
from guiguts.maintext import maintext, HighlightTag
from guiguts.project_dict import ProjectDict
from guiguts.root import root
from guiguts.spell import get_spell_checker, SPELL_CHECK_OK_YES
from guiguts.utilities import (
    folder_dir_str,
    cmd_ctrl_string,
    load_dict_from_json,
    IndexRange,
)
from guiguts.preferences import PersistentBoolean, PrefKey, preferences
from guiguts.widgets import ToplevelDialog, Busy

logger = logging.getLogger(__package__)

CP_NOHYPH = str(importlib.resources.files(cp_files).joinpath("no_hyphen.json"))
NOH_KEY = "no_hyphen"
CP_SCANNOS = str(importlib.resources.files(cp_files).joinpath("scannos.json"))
CP_ENGLIFH = str(importlib.resources.files(cp_files).joinpath("fcannos.json"))


def export_prep_text_files() -> None:
    """Export the current file as separate prep text files."""
    prep_dir = filedialog.askdirectory(
        parent=root(),
        title=f"Select {folder_dir_str(True)} to export prep text files to",
    )
    if not prep_dir:
        return

    prep_path = Path(prep_dir)
    if not prep_path.is_dir():
        logger.error(f'Selected path "{prep_path}" is not a {folder_dir_str(True)}.')
        return

    # Get sorted list of page marks
    pg_mark_list = sorted(
        [name for name in maintext().mark_names() if name.startswith("Pg")]
    )

    for pg_idx, pg_mark in enumerate(pg_mark_list):
        next_mark = (
            "end" if pg_idx == len(pg_mark_list) - 1 else pg_mark_list[pg_idx + 1]
        )
        # Get the text to save to this file
        if maintext().compare(pg_mark, "<=", next_mark):
            file_text = maintext().get(pg_mark, next_mark)
        else:
            logger.error(
                "Corrupt or badly-ordered page markers detected.\n"
                "Quit, then delete json file and any prep text files written.\n"
                "Restart, and check page separator lines are correct before retrying."
            )
            return
        # Strip leading page marker line and trailing blank lines
        file_text = re.sub(r"---+\s?File:.+?\.(png|jpg)---.+?\n", "", file_text)
        file_text = re.sub("\n+$", "", file_text)
        full_path = prep_path / f"{pg_mark[2:]}.txt"
        try:
            full_path.write_text(file_text, encoding="utf-8")
        except OSError as e:
            logger.error(f'Error writing to file "{full_path}": {e}')


def import_prep_text_files() -> None:
    """Import the current file as separate prep text files."""

    # Close existing file (saving first if user wants to)
    if not the_file().close_file():
        return

    prep_dir = filedialog.askdirectory(
        parent=root(),
        mustexist=True,
        title=f"Select {folder_dir_str(True)} to import prep text files from",
    )
    if not prep_dir:
        return

    prep_path = Path(prep_dir)
    if not prep_path.is_dir():
        logger.error(f'Selected path "{prep_path}" is not a {folder_dir_str(True)}.')
        return

    # Get all .txt files sorted alphabetically
    txt_files = sorted(prep_path.glob("*.txt"))

    if not txt_files:
        logger.warning(f'No ".txt" files found in {prep_path}.')
        maintext().undo_block_end()
        return

    maintext().undo_block_begin()
    # Insert each file into maintext, with separator lines
    for file_path in txt_files:
        try:
            file_text = file_path.read_text(encoding="utf-8")
        except OSError as e:
            logger.error(f"Error reading file '{file_path}': {e}")
            maintext().undo_block_end()
            return

        # Remove BOM & trailing blank lines
        file_text = re.sub(r"[ \n]+$", "", file_text.replace("\ufeff", ""))
        separator = f"-----File: {file_path.stem}.png" + "-" * 45
        maintext().insert("end", separator + "\n" + file_text + "\n")
    maintext().undo_block_end()

    the_file().mark_page_boundaries()
    maintext().set_insert_index(maintext().start())
    # Give user chance to save immediately to dir containing files dir
    the_file().save_as_file(str(prep_path.parent))


class DehyphenatorCheckerDialog(CheckerDialog):
    """Dehyphenator Checker dialog."""

    manual_page = "Content_Providing_Menu#Dehyphenation"

    def __init__(self, checker: "DehyphenatorChecker", **kwargs: Any) -> None:
        """Initialize Dehyphenator dialog.

        Args:
            checker: Dehyphenator Checker controlled by the dialog."""
        super().__init__(
            "Dehyphenation",
            tooltip="\n".join(
                [
                    "Left click: Select & find occurrence of hyphenation",
                    "Right click: Hide occurrence of hyphenation in list",
                    f"{cmd_ctrl_string()} left click: Join this occurrence (keeping or removing hyphen)",
                    f"{cmd_ctrl_string()} right click: Join this occurrence and remove from list",
                    f"Shift {cmd_ctrl_string()} left click: Join all with matching error type",
                    f"Shift {cmd_ctrl_string()} right click: Join all with matching error type and remove from list",
                ]
            ),
            **kwargs,
        )
        self.checker = checker
        ttk.Checkbutton(
            self.custom_frame,
            text="Use Dictionary For Dehyphenating",
            variable=PersistentBoolean(PrefKey.CP_DEHYPH_USE_DICT),
        ).grid(row=0, column=0)
        ttk.Button(
            self.custom_frame, text="Keep⇔Remove", command=self.checker.swap_keep_remove
        ).grid(row=0, column=1, padx=(20, 0))


class DehyphenatorChecker:
    """Dehyphenator checker."""

    remove_prefix = "Remove: "
    keep_prefix = "Keep: "

    def __init__(self) -> None:
        """Initialize Dehyphenator checker."""
        self.dialog: DehyphenatorCheckerDialog = DehyphenatorCheckerDialog.show_dialog(
            checker=self,
            rerun_command=self.run,
            process_command=self.dehyphenate,
            match_on_highlight=CheckerMatchType.ERROR_PREFIX,
        )

    def run(self) -> None:
        """Do the actual check and add messages to the dialog."""
        self.dialog.reset()

        # Decide whether to use dictionary too
        use_dict = preferences.get(PrefKey.CP_DEHYPH_USE_DICT)
        spell_checker = get_spell_checker()
        if spell_checker is None:
            return
        dummy_proj_dict = ProjectDict()

        # First load words that should always be dehyphenated
        always_noh = load_dict_from_json(CP_NOHYPH)
        if always_noh is None:
            return
        # Check list of words is in the json file
        if NOH_KEY not in always_noh:
            logger.error(f"{CP_NOHYPH} does not contain {NOH_KEY} key")
            return
        # Get whole file and convert dash variants to hyphens
        slurp_text = maintext().get_text()
        slurp_text = re.sub(r"[\u00AD\u2010\u2011]", "-", slurp_text)
        slurp_text = re.sub(r"[\u2012\u2013\u2014\u2015]", "--", slurp_text)
        # Now list of words contained in file
        words = re.split(r"[^\p{Alpha}']+", slurp_text)
        # Combine into a single set
        no_hyphens = set(always_noh[NOH_KEY]) | set(words)

        # For every end-of-line hyphen, check if the potentially-joined word
        # is in our set of good non-hyphenated words
        start = maintext().start().index()
        while start := maintext().search(r"-$", start, tk.END, regexp=True):
            start = maintext().index(f"{start} lineend")
            line = maintext().get(f"{start} linestart", f"{start} lineend")
            if line.startswith("-----File:"):
                continue
            next_line = maintext().get(f"{start} +1l linestart", f"{start} +1l lineend")
            # If end of page, add asterisk now
            if next_line.startswith("-----File:"):
                maintext().insert(f"{start} lineend", "*")
                continue
            # Get portion of word before (possibly spaced) eol hyphen
            if match := re.search(r"(\w[\w']*?)( ?-)$", line):
                frag1 = match[1]
                punc1 = match[2]
            else:
                frag1 = ""
                punc1 = ""
            # Get portion of word from start of next line
            if match := re.search(r"^([\w']+)([^\p{IsSpace}]*)", next_line):
                frag2 = match[1]
                punc2 = match[2]
            else:
                frag2 = ""
                punc2 = ""
            if not frag1 or not frag2:
                continue
            # Can join if two parts make a valid whole word
            lf1 = len(frag1) + len(punc1)
            lf2 = len(frag2) + len(punc2)
            start_rowcol = maintext().rowcol(f"{start} lineend -{lf1}c")
            end_rowcol = maintext().rowcol(f"{start} +1l linestart +{lf2}c")
            remove = f"{frag1}{frag2}" in no_hyphens
            if not remove:
                remove = bool(
                    re.match(
                        r"\b([\w]?ing|[ts]ion|est|er|[mst]?ent|[\w]?ie)[s]?$", frag2
                    )
                )
            if not remove:
                remove = bool(re.match(r"\b([dt]?ed|[\w]?ly)$", frag2))
            if not remove:
                remove = frag2 == "ness" or frag1 in (
                    "con",
                    "ad",
                    "as",
                    "en",
                    "un",
                    "re",
                    "de",
                    "im",
                )
            if not remove and use_dict:
                remove = (
                    spell_checker.spell_check_word(f"{frag1}{frag2}", dummy_proj_dict)
                    == SPELL_CHECK_OK_YES
                )

            self.dialog.add_entry(
                f"{frag1}{punc1}{frag2}",
                IndexRange(start_rowcol, end_rowcol),
                error_prefix=self.remove_prefix if remove else self.keep_prefix,
                severity=CheckerEntrySeverity.INFO,
            )
        self.dialog.display_entries()

    def dehyphenate(self, checker_entry: CheckerEntry) -> None:
        """Dehyphenate the given word."""
        if checker_entry.text_range is None:
            return
        start_mark = DehyphenatorCheckerDialog.mark_from_rowcol(
            checker_entry.text_range.start
        )
        end_mark = DehyphenatorCheckerDialog.mark_from_rowcol(
            checker_entry.text_range.end
        )
        maintext().undo_block_begin()
        # Fetch and delete second half of word
        part2 = maintext().get(f"{end_mark} linestart", end_mark)
        maintext().delete(f"{end_mark} linestart", end_mark)
        # If it would leave leading blanks or empty line, remove them
        leading_blanks = maintext().get(end_mark, f"{end_mark} lineend")
        nspace = len(leading_blanks) - len(leading_blanks.lstrip())
        if nspace > 0:
            maintext().delete(end_mark, f"{end_mark} +{nspace}c")
        if maintext().compare(end_mark, "==", f"{end_mark} lineend"):
            maintext().delete(end_mark)
        # Remove eol hyphen if needed (possibly spaced)
        last_ch = f"{start_mark} lineend -1c"
        if maintext().get(last_ch) == "-":
            maintext().delete(last_ch)
        if maintext().get(last_ch) == " ":
            maintext().delete(last_ch)
        hyphen = "-" if checker_entry.error_prefix == self.keep_prefix else ""
        maintext().insert(f"{start_mark} lineend", f"{hyphen}{part2}")

    def swap_keep_remove(self) -> None:
        """Swap keep/remove prefix for the selected message."""
        # Find selected entry
        entry_index = self.dialog.current_entry_index()
        if entry_index is None:
            return
        entry = self.dialog.entries[entry_index]
        # Get existing prefix & swap it
        old_prefix = entry.error_prefix
        entry.error_prefix = (
            DehyphenatorChecker.remove_prefix
            if old_prefix == DehyphenatorChecker.keep_prefix
            else DehyphenatorChecker.keep_prefix
        )
        # Also update the dialog
        linenum = self.dialog.linenum_from_entry_index(entry_index)
        ep_index = self.dialog.text.search(old_prefix, f"{linenum}.0", f"{linenum}.end")
        if not ep_index:
            return
        ep_end = f"{ep_index}+{len(old_prefix)}c"
        self.dialog.text.insert(
            ep_end, entry.error_prefix, HighlightTag.CHECKER_ERROR_PREFIX
        )
        self.dialog.text.delete(ep_index, ep_end)
        self.dialog.select_entry_by_index(entry_index)


class HeadFootCheckerDialog(CheckerDialog):
    """Header/Footer Checker dialog."""

    manual_page = "Content_Providing_Menu#Header/Footer_Removal"

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Header/Footer dialog."""
        super().__init__(
            "Header/Footer Removal",
            tooltip="\n".join(
                [
                    "Left click: Select & find header/footer",
                    "Right click: Hide occurrence of header/footer in list",
                    f"{cmd_ctrl_string()} left click: Delete this header/footer",
                    f"{cmd_ctrl_string()} right click: Delete this header/footer and remove from list",
                    f"Shift {cmd_ctrl_string()} left click: Delete all headers/footers with matching error type",
                    f"Shift {cmd_ctrl_string()} right click: Delete all headers/footers with matching error type and remove from list",
                ]
            ),
            **kwargs,
        )


class HeadFootChecker:
    """Header/Footer checker."""

    header_prefix = "Header: "
    footer_prefix = "Footer: "
    pagenum_prefix = "Page Number"
    posspg_prefix = "Page Num?"

    def __init__(self) -> None:
        """Initialize Header/Footer checker."""

        def sort_key_error(
            entry: CheckerEntry,
        ) -> tuple[int, str, int, int]:
            """Sort key function to sort entries by error prefix, then line number."""
            assert entry.text_range is not None
            return (
                entry.section,
                entry.error_prefix,
                entry.text_range.start.row,
                entry.text_range.start.col,
            )

        self.dialog = HeadFootCheckerDialog.show_dialog(
            rerun_command=self.run,
            process_command=self.delete_head_foot,
            sort_key_alpha=sort_key_error,
            match_on_highlight=CheckerMatchType.ERROR_PREFIX,
        )

    def run(self) -> None:
        """Do the actual check and add messages to the dialog."""
        self.dialog.reset()

        start = maintext().start().index()
        while start := maintext().search(r"-----File:", start, tk.END):
            # Find first non-blank line
            non_blank = maintext().search(
                r"\S", f"{start} lineend", tk.END, regexp=True
            )
            if not non_blank:  # Hit end without a non-blank
                break
            self.add_headfoot(
                self.header_prefix, f"{start} +1l", f"{non_blank} linestart"
            )
            end = maintext().search(r"-----File:", f"{start} lineend", tk.END) or tk.END
            # Don't add "footer" if it's the same line as "header"
            if maintext().compare(f"{end} linestart", ">", f"{non_blank} linestart"):
                self.add_headfoot(self.footer_prefix, f"{end} -1l", f"{end} -1l")
            start = f"{end}-1c"
        self.dialog.display_entries()

    def add_headfoot(self, error_prefix: str, location: str, non_blank: str) -> None:
        """Add header or footer entry to dialog.

        Args:
            prefix: `HeadFootChecker.header_prefix` or `HeadFootChecker.footer_prefix`.
            location: Index of start of potential header/footer line(s)
            non_blank: Index of start of first non-blank header line (same as location for footers)
        """
        start_rowcol = maintext().rowcol(f"{location} linestart")
        nb_rowcol = maintext().rowcol(f"{non_blank} linestart")
        end_rowcol = maintext().rowcol(f"{non_blank} lineend")
        # Add prefix to signify blank lines before header line
        newline_prefix = "⏎" * (nb_rowcol.row - start_rowcol.row)
        line = maintext().get(nb_rowcol.index(), end_rowcol.index()).strip()
        # Don't want to report blank lines or pages
        if not line or line.startswith(("-----File:", "[Blank Page]")):
            return
        # Allow one substitution from an all-digit or all roman page number
        if match := re.fullmatch("([0-9]+|[ivxl]+){s<=1}", line.replace(" ", "")):
            if match.fuzzy_counts[0] == 0:  # No substitutions necessary
                error_prefix = self.get_detailed_prefix(
                    error_prefix, self.pagenum_prefix
                )
            else:  # One number was mis-OCRed
                error_prefix = self.get_detailed_prefix(
                    error_prefix, self.posspg_prefix
                )
        self.dialog.add_entry(
            newline_prefix + line,
            IndexRange(start_rowcol, end_rowcol),
            error_prefix=error_prefix,
        )

    def get_detailed_prefix(self, prefix: str, detail: str) -> str:
        """Add detail to header/footer prefix. Assumes valid arguments."""
        return prefix.replace(":", f" {detail}:")

    def delete_head_foot(self, checker_entry: CheckerEntry) -> None:
        """Delete the given header/footer & following/preceding blank lines."""
        assert checker_entry.text_range is not None
        start_mark = self.dialog.mark_from_rowcol(checker_entry.text_range.start)
        end_mark = self.dialog.mark_from_rowcol(checker_entry.text_range.end)
        # If it's already been deleted, don't delete another line
        if maintext().compare(start_mark, "==", end_mark):
            return
        maintext().mark_unset()
        start_idx = maintext().index(f"{start_mark} linestart")
        end_idx = f"{end_mark}+1l linestart"
        # Also remove leading/trailing blank lines if they would be left behind
        if checker_entry.error_prefix.startswith(
            HeadFootChecker.header_prefix.replace(": ", "")
        ):
            while maintext().get(end_idx, f"{end_idx} lineend").strip() == "":
                end_idx = maintext().index(f"{end_idx} +1l")
        else:
            while (
                maintext().get(f"{start_idx}-1l", f"{start_idx}-1l lineend").strip()
                == ""
            ):
                start_idx = maintext().index(f"{start_idx} -1l")
        maintext().delete(start_idx, end_idx)


class CPProcessingDialog(ToplevelDialog):
    """Dialog to process files for Content Providers."""

    manual_page = "Content_Providing_Menu#Prep_Text_Filtering"

    def __init__(self) -> None:
        """Initialize Prep Text Processing dialog."""
        super().__init__("Prep Text Filtering", resize_x=False, resize_y=False)

        self.top_frame.columnconfigure(0, weight=0)
        center_frame = ttk.Frame(
            self.top_frame, borderwidth=1, relief=tk.GROOVE, padding=5
        )
        center_frame.grid(row=0, column=0, sticky="NSEW", columnspan=2)
        center_frame.columnconfigure(0, pad=10)

        ttk.Checkbutton(
            center_frame,
            text="Convert multiple blank lines to single",
            variable=PersistentBoolean(PrefKey.CP_MULTI_BLANK_LINES),
        ).grid(row=0, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Remove blank lines from top of page",
            variable=PersistentBoolean(PrefKey.CP_BLANK_LINES_TOP),
        ).grid(row=0, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert multiple spaces to single space",
            variable=PersistentBoolean(PrefKey.CP_MULTIPLE_SPACES),
        ).grid(row=1, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert non-standard whitespace to space/newline",
            variable=PersistentBoolean(PrefKey.CP_WHITESPACE_TO_SPACE),
        ).grid(row=1, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert non-standard dashes to hyphen(s)",
            variable=PersistentBoolean(PrefKey.CP_DASHES_TO_HYPHEN),
        ).grid(row=2, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Remove space on either side of hyphens",
            variable=PersistentBoolean(PrefKey.CP_SPACED_HYPHENS),
        ).grid(row=2, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert spaced hyphens to emdashes",
            variable=PersistentBoolean(PrefKey.CP_SPACED_HYPHEN_EMDASH),
        ).grid(row=3, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Remove space before mid-word apostrophes",
            variable=PersistentBoolean(PrefKey.CP_SPACED_APOSTROPHES),
        ).grid(row=3, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Remove space before  .  ,  !  ?  :  ;",
            variable=PersistentBoolean(PrefKey.CP_SPACE_BEFORE_PUNC),
        ).grid(row=4, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert, & ensure space before, ellipsis (except ....)",
            variable=PersistentBoolean(PrefKey.CP_SPACE_BEFORE_ELLIPSIS),
        ).grid(row=4, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Remove space after open- or before close-brackets",
            variable=PersistentBoolean(PrefKey.CP_SPACED_BRACKETS),
        ).grid(row=5, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Remove suspect punctuation from start/end of line",
            variable=PersistentBoolean(PrefKey.CP_PUNCT_START_END),
        ).grid(row=5, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Remove suspect space around quotes",
            variable=PersistentBoolean(PrefKey.CP_DUBIOUS_SPACED_QUOTES),
        ).grid(row=6, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert curly quotes to straight",
            variable=PersistentBoolean(PrefKey.CP_CURLY_QUOTES),
        ).grid(row=6, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert two commas to one double quote",
            variable=PersistentBoolean(PrefKey.CP_COMMAS_DOUBLE_QUOTE),
        ).grid(row=7, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert two single quotes to one double quote",
            variable=PersistentBoolean(PrefKey.CP_SINGLE_QUOTES_DOUBLE),
        ).grid(row=7, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert consecutive underscores to emdashes",
            variable=PersistentBoolean(PrefKey.CP_UNDERSCORES_EMDASH),
        ).grid(row=8, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert forward slash to comma apostrophe",
            variable=PersistentBoolean(PrefKey.CP_SLASH_COMMA_APOSTROPHE),
        ).grid(row=8, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert solitary j to semicolon",
            variable=PersistentBoolean(PrefKey.CP_J_SEMICOLON),
        ).grid(row=9, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Fix common 2/3 letter scannos (tii⇒th, wb⇒wh, etc.)",
            variable=PersistentBoolean(PrefKey.CP_COMMON_LETTER_SCANNOS),
        ).grid(row=9, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert he to be if it follows to",
            variable=PersistentBoolean(PrefKey.CP_TO_HE_BE),
        ).grid(row=10, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert solitary lowercase l to I",
            variable=PersistentBoolean(PrefKey.CP_L_TO_I),
        ).grid(row=10, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert solitary 0 to O",
            variable=PersistentBoolean(PrefKey.CP_0_TO_O),
        ).grid(row=11, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Convert solitary 1 to I",
            variable=PersistentBoolean(PrefKey.CP_1_TO_I),
        ).grid(row=11, column=1, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Expand fractions, e.g. ½ to 1/2, 3¼ to 3-1/4",
            variable=PersistentBoolean(PrefKey.CP_FRACTIONS),
        ).grid(row=12, column=0, sticky="NSW")
        ttk.Checkbutton(
            center_frame,
            text="Expand super/subscripts, e.g. x³ to x^3, x₂ to x_{{2}}",
            variable=PersistentBoolean(PrefKey.CP_SUPER_SUB_SCRIPTS),
        ).grid(row=12, column=1, sticky="NSW")

        onoff_frame = ttk.Frame(self.top_frame)
        onoff_frame.grid(row=1, column=0, sticky="NS")
        ttk.Button(
            onoff_frame, text="All On", command=lambda: self.all_on_off(True)
        ).grid(row=0, column=0, sticky="NS", pady=(5, 0), padx=5)
        ttk.Button(
            onoff_frame, text="All Off", command=lambda: self.all_on_off(False)
        ).grid(row=0, column=1, sticky="NS", pady=(5, 0), padx=5)
        ttk.Button(self.top_frame, text="Filter File", command=self.process).grid(
            row=1, column=1, sticky="NS", pady=(5, 0), padx=(10, 0)
        )

    def all_on_off(self, value: bool) -> None:
        """Set all checkboxes to given value."""
        for key in (
            PrefKey.CP_MULTIPLE_SPACES,
            PrefKey.CP_SPACED_HYPHENS,
            PrefKey.CP_SPACED_HYPHEN_EMDASH,
            PrefKey.CP_SPACE_BEFORE_PUNC,
            PrefKey.CP_SPACE_BEFORE_ELLIPSIS,
            PrefKey.CP_SINGLE_QUOTES_DOUBLE,
            PrefKey.CP_COMMON_LETTER_SCANNOS,
            PrefKey.CP_1_TO_I,
            PrefKey.CP_0_TO_O,
            PrefKey.CP_L_TO_I,
            PrefKey.CP_FRACTIONS,
            PrefKey.CP_SUPER_SUB_SCRIPTS,
            PrefKey.CP_UNDERSCORES_EMDASH,
            PrefKey.CP_COMMAS_DOUBLE_QUOTE,
            PrefKey.CP_SPACED_BRACKETS,
            PrefKey.CP_SLASH_COMMA_APOSTROPHE,
            PrefKey.CP_J_SEMICOLON,
            PrefKey.CP_TO_HE_BE,
            PrefKey.CP_PUNCT_START_END,
            PrefKey.CP_BLANK_LINES_TOP,
            PrefKey.CP_MULTI_BLANK_LINES,
            PrefKey.CP_DUBIOUS_SPACED_QUOTES,
            PrefKey.CP_SPACED_APOSTROPHES,
            PrefKey.CP_WHITESPACE_TO_SPACE,
            PrefKey.CP_DASHES_TO_HYPHEN,
            PrefKey.CP_CURLY_QUOTES,
        ):
            preferences.set(key, value)

    def process(self) -> None:
        """Process file according to given options."""
        fractions_map: Final[dict[str, str]] = {
            "\u00bc": "1/4",
            "\u00bd": "1/2",
            "\u00be": "3/4",
            "\u2150": "1/7",
            "\u2151": "1/9",
            "\u2152": "1/10",
            "\u2153": "1/3",
            "\u2154": "2/3",
            "\u2155": "1/5",
            "\u2156": "2/5",
            "\u2157": "3/5",
            "\u2158": "4/5",
            "\u2159": "1/6",
            "\u215a": "5/6",
            "\u215b": "1/8",
            "\u215c": "3/8",
            "\u215d": "5/8",
            "\u215e": "7/8",
        }
        fractions_class = "[" + "".join(fractions_map.keys()) + "]"

        def repl_mixed_frac(m: re.Match[str]) -> str:
            """Return "N-n/d" format fraction from match.

            Args:
                m: Match with whole number in group 1, fraction in group 2."""
            return f"{m.group(1)}-{fractions_map[m.group(2)]}"

        def repl_vulgar_frac(m: re.Match[str]) -> str:
            """Return "n/d" format fraction from match.

            Args:
                m: Match with fraction in group 1."""
            return fractions_map[m.group(0)]

        superscripts_map: Final[dict[str, str]] = {
            "\u2070": "0",
            "\u00b9": "1",
            "\u00b2": "2",
            "\u00b3": "3",
            "\u2074": "4",
            "\u2075": "5",
            "\u2076": "6",
            "\u2077": "7",
            "\u2078": "8",
            "\u2079": "9",
        }
        superscripts_class: Final[str] = "[" + "".join(superscripts_map.keys()) + "]+"

        def repl_sup(m: re.Match[str]) -> str:
            """Return ^2 or ^_{23} format superscript from match.

            Args:
                m: Match with superscript characters in group 1."""
            digits = "".join(superscripts_map[ch] for ch in m.group(0))
            return "^" + digits if len(digits) == 1 else "^{" + digits + "}"

        subscripts_map: Final[dict[str, str]] = {
            "\u2080": "0",
            "\u2081": "1",
            "\u2082": "2",
            "\u2083": "3",
            "\u2084": "4",
            "\u2085": "5",
            "\u2086": "6",
            "\u2087": "7",
            "\u2088": "8",
            "\u2089": "9",
        }
        subscripts_class: Final[str] = "[" + "".join(subscripts_map.keys()) + "]+"

        def repl_sub(m: re.Match[str]) -> str:
            """Return x_{23} format subscript from match.

            Args:
                m: Match with subscript characters in group 1."""
            digits = "".join(subscripts_map[ch] for ch in m.group(0))
            return "_{" + digits + "}"

        Busy.busy()
        maintext().undo_block_begin()

        next_linenum = 1
        all_blank_so_far = True
        prev_line_blank = False
        while maintext().compare(f"{next_linenum}.end", "<", tk.END):
            linenum = next_linenum
            next_linenum += 1
            orig_line = maintext().get(f"{linenum}.0", f"{linenum}.end")
            if orig_line.startswith("-----File:"):
                all_blank_so_far = True
                continue
            line: str = orig_line

            # Convert non-standard whitespace
            if preferences.get(PrefKey.CP_WHITESPACE_TO_SPACE):
                line = re.sub(
                    "[\u0009\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000]",
                    " ",
                    line,
                )
                line = re.sub("[\u000b\u000c\u0085\u2028\u2029]", "\n", line)

            # Convert non-standard dashes
            if preferences.get(PrefKey.CP_DASHES_TO_HYPHEN):
                line = re.sub("[\u00ac\u2010\u2011\u2013\u2212]", "-", line)
                line = re.sub("[\u2012\u2014\u2015]", "--", line)

            # Strip trailing spaces
            line = line.rstrip()
            line = line.replace("\u000c", "")  # Tesseract (used to) add form feed

            # Remove blank lines at start of page
            this_line_blank = len(line) == 0
            all_blank_so_far = all_blank_so_far and this_line_blank
            if preferences.get(PrefKey.CP_BLANK_LINES_TOP) and all_blank_so_far:
                maintext().delete(f"{linenum}.0", f"{linenum+1}.0")
                next_linenum -= 1  # Compensate for deleted line
                continue

            # Compress multiple blank lines into one
            if (
                preferences.get(PrefKey.CP_MULTI_BLANK_LINES)
                and prev_line_blank
                and this_line_blank
            ):
                maintext().delete(f"{linenum}.0", f"{linenum+1}.0")
                next_linenum -= 1  # Compensate for deleted line
                continue
            prev_line_blank = this_line_blank

            # Compress double spaces
            if preferences.get(PrefKey.CP_MULTIPLE_SPACES):
                line = re.sub("  ", " ", line)

            # Spaced single hyphen - convert to emdash (double hyphen)
            if preferences.get(PrefKey.CP_SPACED_HYPHEN_EMDASH):
                line = re.sub(" -( |$)", "--", line)

            # Spaced hyphens - remove spaces
            # Guiprep had a separate option for spaced "emdashes" (double hyphens), but
            # even if that was turned off, the spaced hyphens option would removed the spaces
            if preferences.get(PrefKey.CP_SPACED_HYPHENS):
                line = line.replace(" -", "-").replace("- ", "-")

            # Spaced punctuation - remove space
            if preferences.get(PrefKey.CP_SPACE_BEFORE_PUNC):
                line = re.sub(r" ([\.,!?:;])", r"\1", line)

            # Convert single character ellipsis to 3-dot ellipsis
            # Ensure space before 3-dot ellipsis, but not if 4-dots due to period
            if preferences.get(PrefKey.CP_SPACE_BEFORE_ELLIPSIS):
                line = line.replace("…", "...")
                line = re.sub(r"(?<!\.)\.{3}(?!\.)", " ...", line)

            # Convert 2 single quotes to a double
            if preferences.get(PrefKey.CP_SINGLE_QUOTES_DOUBLE):
                line = line.replace("''", '"')

            # Various 2/3 letter scannos
            if preferences.get(PrefKey.CP_COMMON_LETTER_SCANNOS):
                # tli, tii, tb, Tli, Tii, Tb at start of word to th/Th
                # and similar for w
                line = re.sub(r"(?<=\b[tTw])([li]i|b)", "h", line)
                line = re.sub(r"\brn", "m", line)  # rn at start of word to m
                line = re.sub(
                    r"\bh(?=[lr])", "b", line
                )  # hl/hr at start of word to bl/br
                line = re.sub(r"\bVV", "W", line)  # VV at start of word to W
                line = re.sub(r"\b[vV]{2}", "w", line)  # Vv/vV/vv at start of word to w
                line = re.sub(r"tb\b", "th", line)  # tb at end of word to th
                line = re.sub(r"cl\b", "d", line)  # cl at end of word to d
                line = re.sub(
                    r"(\bcb|cb\b)", "ch", line
                )  # cb at start/end of word to ch
                line = re.sub(r"(?<=[gp])bt", "ht", line)  # gbt/pbt to ght/pht
                line = re.sub(r"\\[\\v]", "w", line)  # \v or \\ to w
                line = re.sub(r"([ai])hle", "\1ble", line)  # ahle to able; ihle to ible
                # variants of mrn to mm (not rnm or rmn which occur in words)
                line = re.sub(r"mrn|mnr|nmr|nrm", "mm", line)
                # rnp to mp (except turnpike, hornpipe & plurals, etc)
                line = (
                    line.replace("rnp", "mp")
                    .replace("tumpike", "turnpike")
                    .replace("hompipe", "hornpipe")
                )
                line = line.replace("'11", "'ll")  # '11 to 'll
                line = re.sub(r"!!(?=\w)", "H", line)  # !! to H if not at end of word
                line = re.sub(r"(?<=\w)!(?=\w)", "l", line)  # ! to l if midword

            # Standalone 1 preceded by space or quote, not followed by period --> I
            if preferences.get(PrefKey.CP_1_TO_I):
                line = re.sub(r"(?<![^'\" ])1\b(?!\.)", "I", line)

            # Standalone 0 preceded by space or quote --> O
            if preferences.get(PrefKey.CP_0_TO_O):
                line = re.sub(r"(?<![^'\" ])0\b", "O", line)

            # Standalone l preceded by space or quote, not followed by apostrophe --> I
            if preferences.get(PrefKey.CP_L_TO_I):
                line = re.sub(r"(?<![^'\" ])l\b(?!')", "I", line)
                # Or followed by apostrophe, but not a letter after that (e.g. preserve l'amie)
                line = re.sub(r"(?<![^'\" ])l'(?!\p{Letter})", "I'", line)

            # Expand Unicode fraction characters, including mixed fractions
            if preferences.get(PrefKey.CP_FRACTIONS):
                line = re.sub(r"(\d+)(" + fractions_class + ")", repl_mixed_frac, line)
                line = re.sub(fractions_class, repl_vulgar_frac, line)

            # Expand super/subscripts
            if preferences.get(PrefKey.CP_SUPER_SUB_SCRIPTS):
                line = re.sub(superscripts_class, repl_sup, line)
                line = re.sub(subscripts_class, repl_sub, line)

            # Double underscore --> emdash
            if preferences.get(PrefKey.CP_UNDERSCORES_EMDASH):
                line = line.replace("__", "--")

            # Double comma --> double quote
            if preferences.get(PrefKey.CP_COMMAS_DOUBLE_QUOTE):
                line = line.replace(",,", '"')  # ,, to "

            # Remove bad space around brackets
            if preferences.get(PrefKey.CP_SPACED_BRACKETS):
                line = re.sub(r"(?<=[[({]) ", "", line)
                line = re.sub(r" (?=[])}])", "", line)

            # Convert slash to comma+apostrophe
            if preferences.get(PrefKey.CP_SLASH_COMMA_APOSTROPHE):
                line = re.sub(r"(?<!(\W))/(?=\W)", ",'", line)

            # Convert solitary or end-of-word j to semicolon
            if preferences.get(PrefKey.CP_J_SEMICOLON):
                line = re.sub(r"(?<![ainu])j(?=\s)", ";", line)

            # Convert he --> be if it follows "to"
            if preferences.get(PrefKey.CP_TO_HE_BE):
                line = re.sub(r"\bto he\b", "to be", line)

            # Remove bad punctuation at start of line:
            #   If ellipsis, preserve it and remove extra punctuation
            #   Otherwise, just keep last beg-of-line punctuation character
            # Remove bad punctuation at end of line, i.e. after at least 3 spaces
            if preferences.get(PrefKey.CP_PUNCT_START_END):
                if line.startswith("..."):
                    line = re.sub(r"^...\p{Punct}+", "...", line)
                else:
                    line = re.sub(r"^\p{Punct}+(\p{Punct})", r"\1", line)
                line = re.sub(r"\s{3,}[\p{Punct}\s]+$", "", line)

            # Dubious spacing around quotes
            if preferences.get(PrefKey.CP_DUBIOUS_SPACED_QUOTES):
                # Straight quotes
                line = re.sub(r'^" +', '"', line)  # Beg line double quote
                line = re.sub(r' +" *$', '"', line)  # End line double quote
                line = re.sub(r' "-', '"-', line)  # With hyphen
                line = re.sub(r'the " ', 'the "', line)  # With "the"
                line = re.sub(
                    r"([.,!]) ([\"'] )", r"\1\2", line
                )  # Punctuation, space, quote, space
                # Curly quotes
                line = re.sub(r"“ +", "“", line)
                line = re.sub(r"‘ +", "‘", line)
                line = re.sub(r" +”", "”", line)
                # Only remove space around apostrophe or close-single quote
                # if beginning/end of line since unsure if apostrophe/quote
                line = re.sub(r" +’ *$", "’", line)
                line = re.sub(r"^ *’ +", "’", line)

            # Convert curly quotes to straight
            if preferences.get(PrefKey.CP_CURLY_QUOTES):
                line = re.sub(r"[‘’]", "'", line)
                line = re.sub(r"[“”]", '"', line)

            # Spaced apostrophes within words
            if preferences.get(PrefKey.CP_SPACED_APOSTROPHES):
                line = re.sub(r" 'll\b", "'ll", line)
                line = re.sub(r" 've\b", "'ve", line)
                line = re.sub(r" 's\b", "'s", line)
                line = re.sub(r" 'd\b", "'d", line)
                line = re.sub(r" n't\b", "n't", line)
                line = re.sub(r"\bI 'm\b", "I'm", line)

            # Only modify line in file if it has changed
            if line != orig_line:
                maintext().delete(f"{linenum}.0", f"{linenum}.end")
                maintext().insert(f"{linenum}.0", line)
        Busy.unbusy()


def cp_fix_common_scannos() -> None:
    """Fix common CP scannos."""
    # Load dictionary of scannos
    scannos_dict = load_dict_from_json(CP_SCANNOS)
    if scannos_dict is None:
        return
    maintext().undo_block_begin()
    Busy.busy()

    slurp_text = maintext().get_text()

    for scanno, correction in scannos_dict.items():
        # Much quicker to search in slurped text before doing search in maintext()
        # Better search also available with negative lookbehind which Tcl doesn't support.
        if not re.search(rf"(?<![-\w']){scanno}(?![-\w'])", slurp_text):
            continue
        start = maintext().start().index()
        while start := maintext().search(
            rf"\y{scanno}(?![-\w'])", start, tk.END, regexp=True
        ):
            maintext().delete(start, f"{start}+{len(scanno)}c")
            maintext().insert(start, correction)
            start = f"{start}+{len(correction)}c"
    Busy.unbusy()


def cp_fix_englifh() -> None:
    """Fix Englifh-->English."""
    # Load dictionary of changes
    englifh_dict = load_dict_from_json(CP_ENGLIFH)
    if englifh_dict is None:
        return
    maintext().undo_block_begin()
    Busy.busy()

    def match_case(word: str, template: str) -> str:
        """
        Return 'word' modified to match the capitalization pattern of 'template'.
        """
        if len(word) != len(template):
            return template
        if template.isupper():
            return word.upper()
        if template.islower():
            return word.lower()
        # Mixed case: build letter by letter, transferring case
        return "".join(
            c.upper() if t.isupper() else c.lower() for c, t in zip(word, template)
        )

    slurp_text = maintext().get_text().lower()

    for englifh, english in englifh_dict.items():
        # Much quicker to search in slurped text before doing search in maintext()
        if not re.search(rf"\b{englifh}\b", slurp_text):
            continue
        start = maintext().start().index()
        while start := maintext().search(
            rf"\y{englifh}\y", start, tk.END, regexp=True, nocase=True
        ):
            end = f"{start}+{len(englifh)}c"
            original = maintext().get(start, end)
            # Ensure we preserve the case of the original
            replacement = match_case(english, original)
            maintext().delete(start, end)
            maintext().insert(start, replacement)
            start = f"{start}+{len(replacement)}c"
    Busy.unbusy()


def cp_fix_empty_pages() -> None:
    """Add "[Blank Page]" to empty pages."""

    maintext().mark_set("cp_next_page", maintext().start().index())
    while start := maintext().search(r"-----File:", "cp_next_page", tk.END):
        # Find next page separator or end of line
        nextl = maintext().search(r"-----File:", f"{start} lineend", tk.END)
        if not nextl:
            nextl = tk.END
        # Mark next page start
        maintext().mark_set("cp_next_page", nextl)
        # If page text is nothing but whitespace, replace with [Blank Page]
        page_text = maintext().get(f"{start} +1l linestart", "cp_next_page")
        if re.fullmatch(r"\s*", page_text):
            maintext().delete(f"{start} +1l linestart", "cp_next_page")
            maintext().insert(f"{start} lineend", "\n[Blank Page]")


def compress_png_file(command: list[str], src: Path, dest: Path) -> bool:
    """
    Compress a single PNG from src → dest.
    Returns True if successful, False otherwise.
    """
    command = [s.replace("$in", str(src)).replace("$out", str(dest)) for s in command]
    if command and command[0]:
        try:
            subprocess.run(command, check=True)
        except FileNotFoundError:
            logger.error(f"Failed to compress {src}: Unable to run {command[0]}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to compress {src}: {e}")
            return False
    else:  # Use Pillow
        try:
            im = Image.open(src)
            im.save(dest, optimize=True)
        except UnidentifiedImageError:
            logger.error(f"Failed to compress {src}: Unable to identify image")
            return False
    if not dest.is_file():
        logger.error(f"Failed to create compressed file {dest}")
        return False
    return True


def cp_compress_pngs() -> None:
    """Compress the PNG files."""
    fd_str = folder_dir_str(lowercase=True)
    if not the_file().filename:
        logger.error(
            f'Save current file in parent {fd_str} before compressing files in "pngs" {fd_str}'
        )
        return
    base = Path(the_file().filename).parent
    src_dir = base / "pngs"
    new_dir = base / "pngs_temp"
    old_dir = base / "pngs_old"
    if not src_dir.is_dir():
        logger.error(f"{src_dir} is not a valid {fd_str}")
        return
    if old_dir.exists():
        logger.error(f"Error: backup {fd_str} {old_dir} already exists. Aborting.")
        return
    if new_dir.exists():
        shutil.rmtree(new_dir)  # clean up any previous run
    new_dir.mkdir()

    total_before = 0
    total_after = 0
    n_files = 0
    cmd_str = preferences.get(PrefKey.CP_PNG_CRUSH_COMMAND)
    if "$in" not in cmd_str or "$out" not in cmd_str:
        logger.error(
            'Command must include "$in" and "$out" arguments to indicate in and out file names\n'
            "Use the Settings dialog, Advanced Tab to configure the PNG compress command (examples in tooltip)"
        )
        return
    Busy.busy()
    command: list[str] = cmd_str.strip().split()
    for src_file in src_dir.glob("*.png"):
        size_before = src_file.stat().st_size
        total_before += size_before
        dest_file = new_dir / src_file.name
        if not compress_png_file(command, src_file, dest_file):
            Busy.unbusy()
            return
        size_after = dest_file.stat().st_size
        # If "compressed" file is no better, keep the old one
        if size_after >= size_before:
            shutil.copy2(src_file, dest_file)
            total_after += size_before
            logger.info(f"{src_file.name} not compressed")
        else:
            total_after += size_after
            saved = size_before - size_after
            logger.info(
                f"{src_file.name} compressed, saving {saved}B ({100*saved/size_before:.1f}%)"
            )
        root().update()
        n_files += 1

    src_dir.rename(old_dir)
    new_dir.rename(src_dir)

    total_saved = total_before - total_after
    percent_saved = 100 * total_saved / total_before if total_before > 0 else 0
    logger.info(
        f"{n_files} files compressed, saving {total_saved/1024:.1f}KB ({percent_saved:.1f}%)"
    )
    Busy.unbusy()


def cp_renumber_pngs() -> None:
    """Renumber PNGs to 001.png, 002.png,... or 0001.png, 0002.png,..."""
    fd_str = folder_dir_str(lowercase=True)
    if not the_file().filename:
        logger.error(
            f'Save current file in parent {fd_str} before renumbering files in "pngs"'
        )
        return

    # Find all .png files
    src_dir = Path(the_file().filename).parent / "pngs"
    files = sorted(src_dir.glob("*.png"))
    if not files:
        logger.error(f"No PNG files found in {src_dir}")
        return

    # Get all files referred to in `-----File:` separator lines
    fnames: list[str] = []
    start = maintext().start().index()
    while start := maintext().search(r"-----File:", start, tk.END):
        end = f"{start} lineend"
        line = maintext().get(start, end)
        fname = re.sub("-----File: *", "", line)
        fname = re.sub("-+$", "", fname)
        fnames.append(fname)
        start = end

    # Sanity checks
    if len(files) != len(fnames):
        logger.error(
            f'Number of "-----File:" lines does not match number of PNG files in {src_dir}'
        )
        return
    for idx, fname in enumerate(fnames):
        if fname != files[idx].name:
            logger.error(
                f'Filename mismatch: "-----File: {fname}" and {src_dir}/{files[idx].name}'
            )
            return

    # Determine zero-padding based on file count
    width = 3 if len(files) <= 999 else 4

    Busy.busy()
    # To avoid overwriting, rename to temporary names first
    # First pass: rename to temporary names to avoid collisions
    temp_files: list[Path] = []
    for idx, file in enumerate(files, start=1):
        temp_name = src_dir / f"__temp_{file.name}"
        file.rename(temp_name)
        temp_files.append(temp_name)

    # Second pass: rename to final names
    for idx, temp_name in enumerate(temp_files, start=1):
        new_name = src_dir / f"{idx:0{width}d}.png"
        temp_name.rename(new_name)

    # Finally, edit page separator lines
    tail = "-" * (60 - width)
    start = maintext().start().index()
    idx = 1
    while start := maintext().search(r"-----File:", start, tk.END):
        end = f"{start} lineend"
        maintext().delete(start, end)
        maintext().insert(start, f"-----File: {idx:0{width}d}.png{tail}")
        idx += 1
        start = end

    the_file().remove_page_marks()
    the_file().mark_page_boundaries()
    Busy.unbusy()


def import_tia_ocr_file() -> None:
    """Import the an Abbyy TIA OCR file."""

    # Close existing file (saving first if user wants to)
    if not the_file().close_file():
        return

    filename = filedialog.askopenfilename(
        title="Open OCR file",
        filetypes=(
            ("Gzip files", "*.gz"),
            ("All files", "*.*"),
        ),
    )
    if not filename:
        return

    maintext().undo_block_begin()
    # Open gzip file and read the text
    with gzip.open(filename) as fp:
        try:
            file_text = fp.read().decode("utf-8")
        except OSError as e:
            logger.error(f"Error reading file '{filename}': {e}")
            maintext().undo_block_end()
            return

    def flush_buffer(buffer: list[str]) -> None:
        """Flush the buffer by appending to text file after translating
        HTML entities and removing unwanted spaces & blank lines."""
        if not buffer:
            return
        buffer.append("\n")  # Ensure terminating newline - duplicates stripped below
        page_text = "".join(buffer)
        page_text = page_text.replace("&amp;", "&")
        page_text = page_text.replace("&lt;", "<")
        page_text = page_text.replace("&gt;", ">")
        page_text = page_text.replace("&apos;", "'")
        page_text = page_text.replace("&quot;", '"')
        page_text = re.sub(" +\n", "\n", page_text)  # Remove trailing spaces on lines
        page_text = re.sub(
            " +$", "", page_text
        )  # Remove trailing spaces at end of page
        page_text = re.sub("  +", " ", page_text)  # Compress multiple spaces to one
        page_text = re.sub("\n\n\n+", "\n\n", page_text)  # Multiple blank lines to one
        page_text = re.sub("\n\n+$", "\n", page_text)  # Remove trailing blank lines
        maintext().insert("end", page_text)

    page_num = 0
    buffer: list[str] = []
    # Split at closing tags so there's just one opening tag per line
    for line in re.split(r"</.+?>", file_text):
        if "<page " in line:
            flush_buffer(buffer)
            buffer = [f"\n-----File: {page_num:05}.png-----"]
            page_num += 1
        elif "<par " in line:
            buffer.append("\n")
        if "<line " in line:
            buffer.append("\n")
        # "char" can be on same text line as "line" so don't use elif
        if match := re.search(r"<charParams.*?>(.+)", line):
            buffer.append(match[1])

    flush_buffer(buffer)
    maintext().undo_block_end()

    the_file().mark_page_boundaries()
    maintext().set_insert_index(maintext().start())
    # Give user chance to save immediately
    the_file().save_as_file()
