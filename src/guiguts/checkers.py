"""Support running of checking tools"""

import regex as re
import tkinter as tk
from typing import Any

from guiguts.maintext import maintext
from guiguts.mainwindow import ScrolledReadOnlyText
from guiguts.utilities import IndexRowCol
from guiguts.widgets import ToplevelDialog


class CheckerDialog(ToplevelDialog):
    """Dialog to show results of running a check.

    Attributes:
        text: Text widget to contain results."""

    def __init__(self, root: tk.Tk, title: str, *args: Any, **kwargs: Any) -> None:
        """Initialize the dialog.

        Args:
            root: Tk root.
            title:  Title for dialog.
        """
        super().__init__(root, title, *args, **kwargs)
        self.text = ScrolledReadOnlyText(self.top_frame, wrap=tk.NONE)
        self.text.grid(column=0, row=0, sticky="NSEW")
        self.text.bind("<ButtonRelease-1>", self.jump_to_rowcol)

    def set_text(self, text: str) -> None:
        """Set the text in the dialog.

        Args:
            text: Text to display in the dialog.
        """
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, text)

    def jump_to_rowcol(self, event: tk.Event) -> None:
        """Jump to the line in the main text widget that corresponds to
        the line clicked in the dialog.

        Args:
            event: Event object containing mouse click position.
        """
        click_rowcol = IndexRowCol(self.text.index(f"@{event.x},{event.y}"))
        line = self.text.get(
            f"{click_rowcol.index()} linestart", f"{click_rowcol.index()} lineend"
        )
        if match := re.search(r"^(\d+\.\d+):", line):
            maintext().set_insert_index(IndexRowCol(match.group(1)), focus=True)
