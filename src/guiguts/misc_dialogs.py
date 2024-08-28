"""Miscellaneous dialogs."""

import tkinter as tk
from tkinter import ttk, font
from typing import Any
import unicodedata

import regex as re

from guiguts.maintext import maintext
from guiguts.preferences import (
    PrefKey,
    PersistentBoolean,
    PersistentInt,
    PersistentString,
    preferences,
)
from guiguts.utilities import is_mac, is_windows, is_x11
from guiguts.widgets import (
    ToplevelDialog,
    ToolTip,
    insert_in_focus_widget,
    OkApplyCancelDialog,
    mouse_bind,
    Combobox,
)

COMBO_SEPARATOR = "―" * 20


class PreferencesDialog(ToplevelDialog):
    """A dialog that displays settings/preferences."""

    def __init__(self) -> None:
        """Initialize preferences dialog."""
        super().__init__("Settings", resize_y=False)
        self.minsize(250, 10)

        # Appearance
        appearance_frame = ttk.LabelFrame(self.top_frame, text="Appearance", padding=10)
        appearance_frame.grid(column=0, row=0, sticky="NSEW")
        theme_frame = ttk.Frame(appearance_frame)
        theme_frame.grid(column=0, row=0, sticky="NSEW")
        theme_frame.columnconfigure(1, weight=1)
        ttk.Label(theme_frame, text="Theme: ").grid(column=0, row=0, sticky="NE")
        cb = ttk.Combobox(
            theme_frame, textvariable=PersistentString(PrefKey.THEME_NAME)
        )
        cb.grid(column=1, row=0, sticky="NEW")
        cb["values"] = ["Default", "Dark", "Light"]
        cb["state"] = "readonly"
        ttk.Label(
            appearance_frame, text="(May need to restart program for full effect)"
        ).grid(column=0, row=1, sticky="NSEW")
        tearoff_check = ttk.Checkbutton(
            appearance_frame,
            text="Use Tear-Off Menus (requires restart)",
            variable=PersistentBoolean(PrefKey.TEAROFF_MENUS),
        )
        tearoff_check.grid(column=0, row=2, sticky="NEW", pady=5)
        if is_mac():
            tearoff_check["state"] = tk.DISABLED
            ToolTip(tearoff_check, "Not available on macOS")

        # Font
        def is_valid_font(new_value: str) -> bool:
            """Validation routine for Combobox - if separator has been selected,
            select Courier New instead.

            Args:
                new_value: New font family selected by user.

            Returns:
                True, because if invalid, it is fixed in this routine.
            """
            if new_value == COMBO_SEPARATOR:
                preferences.set(PrefKey.TEXT_FONT_FAMILY, "Courier")
                preferences.set(PrefKey.TEXT_FONT_FAMILY, "Courier New")
            return True

        font_frame = ttk.Frame(appearance_frame)
        font_frame.grid(column=0, row=3, sticky="NEW", pady=(5, 0))
        ttk.Label(font_frame, text="Font: ").grid(column=0, row=0, sticky="NEW")
        font_list = sorted(font.families(), key=str.lower)
        font_list.insert(0, COMBO_SEPARATOR)
        for preferred_font in "Courier New", "DejaVu Sans Mono", "DP Sans Mono":
            if preferred_font in font_list:
                font_list.insert(0, preferred_font)
            elif preferred_font == "Courier New" and "Courier" in font_list:
                font_list.insert(0, "Courier")
        cb = ttk.Combobox(
            font_frame,
            textvariable=PersistentString(PrefKey.TEXT_FONT_FAMILY),
            width=30,
            validate="all",
            validatecommand=(self.register(is_valid_font), "%P"),
            values=font_list,
            state="readonly",
        )
        cb.grid(column=1, row=0, sticky="NEW")

        spinbox = ttk.Spinbox(
            font_frame,
            textvariable=PersistentInt(PrefKey.TEXT_FONT_SIZE),
            from_=1,
            to=99,
            width=5,
        )
        spinbox.grid(column=2, row=0, sticky="NEW", padx=2)
        ToolTip(spinbox, "Font size")

        ttk.Checkbutton(
            appearance_frame,
            text="Display Line Numbers",
            variable=PersistentBoolean(PrefKey.LINE_NUMBERS),
        ).grid(column=0, row=4, sticky="NEW", pady=5)
        ttk.Checkbutton(
            appearance_frame,
            text="Automatically show current page image",
            variable=PersistentBoolean(PrefKey.AUTO_IMAGE),
        ).grid(column=0, row=5, sticky="NEW", pady=5)
        bell_frame = ttk.Frame(appearance_frame)
        bell_frame.grid(column=0, row=6, sticky="NEW", pady=(5, 0))
        ttk.Label(bell_frame, text="Warning bell: ").grid(column=0, row=0, sticky="NEW")
        ttk.Checkbutton(
            bell_frame,
            text="Audible",
            variable=PersistentBoolean(PrefKey.BELL_AUDIBLE),
        ).grid(column=1, row=0, sticky="NEW", padx=20)
        ttk.Checkbutton(
            bell_frame,
            text="Visual",
            variable=PersistentBoolean(PrefKey.BELL_VISUAL),
        ).grid(column=2, row=0, sticky="NEW")

        # Wrapping tab
        wrapping_frame = ttk.LabelFrame(self.top_frame, text="Wrapping", padding=10)
        wrapping_frame.grid(column=0, row=1, sticky="NSEW", pady=(10, 0))

        def add_label_spinbox(row: int, label: str, key: PrefKey, tooltip: str) -> None:
            """Add a label and spinbox to the wrapping frame.
            Args:
                label: Text for label.
                key: Prefs key to use to store preference.
                tooltip: Text for tooltip.
            """
            ttk.Label(wrapping_frame, text=label).grid(
                column=0, row=row, sticky="NE", pady=2
            )
            spinbox = ttk.Spinbox(
                wrapping_frame,
                textvariable=PersistentInt(key),
                from_=0,
                to=999,
                width=5,
            )
            spinbox.grid(column=1, row=row, sticky="NW", padx=5, pady=2)
            ToolTip(spinbox, tooltip)

        add_label_spinbox(
            0, "Left Margin:", PrefKey.WRAP_LEFT_MARGIN, "Left margin for normal text"
        )
        add_label_spinbox(
            1,
            "Right Margin:",
            PrefKey.WRAP_RIGHT_MARGIN,
            "Right margin for normal text",
        )
        add_label_spinbox(
            2,
            "Blockquote Indent:",
            PrefKey.WRAP_BLOCKQUOTE_INDENT,
            "Extra indent for each level of blockquotes",
        )
        add_label_spinbox(
            3,
            "Blockquote Right Margin:",
            PrefKey.WRAP_BLOCKQUOTE_RIGHT_MARGIN,
            "Right margin for blockquotes",
        )
        add_label_spinbox(
            4,
            "Block Indent:",
            PrefKey.WRAP_BLOCK_INDENT,
            "Indent for /*, /P, /L blocks",
        )
        add_label_spinbox(
            5,
            "Poetry Indent:",
            PrefKey.WRAP_POETRY_INDENT,
            "Indent for /P poetry blocks",
        )
        add_label_spinbox(
            6,
            "Index Main Entry Margin:",
            PrefKey.WRAP_INDEX_MAIN_MARGIN,
            "Indent for main entries in index - sub-entries retain their indent relative to this",
        )
        add_label_spinbox(
            8,
            "Index Wrap Margin:",
            PrefKey.WRAP_INDEX_WRAP_MARGIN,
            "Left margin for all lines rewrapped in index",
        )
        add_label_spinbox(
            9,
            "Index Right Margin:",
            PrefKey.WRAP_INDEX_RIGHT_MARGIN,
            "Right margin for index entries",
        )


_compose_dict: dict[str, str] = {}


class ComposeSequenceDialog(OkApplyCancelDialog):
    """Dialog to enter Compose Sequences.

    Attributes:
        dict: Dictionary mapping sequence of keystrokes to character.
    """

    def __init__(self) -> None:
        """Initialize compose sequence dialog."""
        super().__init__("Compose Sequence", resize_x=False, resize_y=False)
        ttk.Label(self.top_frame, text="Compose: ").grid(column=0, row=0, sticky="NSEW")
        self.string = tk.StringVar()
        self.entry = Combobox(
            self.top_frame, PrefKey.COMPOSE_HISTORY, textvariable=self.string
        )
        # self.entry = ttk.Entry(self.top_frame, textvariable=self.string, name="entry1")
        self.entry.grid(column=1, row=0, sticky="NSEW")
        # In tkinter, binding order is widget, class, toplevel, all
        # Swap first two, so that class binding has time to set textvariable
        # before the widget binding below is executed.
        bindings = self.entry.bindtags()
        self.entry.bindtags((bindings[1], bindings[0], bindings[2], bindings[3]))
        self.entry.bind("<Key>", lambda _event: self.interpret_and_insert())
        self.entry.focus()
        init_compose_dict()

    def apply_changes(self) -> bool:
        """Overridden function called when Apply/OK buttons are pressed.

        Call to attempt to interpret compose sequence

        Returns:
            Always returns True, meaning OK button (or Return key) will close dialog.
        """
        self.interpret_and_insert(force=True)
        self.entry.select_range(0, tk.END)
        return True

    def interpret_and_insert(self, force: bool = False) -> None:
        """Interpret string from Entry field as a compose sequence and insert it.

        If compose sequence is complete, then the composed character will be
        inserted in the most recently focused text/entry widget and the Compose
        dialog will be closed. If sequence is not complete, then nothing will be done,
        unless `force` is True.

        Args:
            force: True if string should be interpreted/inserted as-is,
                rather than waiting for further input.
        """
        sequence = self.string.get()
        char = ""
        # First check if sequence is in dictionary
        if sequence in _compose_dict:
            char = _compose_dict[sequence]
        elif match := re.fullmatch(r"[0-9a-f]{4}", sequence, re.IGNORECASE):
            # Exactly 4 hex digits translates to a single Unicode character
            char = chr(int(sequence, 16))
        elif force:
            if match := re.fullmatch(
                r"(0x|\\x|x|U\+?)?([0-9a-fA-F]{2,})", sequence, re.IGNORECASE
            ):
                # Or user can force interpretation as hex with fewer than 4 digits,
                # or with more than 4 by using a prefix: 0x, \x, x, U or U+
                char = chr(int(match[2], 16))
            elif match := re.fullmatch(r"#(\d{2,})", sequence):
                # Or specify in decimal following '#' character
                char = chr(int(match[1]))
        insert_in_focus_widget(char)
        self.entry.add_to_history(self.string.get())
        if not force:
            self.destroy()


def init_compose_dict() -> None:
    """Initialize dictionary of compose sequences."""
    if _compose_dict:
        return  # Already initialized
    init_char_reversible("‘", "'<")
    init_char_reversible("’", "'>")
    init_char_reversible("“", '"<')
    init_char_reversible("”", '">')
    init_chars("±", "+-")
    init_chars("·", "^.", "*.", ".*")
    init_chars("×", "*x", "x*")
    init_chars("÷", ":-")
    init_char_reversible("°", "oo", "*o")
    init_char_reversible("′", "1'")
    init_char_reversible("″", "2'")
    init_char_reversible("‴", "3'")
    init_char_reversible(" ", "  ", "* ")
    init_chars("—", "--")
    init_char_reversible("–", "- ")
    init_chars("⁂", "**")
    init_char_reversible("º", "o_")
    init_char_reversible("ª", "a_")
    init_chars("‖", "||")
    init_chars("¡", "!!")
    init_chars("¿", "??")
    init_chars("«", "<<")
    init_chars("»", ">>")
    init_char_case("Æ", "AE")
    init_char_case("Œ", "OE")
    init_char_case("ẞ", "SS")
    init_char_case("Ð", "DH", "ETH")
    init_char_case("Þ", "TH")
    init_chars("©", "(c)", "(C)")
    init_chars("†", "dag", "DAG")
    init_chars("‡", "ddag", "DDAG")
    init_accent("£", "L", "-")
    init_accent("¢", "C", "/", "|")
    init_chars("§", "sec", "s*", "*s", "SEC", "S*", "*S")
    init_chars("¶", "pil", "p*", "*p", "PIL", "P*", "*P")
    init_chars("ſ", "sf", "SF")
    init_chars("‚", ",'")
    init_chars("‛", "^'")
    init_chars("„", ',"')
    init_chars("‟", '^"')
    init_chars("½", "1/2")
    init_chars("⅓", "1/3")
    init_chars("⅔", "2/3")
    init_chars("¼", "1/4")
    init_chars("¾", "3/4")
    init_chars("⅕", "1/5")
    init_chars("⅖", "2/5")
    init_chars("⅗", "3/5")
    init_chars("⅘", "4/5")
    init_chars("⅙", "1/6")
    init_chars("⅚", "5/6")
    init_chars("⅐", "1/7")
    init_chars("⅛", "1/8")
    init_chars("⅜", "3/8")
    init_chars("⅝", "5/8")
    init_chars("⅞", "7/8")
    init_chars("⅑", "1/9")
    init_chars("⅒", "1/10")
    for num, char in enumerate("⁰¹²³⁴⁵⁶⁷⁸⁹"):
        init_chars(char, f"^{num}")
    for num, char in enumerate("₀₁₂₃₄₅₆₇₈₉"):
        init_chars(char, f",{num}")

    # Accented characters
    init_accent("À", "A", "`", "\\")
    init_accent("Á", "A", "'", "/")
    init_accent("Â", "A", "^")
    init_accent("Ã", "A", "~")
    init_accent("Ä", "A", '"', ":")
    init_accent("Å", "A", "o", "*")
    init_accent("Ā", "A", "-", "=")
    init_accent("È", "E", "`", "\\")
    init_accent("É", "E", "'", "/")
    init_accent("Ê", "E", "^")
    init_accent("Ë", "E", '"', ":")
    init_accent("Ē", "E", "-", "=")
    init_accent("Ì", "I", "`", "\\")
    init_accent("Í", "I", "'", "/")
    init_accent("Î", "I", "^")
    init_accent("Ï", "I", '"', ":")
    init_accent("Ī", "I", "-", "=")
    init_accent("Ò", "O", "`", "\\")
    init_accent("Ó", "O", "'")
    init_accent("Ô", "O", "^")
    init_accent("Õ", "O", "~")
    init_accent("Ö", "O", '"', ":")
    init_accent("Ø", "O", "/")
    init_accent("Ō", "O", "-", "=")
    init_accent("Ù", "U", "`", "\\")
    init_accent("Ú", "U", "'", "/")
    init_accent("Û", "U", "^")
    init_accent("Ü", "U", '"', ":")
    init_accent("Ū", "U", "-", "=")
    init_accent("Ç", "C", ",")
    init_accent("Ñ", "N", "~")
    init_accent("Ÿ", "Y", '"', ":")
    init_accent("Ý", "Y", "'", "/")

    # Combining characters
    init_combining("\u0300", "\u0316", "\\", "`")  # grave
    init_combining("\u0301", "\u0317", "/", "'")  # acute
    init_combining("\u0302", "\u032D", "^")  # circumflex
    init_combining("\u0303", "\u0330", "~")  # tilde
    init_combining("\u0304", "\u0331", "-", "=")  # macron
    init_combining("\u0306", "\u032E", ")")  # breve
    init_combining("\u0311", "\u032F", "(")  # inverted breve
    init_combining("\u0307", "\u0323", ".")  # dot
    init_combining("\u0308", "\u0324", ":", '"')  # diaresis
    init_combining("\u0309", "", "?")  # hook above
    init_combining("\u030A", "\u0325", "*")  # ring
    init_combining("\u030C", "\u032C", "v")  # caron
    init_combining("", "\u0327", ",")  # cedilla
    init_combining("", "\u0328", ";")  # ogonek

    # Greek characters
    init_greek_alphabet()
    init_greek_accent("Ὰ", "A", "ᾼ")
    init_greek_accent("Ὲ", "E")
    init_greek_accent("Ὴ", "H", "ῌ")
    init_greek_accent("Ὶ", "I")
    init_greek_accent("Ὸ", "O")
    init_greek_accent("Ὺ", "U")
    init_greek_accent("Ὼ", "W", "ῼ")
    init_greek_breathing("Ἀ", "A", "ᾈ")
    init_greek_breathing("Ἐ", "E")
    init_greek_breathing("Ἠ", "H", "ᾘ")
    init_greek_breathing("Ἰ", "I")
    init_greek_breathing("Ὀ", "O")
    init_greek_breathing("὘", "U")
    init_greek_breathing("Ὠ", "W", "ᾨ")


def init_accent(char: str, base: str, *accents: str) -> None:
    """Add entries to the dictionary for upper & lower case versions
    of the given char, using each of the accents.

    Args:
        char: Upper case version of character to be added.
        base: Upper case base English character to be accented.
        *accents: Characters that can be used to add the accent.
    """
    for accent in accents:
        init_char_case(char, base + accent)
        init_char_case(char, accent + base)


def init_chars(char: str, *sequences: str) -> None:
    """Add entries to the dictionary for the given char.

    Args:
        char: Character to be added.
        *sequences: Sequences of keys to generate the character.
    """
    for sequence in sequences:
        _compose_dict[sequence] = char


def init_char_reversible(char: str, *sequences: str) -> None:
    """Add entries to the dictionary for the given char with
    2 reversible characters per sequence.

    Args:
        char: Character to be added.
        *sequences: Sequences of reversible keys to generate the character.
    """
    for sequence in sequences:
        _compose_dict[sequence] = char
        _compose_dict[sequence[::-1]] = char


def init_char_case(char: str, *sequences: str) -> None:
    """Add upper & lower case entries to the dictionary for the given char & sequence.

    Args:
        char: Character to be added.
        *sequences: Sequences of keys to generate the character.
    """
    lchar = char.lower()
    for sequence in sequences:
        lsequence = sequence.lower()
        _compose_dict[sequence] = char
        _compose_dict[lsequence] = lchar


def init_combining(above: str, below: str, *accents: str) -> None:
    """Add entries to the dictionary for combining characters.

    Args:
        above: Combining character above (empty if none to be added).
        base: Combining character below (empty if none to be added).
        *accents: Characters that follow `+` and `_` to create the combining characters.
    """
    for accent in accents:
        if above:
            _compose_dict["+" + accent] = above
        if below:
            _compose_dict["_" + accent] = below


def init_greek_alphabet() -> None:
    """Add entries to the dictionary for non-accented Greek alphabet letters.

    Greek letter sequences are prefixed with `=` sign.
    """
    ualpha = ord("Α")
    lalpha = ord("α")
    for offset, base in enumerate("ABGDEZHQIKLMNXOPRJSTUFCYW"):
        _compose_dict["=" + base] = chr(ualpha + offset)
        _compose_dict["=" + base.lower()] = chr(lalpha + offset)


def init_greek_accent(char: str, base: str, uiota: str = "") -> None:
    """Add varia & oxia accented Greek letters to dictionary.

    Greek letter sequences are prefixed with `=` sign.

    Args:
        char: Upper case version of character with varia to be added.
            Next ordinal gives the character with oxia.
        base: Upper case base English character to be accented.
        uiota: Optional upper case version of character with iota subscript.
            Prev & next ordinals give same with accents for lower case only.
            Note there is no upper case with accent and iota, and not all
            vowels have an iota version.
    """
    _compose_dict["=\\" + base] = _compose_dict["=`" + base] = char
    _compose_dict["=/" + base] = _compose_dict["='" + base] = chr(ord(char) + 1)
    lbase = base.lower()
    lchar = char.lower()
    _compose_dict["=\\" + lbase] = _compose_dict["=`" + lbase] = lchar
    _compose_dict["=/" + lbase] = _compose_dict["='" + lbase] = chr(ord(lchar) + 1)
    if not uiota:
        return
    _compose_dict["=|" + base] = uiota
    liota = uiota.lower()
    _compose_dict["=|" + lbase] = liota
    _compose_dict["=\\|" + lbase] = _compose_dict["=`|" + lbase] = chr(ord(liota) - 1)
    _compose_dict["=/|" + lbase] = _compose_dict["='|" + lbase] = chr(ord(liota) + 1)


def init_greek_breathing(char: str, base: str, uiota: str = "") -> None:
    """Add accented Greek letters including breathing to dictionary.

    Greek letter sequences are prefixed with `=` sign.

    Args:
        char: Upper case char in middle group of 16, e.g. alpha with various accents.
        base: Upper case base English character to be accented.
        iota: Optional upper case verison with iota subscript if needed.
    """
    lbase = base.lower()
    ord_list = (ord(char), ord(uiota)) if uiota else (ord(char),)
    for char_ord in ord_list:
        _compose_dict["=)" + base] = chr(char_ord)
        _compose_dict["=(" + base] = chr(char_ord + 1)
        _compose_dict["=(`" + base] = _compose_dict["=(\\" + base] = chr(char_ord + 2)
        _compose_dict["=)`" + base] = _compose_dict["=)\\" + base] = chr(char_ord + 3)
        _compose_dict["=('" + base] = _compose_dict["=(/" + base] = chr(char_ord + 4)
        _compose_dict["=)'" + base] = _compose_dict["=)/" + base] = chr(char_ord + 5)
        _compose_dict["=(^" + base] = _compose_dict["=(~" + base] = chr(char_ord + 6)
        _compose_dict["=)^" + base] = _compose_dict["=)~" + base] = chr(char_ord + 7)
        _compose_dict["=)" + lbase] = chr(char_ord - 8)
        _compose_dict["=(" + lbase] = chr(char_ord - 7)
        _compose_dict["=(`" + lbase] = _compose_dict["=(\\" + lbase] = chr(char_ord - 6)
        _compose_dict["=)`" + lbase] = _compose_dict["=)\\" + lbase] = chr(char_ord - 5)
        _compose_dict["=('" + lbase] = _compose_dict["=(/" + lbase] = chr(char_ord - 4)
        _compose_dict["=)'" + lbase] = _compose_dict["=)/" + lbase] = chr(char_ord - 3)
        _compose_dict["=(^" + lbase] = _compose_dict["=(~" + lbase] = chr(char_ord - 2)
        _compose_dict["=)^" + lbase] = _compose_dict["=)~" + base] = chr(char_ord - 1)
        # Add iota sequence character in case going round loop a second time
        base = "|" + base
        lbase = "|" + lbase


class ComposeHelpDialog(ToplevelDialog):
    """A dialog to show the compose sequences."""

    def __init__(self) -> None:
        """Initialize class members from page details."""
        super().__init__("List of Compose Sequences")

        self.column_headings = ("Character", "Sequence", "Name")
        widths = (70, 70, 600)
        self.help = ttk.Treeview(
            self.top_frame,
            columns=self.column_headings,
            show="headings",
            height=10,
            selectmode=tk.NONE,
        )
        ToolTip(
            self.help,
            "Click to insert character",
            use_pointer_pos=True,
        )
        for col, column in enumerate(self.column_headings):
            self.help.column(
                f"#{col + 1}",
                minwidth=10,
                width=widths[col],
                stretch=False,
                anchor=tk.W,
            )
            self.help.heading(
                f"#{col + 1}",
                text=column,
                anchor=tk.W,
            )
        self.help.grid(row=0, column=0, sticky=tk.NSEW)

        self.scrollbar = ttk.Scrollbar(
            self.top_frame, orient=tk.VERTICAL, command=self.help.yview
        )
        self.help.configure(yscroll=self.scrollbar.set)  # type: ignore[call-overload]
        self.scrollbar.grid(row=0, column=1, sticky=tk.NS)

        mouse_bind(self.help, "1", self.insert_char)

        init_compose_dict()

        # Avoid displaying help for reversed 2-char sequence, e.g. "o*" and "*o"
        # Remember ones that have been entered already
        reverse_done = {}
        for sequence, char in _compose_dict.items():
            seq_display = sequence.replace(" ", "␣")
            if len(sequence) == 2:
                rev_sequence = sequence[::-1]
                if rev_sequence in reverse_done:
                    continue
                rev_char = _compose_dict.get(rev_sequence)
                if rev_char == char and rev_sequence != sequence:
                    seq_display += f"  or  {rev_sequence.replace(' ', '␣')}"
                    reverse_done[sequence] = char
            # Don't add uppercase version if it leads to identical character, e.g. "dag"/"DAG" for dagger
            if (
                char == _compose_dict.get(sequence.lower())
                and sequence != sequence.lower()
            ):
                continue
            try:
                name = unicodedata.name(char)
            except ValueError:
                continue  # Some Greek combinations don't exist
            entry = (char, seq_display, name)
            self.help.insert("", tk.END, values=entry)

        children = self.help.get_children()
        if children:
            self.help.see(children[0])

    def insert_char(self, event: tk.Event) -> None:
        """Insert character corresponding to row clicked.

        Args:
            event: Event containing location of mouse click
        """
        row_id = self.help.identify_row(event.y)
        row = self.help.set(row_id)
        try:
            char = row[self.column_headings[0]]
        except KeyError:
            return
        insert_in_focus_widget(char)


class ScrollableFrame(ttk.Frame):
    """A scrollable ttk.Frame."""

    def __init__(self, container: tk.Widget, *args: Any, **kwargs: Any) -> None:
        """Initialize ScrollableFrame."""
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(
            self, orient="horizontal", command=self.canvas.xview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)
        bg = str(ttk.Style().lookup(self["style"], "background"))
        self.canvas["background"] = bg

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.scrollable_frame.bind("<Enter>", self.on_enter)
        self.scrollable_frame.bind("<Leave>", self.on_leave)

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas.grid(column=0, row=0, sticky="NSEW")
        v_scrollbar.grid(column=1, row=0, sticky="NSEW")
        h_scrollbar.grid(column=0, row=1, sticky="NSEW")

    def on_mouse_wheel(self, event: tk.Event) -> None:
        """Cross platform scroll wheel event."""
        if is_windows():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif is_mac():
            self.canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")

    def on_enter(self, _event: tk.Event) -> None:
        """Bind wheel events when the cursor enters the control."""
        if is_x11():
            self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)
            self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)
        else:
            self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

    def on_leave(self, _event: tk.Event) -> None:
        """unbind wheel events when the cursorl leaves the control."""
        if is_x11():
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")
        else:
            self.canvas.unbind_all("<MouseWheel>")


class UnicodeBlockDialog(ToplevelDialog):
    """A dialog that displays a block of Unicode characters, and allows
    the user to click on them to insert them into text window."""

    commonly_used_characters_name = "Commonly Used Characters"

    def __init__(self) -> None:
        """Initialize Unicode Block dialog."""

        super().__init__("Unicode Block")  # , resize_x=False, resize_y=False)

        cb = ttk.Combobox(
            self.top_frame,
            textvariable=PersistentString(PrefKey.UNICODE_BLOCK),
            width=30,
        )
        cb.grid(column=0, row=0, sticky="NSEW")
        block_list = list(_unicode_blocks)
        block_list.insert(0, UnicodeBlockDialog.commonly_used_characters_name)
        cb["values"] = block_list
        cb["state"] = "readonly"
        cb.bind("<<ComboboxSelected>>", lambda _e: self.block_selected())
        self.top_frame.rowconfigure(0, weight=0)
        self.top_frame.rowconfigure(1, weight=1)
        self.chars_frame = ScrollableFrame(self.top_frame, padding=10)
        self.chars_frame.grid(column=0, row=1, sticky="NSEW")

        self.button_list: list[ttk.Label] = []
        style = ttk.Style()
        style.configure("unicodedialog.TLabel", font=maintext().font)
        self.block_selected()

    def block_selected(self) -> None:
        """Called when a Unicode block is selected."""
        for btn in self.button_list:
            if btn.winfo_exists():
                btn.destroy()
        self.button_list.clear()

        def add_button(count: int, char: str) -> None:
            """Add a button to the Unicode block dialog.

            Args:
                count: Count of buttons added, used to determine row/column.
                char: Character to use as label for button.
            """
            btn = ttk.Label(
                self.chars_frame.scrollable_frame,
                text=char,
                # command=lambda: insert_in_focus_widget(char),
                width=2,
                borderwidth=2,
                relief=tk.FLAT,
                anchor=tk.CENTER,
                style="unicodedialog.TLabel",
            )

            def press(event: tk.Event) -> None:
                event.widget["relief"] = tk.SUNKEN

            def release(event: tk.Event, char: str) -> None:
                event.widget["relief"] = tk.RAISED
                insert_in_focus_widget(char)

            def enter(event: tk.Event) -> None:
                event.widget["relief"] = tk.RAISED

            def leave(event: tk.Event) -> None:
                relief = str(event.widget["relief"])
                if relief == tk.RAISED:
                    event.widget["relief"] = tk.FLAT

            btn.bind("<ButtonPress-1>", press)
            btn.bind("<ButtonRelease-1>", lambda e: release(e, char))
            btn.bind("<Enter>", enter)
            btn.bind("<Leave>", leave)
            btn.grid(column=count % 16, row=int(count / 16), sticky="NSEW")
            self.button_list.append(btn)

        block_name = preferences.get(PrefKey.UNICODE_BLOCK)
        if block_name == UnicodeBlockDialog.commonly_used_characters_name:
            for count, char in enumerate(_common_characters):
                add_button(count, char)
        else:
            block_range = _unicode_blocks[block_name]
            for count, c_ord in enumerate(range(block_range[0], block_range[1] + 1)):
                add_button(count, chr(c_ord))
        # Add tooltips
        for btn in self.button_list:
            char = btn["text"]
            try:
                ToolTip(btn, f"U+{ord(char):04x}: {unicodedata.name(char)}")
            except ValueError:
                ToolTip(btn, f"U+{ord(char):04x}")


# Somewhat arbitrarily, certain Unicode blocks are not displayed, trying to
# balance usefulness with excessive number of blocks to choose from.
# Currently this list matches the blocks shown in GG1.
_unicode_blocks: dict[str, tuple[int, int]] = {
    "Alphabetic Presentation Forms": (0xFB00, 0xFB4F),
    # Really FDFF but there are illegal characters in fdc0-fdff
    "Arabic Presentation Forms-A": (0xFB50, 0xFDCF),
    "Arabic Presentation Forms-B": (0xFE70, 0xFEFF),
    "Arabic": (0x0600, 0x06FF),
    "Armenian": (0x0530, 0x058F),
    "Arrows": (0x2190, 0x21FF),
    "Bengali": (0x0980, 0x09FF),
    "Block Elements": (0x2580, 0x259F),
    # 'Bopomofo Extended' : (0x31A0, 0x31BF),
    # 'Bopomofo' : (0x3100, 0x312F),
    "Box Drawing": (0x2500, 0x257F),
    "Braille Patterns": (0x2800, 0x28FF),
    "Buhid": (0x1740, 0x175F),
    "Cherokee": (0x13A0, 0x13FF),
    # 'CJK Compatibility Forms' : (0xFE30, 0xFE4F),
    # 'CJK Compatibility Ideographs' : (0xF900, 0xFAFF),
    # 'CJK Compatibility' : (0x3300, 0x33FF),
    # 'CJK Radicals Supplement' : (0x2E80, 0x2EFF),
    # 'CJK Symbols and Punctuation' : (0x3000, 0x303F),
    # 'CJK Unified Ideographs Extension A' : (0x3400, 0x4DBF),
    # 'CJK Unified Ideographs' : (0x4E00, 0x9FFF),
    "Combining Diacritical Marks for Symbols": (0x20D0, 0x20FF),
    "Combining Diacritical Marks": (0x0300, 0x036F),
    "Combining Half Marks": (0xFE20, 0xFE2F),
    "Control Pictures": (0x2400, 0x243F),
    "Currency Symbols": (0x20A0, 0x20CF),
    "Cyrillic Supplementary": (0x0500, 0x052F),
    "Cyrillic": (0x0400, 0x04FF),
    "Devanagari": (0x0900, 0x097F),
    "Dingbats": (0x2700, 0x27BF),
    "Enclosed Alphanumerics": (0x2460, 0x24FF),
    # 'Enclosed CJK Letters and Months' : (0x3200, 0x32FF),
    "Ethiopic": (0x1200, 0x137F),
    "General Punctuation": (0x2000, 0x206F),
    "Geometric Shapes": (0x25A0, 0x25FF),
    "Georgian": (0x10A0, 0x10FF),
    "Greek and Coptic": (0x0370, 0x03FF),
    "Greek Extended": (0x1F00, 0x1FFF),
    "Gujarati": (0x0A80, 0x0AFF),
    "Gurmukhi": (0x0A00, 0x0A7F),
    "Halfwidth and Fullwidth Forms": (0xFF00, 0xFFEF),
    # 'Hangul Compatibility Jamo' : (0x3130, 0x318F),
    # 'Hangul Jamo' : (0x1100, 0x11FF),
    # 'Hangul Syllables' : (0xAC00, 0xD7AF),
    # 'Hanunoo' : (0x1720, 0x173F),
    "Hebrew": (0x0590, 0x05FF),
    # 'High Private Use Surrogates' : (0xDB80, 0xDBFF),
    # 'High Surrogates' : (0xD800, 0xDB7F),
    # 'Hiragana' : (0x3040, 0x309F),
    # 'Ideographic Description Characters' : (0x2FF0, 0x2FFF),
    # 'Kanbun' : (0x3190, 0x319F),
    # 'Kangxi Radicals' : (0x2F00, 0x2FDF),
    "Kannada": (0x0C80, 0x0CFF),
    # 'Katakana Phonetic Extensions' : (0x31F0, 0x31FF),
    # 'Katakana' : (0x30A0, 0x30FF),
    # 'Khmer Symbols' : (0x19E0, 0x19FF),
    # 'Khmer' : (0x1780, 0x17FF),
    "Lao": (0x0E80, 0x0EFF),
    "Latin Extended Additional": (0x1E00, 0x1EFF),
    "Latin Extended-A": (0x0100, 0x017F),
    "Latin Extended-B": (0x0180, 0x024F),
    "Latin IPA Extensions": (0x0250, 0x02AF),
    "Latin-1 Supplement": (0x00A0, 0x00FF),
    "Letterlike Symbols": (0x2100, 0x214F),
    # 'Limbu' : (0x1900, 0x194F),
    # 'Low Surrogates' : (0xDC00, 0xDFFF),
    "Malayalam": (0x0D00, 0x0D7F),
    "Mathematical Operators": (0x2200, 0x22FF),
    "Miscellaneous Mathematical Symbols-A": (0x27C0, 0x27EF),
    "Miscellaneous Mathematical Symbols-B": (0x2980, 0x29FF),
    "Miscellaneous Symbols and Arrows": (0x2B00, 0x2BFF),
    "Miscellaneous Symbols": (0x2600, 0x26FF),
    "Miscellaneous Technical": (0x2300, 0x23FF),
    "Mongolian": (0x1800, 0x18AF),
    "Myanmar": (0x1000, 0x109F),
    "Number Forms": (0x2150, 0x218F),
    "Ogham": (0x1680, 0x169F),
    "Optical Character Recognition": (0x2440, 0x245F),
    "Oriya": (0x0B00, 0x0B7F),
    "Phonetic Extensions": (0x1D00, 0x1D7F),
    "Runic": (0x16A0, 0x16FF),
    "Sinhala": (0x0D80, 0x0DFF),
    "Small Form Variants": (0xFE50, 0xFE6F),
    "Spacing Modifier Letters": (0x02B0, 0x02FF),
    "Superscripts and Subscripts": (0x2070, 0x209F),
    "Supplemental Arrows-A": (0x27F0, 0x27FF),
    "Supplemental Arrows-B": (0x2900, 0x297F),
    "Supplemental Mathematical Operators": (0x2A00, 0x2AFF),
    "Syriac": (0x0700, 0x074F),
    "Tagalog": (0x1700, 0x171F),
    # 'Tagbanwa' : (0x1760, 0x177F),
    # 'Tai Le' : (0x1950, 0x197F),
    "Tamil": (0x0B80, 0x0BFF),
    "Telugu": (0x0C00, 0x0C7F),
    "Thaana": (0x0780, 0x07BF),
    "Thai": (0x0E00, 0x0E7F),
    # 'Tibetan' : (0x0F00, 0x0FFF),
    "Unified Canadian Aboriginal Syllabics": (0x1400, 0x167F),
    "Variation Selectors": (0xFE00, 0xFE0F),
    # 'Yi Radicals' : (0xA490, 0xA4CF),
    # 'Yi Syllables' : (0xA000, 0xA48F),
    # 'Yijing Hexagram Symbols' : (0x4DC0, 0x4DFF),
}


_common_characters: list[str] = [
    "À",
    "Á",
    "Â",
    "Ã",
    "Ä",
    "Å",
    "Æ",
    "Ç",
    "È",
    "É",
    "Ê",
    "Ë",
    "Ì",
    "Í",
    "Î",
    "Ï",
    "Ò",
    "Ó",
    "Ô",
    "Õ",
    "Ö",
    "Ø",
    "Œ",
    "Ñ",
    "Ù",
    "Ú",
    "Û",
    "Ü",
    "Ð",
    "þ",
    "Ÿ",
    "Ý",
    "à",
    "á",
    "â",
    "ã",
    "ä",
    "å",
    "æ",
    "ç",
    "è",
    "é",
    "ê",
    "ë",
    "ì",
    "í",
    "î",
    "ï",
    "ò",
    "ó",
    "ô",
    "õ",
    "ö",
    "ø",
    "œ",
    "ñ",
    "ù",
    "ú",
    "û",
    "ü",
    "ð",
    "Þ",
    "ÿ",
    "ý",
    "¡",
    "¿",
    "«",
    "»",
    "‘",
    "’",
    "“",
    "”",
    "‚",
    "‛",
    "„",
    "‟",
    "ß",
    "⁂",
    "☞",
    "☜",
    "±",
    "·",
    "×",
    "÷",
    "°",
    "′",
    "″",
    "‴",
    "‰",
    "¹",
    "²",
    "³",
    "£",
    "¢",
    "©",
    "\xa0",
    "½",
    "⅓",
    "⅔",
    "¼",
    "¾",
    "⅕",
    "⅖",
    "⅗",
    "⅘",
    "⅙",
    "⅚",
    "⅐",
    "⅛",
    "⅜",
    "⅝",
    "⅞",
    "—",
    "–",
    "†",
    "‡",
    "§",
    "‖",
    "¶",
    "¦",
    "º",
    "ª",
]
