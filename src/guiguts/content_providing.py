"""Functionality to support content providers."""

import gzip
import logging
from pathlib import Path
from tkinter import filedialog

import regex as re

from guiguts.file import the_file
from guiguts.maintext import maintext
from guiguts.root import root
from guiguts.utilities import folder_dir_str

logger = logging.getLogger(__package__)


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

        file_text = re.sub(r"[ \n]+$", "", file_text)
        separator = f"-----File: {file_path.stem}.png" + "-" * 45
        maintext().insert("end", separator + "\n" + file_text + "\n")
    maintext().undo_block_end()

    the_file().mark_page_boundaries()
    maintext().set_insert_index(maintext().start())
    # Give user chance to save immediately
    the_file().save_as_file()


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
