"""Support running of checking tools"""

import logging
import os.path
import subprocess
import tkinter as tk
from tkinter import font
from typing import Any

from guiguts.mainwindow import maintext, root, ScrolledReadOnlyText
from guiguts.widgets import ToplevelDialog

logger = logging.getLogger(__package__)

TOOL_TMPFILE = "ggtmpfile.txt"


def run_pptxt(pathname: str) -> None:
    """Run the pptxt tool on the current file.

    Args:
        pathname: Path name of currently loaded file.
    """
    result = run_tool("pptxt", pathname)
    if result.returncode == 0:
        dialog = CheckerDialog("PPtxt results")
        dialog.set_text(result.stdout)


def run_tool(tool_name: str, pathname: str) -> subprocess.CompletedProcess:
    """Run a tool. Pass the name of a temporary file containing
    the currently loaded text as the sole argument to the tool.

    Subprocess is run in the current project folder.

    Args:
        tool_name: Name of tool to run. For now, assumes this is the
          basename of a python script in the tools subdir, e.g.
          `pptxt` assumes tool is `tools/pptxt.py`.
          May be handled differently in due course.
        path_name: Path name of currently loaded file.

    Returns:
        CompletedProcess object containing stdout & stderr output.
    """
    script = os.path.join(os.path.dirname(__file__), "tools", tool_name + ".py")

    # Change to project dir to run tool in case any current dir
    # is read-only/under the release, or in case any files get left behind.
    save_cwd = os.getcwd()
    os.chdir(os.path.dirname(pathname))
    maintext().do_save(TOOL_TMPFILE)
    result = run_python_tool(script)
    os.remove(TOOL_TMPFILE)
    os.chdir(save_cwd)

    if result.returncode != 0:
        if result.stderr:
            logger.error(f"Error running {tool_name}. Details in message log")
            logger.info(result.stderr)
        else:
            logger.error(f"Unknown error running {tool_name}")
    return result


def run_python_tool(script_name: str) -> subprocess.CompletedProcess:
    """Run python tool, allowing for interpreter being named either
    `python` or `python3`.

    Args:
        script_name: Pathname of script to run.

    Returns:
        CompletedProcess object containing stdout & stderr output.
    """
    try:
        result = run_subprocess(["python3", script_name, TOOL_TMPFILE])
    except FileNotFoundError:
        result = run_subprocess(["python", script_name, TOOL_TMPFILE])
    return result


def run_subprocess(command: list[str]) -> subprocess.CompletedProcess:
    """Spawn a subprocess.

    Executes a command, sends input to the process and captures
    stdout and stderr from the process.

    Args:
        command: List of strings containing command and arguments.
    """
    return subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )


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
        bold_font = font.Font(self.text, self.text.cget("font"))
        bold_font.configure(weight="bold")
        self.text.tag_config("bold", font=bold_font)
        italic_font = font.Font(self.text, self.text.cget("font"))
        italic_font.configure(slant="italic")
        self.text.tag_config("italic", font=italic_font)
        self.text.tag_config("underline", underline=True)

        self.format_text("red", "\033[91m")
        self.format_text("green", "\033[92m")
        self.format_text("yellow", "\033[93m")
        self.format_text("bold", "\033[1m")
        self.format_text("italic", "\033[3m")
        self.format_text("underline", "\033[4m")

    def format_text(self, tag: str, code: str) -> None:
        """Format text based on ANSI escape sequences.

        Args:
            tag: Name of tag used to mark text.
            code: Escape sequence start code.
        """
        code_len = len(code)
        while start := self.text.search(code, "1.0"):
            end = self.text.search("\033[0m", start)
            if not end:
                return
            self.text.tag_add(tag, start, end)
            self.text.delete(end, f"{end}+4c")
            self.text.delete(start, f"{start}+{code_len}c")
