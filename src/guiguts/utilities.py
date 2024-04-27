"""Handy utility functions"""

import importlib.resources
import json
import platform
import logging
from pathlib import Path
import os.path
from tkinter import _tkinter
from typing import Any, Optional, Callable, Mapping
from unicodedata import combining, normalize

import regex as re

logger = logging.getLogger(__package__)

TraversablePath = importlib.resources.abc.Traversable | Path

# Flag so application code can detect if within a pytest run - only use if really needed
# See: https://pytest.org/en/7.4.x/example/simple.html#detect-if-running-from-within-a-pytest-run
called_from_test = False  # pylint: disable=invalid-name


#
# Functions to check which OS is being used
def is_mac() -> bool:
    """Return true if running on Mac"""
    return _is_system("Darwin")


def is_windows() -> bool:
    """Return true if running on Windows"""
    return _is_system("Windows")


def is_x11() -> bool:
    """Return true if running on Linux"""
    return _is_system("Linux")


# mypy: disable-error-code="attr-defined"
def _is_system(system: str) -> bool:
    """Return true if running on given system

    Args:
        system: Name of system to check against
    """
    try:
        return _is_system.system == system
    except AttributeError as exc:
        _is_system.system = platform.system()
        if _is_system.system not in ["Darwin", "Linux", "Windows"]:
            raise RuntimeError("Unknown windowing system") from exc
        return _is_system.system == system


def load_dict_from_json(filename: str) -> Optional[dict[str, Any]]:
    """If file exists, attempt to load into dict.

    Args:
        filename: Name of JSON file to load.

    Returns:
        Dictionary if loaded successfully, or None.
    """
    if os.path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as fp:
            try:
                return json.load(fp)
            except json.decoder.JSONDecodeError as exc:
                logger.error(
                    f"Unable to load {filename} -- not valid JSON format\n" + str(exc)
                )
    return None


def load_wordfile_into_dict(path: TraversablePath, target_dict: dict) -> bool:
    """Load a one-word-per-line word list file into the target dictionary.

    Args:
        path: File to be loaded - accepts either a pathlib Path or
            an importlib.resources Traversable object.
        target_dict: Dictionary to be populated.

    Returns:
        True if file opened successfully, False if file not found.
    """
    try:
        try:
            with path.open("r", encoding="utf-8") as fp:
                data = fp.read()
        except UnicodeDecodeError:
            with path.open("r", encoding="iso-8859-1") as fp:
                data = fp.read()
        for line in data.split("\n"):
            word = line.strip()
            if word:
                target_dict[word] = True
        return True
    except FileNotFoundError:
        return False


class IndexRowCol:
    """Class to store/manipulate Tk Text indexes.

    Attributes:
        row: Row or line number.
        col: Column number.
    """

    row: int
    col: int

    def __init__(
        self, index_or_row: _tkinter.Tcl_Obj | str | int, col: Optional[int] = None
    ) -> None:
        """Construct index either from string or two ints.

        Args:
            index_or_row: Either int row, or index, which is string or Tcl_Obj that can be cast to string
            col: Optional column - needed if index_or_row is an int
        """
        if isinstance(index_or_row, _tkinter.Tcl_Obj):
            index_or_row = str(index_or_row)
        if isinstance(index_or_row, str):
            assert col is None
            rr, cc = index_or_row.split(".", 1)
            self.row = int(rr)
            self.col = int(cc)
        else:
            assert isinstance(index_or_row, int) and isinstance(col, int)
            self.row = index_or_row
            self.col = col

    def index(self) -> str:
        """Return string index from object's row/col attributes."""
        return f"{self.row}.{self.col}"

    def rowcol(self) -> tuple[int, int]:
        """Return row, col tuple."""
        return self.row, self.col

    def __eq__(self, other: object) -> bool:
        """Override equality test to check row and col."""
        if not isinstance(other, IndexRowCol):
            return NotImplemented
        return (self.row, self.col) == (other.row, other.col)


class IndexRange:
    """Class to store/manipulate a Text range defined by two indexes.

    Attributes:
        start: Start index.
        end: End index.
    """

    def __init__(
        self,
        start: _tkinter.Tcl_Obj | str | IndexRowCol,
        end: _tkinter.Tcl_Obj | str | IndexRowCol,
    ) -> None:
        """Initialize IndexRange with two Tcl_Obj/strings or IndexRowCol objects.


        Args:
            start: Index of start of range - either string or IndexRowCol/Tcl_Obj
            end: Index of end of range - either string or IndexRowCol/Tcl_Obj
        """
        if isinstance(start, _tkinter.Tcl_Obj):
            start = str(start)
        if isinstance(end, _tkinter.Tcl_Obj):
            end = str(end)
        if isinstance(start, str):
            self.start = IndexRowCol(start)
        else:
            assert isinstance(start, IndexRowCol)
            self.start = start
        if isinstance(end, str):
            self.end = IndexRowCol(end)
        else:
            assert isinstance(start, IndexRowCol)
            self.end = end

    def __eq__(self, other: object) -> bool:
        """Override equality test to check start and end of range."""
        if not isinstance(other, IndexRange):
            return NotImplemented
        return (self.start, self.end) == (other.start, other.end)


def sing_plur(count: int, singular: str, plural: str = "") -> str:
    """Return singular/plural phrase depending on count.

    Args:
        count: Number of items.
        singular: Singular version of item name.
        plural: Plural version of item name (default - add `s` to singular).

    Examples:
        sing_plur(1, "word") -> "1 word"
        sing_plur(2, "error") -> "2 errors"
        sing_plur(3, "match", "matches") -> "3 matches"
    """
    if count == 1:
        word = singular
    elif plural == "":
        word = singular + "s"
    else:
        word = plural
    return f"{count} {word}"


# Store callback that sounds bell, and provide function to call it.
# This is necessary since the bell requires various Tk features/widgets,
# like root and the status bar. We don't want to have to import those
# into every module that wants to sound the bell, e.g. Search.
_bell_callback = None  # pylint: disable=invalid-name


def bell_set_callback(callback: Callable[[], None]) -> None:
    """Register a callback function that will sound the bell.

    Args:
        callback: Bell-sounding function."""
    global _bell_callback
    _bell_callback = callback


def sound_bell() -> None:
    """Call the registered bell callback in order to sound the bell."""
    assert _bell_callback is not None
    _bell_callback()


def process_label(label: str) -> tuple[int, str]:
    """Convert a button label string, e.g. "~Save...", where the optional
    tilde indicates the underline location for keyboard activation,
    to the tilde location (-1 if none), and the string without the tilde.

    Args:
        label: Label to appear on widget, e.g. button.

    Returns:
        Tuple containing location of tilde in label string (-1 if none),
            and string with tilde removed.
    """
    return (label.find("~"), label.replace("~", ""))


def process_accel(accel: str) -> tuple[str, str]:
    """Convert accelerator string, e.g. "Ctrl+X" to appropriate keyevent
    string for platform, e.g. "Control-X".

    "Cmd/Ctrl" means use ``Cmd`` key on Mac; ``Ctrl`` key on Windows/Linux.

    Args:
        accel: Accelerator string.

    Returns:
        Tuple containing accelerator string and key event string suitable
        for current platform.
    """
    if is_mac():
        accel = accel.replace("/Ctrl", "")
    else:
        accel = accel.replace("Cmd/", "")
    keyevent = accel.replace("Ctrl+", "Control-")
    keyevent = keyevent.replace("Shift+", "Shift-")
    keyevent = keyevent.replace("Cmd+", "Command-")
    if is_mac():
        keyevent = keyevent.replace("Alt+", "Option-")
    else:
        keyevent = keyevent.replace("Alt+", "Alt-")
    return (accel, f"<{keyevent}>")


def folder_dir_str(lowercase: bool = False) -> str:
    """Return "Folder" or "Directory" depending on platform.

    Args:
        lowercase: If True, return lowercase version.
    """
    fd_string = "Folder" if is_windows() else "Directory"
    return fd_string.lower() if lowercase else fd_string


def cmd_ctrl_string() -> str:
    """Return "Command" or "Control" depending on platform."""
    return "Command" if is_mac() else "Control"


def force_tcl_wholeword(string: str, regex: bool) -> tuple[str, bool]:
    """Change string to only match whole word(s) by converting to
    a regex (if not already), then prepending and appending Tcl-style
    word boundary flags.

    Args:
        string: String to be converted to a match wholeword regex.
        regex: True if string is already a regex.

    Returns:
        Tuple containing converted string and new regex flag value (always True)
    """
    if not regex:
        string = re.escape(string)
    return r"\y" + string + r"\y", True


def convert_to_tcl_regex(regex: str) -> str:
    """Convert regex to a Tcl-style regex.

    Currently, only converts backslash-b to backslash-y.
    Does not convert backslash-backslash-b.

    Args:
        regex: The regex to be converted

    Returns:
        Converted regex.
    """
    return re.sub(r"(?<!\\)\\b", r"\\y", regex)


class DiacriticRemover:
    """Supports removal of diacritics from strings."""

    outliers: Mapping
    source_outliers = "ä  æ  ǽ  đ ð ƒ ħ ı ł ø ǿ ö  œ  ß  ŧ ü  Ä  Æ  Ǽ  Đ Ð Ƒ Ħ I Ł Ø Ǿ Ö  Œ  ẞ  Ŧ Ü  Þ  þ"
    target_outliers = "ae ae ae d d f h i l o o oe oe ss t ue AE AE AE D D F H I L O O OE OE SS T UE TH th"

    @classmethod
    def setup_outliers(cls, source_outliers: str, target_outliers: str) -> None:
        """Setup the outliers mapping from source & target strings.

        Should be called with the relevant outliers when the language is changed."""
        DiacriticRemover.outliers = str.maketrans(
            dict(zip(source_outliers.split(), target_outliers.split()))
        )

    @classmethod
    def remove_diacritics(cls, string: str) -> str:
        """Remove accents, etc., from string.

        Based on https://stackoverflow.com/a/71408065
        First fixes a few outliers, like ǿ --> o, then uses Unicode Normalization
        to decompose string, then discards combining characters.
        """
        try:
            DiacriticRemover.outliers
        except AttributeError:
            DiacriticRemover.setup_outliers(
                DiacriticRemover.source_outliers, DiacriticRemover.target_outliers
            )
        return "".join(
            char
            for char in normalize("NFD", string.translate(DiacriticRemover.outliers))
            if not combining(char)
        )
