"""Functionality to support content providers."""

import gzip
import importlib.resources
import logging
from pathlib import Path
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk
from typing import Any, Final, Iterator

from PIL import Image, UnidentifiedImageError
import regex as re

from guiguts.checkers import (
    CheckerDialog,
    CheckerEntry,
    CheckerMatchType,
    CheckerEntrySeverity,
    CheckerViewOptionsDialog,
    CheckerFilterErrorPrefix,
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
    sing_plur,
)
from guiguts.preferences import PersistentBoolean, PrefKey, preferences
from guiguts.widgets import ToplevelDialog, Busy, ToolTip, FileDialog

logger = logging.getLogger(__package__)

CP_NOHYPH = str(importlib.resources.files(cp_files).joinpath("no_hyphen.json"))
NOH_KEY = "no_hyphen"
CP_SCANNOS = str(importlib.resources.files(cp_files).joinpath("scannos.json"))
CP_ENGLIFH = str(importlib.resources.files(cp_files).joinpath("fcannos.json"))

HEAD_FOOT_CHECKER_FILTERS = [
    CheckerFilterErrorPrefix("Odd Headers", "Odd Header.*"),
    CheckerFilterErrorPrefix("Even Headers", "Even Header.*"),
    CheckerFilterErrorPrefix("Odd Footers", "Odd Footer.*"),
    CheckerFilterErrorPrefix("Even Footers", "Even Footer.*"),
]


def export_prep_text_files() -> None:
    """Export the current file as separate prep text files."""
    prep_dir = FileDialog.askdirectory(
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

    prep_dir = FileDialog.askdirectory(
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
            try:
                file_text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                file_text = file_path.read_text(encoding="iso-8859-1")
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
        ttk.Button(
            self.custom_frame,
            text="All⇒Remove",
            command=lambda: self.checker.all_keep_remove(remove=True),
        ).grid(row=0, column=2, padx=(10, 0))
        ttk.Button(
            self.custom_frame,
            text="All⇒Keep",
            command=lambda: self.checker.all_keep_remove(remove=False),
        ).grid(row=0, column=3, padx=(10, 0))


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
            self.dialog.display_entries()
            self.dialog.lift()
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

        # Some tests are English-only
        english = any(lang.startswith("en") for lang in maintext().get_language_list())
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
            if english:
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

    def all_keep_remove(self, remove: bool) -> None:
        """Swap keep/remove prefix for the selected message."""
        entry_index = self.dialog.current_entry_index()
        old_prefix = (
            DehyphenatorChecker.keep_prefix
            if remove
            else DehyphenatorChecker.remove_prefix
        )
        new_prefix = (
            DehyphenatorChecker.remove_prefix
            if remove
            else DehyphenatorChecker.keep_prefix
        )
        for idx, entry in enumerate(self.dialog.entries):
            if remove == (entry.error_prefix == DehyphenatorChecker.remove_prefix):
                continue
            entry.error_prefix = new_prefix
            linenum = self.dialog.linenum_from_entry_index(idx)
            ep_index = self.dialog.text.search(
                old_prefix, f"{linenum}.0", f"{linenum}.end"
            )
            if not ep_index:
                continue
            ep_end = f"{ep_index}+{len(old_prefix)}c"
            self.dialog.text.insert(
                ep_end, entry.error_prefix, HighlightTag.CHECKER_ERROR_PREFIX
            )
            self.dialog.text.delete(ep_index, ep_end)
        if entry_index is not None:
            self.dialog.select_entry_by_index(entry_index)


class HeadFootViewOptionsDialog(CheckerViewOptionsDialog):
    """Minimal class to identify dialog type.

    This dialog is never displayed."""

    manual_page = "Content_Providing_Menu#Header/Footer_Removal"


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

        self.view_options_frame.grid_remove()

        # Odd/Even page flags don't warrant View Options, so simulate
        # using checkbuttons in this dialog instead
        def btn_clicked(
            idx: int,
            var: tk.BooleanVar,
            wgt: ttk.Checkbutton,
        ) -> None:
            """Called when even/odd settings are changed."""
            self.view_options_filters[idx].on = var.get()
            self.display_entries()
            wgt.focus()  # Or focus gets pulled to list

        odd_head_var = tk.BooleanVar(value=True)
        odd_head_btn = ttk.Checkbutton(
            self.custom_frame,
            text="Odd Headers",
            variable=odd_head_var,
        )
        odd_head_btn["command"] = lambda: btn_clicked(0, odd_head_var, odd_head_btn)
        odd_head_btn.grid(row=0, column=0, padx=5)
        self.view_options_filters[0].on = True
        even_head_var = tk.BooleanVar(value=True)
        even_head_btn = ttk.Checkbutton(
            self.custom_frame,
            text="Even Headers",
            variable=even_head_var,
        )
        even_head_btn["command"] = lambda: btn_clicked(1, even_head_var, even_head_btn)
        even_head_btn.grid(row=0, column=1, padx=5)
        self.view_options_filters[1].on = True
        odd_foot_var = tk.BooleanVar(value=True)
        odd_foot_btn = ttk.Checkbutton(
            self.custom_frame,
            text="Odd Footers",
            variable=odd_foot_var,
        )
        odd_foot_btn["command"] = lambda: btn_clicked(2, odd_foot_var, odd_foot_btn)
        odd_foot_btn.grid(row=0, column=2, padx=5)
        self.view_options_filters[2].on = True
        even_foot_var = tk.BooleanVar(value=True)
        even_foot_btn = ttk.Checkbutton(
            self.custom_frame,
            text="Even Footers",
            variable=even_foot_var,
        )
        even_foot_btn["command"] = lambda: btn_clicked(3, even_foot_var, even_foot_btn)
        even_foot_btn.grid(row=0, column=3, padx=5)
        self.view_options_filters[3].on = True


class HeadFootChecker:
    """Header/Footer checker."""

    header_prefix = "Header: "
    footer_prefix = "Footer: "
    pagenum_prefix = "Page Number"
    posspg_prefix = "Page Num?"
    num_allcap_prefix = "Num & Allcap"
    newline_prefix = "Blank lines"

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
            view_options_dialog_class=HeadFootViewOptionsDialog,
            view_options_filters=HEAD_FOOT_CHECKER_FILTERS,
        )

    def run(self) -> None:
        """Do the actual check and add messages to the dialog."""
        self.dialog.reset()

        start = maintext().start().index()
        page_num = 0
        while start := maintext().search(r"-----File:", start, tk.END):
            page_num += 1
            # Find first non-blank line
            non_blank = maintext().search(
                r"\S", f"{start} lineend", tk.END, regexp=True
            )
            if not non_blank:  # Hit end without a non-blank
                break
            self.add_headfoot(
                page_num,
                HeadFootChecker.header_prefix,
                f"{start} +1l",
                f"{non_blank} linestart",
            )
            end = maintext().search(r"-----File:", f"{start} lineend", tk.END) or tk.END
            # Don't add "footer" if it's the same line as "header"
            if maintext().compare(f"{end} linestart", ">", f"{non_blank} linestart"):
                self.add_headfoot(
                    page_num,
                    HeadFootChecker.footer_prefix,
                    f"{end} -1l",
                    f"{end} -1l",
                )
            start = f"{end}-1c"
        self.dialog.display_entries()

    def add_headfoot(
        self, page_num: int, hf_prefix: str, location: str, non_blank: str
    ) -> None:
        """Add header or footer entry to dialog.

        Args:
            page_num: Page number of this page (starting 1 at beginning of book).
            prefix: `HeadFootChecker.header_prefix` or `HeadFootChecker.footer_prefix`.
            location: Index of start of potential header/footer line(s)
            non_blank: Index of start of first non-blank header line (same as location for footers)
        """
        even_odd = "Odd" if page_num % 2 else "Even"
        error_prefix = f"{even_odd} {hf_prefix}"
        start_rowcol = maintext().rowcol(f"{location} linestart")
        nb_rowcol = maintext().rowcol(f"{non_blank} linestart")
        end_rowcol = maintext().rowcol(f"{non_blank} lineend")
        # Add prefix to signify blank lines before header line
        nl_prefix = "⏎" * (nb_rowcol.row - start_rowcol.row)
        line = maintext().get(nb_rowcol.index(), end_rowcol.index()).strip()
        # Don't want to report blank lines or pages
        if not line or line.startswith(("-----File:", "[Blank Page]")):
            return
        no_space = line.replace(" ", "")
        # If 4-digit year (including up to one substitution), it's not a page number
        # Only do on footers in first 10 pages of book, since later it may be a page number
        if (
            page_num <= 10
            and hf_prefix == HeadFootChecker.footer_prefix
            and re.fullmatch("[1IJl]([0-9]{3}){s<=1}", line)
        ):
            pass
        # At least one digit and remainder allcaps (not just one mis-OCRed number)
        elif " " in line.strip() and re.search("[0-9]", line) and line == line.upper():
            error_prefix = self.get_detailed_prefix(
                error_prefix, HeadFootChecker.num_allcap_prefix
            )
        # Is it a valid page number?
        elif re.fullmatch("([0-9]+|[ivxlc]+)", no_space):
            error_prefix = self.get_detailed_prefix(
                error_prefix, HeadFootChecker.pagenum_prefix
            )
        # Now allow one substitution from an all-digit or all roman page number
        # Removing space will allow "123     ." (or other speck)
        elif re.fullmatch("([0-9]+|[ivxlc]+){s<=1}", no_space):
            error_prefix = self.get_detailed_prefix(
                error_prefix, HeadFootChecker.posspg_prefix
            )
        # If blank line(s) before header, note it
        elif nl_prefix:
            error_prefix = self.get_detailed_prefix(
                error_prefix, HeadFootChecker.newline_prefix
            )
        self.dialog.add_entry(
            nl_prefix + line,
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
        if "Header" in checker_entry.error_prefix:
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
            text="Convert non-standard dashes to (max 4) hyphen(s)",
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
        n_changes = 0
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
                n_changes += 1
                continue

            # Compress multiple blank lines into one
            if (
                preferences.get(PrefKey.CP_MULTI_BLANK_LINES)
                and prev_line_blank
                and this_line_blank
            ):
                maintext().delete(f"{linenum}.0", f"{linenum+1}.0")
                next_linenum -= 1  # Compensate for deleted line
                n_changes += 1
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
                line = line.replace("'!!", "'ll")  # '!! to 'll
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

            # Looong dashes to 4 hyphens (now all hyphen replaces have been done)
            if preferences.get(PrefKey.CP_DASHES_TO_HYPHEN):
                line = re.sub("-{5,}", "----", line)

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
                n_changes += 1
        logger.info(f"{sing_plur(n_changes, 'line')} changed/deleted during filtering")
        Busy.unbusy()


class CPCharSuitesDialog(ToplevelDialog):
    """Dialog to manage project's character suites."""

    manual_page = "Content_Providing_Menu#Manage_Character_Suites"

    def __init__(self) -> None:
        """Initialize Character Suites dialog."""
        super().__init__("Character Suites", resize_x=False, resize_y=False)

        def update_charsuite_flag(suite: str, var: tk.BooleanVar) -> None:
            """Update appropriate character suite flag when checkbutton is toggled."""
            the_file().charsuites[suite] = var.get()
            maintext().set_modified(True)

        for row, suite in enumerate(character_suites):
            bvar = tk.BooleanVar(value=the_file().charsuites.get(suite, False))
            ttk.Checkbutton(
                self.top_frame,
                text=suite,
                variable=bvar,
                state=tk.DISABLED if suite == "Basic Latin" else tk.ACTIVE,
                command=lambda s=suite, v=bvar: update_charsuite_flag(  # type:ignore[misc]
                    s, v
                ),
            ).grid(row=row, column=0, sticky="NSW")

    @classmethod
    def selected_charsuite_check(cls, char: str) -> tuple[list[str], bool]:
        """Return which charsuite(s) character is in (or []) and whether
        any containing charsuite is enabled."""
        suites: list[str] = []
        enabled = False
        for suite, chars in character_suites.items():
            if char in chars:
                if the_file().charsuites.get(suite, False):
                    enabled = True
                suites.append(suite)
        return suites, enabled


class CPRenumberDialog(ToplevelDialog):
    """Dialog to renumber pages & PNG files for Content Providers."""

    manual_page = "Content_Providing_Menu#Renumber_PNG_files"

    num_sections = 5

    def __init__(self) -> None:
        """Initialize CP Renumbering dialog."""
        super().__init__("Page & File Renumbering", resize_x=False, resize_y=False)

        self.top_frame.columnconfigure(0, weight=0)
        center_frame = ttk.Frame(
            self.top_frame, borderwidth=1, relief=tk.GROOVE, padding=5
        )
        center_frame.grid(row=0, column=0, sticky="NSEW")
        for col in range(5):
            center_frame.columnconfigure(col, pad=5)
        center_frame.rowconfigure(0, pad=5)
        ttk.Label(center_frame, text="Prefix").grid(row=0, column=1)
        ttk.Label(center_frame, text="Start Number").grid(row=0, column=2)
        ttk.Label(center_frame, text="End Number").grid(row=0, column=3)
        ttk.Label(center_frame, text="Suffix(es)").grid(row=0, column=4)
        self.prefixes: list[tk.StringVar] = []
        self.starts: list[tk.StringVar] = []
        self.ends: list[tk.StringVar] = []
        self.suffixes: list[tk.StringVar] = []
        for section in range(1, self.num_sections + 1):
            center_frame.rowconfigure(section, pad=5)
            self.prefixes.append(tk.StringVar(value=""))
            self.starts.append(tk.StringVar(value=""))
            self.ends.append(tk.StringVar(value=""))
            self.suffixes.append(tk.StringVar(value=""))
            ttk.Label(center_frame, text=f"Section {section}:").grid(
                row=section, column=0
            )
            prefix_entry = tk.Entry(
                center_frame,
                width=3,
                justify=tk.CENTER,
                textvariable=self.prefixes[-1],
            )
            prefix_entry.grid(row=section, column=1)
            ToolTip(
                prefix_entry,
                f'Prefix to use for section {section}, e.g. "a" for "a001", "a002",...',
            )
            start_entry = tk.Entry(
                center_frame,
                width=5,
                justify=tk.CENTER,
                textvariable=self.starts[-1],
                validate=tk.ALL,
                validatecommand=(
                    self.register(lambda val: val.isdigit() or not val),
                    "%P",
                ),
            )
            start_entry.grid(row=section, column=2)
            ToolTip(
                start_entry,
                f'Starting number to use for section {section}, e.g. "5" for "005", "006",...',
            )
            end_entry = tk.Entry(
                center_frame,
                width=5,
                justify=tk.CENTER,
                textvariable=self.ends[-1],
                validate=tk.ALL,
                validatecommand=(
                    self.register(lambda val: val.isdigit() or not val),
                    "%P",
                ),
            )
            end_entry.grid(row=section, column=3)
            ToolTip(
                end_entry,
                f'Ending number to use for section {section}, e.g. "27" for ..."026", "027"',
            )
            suffixes_entry = tk.Entry(
                center_frame,
                width=12,
                justify=tk.CENTER,
                textvariable=self.suffixes[-1],
            )
            suffixes_entry.grid(row=section, column=4)
            ToolTip(
                suffixes_entry,
                f'Suffixes to use for section {section}, e.g. "l, r" for "015l", "015r", "016l", "016r",...',
            )
        ttk.Button(
            self.top_frame, text="Renumber Pages & Files", command=self.renumber
        ).grid(row=1, column=0, sticky="NS", pady=(5, 0))

        self.num_width = 3

    def renumber(self) -> None:
        """Renumber PNGs to 001.png, 002.png,... based on dialog settings."""
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

        # Determine zero-padding based on file count
        self.num_width = 3 if len(files) <= 999 else 4

        Busy.busy()
        # To avoid overwriting, rename to temporary names first
        # First pass: rename to temporary names to avoid collisions
        temp_files: list[Path] = []
        for idx, file in enumerate(files, start=1):
            temp_name = src_dir / f"__temp_{file.name}"
            file.rename(temp_name)
            temp_files.append(temp_name)

        start = maintext().start().index()
        names = self.generate_pages()
        long_name = False
        # Second pass: rename to final names
        for idx, temp_name in enumerate(temp_files, start=1):
            base_name = next(names)
            if len(base_name) > 8:
                long_name = True
            new_name = src_dir / f"{base_name}.png"
            temp_name.rename(new_name)
            # Edit page separator lines
            if start := maintext().search(r"-----File:", start, tk.END):
                end = f"{start} lineend"
                tail = "-" * (60 - len(base_name))
                maintext().delete(start, end)
                maintext().insert(start, f"-----File: {base_name}.png{tail}")
                idx += 1
                start = end

        the_file().remove_page_marks()
        the_file().mark_page_boundaries()
        Busy.unbusy()
        if long_name:
            logger.error(
                "PNG filenames longer than 12 characters cannot be used at PGDP"
            )

    def generate_pages(
        self,
    ) -> Iterator[str]:
        """Yield page names from section parameters."""
        for sec in range(self.num_sections):
            prefix = self.prefixes[sec].get().strip()
            start = int(self.starts[sec].get().strip() or "1")
            end = int(self.ends[sec].get().strip() or "999999")
            suffixes = re.split(r"[, ]+", self.suffixes[sec].get().strip())

            for num in range(start, end + 1):
                page_num = f"{num:0{self.num_width}d}"
                if suffixes:
                    for suf in suffixes:
                        yield f"{prefix}{page_num}{suf}"
                else:
                    yield f"{prefix}{page_num}"


def cp_fix_common_scannos() -> None:
    """Fix common CP scannos."""
    # Load dictionary of scannos
    scannos_dict = load_dict_from_json(CP_SCANNOS)
    if scannos_dict is None:
        return
    Busy.busy()
    maintext().undo_block_begin()

    slurp_text = maintext().get_text()

    n_fixed = 0
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
            n_fixed += 1
    Busy.unbusy()
    logger.info(f"{sing_plur(n_fixed, 'common scanno')} fixed")


def cp_fix_englifh() -> None:
    """Fix Englifh-->English."""
    # Load dictionary of changes
    englifh_dict = load_dict_from_json(CP_ENGLIFH)
    if englifh_dict is None:
        return
    Busy.busy()
    maintext().undo_block_begin()

    slurp_text = maintext().get_text().lower()

    n_fs = 0
    n_ast = 0
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
            # Ensure we preserve the case of the original, e.g. Thanklefs --> Thankless
            # but not for uppercase "F", e.g. "fire"-->"*ire", but "Fire" --> "Fire"
            replacement = "".join(
                o if o.isupper() else e for e, o in zip(english, original)
            )
            if replacement != original:
                maintext().delete(start, end)
                maintext().insert(start, replacement)
                if "*" in replacement:
                    n_ast += 1
                else:
                    n_fs += 1
            start = f"{start}+{len(replacement)}c"
    Busy.unbusy()
    if n_ast + n_fs == 0:
        logger.info("No Olde Englifh replacements made")
    elif n_ast == 0:
        logger.info(f"{sing_plur(n_fs, 'f→s replacement')} made")
    elif n_fs == 0:
        logger.info(f"{sing_plur(n_ast, 'f→* replacement')} made")
    else:
        logger.info(
            f"{sing_plur(n_ast+n_fs, 'Olde Englifh replacement')} made ({n_fs} f→s; {n_ast} f→*)"
        )


def cp_fix_empty_pages() -> None:
    """Add "[Blank Page]" to empty pages."""

    Busy.busy()
    maintext().undo_block_begin()
    maintext().mark_set("cp_next_page", maintext().start().index())
    n_fixed = 0
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
            n_fixed += 1
    Busy.unbusy()
    logger.info(f"""{sing_plur(n_fixed, '"[Blank Page]" markup')} added""")


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


def import_tia_ocr_file() -> None:
    """Import the an Abbyy TIA OCR file."""

    # Close existing file (saving first if user wants to)
    if not the_file().close_file():
        return

    filename = FileDialog.askopenfilename(
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


# DP character suites (easier to copy and edit with regexes from the tables on
# https://www.pgdp.net/c/tools/charsuites.php than from the DP code)
# Note that combining characters are used in some of the character suites. They are
# not included here since tools such as Character Count do not treat the characters
# in a combined way, so allowing "s + combinining diaresis below" would inadvertently
# allow "combinining diaresis below" and thus "x + combinining diaresis below"
# where x is any other permitted letter.
# Combining characters appear as standalone characters in Character Count, as they always
# have, and will be flagged as not being in any character suite, thus warning the
# user to check how they are used in the file.
character_suites = {
    "Basic Cyrillic": "\u0401\u0406\u0410\u0411\u0412\u0413\u0414\u0415\u0416\u0417"
    "\u0418\u0419\u041a\u041b\u041c\u041d\u041e\u041f\u0420\u0421"
    "\u0422\u0423\u0424\u0425\u0426\u0427\u0428\u0429\u042a\u042b"
    "\u042c\u042d\u042e\u042f\u0430\u0431\u0432\u0433\u0434\u0435"
    "\u0436\u0437\u0438\u0439\u043a\u043b\u043c\u043d\u043e\u043f"
    "\u0440\u0441\u0442\u0443\u0444\u0445\u0446\u0447\u0448\u0449"
    "\u044a\u044b\u044c\u044d\u044e\u044f\u0451\u0456\u0462\u0463"
    "\u0472\u0473",
    "Basic Greek": "\u0391\u0392\u0393\u0394\u0395\u0396\u0397\u0398\u0399\u039a"
    "\u039b\u039c\u039d\u039e\u039f\u03a0\u03a1\u03a3\u03a4\u03a5"
    "\u03a6\u03a7\u03a8\u03a9\u03b1\u03b2\u03b3\u03b4\u03b5\u03b6"
    "\u03b7\u03b8\u03b9\u03ba\u03bb\u03bc\u03bd\u03be\u03bf\u03c0"
    "\u03c1\u03c2\u03c3\u03c4\u03c5\u03c6\u03c7\u03c8\u03c9",
    "Basic Latin": "\u0020\u0021\u0022\u0023\u0024\u0025\u0026\u0027\u0028\u0029"
    "\u002a\u002b\u002c\u002d\u002e\u002f\u0030\u0031\u0032\u0033"
    "\u0034\u0035\u0036\u0037\u0038\u0039\u003a\u003b\u003c\u003d"
    "\u003e\u003f\u0040\u0041\u0042\u0043\u0044\u0045\u0046\u0047"
    "\u0048\u0049\u004a\u004b\u004c\u004d\u004e\u004f\u0050\u0051"
    "\u0052\u0053\u0054\u0055\u0056\u0057\u0058\u0059\u005a\u005b"
    "\u005c\u005d\u005e\u005f\u0060\u0061\u0062\u0063\u0064\u0065"
    "\u0066\u0067\u0068\u0069\u006a\u006b\u006c\u006d\u006e\u006f"
    "\u0070\u0071\u0072\u0073\u0074\u0075\u0076\u0077\u0078\u0079"
    "\u007a\u007b\u007c\u007d\u007e\u00a1\u00a2\u00a3\u00a4\u00a5"
    "\u00a6\u00a7\u00a8\u00a9\u00aa\u00ab\u00ac\u00ae\u00af\u00b0"
    "\u00b1\u00b2\u00b3\u00b4\u00b5\u00b6\u00b7\u00b8\u00b9\u00ba"
    "\u00bb\u00bc\u00bd\u00be\u00bf\u00c0\u00c1\u00c2\u00c3\u00c4"
    "\u00c5\u00c6\u00c7\u00c8\u00c9\u00ca\u00cb\u00cc\u00cd\u00ce"
    "\u00cf\u00d0\u00d1\u00d2\u00d3\u00d4\u00d5\u00d6\u00d7\u00d8"
    "\u00d9\u00da\u00db\u00dc\u00dd\u00de\u00df\u00e0\u00e1\u00e2"
    "\u00e3\u00e4\u00e5\u00e6\u00e7\u00e8\u00e9\u00ea\u00eb\u00ec"
    "\u00ed\u00ee\u00ef\u00f0\u00f1\u00f2\u00f3\u00f4\u00f5\u00f6"
    "\u00f7\u00f8\u00f9\u00fa\u00fb\u00fc\u00fd\u00fe\u00ff\u0152"
    "\u0153\u0160\u0161\u017d\u017e\u0178\u0192\u2039\u203a",
    "Extended European Latin A": "\u0102\u0103\u0108\u0109\u011c\u011d\u014a\u014b\u015c\u015d"
    "\u016c\u016d\u0124\u0125\u0134\u0135\u0150\u0151\u0166\u0167"
    "\u0170\u0171\u0174\u0175\u0176\u0177\u0218\u0219\u021a\u021b",
    "Extended European Latin B": "\u0100\u0101\u010c\u010d\u010e\u010f\u0112\u0113\u011a\u011b"
    "\u0122\u0123\u012a\u012b\u0136\u0137\u0139\u013a\u013b\u013c"
    "\u013d\u013e\u0145\u0146\u0147\u0148\u014c\u014d\u0154\u0155"
    "\u0156\u0157\u0158\u0159\u0160\u0161\u0164\u0165\u016a\u016b"
    "\u016e\u016f\u017d\u017e",
    "Extended European Latin C": "\u0104\u0105\u0106\u0107\u010a\u010b\u010c\u010d\u0110\u0111"
    "\u0116\u0117\u0118\u0119\u0120\u0121\u0126\u0127\u012e\u012f"
    "\u0141\u0142\u0143\u0144\u015a\u015b\u0160\u0161\u016a\u016b"
    "\u0172\u0173\u0179\u017a\u017b\u017c\u017d\u017e",
    "Math symbols": "\u2202\u2203\u2207\u2208\u2209\u221a\u221e\u2220\u2229\u222a"
    "\u222b\u2234\u2235\u2237\u2248\u2260\u2261\u2264\u2265\u2282"
    "\u2283\u2295\u2297",
    "Medievalist supplement": "\u0100\u0101\u0102\u0103\u0111\u0112\u0113\u0114\u0115\u0118"
    "\u0119\u0127\u012a\u012b\u012c\u012d\u014c\u014d\u014e\u014f"
    "\u016a\u016b\u016c\u016d\u017f\u0180\u01bf\u01e2\u01e3\u01ea"
    "\u01eb\u01f7\u01fc\u01fd\u021c\u021d\u0232\u0233\u204a\ua734"
    "\ua735\ua751\ua753\ua755\ua75d\ua765\ua76b\ua76d\ua770",
    "Polytonic Greek": "\u02b9\u0375\u0391\u0392\u0393\u0394\u0395\u0396\u0397\u0398"
    "\u0399\u039a\u039b\u039c\u039d\u039e\u039f\u03a0\u03a1\u03a3"
    "\u03a4\u03a5\u03a6\u03a7\u03a8\u03a9\u03aa\u03ab\u03b1\u03b2"
    "\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8\u03b9\u03ba\u03bb\u03bc"
    "\u03bd\u03be\u03bf\u03c0\u03c1\u03c2\u03c3\u03c4\u03c5\u03c6"
    "\u03c7\u03c8\u03c9\u03ca\u03cb\u03db\u03dc\u03dd\u03f2\u03f9"
    "\u0386\u0388\u0389\u038a\u038c\u038e\u038f\u0390\u03ac\u03ad"
    "\u03ae\u03af\u03b0\u03cc\u03cd\u03ce\u1f00\u1f01\u1f02\u1f03"
    "\u1f04\u1f05\u1f06\u1f07\u1f08\u1f09\u1f0a\u1f0b\u1f0c\u1f0d"
    "\u1f0e\u1f0f\u1f10\u1f11\u1f12\u1f13\u1f14\u1f15\u1f18\u1f19"
    "\u1f1a\u1f1b\u1f1c\u1f1d\u1f20\u1f21\u1f22\u1f23\u1f24\u1f25"
    "\u1f26\u1f27\u1f28\u1f29\u1f2a\u1f2b\u1f2c\u1f2d\u1f2e\u1f2f"
    "\u1f30\u1f31\u1f32\u1f33\u1f34\u1f35\u1f36\u1f37\u1f38\u1f39"
    "\u1f3a\u1f3b\u1f3c\u1f3d\u1f3e\u1f3f\u1f40\u1f41\u1f42\u1f43"
    "\u1f44\u1f45\u1f48\u1f49\u1f4a\u1f4b\u1f4c\u1f4d\u1f50\u1f51"
    "\u1f52\u1f53\u1f54\u1f55\u1f56\u1f57\u1f59\u1f5b\u1f5d\u1f5f"
    "\u1f60\u1f61\u1f62\u1f63\u1f64\u1f65\u1f66\u1f67\u1f68\u1f69"
    "\u1f6a\u1f6b\u1f6c\u1f6d\u1f6e\u1f6f\u1f70\u1f72\u1f74\u1f76"
    "\u1f78\u1f7a\u1f7c\u1f80\u1f81\u1f82\u1f83\u1f84\u1f85\u1f86"
    "\u1f87\u1f88\u1f89\u1f8a\u1f8b\u1f8c\u1f8d\u1f8e\u1f8f\u1f90"
    "\u1f91\u1f92\u1f93\u1f94\u1f95\u1f96\u1f97\u1f98\u1f99\u1f9a"
    "\u1f9b\u1f9c\u1f9d\u1f9e\u1f9f\u1fa0\u1fa1\u1fa2\u1fa3\u1fa4"
    "\u1fa5\u1fa6\u1fa7\u1fa8\u1fa9\u1faa\u1fab\u1fac\u1fad\u1fae"
    "\u1faf\u1fb0\u1fb1\u1fb2\u1fb3\u1fb4\u1fb6\u1fb7\u1fb8\u1fb9"
    "\u1fba\u1fbc\u1fc2\u1fc3\u1fc4\u1fc6\u1fc7\u1fc8\u1fca\u1fcc"
    "\u1fd0\u1fd1\u1fd2\u1fd6\u1fd7\u1fd8\u1fd9\u1fda\u1fe0\u1fe1"
    "\u1fe2\u1fe4\u1fe5\u1fe6\u1fe7\u1fe8\u1fe9\u1fea\u1fec\u1ff2"
    "\u1ff3\u1ff4\u1ff6\u1ff7\u1ff8\u1ffa\u1ffc",
    "Semitic and Indic transcriptions": "\u0100\u0101\u0112\u0113\u012a\u012b\u014c\u014d\u015a\u015b"
    "\u0160\u0161\u016a\u016b\u02be\u02bf\u1e0c\u1e0d\u1e24\u1e25"
    "\u1e2a\u1e2b\u1e32\u1e33\u1e37\u1e39\u1e40\u1e41\u1e42\u1e43"
    "\u1e44\u1e45\u1e46\u1e47\u1e5a\u1e5b\u1e5c\u1e5d\u1e62\u1e63"
    "\u1e6c\u1e6d\u1e92\u1e93\u1e94\u1e95\u1e96",
    # Characters s, t & z with combining diaresis below are in the Semitic/Indic charsuite
    # They are not included for the reason explained in the comment above
    # \u0053\u0324\u0054\u0324\u005a\u0324\u0073\u0324\u0074\u0324\u007a\u0324
    "Symbols collection": "\u0292\u2108\u2114\u211e\u2125\u2609\u260a\u260b\u260c\u260d"
    "\u263d\u263e\u263f\u2640\u2641\u2642\u2643\u2644\u2645\u2646"
    # In the symbols charsuite, these 12 astrological signs are followed by \x{fe0e},
    # a variation selector, to force them to be displayed in text rather than image form
    # The variation selectors are omitted for the reason explained in the comment above
    "\u2648\u2649\u264a\u264b\u264c\u264d\u264e\u264f\u2650\u2651\u2652\u2653"
    "\u2669\u266a\u266d\u266e\u266f",
}
