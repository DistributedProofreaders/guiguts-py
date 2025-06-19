"""Functionality to support content providers."""

import logging
from pathlib import Path
from tkinter import filedialog

import regex as re

from guiguts.maintext import maintext
from guiguts.root import root
from guiguts.utilities import folder_dir_str

logger = logging.getLogger(__package__)


def export_as_prep_text_files() -> None:
    """Export the current file as separate prep text files."""
    prep_dir = filedialog.askdirectory(
        parent=root(),
        mustexist=True,
        title=f"Select {folder_dir_str(True)} to export text files to",
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
