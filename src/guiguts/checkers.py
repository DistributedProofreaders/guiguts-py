"""Support running of checking tools"""

import io
import logging
import tkinter as tk
from tkinter import font
from typing import Any, Callable

from guiguts.mainwindow import maintext, root, ScrolledReadOnlyText
from guiguts.tools.pptxt import pptxt
from guiguts.tools.pptxt import color
from guiguts.widgets import ToplevelDialog

logger = logging.getLogger(__package__)

TOOL_TMPFILE = "ggtmpfile.txt"


def run_pptxt() -> None:
    """Run the pptxt tool on the current file."""
    run_tool(pptxt, "PPtxt results", verbose=False, highlight=True)


def run_tool(tool_func: Callable, title: str, **kwargs: Any) -> None:
    """Run a tool & display results in dialog.

    Args:
        tool_func: Function to run.
        title: Title for dialog.
        kwargs: Arguments to pass to tool, e.g. verbose=True.
    """
    buffer = maintext().get(1.0, tk.END)
    string_in = io.StringIO(buffer)
    string_out = io.StringIO()
    tool_func(string_in, string_out, **kwargs)
    dialog = CheckerDialog(title)
    dialog.set_text(string_out.getvalue())


class CheckerDialog(ToplevelDialog):
    """Dialog to show results of running a check.

    Attributes:
        text: Text widget to contain results."""

    def __init__(self, title: str, *args: Any, **kwargs: Any) -> None:
        """Initialize the dialog.

        Args:
            title:  Title for dialog.
        """
        super().__init__(root(), title, *args, **kwargs)
        self.text = ScrolledReadOnlyText(self.top_frame, wrap=tk.NONE)
        self.text.grid(column=0, row=0, sticky="NSEW")

    def set_text(self, text: str) -> None:
        """Set the text in the dialog.

        Args:
            text: Text to display in the dialog.
        """
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, text)

        self.text.tag_config("red", foreground="red")
        self.text.tag_config("green", foreground="green")
        self.text.tag_config("yellow", foreground="yellow")
        self.text.tag_config("redonyellow", foreground="red", background="yellow")

        bold_font = font.Font(self.text, self.text.cget("font"))
        bold_font.configure(weight="bold")
        self.text.tag_config("bold", font=bold_font)
        italic_font = font.Font(self.text, self.text.cget("font"))
        italic_font.configure(slant="italic")
        self.text.tag_config("italic", font=italic_font)
        self.text.tag_config("underline", underline=True)

        self.format_text("red", color.RED)
        self.format_text("green", color.GREEN)
        self.format_text("yellow", color.YELLOW)
        self.format_text("redonyellow", color.REDONYELLOW)
        self.format_text("bold", color.BOLD)
        self.format_text("italic", color.ITALIC)
        self.format_text("underline", color.UNDERLINE)

    def format_text(self, tag: str, code: str) -> None:
        """Format text based on ANSI escape sequences.

        Args:
            tag: Name of tag used to mark text.
            code: Escape sequence start code.
        """
        code_len = len(code)
        end_len = len(color.END)
        while start := self.text.search(code, "1.0"):
            end = self.text.search(color.END, start)
            if not end:
                return
            self.text.tag_add(tag, start, end)
            self.text.delete(end, f"{end}+{end_len}c")
            self.text.delete(start, f"{start}+{code_len}c")
