"""Handy utility functions"""

import ctypes
import importlib.resources
import json
import platform
import logging
from pathlib import Path
import os.path
import subprocess
from tkinter import _tkinter  # type: ignore[attr-defined]
from typing import Any, Optional, Callable, Mapping
from unicodedata import combining, normalize

import regex as re

logger = logging.getLogger(__package__)

TraversablePath = importlib.resources.abc.Traversable | Path

# Flag so application code can detect if within a pytest run - only use if really needed
# See: https://pytest.org/en/7.4.x/example/simple.html#detect-if-running-from-within-a-pytest-run
CALLED_FROM_TEST = False

# Event keysym names as keys, display names as values
SUPPORTED_SHORTCUT_KEYS = {
    "F1": "F1",
    "F2": "F2",
    "F3": "F3",
    "F4": "F4",
    "F5": "F5",
    "F6": "F6",
    "F7": "F7",
    "F8": "F8",
    "F9": "F9",
    "F10": "F10",
    "F11": "F11",
    "F12": "F12",
    "Left": "Left",
    "Right": "Right",
    "Up": "Up",
    "Down": "Down",
    "Home": "Home",
    "End": "End",
    "Prior": "PgUp",
    "Next": "PgDn",
    "Insert": "Insert",
    "exclam": "!",
    "quotedbl": '"',
    "numbersign": "#",
    "dollar": "$",
    "percent": "%",
    "ampersand": "&",
    "quoteright": "'",
    "parenleft": "(",
    "parenright": ")",
    "asterisk": "*",
    "plus": "+",
    "comma": ",",
    "minus": "-",
    "period": ".",
    "slash": "/",
    "colon": ":",
    "semicolon": ";",
    "less": "<",
    "equal": "=",
    "greater": ">",
    "question": "?",
    "at": "@",
    "bracketleft": "[",
    "backslash": "\\",
    "bracketright": "]",
    "asciicircum": "^",
    "underscore": "_",
    "quoteleft": "`",
    "braceleft": "{",
    "bar": "|",
    "braceright": "}",
    "asciitilde": "~",
    "sterling": "£",
    "notsign": "¬",
    "grave": "`",
    "apostrophe": "'",
    "plusminus": "±",
    "section": "§",
}


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


def _is_system(system: str) -> bool:
    """Return true if running on given system

    Args:
        system: Name of system to check against
    """
    my_system = platform.system()
    assert my_system in ("Darwin", "Linux", "Windows")
    return my_system == system


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
            assert isinstance(end, IndexRowCol)
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
_BELL_CALLBACK = None


def bell_set_callback(callback: Callable[[], None]) -> None:
    """Register a callback function that will sound the bell.

    Args:
        callback: Bell-sounding function."""
    global _BELL_CALLBACK
    _BELL_CALLBACK = callback


def sound_bell() -> None:
    """Call the registered bell callback in order to sound the bell."""
    assert _BELL_CALLBACK is not None
    _BELL_CALLBACK()


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
    if is_mac():
        keyevent = keyevent.replace("Cmd+", "Command-")
        keyevent = keyevent.replace("Option+", "Option-")
        keyevent = keyevent.replace("Alt+", "Option-")
    else:
        keyevent = keyevent.replace("Alt+", "Alt-")
    accel = accel.replace("Key-", "")
    # More friendly names for display
    for key, display in SUPPORTED_SHORTCUT_KEYS.items():
        accel = accel.replace(key, display)
    return (accel, f"<{keyevent}>")


def folder_dir_str(lowercase: bool = False) -> str:
    """Return "Folder" or "Directory" depending on platform.

    Args:
        lowercase: If True, return lowercase version.
    """
    fd_string = "Directory" if is_x11() else "Folder"
    return fd_string.lower() if lowercase else fd_string


def cmd_ctrl_string() -> str:
    """Return "Command" or "Control" depending on platform."""
    return "Command" if is_mac() else "Control"


def get_keyboard_layout() -> int:
    """Return keyboard layout: 1 for UK, 0 for all others."""
    layout = "00000409"  # Default to US
    if is_windows():
        buf = ctypes.create_unicode_buffer(9)
        ctypes.windll.user32.GetKeyboardLayoutNameW(buf)  # type: ignore[attr-defined]
        layout = buf.value  # e.g. "00000409" for US or "00000809" for UK
    elif is_mac():
        try:
            result = subprocess.run(
                [
                    "defaults",
                    "read",
                    "~/Library/Preferences/com.apple.HIToolbox.plist",
                    "AppleSelectedInputSources",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in result.stdout.splitlines():
                if "KeyboardLayout Name" in line:
                    # May begin with "British" or "U.S." or "US"
                    layout = re.sub(r'.*"([^"]+)";$', r"\1", line)
                    break
        except subprocess.SubprocessError:
            pass
    else:
        try:
            result = subprocess.run(
                ["setxkbmap", "-query"], capture_output=True, text=True, check=False
            )
            for line in result.stdout.splitlines():
                if line.startswith("layout:"):
                    layout = line.split()[1]  # e.g. "us" or "gb"
                    break
        except subprocess.SubprocessError:
            pass
    return 1 if layout.startswith(("00000809", "gb", "British")) else 0


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


class TextWrapper:
    """Provides Knuth-Plass rewrapping functionality.

    Can be replaced with Python's textwrap/TextWrapper if "greedy" wrapping is preferred:
        ``from textwrap import TextWrapper``

        ``wrapper = TextWrapper(break_long_words=False, break_on_hyphens=False)``
    """

    def __init__(self) -> None:
        """Initialize rewrap parameters."""

        # The four attributes below match the Perl version's four
        # options. However the Python version is normally passed
        # just three of them, namely:
        #
        #    width
        #    first_indent
        #    subsequent_indent
        #
        # The Python version will calculate a default value for
        # 'optimum_width' (see 'def fill' below) unless the caller
        # sets a value for this attribute.
        #
        # Only consider setting a value for 'optimum_width' if you
        # want to explore different optimal rewrappings. Using the
        # default value means that Knuth-Plass wrapping behaviour
        # is indentical in GG1 & GG2.

        self.width = 72
        self.optimum_width = -1
        self.initial_indent = ""
        self.subsequent_indent = ""

    def fill(self, paragraph: str) -> str:
        """Python implementation of ReflowGG.pm (Knuth-Plass)."""

        ####
        # The following are declared and accessed as 'nonlocal' variables
        # by functions defined within the enclosing scope of this top-most
        # function definition. The names must exist when first encountered
        # as they cannot be created by a first assignment in a nested def.
        ####

        # Maximum possible line length. Caller sets this to the current
        # 'rightmargin' value.
        maximum = self.width
        # Not normally passed by the caller so set default as per Perl
        # version, namely 'width - rmargindiff'. The latter is normally
        # '1'. Deal with situation when 'optimum_width' is set by the
        # caller to change the default value.
        if self.optimum_width == -1:
            # Caller hasn't changed it so set default value for optimum.
            optimum = [self.width - 1]
        else:
            # Use value set by caller for optimum.
            optimum = [self.optimum_width]
        # Indentation for first line.
        indent1 = self.initial_indent
        # Indentation for each line after the first.
        indent2 = self.subsequent_indent

        # Used by reflow_trial() in its calculation of the best breaks
        # in lines to produce the optimal rewrapping.
        penaltylimit = 0x2000000
        # Will hold the newline-terminated lines that are split from
        # the passed in paragraph text. This is the source of the
        # lines to be rewrapped by the Knuth algorithm.
        from_lines = []
        # Will hold the trimmed and newline-terminated lines that are
        # the result of the Knuth rewrapping.
        to_lines = []
        # Used by reflow_trial() to pick the break for the last line
        # which gives the least penalties for previous lines.
        lastbreak = 0
        # Is the list of breaks determined by reflow_trial. Will be used
        # by print_output() to construct the each of the rewrapped lines.
        linkbreak = []
        # The list of words from the passed in paragraph that are used
        # in the calculations by the Knuth algorithm to build rewrapped
        # lines with optimal breaks.
        words: list[str] = []
        # The count of words in the above list.
        wordcount = 0
        # Length of each word (excluding spaces) in the above list.
        word_len: list[int] = []
        # Length of the space after each word in word_len.
        space_len: list[int] = []
        # Used as an interim buffer of rewrapped lines that are edited
        # (e.g. to reinsert spaces in ellipses, etc.) before being
        # written to 'to_lines'.
        output: list[str] = []

        # NB The variables above are declared in this enclosing function's
        #    scope so that they exist when encountered as Python 'nonlocal'
        #    variables within the nested functions that follow.

        def reflow_trial() -> int:
            """Finds the optimal Knuth-Plass wrapping for a text
            within given margins and suggested optimum width.
            """

            nonlocal linkbreak

            totalpenalty = [0] * wordcount
            best = penaltylimit * 21
            best_lastbreak = 0
            for opt in optimum:
                my_linkbreak = [0] * wordcount
                j = 0
                # Optimize preceding break
                while j < wordcount:
                    interval = 0
                    totalpenalty[j] = penaltylimit * 2
                    k = j
                    while k >= 0:
                        interval += word_len[k]
                        if k < j and ((interval > opt + 10) or (interval >= maximum)):
                            break
                        penalty = (interval - opt) * (interval - opt)
                        interval += space_len[k]
                        if k > 0:
                            penalty += totalpenalty[k - 1]
                        if penalty < totalpenalty[j]:
                            totalpenalty[j] = penalty
                            my_linkbreak[j] = k - 1
                        k -= 1
                    j += 1
                interval = 0
                bestsofar = penaltylimit * 20
                lastbreak = wordcount - 2
                # Pick a break for the last line which gives the least
                # penalties for previous lines.
                k = wordcount - 2
                while k >= -1:
                    interval += word_len[k + 1]
                    if (interval > opt + 10) or (interval > maximum):
                        break
                    # Don't make last line too long.
                    if interval > opt:
                        penalty = (interval - opt) * (interval - opt)
                    else:
                        penalty = 0
                    interval += space_len[k + 1]
                    if k >= 0:
                        penalty += totalpenalty[k]
                    if penalty <= bestsofar:
                        bestsofar = penalty
                        lastbreak = k
                    k -= 1
                # Save these breaks if they are an improvement.
                if bestsofar < best:
                    best_lastbreak = lastbreak
                    linkbreak = my_linkbreak.copy()
                    best = bestsofar
                # Next opt
            return best_lastbreak

        def paragraph_to_lines(paragraph: str) -> None:
            """Split paragraph string into lines, keeping trailing empty lines.
            The split is on newlines and then they are restored, being careful
            not to add an extra newline at the end.

            Args:
                paragraph: String to be rewrapped. Usually one or more lines
                           each terminated with a newline.
            """

            nonlocal from_lines

            lines = paragraph.split("\n")
            # Remove any additional newline at the end.
            if len(lines) > 0 and lines[-1] == "":
                lines.pop()
            # Restore the terminating newlines.
            lines_with_newlines = map(lambda s: f"{s}\n", lines)
            # Create a global list of lines.
            from_lines = list(lines_with_newlines)

        def get_line() -> str:
            """Returns the next element of global array 'from_lines'. Assumes
            that no element in that list is zero length.
            """

            if len(from_lines) > 0:
                tmp = from_lines[0]
                del from_lines[0]
            else:
                tmp = ""
            return tmp

        def print_lines(lines: list[str]) -> None:
            """Trim EOL spaces and store the lines in the output buffer."""

            for line in lines:
                to_lines.append(re.sub(r"[ \t]+\n", r"\n", line))

        def reflow_penalties() -> None:
            """Initialise global word- and space-length lists"""

            nonlocal wordcount, word_len, space_len

            wordcount = len(words)
            # Add paragraph indentation to first word if there is one.
            if wordcount > 0:
                words[0] = f"{indent1}{words[0]}"
            word_len = [0] * wordcount  # Length of each word (excluding spaces).
            space_len = [0] * wordcount  # Length of the space after after this word.
            for j in range(wordcount):
                if re.findall(r" $", words[j]):
                    word_len[j] = len(words[j]) - 1
                    space_len[j] = 2
                else:
                    word_len[j] = len(words[j])
                    space_len[j] = 1
            # First word already has 'indent1' added and will not be indented further.
            if wordcount > 0:
                word_len[0] -= len(indent2)

        def compute_output() -> None:
            """Compute global 'output' list from 'wordcount', 'words' list,
            lastbreak and linkbreak"""

            nonlocal output, lastbreak

            output = []
            terminus = wordcount - 1
            while terminus >= 0:
                # NB The lower bound is inclusive, the upper bound is noninclusive.
                my_str = " ".join(words[lastbreak + 1 : terminus + 1]) + "\n"
                output.append(my_str)
                terminus = lastbreak
                lastbreak = linkbreak[lastbreak]
            output.reverse()
            # Add the indent to all but the first line.
            mapped = map(lambda s: f"{indent2}{s}", output[1 : len(output)])
            output = [output[0]]
            for m in mapped:
                output.append(m)

        def reflow_para() -> None:
            """Rewrap pragraph"""

            nonlocal words
            nonlocal lastbreak, output

            if len(words) == 0:
                return
            reflow_penalties()
            lastbreak = 0
            lastbreak = reflow_trial()
            compute_output()
            # Restore spaces in ellipses
            tmp = []
            for line in output:
                tmp.append(re.sub(r"\x9f", " ", line))
            output = tmp.copy()
            print_lines(output)
            words = []

        def process(line: str) -> None:
            """Process a line by appending each word to global 'words' list.
            If the line is blank, reflow the paragraph of words in 'words'.
            """

            # Protect " . . ." ellipses by replacing space with unused byte \x9f.
            line = re.sub(r" \. \. \.", r"\x9f.\x9f.\x9f.", line)
            line = re.sub(r"\. \. \.", r".\x9f.\x9f.", line)
            # Splitting assumes a single space between words in 'line'
            line = re.sub(r"\s+", " ", line)
            # Remove any extra space at end of line.
            line = re.sub(r"\s$", "", line)
            linewords = line.split(" ")
            if len(linewords) != 0 and linewords[0] == "":
                del linewords[0]
            # If no words on this line then end of paragraph.
            if len(linewords) == 0:
                # No words on this line so end of paragraph.
                reflow_para()
                # Function expects a list of strings, each terminated with \n.
                print_lines([f"{indent1}\n"])
            else:
                # Add contents of global 'linewords' list to global 'words' list.
                for word in linewords:
                    words.append(word)

        ####
        # Executable section of enclosing function 'fill'.
        ####

        # Empty paragraphs don't need wrapping
        if paragraph == "":
            return ""

        # Split the passed in paragraph into lines and add them
        # to the global list 'from_lines'.
        paragraph_to_lines(paragraph)

        # Adjust global variables 'optimum' and 'maximum' by
        # 'indent2' length.
        if indent2 != "":
            maximum = maximum - len(indent2)
            mapped = map(lambda s: s - len(indent2), optimum)
            optimum = list(mapped)

        # Do the rewrapping.
        while line := get_line():
            process(line)
        # Reflow any remaining words in 'words' list.
        reflow_para()
        rewrapped_para = ""
        for line in to_lines:
            rewrapped_para = "".join((rewrapped_para, line))
        # If input paragraph did not have a terminating newline, output shouldn't
        if paragraph[-1] != "\n":
            rewrapped_para = rewrapped_para.rstrip("\n")
        return rewrapped_para


def non_text_line(line: str) -> bool:
    """Return True if line is not part of text, due to being a page separator or
    ppgen command or ppgen comment."""
    return bool(re.match(r"-----File:|\.[\p{Letter}\p{Number}]{2} |//", line))


def is_debug() -> bool:
    """Return whether in debug mode, specifically if error logging level is debug."""
    return logger.getEffectiveLevel() == logging.DEBUG
