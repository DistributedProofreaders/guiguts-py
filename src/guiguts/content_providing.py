"""Functionality to support content providers."""

import gzip
import importlib.resources
import logging
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any

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
    sound_bell,
)
from guiguts.preferences import PersistentBoolean, PrefKey, preferences

logger = logging.getLogger(__package__)

CP_NOHYPH = str(importlib.resources.files(cp_files).joinpath("no_hyphen.json"))
NOH_KEY = "no_hyphen"


def export_prep_text_files() -> None:
    """Export the current file as separate prep text files."""
    prep_dir = filedialog.askdirectory(
        parent=root(),
        mustexist=True,
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
                    f"Shift {cmd_ctrl_string()} left click: Join all (keeping or removing hyphens)",
                    f"Shift {cmd_ctrl_string()} right click: Join all and remove from list",
                ]
            ),
            **kwargs,
        )
        self.checker = checker
        ttk.Checkbutton(
            self.custom_frame,
            text="Use Dictionary For Dehyphenating",
            variable=PersistentBoolean(PrefKey.GUIPREP_DEHYPH_USE_DICT),
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
            match_on_highlight=CheckerMatchType.ALL_MESSAGES,
        )

    def run(self) -> None:
        """Do the actual check and add messages to the dialog."""
        self.dialog.reset()

        # Decide whether to use dictionary too
        use_dict = preferences.get(PrefKey.GUIPREP_DEHYPH_USE_DICT)
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
        hyphen = "-*" if checker_entry.error_prefix == self.keep_prefix else ""
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
                    f"Shift {cmd_ctrl_string()} left click: Delete all headers/footers with matching text, or matching page number type",
                    f"Shift {cmd_ctrl_string()} right click: As above and remove from list",
                ]
            ),
            all_match_string="all with matching text, or matching page number type",
            **kwargs,
        )

    def process_remove_entries(
        self, process: bool, remove: bool, all_matching: bool
    ) -> None:
        """Process and/or remove the current entry, if any.

        Override to provide nuanced "match all" behavior: if error prefix is
        plain header/footer, use `CheckerMatchType.WHOLE`, but if page number,
        use `CheckerMatchType.ERROR_PREFIX`.
        """
        entry_index = self.current_entry_index()
        if entry_index is None:
            return
        self.match_on_highlight = (
            CheckerMatchType.WHOLE
            if self.entries[entry_index].error_prefix
            in (HeadFootChecker.header_prefix, HeadFootChecker.footer_prefix)
            else CheckerMatchType.ERROR_PREFIX
        )
        super().process_remove_entries(process, remove, all_matching)


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
            self.add_headfoot(self.header_prefix, f"{start} +1l")
            end = maintext().search(r"-----File:", f"{start} lineend", tk.END) or tk.END
            # Don't add "footer" if it's the same line as "header"
            if maintext().compare(f"{end}-1l", ">", f"{start}+1l"):
                self.add_headfoot(self.footer_prefix, f"{end} -1l")
            start = f"{end}-1c"
        self.dialog.display_entries()

    def add_headfoot(self, prefix: str, location: str) -> None:
        """Add header or footer entry to dialog.

        Args:
            prefix: `HeadFootChecker.header_prefix` or `HeadFootChecker.footer_prefix`.
            location: Index of start of potential header/footer line.
        """
        start_rowcol = maintext().rowcol(f"{location} linestart")
        end_rowcol = maintext().rowcol(f"{location} lineend")
        line = maintext().get(start_rowcol.index(), end_rowcol.index()).strip()
        # Don't want to report blank lines or pages
        if not line or line.startswith(("-----File:", "[Blank Page]")):
            return
        # Allow one substitution from an all-digit or all roman page number
        if match := re.fullmatch("([0-9]+|[ivxl]+){s<=1}", line.replace(" ", "")):
            if match.fuzzy_counts[0] == 0:  # No substitutions necessary
                prefix = self.get_detailed_prefix(prefix, self.pagenum_prefix)
            else:  # One number was mis-OCRed
                prefix = self.get_detailed_prefix(prefix, self.posspg_prefix)
        self.dialog.add_entry(
            line, IndexRange(start_rowcol, end_rowcol), error_prefix=prefix
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
            sound_bell()
            return
        maintext().mark_unset()
        start_idx = maintext().index(f"{start_mark} linestart")
        end_idx = f"{start_idx}+1l linestart"
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


def cp_character_substitutions() -> None:
    """Apply standard character substitutions."""

    # List of (search_char, replacement_string) pairs
    fixes = [
        ("\u0009", " "),  # horizontal tab
        ("\u000b", "\n"),  # vertical tab
        ("\u000c", "\n"),  # form feed
        ("\u0085", "\n"),  # next line
        ("\u00a0", " "),  # no-break space
        ("\u1680", " "),  # ogham space mark
        ("\u2000", " "),  # en quad
        ("\u2001", " "),  # em quad
        ("\u2002", " "),  # en space
        ("\u2003", " "),  # em space
        ("\u2004", " "),  # three-per-em space
        ("\u2005", " "),  # four-per-em space
        ("\u2006", " "),  # six-per-em space
        ("\u2007", " "),  # figure space
        ("\u2008", " "),  # punctuation space
        ("\u2009", " "),  # thin space
        ("\u200a", " "),  # hair space
        ("\u2010", "-"),  # hyphen
        ("\u2011", "-"),  # non-breaking hyphen
        ("\u2012", "--"),  # figure dash
        ("\u2013", "-"),  # en-dash
        ("\u2014", "--"),  # em-dash
        ("\u2015", "--"),  # horizontal bar
        ("\u2018", "'"),  # open curly single quote
        ("\u2019", "'"),  # close curly single quote
        ("\u201c", '"'),  # open curly double quote
        ("\u201d", '"'),  # close curly double quote
        ("\u2026", "..."),  # horizontal ellipsis
        ("\u2028", "\n"),  # line separator
        ("\u2029", "\n"),  # paragraph separator
        ("\u202f", " "),  # narrow no-break space
        ("\u205f", " "),  # medium mathematical space
        ("\u2212", "-"),  # minus sign
        ("\u3000", " "),  # ideographic space
    ]

    maintext().undo_block_begin()
    for search_char, replacement in fixes:
        maintext().replace_all(search_char, replacement)
    maintext().undo_block_end()
