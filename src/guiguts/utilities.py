"""Handy utility functions"""

import json
import platform
import logging
import os.path
from typing import Any, Optional, Callable

logger = logging.getLogger(__package__)

# Flag so application code can detect if within a pytest run - only use if really needed
# See: https://pytest.org/en/7.4.x/example/simple.html#detect-if-running-from-within-a-pytest-run
_called_from_test = False


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
    except AttributeError:
        _is_system.system = platform.system()
        if _is_system.system not in ["Darwin", "Linux", "Windows"]:
            raise Exception("Unknown windowing system")
        return _is_system.system == system


def load_dict_from_json(filename: str) -> Optional[dict[str, Any]]:
    """If file exists, attempt to load into dict.

    Args:
        filename: Name of JSON file to load.

    Returns:
        Dictionary if loaded successfully, or None.
    """
    if os.path.isfile(filename):
        with open(filename, "r") as fp:
            try:
                return json.load(fp)
            except json.decoder.JSONDecodeError as exc:
                logger.error(
                    f"Unable to load {filename} -- not valid JSON format\n" + str(exc)
                )
    return None


class IndexRowCol:
    """Class to store/manipulate Tk Text indexes.

    Attributes:
        row: Row or line number.
        col: Column number.
    """

    row: int
    col: int

    def __init__(self, index_or_row: str | int, col: Optional[int] = None) -> None:
        """Construct index either from string or two ints.

        Args:
            index_or_row: String index, or int row
            col: Optional column - needed if index_or_row is an int
        """
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


class IndexRange:
    """Class to store/manipulate a Text range defined by two indexes.

    Attributes:
        start: Start index.
        end: End index.
    """

    def __init__(self, start: str | IndexRowCol, end: str | IndexRowCol) -> None:
        """Initialize IndexRange with two strings or IndexRowCol objects.


        Args:
            start: Index of start of range - either string or IndexRowCol
            end: Index of end of range - either string or IndexRowCol
        """
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


# Store callback that sounds bell, and provide function to call it.
# This is necessary since the bell requires various Tk features/widgets,
# like root and the status bar. We don't want to have to import those
# into every module that wants to sound the bell, e.g. Search.
_bell_callback = None


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
