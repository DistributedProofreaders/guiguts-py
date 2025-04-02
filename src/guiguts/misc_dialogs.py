"""Miscellaneous dialogs."""

from importlib.metadata import version
import platform
import sys
import tkinter as tk
from tkinter import ttk, font, filedialog
from typing import Any, Literal
import unicodedata

import regex as re

from guiguts.file import the_file
from guiguts.maintext import maintext
from guiguts.mainwindow import ScrolledReadOnlyText
from guiguts.preferences import (
    PrefKey,
    PersistentBoolean,
    PersistentInt,
    PersistentString,
    preferences,
)
from guiguts.root import root
from guiguts.utilities import is_mac, sound_bell
from guiguts.widgets import (
    ToplevelDialog,
    ToolTip,
    insert_in_focus_widget,
    OkApplyCancelDialog,
    mouse_bind,
    Combobox,
    Notebook,
    bind_mouse_wheel,
    unbind_mouse_wheel,
    menubar_metadata,
    Busy,
    EntryMetadata,
)

COMBO_SEPARATOR = "―" * 20


class PreferencesDialog(ToplevelDialog):
    """A dialog that displays settings/preferences."""

    manual_page = "Edit_Menu#Preferences"

    def __init__(self) -> None:
        """Initialize preferences dialog."""
        super().__init__("Settings", resize_x=False, resize_y=False)
        self.minsize(250, 10)

        # Set up tab notebook
        notebook = Notebook(self.top_frame, takefocus=False)
        notebook.grid(column=0, row=0, sticky="NSEW")
        notebook.enable_traversal()

        # Appearance
        appearance_frame = ttk.Frame(notebook, padding=10)
        notebook.add(appearance_frame, text="Appearance")
        theme_frame = ttk.Frame(appearance_frame)
        theme_frame.grid(column=0, row=0, sticky="NSEW")
        theme_frame.columnconfigure(1, weight=1)
        ttk.Label(theme_frame, text="Theme (change requires restart): ").grid(
            column=0, row=0, sticky="NE"
        )
        cb = ttk.Combobox(
            theme_frame, textvariable=PersistentString(PrefKey.THEME_NAME)
        )
        cb.grid(column=1, row=0, sticky="NEW")
        cb["values"] = ["Default", "Dark", "Light"]
        cb["state"] = "readonly"
        ttk.Checkbutton(
            appearance_frame,
            text="High Contrast",
            variable=PersistentBoolean(PrefKey.HIGH_CONTRAST),
        ).grid(column=0, row=1, sticky="NEW", pady=5)
        tearoff_check = ttk.Checkbutton(
            appearance_frame,
            text="Use Tear-Off Menus (change requires restart)",
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
            validate=tk.ALL,
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
            text="Display Column Numbers",
            variable=PersistentBoolean(PrefKey.COLUMN_NUMBERS),
        ).grid(column=0, row=5, sticky="NEW", pady=5)
        ttk.Checkbutton(
            appearance_frame,
            text="Show Character Names in Status Bar",
            variable=root().ordinal_names_state,
        ).grid(column=0, row=6, sticky="NEW", pady=5)
        bell_frame = ttk.Frame(appearance_frame)
        bell_frame.grid(column=0, row=7, sticky="NEW", pady=(5, 0))
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

        # Image Viewer
        image_viewer_frame = ttk.Frame(notebook, padding=10)
        notebook.add(image_viewer_frame, text="Image Viewer")
        image_viewer_frame.columnconfigure(0, weight=1)
        image_viewer_frame.columnconfigure(1, weight=1)

        iv_btn = ttk.Checkbutton(
            image_viewer_frame,
            text="Auto Img Reload Alert",
            variable=PersistentBoolean(PrefKey.IMAGE_VIEWER_ALERT),
        )
        iv_btn.grid(column=0, row=0, sticky="NEW", pady=5)
        ToolTip(
            iv_btn,
            "Whether to flash the border when Auto Img re-loads the\n"
            "default image after you manually select a different image",
        )
        ttk.Checkbutton(
            image_viewer_frame,
            text="Use External Viewer",
            variable=PersistentBoolean(PrefKey.IMAGE_VIEWER_EXTERNAL),
        ).grid(column=0, row=1, sticky="NEW", pady=5)
        file_name_frame = ttk.Frame(image_viewer_frame)
        file_name_frame.grid(row=2, column=0, columnspan=2, sticky="NSEW")
        file_name_frame.columnconfigure(0, weight=1)
        self.filename_textvariable = tk.StringVar(self, "")
        ttk.Entry(
            file_name_frame,
            textvariable=PersistentString(PrefKey.IMAGE_VIEWER_EXTERNAL_PATH),
            width=30,
        ).grid(row=0, column=0, sticky="EW", padx=(0, 2))

        def choose_external_viewer() -> None:
            """Choose program to view images."""
            if filename := filedialog.askopenfilename(
                parent=self, title="Choose Image Viewer"
            ):
                preferences.set(PrefKey.IMAGE_VIEWER_EXTERNAL_PATH, filename)

        ttk.Button(
            file_name_frame,
            text="Browse...",
            command=choose_external_viewer,
            takefocus=False,
        ).grid(row=0, column=1, sticky="NSEW")

        def add_label_spinbox(
            frame: ttk.Frame, row: int, label: str, key: PrefKey, tooltip: str
        ) -> None:
            """Add a label and spinbox to given frame.
            Args:
                frame: Frame to add label & spinbox to.
                row: Which row in frame to add to.
                label: Text for label.
                key: Prefs key to use to store preference.
                tooltip: Text for tooltip.
            """
            ttk.Label(frame, text=label).grid(column=0, row=row, sticky="NSE", pady=2)
            spinbox = ttk.Spinbox(
                frame,
                textvariable=PersistentInt(key),
                from_=0,
                to=999,
                width=5,
            )
            spinbox.grid(column=1, row=row, sticky="NW", padx=5, pady=2)
            ToolTip(spinbox, tooltip)

        # Wrapping tab
        wrapping_frame = ttk.Frame(notebook, padding=10)
        notebook.add(wrapping_frame, text="Wrapping")

        add_label_spinbox(
            wrapping_frame,
            0,
            "Left Margin:",
            PrefKey.WRAP_LEFT_MARGIN,
            "Left margin for normal text",
        )
        add_label_spinbox(
            wrapping_frame,
            1,
            "Right Margin:",
            PrefKey.WRAP_RIGHT_MARGIN,
            "Right margin for normal text",
        )
        add_label_spinbox(
            wrapping_frame,
            2,
            "Blockquote Indent:",
            PrefKey.WRAP_BLOCKQUOTE_INDENT,
            "Extra indent for each level of /# blockquotes",
        )
        add_label_spinbox(
            wrapping_frame,
            3,
            "Blockquote Right Margin:",
            PrefKey.WRAP_BLOCKQUOTE_RIGHT_MARGIN,
            "Right margin for /# blockquotes",
        )
        add_label_spinbox(
            wrapping_frame,
            4,
            "Nowrap Block Indent:",
            PrefKey.WRAP_BLOCK_INDENT,
            "Indent for /* and /L blocks",
        )
        add_label_spinbox(
            wrapping_frame,
            5,
            "Poetry Indent:",
            PrefKey.WRAP_POETRY_INDENT,
            "Indent for /P poetry blocks",
        )
        add_label_spinbox(
            wrapping_frame,
            6,
            "Index Main Entry Margin:",
            PrefKey.WRAP_INDEX_MAIN_MARGIN,
            "Indent for main entries in index - sub-entries retain their indent relative to this",
        )
        add_label_spinbox(
            wrapping_frame,
            8,
            "Index Wrap Margin:",
            PrefKey.WRAP_INDEX_WRAP_MARGIN,
            "Left margin for all lines rewrapped in index",
        )
        add_label_spinbox(
            wrapping_frame,
            9,
            "Index Right Margin:",
            PrefKey.WRAP_INDEX_RIGHT_MARGIN,
            "Right margin for index entries",
        )

        # Advanced tab
        advance_frame = ttk.Frame(notebook, padding=10)
        notebook.add(advance_frame, text="Advanced")

        add_label_spinbox(
            advance_frame,
            0,
            "Text Line Spacing:",
            PrefKey.TEXT_LINE_SPACING,
            "Additional line spacing in text windows",
        )
        add_label_spinbox(
            advance_frame,
            1,
            "Text Cursor Width:",
            PrefKey.TEXT_CURSOR_WIDTH,
            "Width of insert cursor in main text window",
        )
        ttk.Checkbutton(
            advance_frame,
            text="Highlight Cursor Line",
            variable=PersistentBoolean(PrefKey.HIGHLIGHT_CURSOR_LINE),
        ).grid(column=0, row=2, sticky="NEW", pady=5)

        backup_btn = ttk.Checkbutton(
            advance_frame,
            text="Keep Backup Before Saving",
            variable=PersistentBoolean(PrefKey.BACKUPS_ENABLED),
        )
        backup_btn.grid(column=0, row=3, sticky="EW", pady=(10, 0))
        ToolTip(backup_btn, "Backup file will have '.bak' extension")
        ttk.Checkbutton(
            advance_frame,
            text="Enable Auto Save Every",
            variable=PersistentBoolean(PrefKey.AUTOSAVE_ENABLED),
            command=the_file().reset_autosave,
        ).grid(column=0, row=4, sticky="EW")
        spinbox = ttk.Spinbox(
            advance_frame,
            textvariable=PersistentInt(PrefKey.AUTOSAVE_INTERVAL),
            from_=1,
            to=60,
            width=3,
        )
        spinbox.grid(column=1, row=4, sticky="EW", padx=5)
        ToolTip(
            spinbox,
            "Autosave your file (with '.bk1', '.bk2' extensions) after this number of minutes",
        )
        ttk.Label(advance_frame, text="Minutes").grid(column=2, row=4, sticky="EW")

        notebook.bind(
            "<<NotebookTabChanged>>",
            lambda _: preferences.set(
                PrefKey.PREF_TAB_CURRENT, notebook.index(tk.CURRENT)
            ),
        )
        tab = preferences.get(PrefKey.PREF_TAB_CURRENT)
        if 0 <= tab < notebook.index(tk.END):
            notebook.select(tab)


class HelpAboutDialog(ToplevelDialog):
    """A "Help About Guiguts" dialog with version numbers."""

    manual_page = ""  # Main manual page

    def __init__(self) -> None:
        """Initialize preferences dialog."""
        super().__init__("Help About Guiguts", resize_x=False, resize_y=False)

        # Default font is monospaced. Helvetica is guaranteed to give a proportional font
        font_family = "Helvetica"
        font_small = 10
        font_medium = 12
        font_large = 14
        title_start = "1.0"
        title_end = "2.0 lineend"
        version_start = "3.0"
        version_end = "9.0"

        def copy_to_clipboard() -> None:
            """Copy text to clipboard."""
            maintext().clipboard_clear()
            maintext().clipboard_append(self.text.get(version_start, version_end))

        copy_button = ttk.Button(
            self.top_frame,
            text="Copy Version Information to Clipboard",
            command=copy_to_clipboard,
            takefocus=False,
        )
        copy_button.grid(row=0, column=0, pady=(5, 5))
        self.text = ScrolledReadOnlyText(
            self.top_frame, wrap=tk.NONE, font=(font_family, font_small)
        )
        self.text.grid(row=1, column=0, sticky="NSEW")
        ToolTip(
            self.text,
            "Copy version information when reporting issues",
            use_pointer_pos=True,
        )

        self.text.insert(
            tk.END,
            f"""Guiguts - an application to support creation of ebooks for PG

Guiguts version: {version('guiguts')}

Python version: {sys.version}
Tk/Tcl version: {root().call("info", "patchlevel")}
OS Platform: {platform.platform()}
OS Release: {platform.release()}



Copyright Contributors to the Guiguts-py project.

This program is free software; you can redistribute it
and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even
the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public
License along with this program; if not, write to the
Free Software Foundation, Inc., 51 Franklin Street,
Fifth Floor, Boston, MA 02110-1301 USA.""",
        )
        self.text.tag_add("title_tag", title_start, title_end)
        self.text.tag_config("title_tag", font=(font_family, font_large))
        self.text.tag_add("version_tag", version_start, version_end)
        self.text.tag_config("version_tag", font=(font_family, font_medium))


_compose_dict: dict[str, str] = {}


class ComposeSequenceDialog(OkApplyCancelDialog):
    """Dialog to enter Compose Sequences.

    Attributes:
        dict: Dictionary mapping sequence of keystrokes to character.
    """

    manual_page = "Tools_Menu#Compose_Sequence"

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
        # Don't insert anything if no match
        if not char:
            return
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

    manual_page = "Tools_Menu#Compose_Sequence"

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
        self.help.configure(yscrollcommand=self.scrollbar.set)
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


class CommandPaletteDialog(ToplevelDialog):
    """Command Palette Dialog."""

    manual_page = "Help_Menu#Command_Palette"
    NUM_HISTORY = 5

    def __init__(self) -> None:
        """Initialize the command palette window."""
        super().__init__("Command Palette")
        self.commands = menubar_metadata().get_all_commands()
        self.filtered_commands: list[EntryMetadata] = self.commands

        self.top_frame.grid_rowconfigure(0, weight=0)
        self.top_frame.grid_rowconfigure(1, weight=1)

        entry_frame = ttk.Frame(self.top_frame)
        entry_frame.grid(row=0, column=0, sticky="NSEW", columnspan=2)
        entry_frame.grid_columnconfigure(0, weight=1)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda _1, _2, _3: self.update_list())
        self.entry = ttk.Entry(entry_frame, textvariable=self.search_var)
        self.entry.grid(row=0, column=0, padx=5, pady=5, sticky="NSEW")
        ToolTip(self.entry, "Type part of a command to filter the list")
        ttk.Button(
            entry_frame,
            text="Run",
            command=lambda: self.execute_command(tk.Event()),
            takefocus=False,
        ).grid(row=0, column=1, sticky="NSE")

        columns = ("Command", "Shortcut", "Menu")
        widths = (150, 120, 100)
        self.list = ttk.Treeview(
            self.top_frame,
            columns=columns,
            show="headings",
            selectmode=tk.BROWSE,
            height=20,
        )
        for col, column in enumerate(columns):
            self.list.heading(f"#{col + 1}", text=column)
            self.list.column(
                f"#{col + 1}",
                minwidth=10,
                width=widths[col],
                stretch=(col == 0),
                anchor=tk.W if col == 0 else tk.CENTER,
            )
        self.list.grid(row=1, column=0, padx=5, sticky="NSEW")
        self.scrollbar = ttk.Scrollbar(
            self.top_frame, orient="vertical", command=self.list.yview
        )
        self.scrollbar.grid(row=1, column=1, sticky="NS")
        self.list.config(yscrollcommand=self.scrollbar.set)

        # Bind events for list and entry
        self.list.bind("<Return>", self.execute_command)
        self.list.bind("<Double-Button-1>", self.execute_command)
        self.list.bind("<Down>", lambda _: self.move_in_list(1))
        self.list.bind("<Control-n>", lambda _: self.move_in_list(1))
        self.list.bind("<Up>", lambda _: self.move_in_list(-1))
        self.list.bind("<Control-p>", lambda _: self.move_in_list(-1))
        self.list.bind("<Key>", self.handle_list_typing)

        self.entry.bind("<Down>", self.focus_on_list)
        self.entry.bind("<Control-n>", self.focus_on_list)
        self.entry.bind("<Return>", self.execute_command)

        self.update_list()
        self.entry.focus()

    def update_list(self) -> None:
        """Update the command list based on search input."""
        self.list.tag_configure(
            "recent", foreground="green2" if maintext().is_dark_theme() else "green4"
        )

        # Recent commands are those in history that match search filter
        search_text = self.search_var.get().lower().strip()
        history: list[list[str]] = []
        recent_commands: list[EntryMetadata] = []
        if history := preferences.get(PrefKey.COMMAND_PALETTE_HISTORY):
            for label, parent_label in history:
                for cmd in self.commands:
                    if (
                        label == cmd.label
                        and parent_label == cmd.parent_label
                        and cmd.matches(search_text)
                    ):
                        recent_commands.append(cmd)
                        break

        # Insert recent commands first
        self.filtered_commands = recent_commands[:]
        # Then all matching non-recent commands, sorted
        self.filtered_commands.extend(
            sorted(
                cmd
                for cmd in self.commands
                if cmd.matches(search_text) and cmd not in recent_commands
            )
        )

        self.list.delete(*self.list.get_children())
        for idx, cmd in enumerate(self.filtered_commands):
            iid = self.list.insert(
                "", "end", values=(cmd.label, cmd.shortcut, cmd.parent_label)
            )
            if idx < len(recent_commands):
                self.list.item(iid, tags="recent")

        if self.filtered_commands:
            self.select_and_focus(self.list.get_children()[0])

    def execute_command(self, _: tk.Event) -> None:
        """Execute the selected command."""
        selection = self.list.selection()
        if selection:
            item = selection[0]
            entry = self.filtered_commands[self.list.index(item)]
            self.add_to_history(entry.label, entry.parent_label)
            command = entry.get_command()
            self.destroy()
            Busy.busy()  # In case it's a slow command
            command()
            Busy.unbusy()  # In case it's a slow command

    def focus_on_list(self, _: tk.Event) -> None:
        """Move focus to the list and select the first item."""
        self.list.focus_set()
        if self.filtered_commands:  # Select the first item in the list
            self.select_and_focus(self.list.get_children()[0])

    def select_and_focus(self, item: str) -> None:
        """Select and set focus to the given item. See page_details for
        description of the need for this.

        Args:
            item: The item to be selected/focused.
        """
        self.list.selection_set(item)
        self.list.focus(item)

    def move_in_list(self, direction: int) -> str:
        """Move the selection in the list."""
        current_selection = self.list.selection()
        if current_selection:
            current_index = self.list.index(current_selection[0])
            new_index = current_index + direction
            if 0 <= new_index < len(self.filtered_commands):
                next_item = self.list.get_children()[new_index]
                self.select_and_focus(next_item)
            elif new_index < 0:
                # Moving up from first list element - focus in entry field
                self.entry.focus_set()
                self.entry.icursor(tk.END)
        return "break"

    def handle_list_typing(self, event: tk.Event) -> None:
        """Handle key press in the list to simulate typing in the Entry box."""
        current_text = self.search_var.get()
        if event.keysym in ("Backspace", "Delete"):
            self.search_var.set(current_text[:-1])
        elif event.char:  # If a proper char, add it to the entry
            self.search_var.set(current_text + event.char)
        self.update_list()  # Update the list based on the new search text

    def add_to_history(self, label: str, parent_label: str) -> None:
        """Store given entry in history list pref.

        Args:
            label: Label of entry to add to history.
            menu: Name of menu for entry to add to history.
        """
        history: list[list[str]] = preferences.get(PrefKey.COMMAND_PALETTE_HISTORY)
        try:
            history.remove([label, parent_label])
        except ValueError:
            pass  # OK if entry wasn't in list
        history.insert(0, [label, parent_label])
        preferences.set(PrefKey.COMMAND_PALETTE_HISTORY, history[: self.NUM_HISTORY])


class ScrollableFrame(ttk.Frame):
    """A scrollable ttk.Frame.

    Consider rewriting, so it's like ScrolledReadOnlyText, i.e. self is the frame you add to,
    and grid method is overridden for correct placement.
    """

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

    def on_enter(self, _event: tk.Event) -> None:
        """Bind wheel events when the cursor enters the control."""
        bind_mouse_wheel(self.canvas)

    def on_leave(self, _event: tk.Event) -> None:
        """Unbind wheel events when the cursor leaves the control."""
        unbind_mouse_wheel(self.canvas)

    def reset_scroll(self) -> None:
        """Scroll canvas to top left position."""
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)


class UnicodeBlockDialog(ToplevelDialog):
    """A dialog that displays a block of Unicode characters, and allows
    the user to click on them to insert them into text window."""

    manual_page = "Tools_Menu#Unicode_Blocks"
    commonly_used_characters_name = "Commonly Used Characters"

    def __init__(self) -> None:
        """Initialize Unicode Block dialog."""

        super().__init__("Unicode Block")

        cb = ttk.Combobox(
            self.top_frame,
            textvariable=PersistentString(PrefKey.UNICODE_BLOCK),
            width=50,
        )
        cb.grid(column=0, row=0, sticky="NSW", padx=5, pady=(5, 0))
        block_list = []
        for name, (beg, end, show) in _unicode_blocks.items():
            if show:
                block_list.append(f"{name}   ({beg:04X}–{end:04X})")
        block_list.sort()
        block_list.insert(0, UnicodeBlockDialog.commonly_used_characters_name)
        cb["values"] = block_list
        cb["state"] = "readonly"
        cb.bind("<<ComboboxSelected>>", lambda _e: self.block_selected())
        self.top_frame.rowconfigure(0, weight=0)
        self.top_frame.rowconfigure(1, weight=1)
        self.chars_frame = ScrollableFrame(self.top_frame)
        self.chars_frame.grid(column=0, row=1, sticky="NSEW", padx=5, pady=5)

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
        self.chars_frame.reset_scroll()

        def add_button(count: int, char: str) -> None:
            """Add a button to the Unicode block dialog.

            Args:
                count: Count of buttons added, used to determine row/column.
                char: Character to use as label for button.
            """
            btn = ttk.Label(
                self.chars_frame.scrollable_frame,
                text=char,
                width=2,
                borderwidth=2,
                relief=tk.SOLID,
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
                    event.widget["relief"] = tk.SOLID

            btn.bind("<ButtonPress-1>", press)
            btn.bind("<ButtonRelease-1>", lambda e: release(e, char))
            btn.bind("<Enter>", enter)
            btn.bind("<Leave>", leave)
            btn.grid(column=count % 16, row=int(count / 16), sticky="NSEW")
            self.button_list.append(btn)

        block_name = re.sub(r" *\(.*", "", preferences.get(PrefKey.UNICODE_BLOCK))
        if block_name == UnicodeBlockDialog.commonly_used_characters_name:
            for count, char in enumerate(_common_characters):
                add_button(count, char)
        else:
            block_range = _unicode_blocks[block_name]
            for count, c_ord in enumerate(range(block_range[0], block_range[1] + 1)):
                add_button(count, chr(c_ord))
        # Add tooltips
        for btn in self.button_list:
            char = str(btn["text"])
            name, new = unicode_char_to_name(char)
            if name:
                name = ": " + name
            warning_flag = "⚠\ufe0f" if new else ""
            ToolTip(btn, f"{warning_flag}U+{ord(char):04x}{name}")


class UnicodeSearchDialog(ToplevelDialog):
    """A dialog that allows user to search for Unicode characters,
    given partial name match or Unicode ordinal, and allows
    the user to insert it into text window."""

    manual_page = "Tools_Menu#Unicode_Search/Entry"
    CHAR_COL_ID = "#1"
    CHAR_COL_HEAD = "Char"
    CHAR_COL_WIDTH = 50
    CODEPOINT_COL_ID = "#2"
    CODEPOINT_COL_HEAD = "Code Point"
    CODEPOINT_COL_WIDTH = 80
    NAME_COL_ID = "#3"
    NAME_COL_HEAD = "Name"
    NAME_COL_WIDTH = 250
    BLOCK_COL_ID = "#4"
    BLOCK_COL_HEAD = "Block"
    BLOCK_COL_WIDTH = 180

    def __init__(self) -> None:
        """Initialize Unicode Search dialog."""

        super().__init__("Unicode Search")

        search_frame = ttk.Frame(self.top_frame)
        search_frame.grid(column=0, row=0, sticky="NSEW")
        search_frame.columnconfigure(0, weight=1)
        search_frame.columnconfigure(1, weight=0)
        self.search = Combobox(
            search_frame,
            PrefKey.UNICODE_SEARCH_HISTORY,
            width=50,
            font=maintext().font,
        )
        self.search.grid(column=0, row=0, sticky="NSEW", padx=5, pady=(5, 0))
        self.search.focus()
        ToolTip(
            self.search,
            "\n".join(
                [
                    "Type words from character name to match against,",
                    "or hex codepoint (optionally preceded by 'U+' or 'X'),",
                    "or type/paste a single character to search for",
                ]
            ),
        )

        search_btn = ttk.Button(
            search_frame,
            text="Search",
            default="active",
            takefocus=False,
            command=lambda: self.find_matches(self.search.get()),
        )
        search_btn.grid(column=1, row=0, sticky="NSEW")
        self.bind("<Return>", lambda _: search_btn.invoke())
        self.search.bind("<<ComboboxSelected>>", lambda _e: search_btn.invoke())

        self.top_frame.rowconfigure(0, weight=0)
        self.top_frame.rowconfigure(1, weight=1)

        columns = (
            UnicodeSearchDialog.CHAR_COL_HEAD,
            UnicodeSearchDialog.CODEPOINT_COL_HEAD,
            UnicodeSearchDialog.NAME_COL_HEAD,
            UnicodeSearchDialog.BLOCK_COL_HEAD,
        )
        widths = (
            UnicodeSearchDialog.CHAR_COL_WIDTH,
            UnicodeSearchDialog.CODEPOINT_COL_WIDTH,
            UnicodeSearchDialog.NAME_COL_WIDTH,
            UnicodeSearchDialog.BLOCK_COL_WIDTH,
        )
        self.list = ttk.Treeview(
            self.top_frame,
            columns=columns,
            show="headings",
            height=15,
            selectmode=tk.BROWSE,
        )
        ToolTip(
            self.list,
            "\n".join(
                [
                    f"Click in {UnicodeSearchDialog.CHAR_COL_HEAD},  {UnicodeSearchDialog.CODEPOINT_COL_HEAD} or {UnicodeSearchDialog.NAME_COL_HEAD} column to insert character",
                    f"Click in {UnicodeSearchDialog.BLOCK_COL_HEAD} column to open Unicode Block dialog",
                    "(⚠\ufe0f before a character's name means it was added more recently - use with caution)",
                ]
            ),
            use_pointer_pos=True,
        )
        for col, column in enumerate(columns):
            col_id = f"#{col + 1}"
            anchor: Literal["center", "w"] = (
                tk.CENTER if col_id == UnicodeSearchDialog.CHAR_COL_ID else tk.W
            )
            self.list.column(
                col_id,
                minwidth=20,
                width=widths[col],
                stretch=(col_id == UnicodeSearchDialog.NAME_COL_ID),
                anchor=anchor,
            )
            self.list.heading(col_id, text=column, anchor=anchor)
        self.list.grid(row=1, column=0, sticky=tk.NSEW, pady=(5, 0))

        self.scrollbar = ttk.Scrollbar(
            self.top_frame, orient=tk.VERTICAL, command=self.list.yview
        )
        self.list.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=1, column=1, sticky=tk.NS)
        mouse_bind(self.list, "1", self.item_clicked)

    def find_matches(self, string: str) -> None:
        """Find & display Unicode characters that match all criteria (words) in the given string.

        Args:
            string: String containing words that must appear in the characters' names. If no match
                    is found, check if string is a hex number which is the codepoint of a character.
        """
        # Clear existing display of chars
        children = self.list.get_children()
        for child in children:
            self.list.delete(child)

        # Split user string into words
        match_words = [x.lower() for x in string.split(" ") if x]
        if len(match_words) > 0:
            self.search.add_to_history(string)

        # Check every Unicode character to see if its name contains all the given words
        # (including hyphenated, e.g. BREAK will match NO-BREAK, but not NON-BREAKING)
        found = False
        if len(match_words) > 0:
            for ordinal in range(0, sys.maxunicode + 1):
                char = chr(ordinal)
                name, new = unicode_char_to_name(char)
                name_list = name.lower().split(" ")
                hyphen_parts: list[str] = []
                for word in name_list:
                    if "-" in word:
                        hyphen_parts += word.split("-")
                name_list += hyphen_parts
                if name and all(word in name_list for word in match_words):
                    self.add_row(char, new)
                    found = True

        if not found:  # Maybe string was a hex codepoint?
            hex_string = re.sub(r"^(U\+|0?X)", "", string.strip(), flags=re.IGNORECASE)
            char = ""
            try:
                char = chr(int(hex_string, 16))
            except (OverflowError, ValueError):
                pass
            if char:
                name, new = unicode_char_to_name(char)
                if name:
                    self.add_row(char, new)
                    found = True

        # Maybe string was a single character?
        # Carefully strip spaces, so that a single space still works
        if not found and len(string) >= 1:
            string = string.strip(" ")
            if len(string) == 0:
                string = " "  # String was all spaces
            if len(string) == 1:
                name, new = unicode_char_to_name(string)
                if name:
                    self.add_row(string, new)
                    found = True

        if not found:
            sound_bell()

    def add_row(self, char: str, new: bool) -> None:
        """Add a row to the Unicode Search dialog.

        Args:
            count: Row to add.
            char: Character to display in row.
            new: True if character was added to unicode since version 3.2 (March 2002)
        """
        ordinal = ord(char)
        block_name = ""
        warning_flag = "⚠\ufe0f" if new else ""
        # Find block name
        for block, (beg, end, _) in _unicode_blocks.items():
            if beg <= ordinal <= end:
                block_name = block
                break
        # Add entry to Treeview
        entry = (
            char,
            f"U+{ord(char):04x}",
            warning_flag + unicodedata.name(char),
            block_name,
        )
        self.list.insert("", tk.END, values=entry)

    def item_clicked(self, event: tk.Event) -> None:
        """Called when Unicode search item is clicked.

        If click is in char, codepoint or name column, then insert character.
        If in block column, open the block dialog.

        Args:
            event: Event containing location of mouse click
        """
        row_id = self.list.identify_row(event.y)
        row = self.list.set(row_id)
        if not row:  # Heading clicked
            return
        col_id = self.list.identify_column(event.x)

        if col_id in (
            UnicodeSearchDialog.CHAR_COL_ID,
            UnicodeSearchDialog.CODEPOINT_COL_ID,
            UnicodeSearchDialog.NAME_COL_ID,
        ):
            insert_in_focus_widget(row[UnicodeSearchDialog.CHAR_COL_HEAD])
        elif col_id == UnicodeSearchDialog.BLOCK_COL_ID:
            block = row[UnicodeSearchDialog.BLOCK_COL_HEAD]
            if not block:
                return
            preferences.set(PrefKey.UNICODE_BLOCK, block)
            dlg = UnicodeBlockDialog.show_dialog()
            dlg.block_selected()


def unicode_char_to_name(char: str) -> tuple[str, bool]:
    """Convert char to Unicode name, and note if it is "new".

    Args:
        char: Character to convert.

    Returns:
        Tuple containing name of character (empty if no name),
        and bool flagging if character is new (Unicode version > 3.2).
    """
    new = False
    try:
        name = unicodedata.name(char)
        try:
            unicodedata.ucd_3_2_0.name(char)
        except ValueError:
            new = True
    except ValueError:
        name = ""
    return name, new


# Somewhat arbitrarily, certain Unicode blocks are not displayed in the
# dropdown menu, roughly matching the GG1 list, and trying to
# balance usefulness with excessive number of blocks to choose from.
# List of blocks taken from https://unicode.org/Public/UNIDATA/Blocks.txt with header
#     Blocks-16.0.0.txt
#     Date: 2024-02-02
# Start point of Basic Latin and Latin-1 Supplement adjusted to avoid unprintables
_unicode_blocks: dict[str, tuple[int, int, bool]] = {
    "Basic Latin": (0x0020, 0x007E, True),
    "Latin-1 Supplement": (0x00A0, 0x00FF, True),
    "Latin Extended-A": (0x0100, 0x017F, True),
    "Latin Extended-B": (0x0180, 0x024F, True),
    "IPA Extensions": (0x0250, 0x02AF, True),
    "Spacing Modifier Letters": (0x02B0, 0x02FF, True),
    "Combining Diacritical Marks": (0x0300, 0x036F, True),
    "Greek and Coptic": (0x0370, 0x03FF, True),
    "Cyrillic": (0x0400, 0x04FF, True),
    "Cyrillic Supplement": (0x0500, 0x052F, True),
    "Armenian": (0x0530, 0x058F, True),
    "Hebrew": (0x0590, 0x05FF, True),
    "Arabic": (0x0600, 0x06FF, True),
    "Syriac": (0x0700, 0x074F, True),
    "Arabic Supplement": (0x0750, 0x077F, False),
    "Thaana": (0x0780, 0x07BF, True),
    "NKo": (0x07C0, 0x07FF, False),
    "Samaritan": (0x0800, 0x083F, False),
    "Mandaic": (0x0840, 0x085F, False),
    "Syriac Supplement": (0x0860, 0x086F, False),
    "Arabic Extended-B": (0x0870, 0x089F, False),
    "Arabic Extended-A": (0x08A0, 0x08FF, False),
    "Devanagari": (0x0900, 0x097F, True),
    "Bengali": (0x0980, 0x09FF, True),
    "Gurmukhi": (0x0A00, 0x0A7F, True),
    "Gujarati": (0x0A80, 0x0AFF, True),
    "Oriya": (0x0B00, 0x0B7F, True),
    "Tamil": (0x0B80, 0x0BFF, True),
    "Telugu": (0x0C00, 0x0C7F, True),
    "Kannada": (0x0C80, 0x0CFF, True),
    "Malayalam": (0x0D00, 0x0D7F, True),
    "Sinhala": (0x0D80, 0x0DFF, True),
    "Thai": (0x0E00, 0x0E7F, True),
    "Lao": (0x0E80, 0x0EFF, True),
    "Tibetan": (0x0F00, 0x0FFF, False),
    "Myanmar": (0x1000, 0x109F, True),
    "Georgian": (0x10A0, 0x10FF, True),
    "Hangul Jamo": (0x1100, 0x11FF, True),
    "Ethiopic": (0x1200, 0x137F, True),
    "Ethiopic Supplement": (0x1380, 0x139F, False),
    "Cherokee": (0x13A0, 0x13FF, True),
    "Unified Canadian Aboriginal Syllabics": (0x1400, 0x167F, True),
    "Ogham": (0x1680, 0x169F, True),
    "Runic": (0x16A0, 0x16FF, True),
    "Tagalog": (0x1700, 0x171F, True),
    "Hanunoo": (0x1720, 0x173F, False),
    "Buhid": (0x1740, 0x175F, True),
    "Tagbanwa": (0x1760, 0x177F, False),
    "Khmer": (0x1780, 0x17FF, False),
    "Mongolian": (0x1800, 0x18AF, True),
    "Unified Canadian Aboriginal Syllabics Extended": (0x18B0, 0x18FF, False),
    "Limbu": (0x1900, 0x194F, False),
    "Tai Le": (0x1950, 0x197F, False),
    "New Tai Lue": (0x1980, 0x19DF, False),
    "Khmer Symbols": (0x19E0, 0x19FF, False),
    "Buginese": (0x1A00, 0x1A1F, False),
    "Tai Tham": (0x1A20, 0x1AAF, False),
    "Combining Diacritical Marks Extended": (0x1AB0, 0x1AFF, False),
    "Balinese": (0x1B00, 0x1B7F, False),
    "Sundanese": (0x1B80, 0x1BBF, False),
    "Batak": (0x1BC0, 0x1BFF, False),
    "Lepcha": (0x1C00, 0x1C4F, False),
    "Ol Chiki": (0x1C50, 0x1C7F, False),
    "Cyrillic Extended-C": (0x1C80, 0x1C8F, False),
    "Georgian Extended": (0x1C90, 0x1CBF, False),
    "Sundanese Supplement": (0x1CC0, 0x1CCF, False),
    "Vedic Extensions": (0x1CD0, 0x1CFF, False),
    "Phonetic Extensions": (0x1D00, 0x1D7F, True),
    "Phonetic Extensions Supplement": (0x1D80, 0x1DBF, False),
    "Combining Diacritical Marks Supplement": (0x1DC0, 0x1DFF, False),
    "Latin Extended Additional": (0x1E00, 0x1EFF, True),
    "Greek Extended": (0x1F00, 0x1FFF, True),
    "General Punctuation": (0x2000, 0x206F, True),
    "Superscripts and Subscripts": (0x2070, 0x209F, True),
    "Currency Symbols": (0x20A0, 0x20CF, True),
    "Combining Diacritical Marks for Symbols": (0x20D0, 0x20FF, True),
    "Letterlike Symbols": (0x2100, 0x214F, True),
    "Number Forms": (0x2150, 0x218F, True),
    "Arrows": (0x2190, 0x21FF, True),
    "Mathematical Operators": (0x2200, 0x22FF, True),
    "Miscellaneous Technical": (0x2300, 0x23FF, True),
    "Control Pictures": (0x2400, 0x243F, True),
    "Optical Character Recognition": (0x2440, 0x245F, True),
    "Enclosed Alphanumerics": (0x2460, 0x24FF, True),
    "Box Drawing": (0x2500, 0x257F, True),
    "Block Elements": (0x2580, 0x259F, True),
    "Geometric Shapes": (0x25A0, 0x25FF, True),
    "Miscellaneous Symbols": (0x2600, 0x26FF, True),
    "Dingbats": (0x2700, 0x27BF, True),
    "Miscellaneous Mathematical Symbols-A": (0x27C0, 0x27EF, True),
    "Supplemental Arrows-A": (0x27F0, 0x27FF, True),
    "Braille Patterns": (0x2800, 0x28FF, True),
    "Supplemental Arrows-B": (0x2900, 0x297F, True),
    "Miscellaneous Mathematical Symbols-B": (0x2980, 0x29FF, True),
    "Supplemental Mathematical Operators": (0x2A00, 0x2AFF, True),
    "Miscellaneous Symbols and Arrows": (0x2B00, 0x2BFF, True),
    "Glagolitic": (0x2C00, 0x2C5F, False),
    "Latin Extended-C": (0x2C60, 0x2C7F, False),
    "Coptic": (0x2C80, 0x2CFF, False),
    "Georgian Supplement": (0x2D00, 0x2D2F, False),
    "Tifinagh": (0x2D30, 0x2D7F, False),
    "Ethiopic Extended": (0x2D80, 0x2DDF, False),
    "Cyrillic Extended-A": (0x2DE0, 0x2DFF, False),
    "Supplemental Punctuation": (0x2E00, 0x2E7F, False),
    "CJK Radicals Supplement": (0x2E80, 0x2EFF, False),
    "Kangxi Radicals": (0x2F00, 0x2FDF, False),
    "Ideographic Description Characters": (0x2FF0, 0x2FFF, False),
    "CJK Symbols and Punctuation": (0x3000, 0x303F, False),
    "Hiragana": (0x3040, 0x309F, False),
    "Katakana": (0x30A0, 0x30FF, False),
    "Bopomofo": (0x3100, 0x312F, False),
    "Hangul Compatibility Jamo": (0x3130, 0x318F, False),
    "Kanbun": (0x3190, 0x319F, False),
    "Bopomofo Extended": (0x31A0, 0x31BF, False),
    "CJK Strokes": (0x31C0, 0x31EF, False),
    "Katakana Phonetic Extensions": (0x31F0, 0x31FF, False),
    "Enclosed CJK Letters and Months": (0x3200, 0x32FF, False),
    "CJK Compatibility": (0x3300, 0x33FF, False),
    "CJK Unified Ideographs Extension A": (0x3400, 0x4DBF, False),
    "Yijing Hexagram Symbols": (0x4DC0, 0x4DFF, False),
    "CJK Unified Ideographs": (0x4E00, 0x9FFF, False),
    "Yi Syllables": (0xA000, 0xA48F, False),
    "Yi Radicals": (0xA490, 0xA4CF, False),
    "Lisu": (0xA4D0, 0xA4FF, False),
    "Vai": (0xA500, 0xA63F, False),
    "Cyrillic Extended-B": (0xA640, 0xA69F, False),
    "Bamum": (0xA6A0, 0xA6FF, False),
    "Modifier Tone Letters": (0xA700, 0xA71F, False),
    "Latin Extended-D": (0xA720, 0xA7FF, False),
    "Syloti Nagri": (0xA800, 0xA82F, False),
    "Common Indic Number Forms": (0xA830, 0xA83F, False),
    "Phags-pa": (0xA840, 0xA87F, False),
    "Saurashtra": (0xA880, 0xA8DF, False),
    "Devanagari Extended": (0xA8E0, 0xA8FF, False),
    "Kayah Li": (0xA900, 0xA92F, False),
    "Rejang": (0xA930, 0xA95F, False),
    "Hangul Jamo Extended-A": (0xA960, 0xA97F, False),
    "Javanese": (0xA980, 0xA9DF, False),
    "Myanmar Extended-B": (0xA9E0, 0xA9FF, False),
    "Cham": (0xAA00, 0xAA5F, False),
    "Myanmar Extended-A": (0xAA60, 0xAA7F, False),
    "Tai Viet": (0xAA80, 0xAADF, False),
    "Meetei Mayek Extensions": (0xAAE0, 0xAAFF, False),
    "Ethiopic Extended-A": (0xAB00, 0xAB2F, False),
    "Latin Extended-E": (0xAB30, 0xAB6F, False),
    "Cherokee Supplement": (0xAB70, 0xABBF, False),
    "Meetei Mayek": (0xABC0, 0xABFF, False),
    "Hangul Syllables": (0xAC00, 0xD7AF, False),
    "Hangul Jamo Extended-B": (0xD7B0, 0xD7FF, False),
    "High Surrogates": (0xD800, 0xDB7F, False),
    "High Private Use Surrogates": (0xDB80, 0xDBFF, False),
    "Low Surrogates": (0xDC00, 0xDFFF, False),
    "Private Use Area": (0xE000, 0xF8FF, False),
    "CJK Compatibility Ideographs": (0xF900, 0xFAFF, False),
    "Alphabetic Presentation Forms": (0xFB00, 0xFB4F, True),
    "Arabic Presentation Forms-A": (0xFB50, 0xFDFF, True),
    "Variation Selectors": (0xFE00, 0xFE0F, True),
    "Vertical Forms": (0xFE10, 0xFE1F, False),
    "Combining Half Marks": (0xFE20, 0xFE2F, True),
    "CJK Compatibility Forms": (0xFE30, 0xFE4F, False),
    "Small Form Variants": (0xFE50, 0xFE6F, True),
    "Arabic Presentation Forms-B": (0xFE70, 0xFEFF, True),
    "Halfwidth and Fullwidth Forms": (0xFF00, 0xFFEF, True),
    "Specials": (0xFFF0, 0xFFFF, False),
    "Linear B Syllabary": (0x10000, 0x1007F, False),
    "Linear B Ideograms": (0x10080, 0x100FF, False),
    "Aegean Numbers": (0x10100, 0x1013F, False),
    "Ancient Greek Numbers": (0x10140, 0x1018F, False),
    "Ancient Symbols": (0x10190, 0x101CF, False),
    "Phaistos Disc": (0x101D0, 0x101FF, False),
    "Lycian": (0x10280, 0x1029F, False),
    "Carian": (0x102A0, 0x102DF, False),
    "Coptic Epact Numbers": (0x102E0, 0x102FF, False),
    "Old Italic": (0x10300, 0x1032F, False),
    "Gothic": (0x10330, 0x1034F, False),
    "Old Permic": (0x10350, 0x1037F, False),
    "Ugaritic": (0x10380, 0x1039F, False),
    "Old Persian": (0x103A0, 0x103DF, False),
    "Deseret": (0x10400, 0x1044F, False),
    "Shavian": (0x10450, 0x1047F, False),
    "Osmanya": (0x10480, 0x104AF, False),
    "Osage": (0x104B0, 0x104FF, False),
    "Elbasan": (0x10500, 0x1052F, False),
    "Caucasian Albanian": (0x10530, 0x1056F, False),
    "Vithkuqi": (0x10570, 0x105BF, False),
    "Todhri": (0x105C0, 0x105FF, False),
    "Linear A": (0x10600, 0x1077F, False),
    "Latin Extended-F": (0x10780, 0x107BF, False),
    "Cypriot Syllabary": (0x10800, 0x1083F, False),
    "Imperial Aramaic": (0x10840, 0x1085F, False),
    "Palmyrene": (0x10860, 0x1087F, False),
    "Nabataean": (0x10880, 0x108AF, False),
    "Hatran": (0x108E0, 0x108FF, False),
    "Phoenician": (0x10900, 0x1091F, False),
    "Lydian": (0x10920, 0x1093F, False),
    "Meroitic Hieroglyphs": (0x10980, 0x1099F, False),
    "Meroitic Cursive": (0x109A0, 0x109FF, False),
    "Kharoshthi": (0x10A00, 0x10A5F, False),
    "Old South Arabian": (0x10A60, 0x10A7F, False),
    "Old North Arabian": (0x10A80, 0x10A9F, False),
    "Manichaean": (0x10AC0, 0x10AFF, False),
    "Avestan": (0x10B00, 0x10B3F, False),
    "Inscriptional Parthian": (0x10B40, 0x10B5F, False),
    "Inscriptional Pahlavi": (0x10B60, 0x10B7F, False),
    "Psalter Pahlavi": (0x10B80, 0x10BAF, False),
    "Old Turkic": (0x10C00, 0x10C4F, False),
    "Old Hungarian": (0x10C80, 0x10CFF, False),
    "Hanifi Rohingya": (0x10D00, 0x10D3F, False),
    "Garay": (0x10D40, 0x10D8F, False),
    "Rumi Numeral Symbols": (0x10E60, 0x10E7F, False),
    "Yezidi": (0x10E80, 0x10EBF, False),
    "Arabic Extended-C": (0x10EC0, 0x10EFF, False),
    "Old Sogdian": (0x10F00, 0x10F2F, False),
    "Sogdian": (0x10F30, 0x10F6F, False),
    "Old Uyghur": (0x10F70, 0x10FAF, False),
    "Chorasmian": (0x10FB0, 0x10FDF, False),
    "Elymaic": (0x10FE0, 0x10FFF, False),
    "Brahmi": (0x11000, 0x1107F, False),
    "Kaithi": (0x11080, 0x110CF, False),
    "Sora Sompeng": (0x110D0, 0x110FF, False),
    "Chakma": (0x11100, 0x1114F, False),
    "Mahajani": (0x11150, 0x1117F, False),
    "Sharada": (0x11180, 0x111DF, False),
    "Sinhala Archaic Numbers": (0x111E0, 0x111FF, False),
    "Khojki": (0x11200, 0x1124F, False),
    "Multani": (0x11280, 0x112AF, False),
    "Khudawadi": (0x112B0, 0x112FF, False),
    "Grantha": (0x11300, 0x1137F, False),
    "Tulu-Tigalari": (0x11380, 0x113FF, False),
    "Newa": (0x11400, 0x1147F, False),
    "Tirhuta": (0x11480, 0x114DF, False),
    "Siddham": (0x11580, 0x115FF, False),
    "Modi": (0x11600, 0x1165F, False),
    "Mongolian Supplement": (0x11660, 0x1167F, False),
    "Takri": (0x11680, 0x116CF, False),
    "Myanmar Extended-C": (0x116D0, 0x116FF, False),
    "Ahom": (0x11700, 0x1174F, False),
    "Dogra": (0x11800, 0x1184F, False),
    "Warang Citi": (0x118A0, 0x118FF, False),
    "Dives Akuru": (0x11900, 0x1195F, False),
    "Nandinagari": (0x119A0, 0x119FF, False),
    "Zanabazar Square": (0x11A00, 0x11A4F, False),
    "Soyombo": (0x11A50, 0x11AAF, False),
    "Unified Canadian Aboriginal Syllabics Extended-A": (0x11AB0, 0x11ABF, False),
    "Pau Cin Hau": (0x11AC0, 0x11AFF, False),
    "Devanagari Extended-A": (0x11B00, 0x11B5F, False),
    "Sunuwar": (0x11BC0, 0x11BFF, False),
    "Bhaiksuki": (0x11C00, 0x11C6F, False),
    "Marchen": (0x11C70, 0x11CBF, False),
    "Masaram Gondi": (0x11D00, 0x11D5F, False),
    "Gunjala Gondi": (0x11D60, 0x11DAF, False),
    "Makasar": (0x11EE0, 0x11EFF, False),
    "Kawi": (0x11F00, 0x11F5F, False),
    "Lisu Supplement": (0x11FB0, 0x11FBF, False),
    "Tamil Supplement": (0x11FC0, 0x11FFF, False),
    "Cuneiform": (0x12000, 0x123FF, False),
    "Cuneiform Numbers and Punctuation": (0x12400, 0x1247F, False),
    "Early Dynastic Cuneiform": (0x12480, 0x1254F, False),
    "Cypro-Minoan": (0x12F90, 0x12FFF, False),
    "Egyptian Hieroglyphs": (0x13000, 0x1342F, False),
    "Egyptian Hieroglyph Format Controls": (0x13430, 0x1345F, False),
    "Egyptian Hieroglyphs Extended-A": (0x13460, 0x143FF, False),
    "Anatolian Hieroglyphs": (0x14400, 0x1467F, False),
    "Gurung Khema": (0x16100, 0x1613F, False),
    "Bamum Supplement": (0x16800, 0x16A3F, False),
    "Mro": (0x16A40, 0x16A6F, False),
    "Tangsa": (0x16A70, 0x16ACF, False),
    "Bassa Vah": (0x16AD0, 0x16AFF, False),
    "Pahawh Hmong": (0x16B00, 0x16B8F, False),
    "Kirat Rai": (0x16D40, 0x16D7F, False),
    "Medefaidrin": (0x16E40, 0x16E9F, False),
    "Miao": (0x16F00, 0x16F9F, False),
    "Ideographic Symbols and Punctuation": (0x16FE0, 0x16FFF, False),
    "Tangut": (0x17000, 0x187FF, False),
    "Tangut Components": (0x18800, 0x18AFF, False),
    "Khitan Small Script": (0x18B00, 0x18CFF, False),
    "Tangut Supplement": (0x18D00, 0x18D7F, False),
    "Kana Extended-B": (0x1AFF0, 0x1AFFF, False),
    "Kana Supplement": (0x1B000, 0x1B0FF, False),
    "Kana Extended-A": (0x1B100, 0x1B12F, False),
    "Small Kana Extension": (0x1B130, 0x1B16F, False),
    "Nushu": (0x1B170, 0x1B2FF, False),
    "Duployan": (0x1BC00, 0x1BC9F, False),
    "Shorthand Format Controls": (0x1BCA0, 0x1BCAF, False),
    "Symbols for Legacy Computing Supplement": (0x1CC00, 0x1CEBF, False),
    "Znamenny Musical Notation": (0x1CF00, 0x1CFCF, False),
    "Byzantine Musical Symbols": (0x1D000, 0x1D0FF, False),
    "Musical Symbols": (0x1D100, 0x1D1FF, False),
    "Ancient Greek Musical Notation": (0x1D200, 0x1D24F, False),
    "Kaktovik Numerals": (0x1D2C0, 0x1D2DF, False),
    "Mayan Numerals": (0x1D2E0, 0x1D2FF, False),
    "Tai Xuan Jing Symbols": (0x1D300, 0x1D35F, False),
    "Counting Rod Numerals": (0x1D360, 0x1D37F, False),
    "Mathematical Alphanumeric Symbols": (0x1D400, 0x1D7FF, False),
    "Sutton SignWriting": (0x1D800, 0x1DAAF, False),
    "Latin Extended-G": (0x1DF00, 0x1DFFF, False),
    "Glagolitic Supplement": (0x1E000, 0x1E02F, False),
    "Cyrillic Extended-D": (0x1E030, 0x1E08F, False),
    "Nyiakeng Puachue Hmong": (0x1E100, 0x1E14F, False),
    "Toto": (0x1E290, 0x1E2BF, False),
    "Wancho": (0x1E2C0, 0x1E2FF, False),
    "Nag Mundari": (0x1E4D0, 0x1E4FF, False),
    "Ol Onal": (0x1E5D0, 0x1E5FF, False),
    "Ethiopic Extended-B": (0x1E7E0, 0x1E7FF, False),
    "Mende Kikakui": (0x1E800, 0x1E8DF, False),
    "Adlam": (0x1E900, 0x1E95F, False),
    "Indic Siyaq Numbers": (0x1EC70, 0x1ECBF, False),
    "Ottoman Siyaq Numbers": (0x1ED00, 0x1ED4F, False),
    "Arabic Mathematical Alphabetic Symbols": (0x1EE00, 0x1EEFF, False),
    "Mahjong Tiles": (0x1F000, 0x1F02F, False),
    "Domino Tiles": (0x1F030, 0x1F09F, False),
    "Playing Cards": (0x1F0A0, 0x1F0FF, False),
    "Enclosed Alphanumeric Supplement": (0x1F100, 0x1F1FF, False),
    "Enclosed Ideographic Supplement": (0x1F200, 0x1F2FF, False),
    "Miscellaneous Symbols and Pictographs": (0x1F300, 0x1F5FF, False),
    "Emoticons": (0x1F600, 0x1F64F, False),
    "Ornamental Dingbats": (0x1F650, 0x1F67F, False),
    "Transport and Map Symbols": (0x1F680, 0x1F6FF, False),
    "Alchemical Symbols": (0x1F700, 0x1F77F, False),
    "Geometric Shapes Extended": (0x1F780, 0x1F7FF, False),
    "Supplemental Arrows-C": (0x1F800, 0x1F8FF, False),
    "Supplemental Symbols and Pictographs": (0x1F900, 0x1F9FF, False),
    "Chess Symbols": (0x1FA00, 0x1FA6F, False),
    "Symbols and Pictographs Extended-A": (0x1FA70, 0x1FAFF, False),
    "Symbols for Legacy Computing": (0x1FB00, 0x1FBFF, False),
    "CJK Unified Ideographs Extension B": (0x20000, 0x2A6DF, False),
    "CJK Unified Ideographs Extension C": (0x2A700, 0x2B73F, False),
    "CJK Unified Ideographs Extension D": (0x2B740, 0x2B81F, False),
    "CJK Unified Ideographs Extension E": (0x2B820, 0x2CEAF, False),
    "CJK Unified Ideographs Extension F": (0x2CEB0, 0x2EBEF, False),
    "CJK Unified Ideographs Extension I": (0x2EBF0, 0x2EE5F, False),
    "CJK Compatibility Ideographs Supplement": (0x2F800, 0x2FA1F, False),
    "CJK Unified Ideographs Extension G": (0x30000, 0x3134F, False),
    "CJK Unified Ideographs Extension H": (0x31350, 0x323AF, False),
    "Tags": (0xE0000, 0xE007F, False),
    "Variation Selectors Supplement": (0xE0100, 0xE01EF, False),
    "Supplementary Private Use Area-A": (0xF0000, 0xFFFFF, False),
    "Supplementary Private Use Area-B": (0x100000, 0x10FFFF, False),
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

_unicode_names: dict[str, list[str]] = {}
