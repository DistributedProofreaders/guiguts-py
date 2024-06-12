"""Miscellaneous dialogs."""

import tkinter as tk
from tkinter import ttk

import regex as re

from guiguts.preferences import (
    PrefKey,
    PersistentBoolean,
    PersistentInt,
    PersistentString,
)
from guiguts.utilities import is_mac
from guiguts.widgets import (
    ToplevelDialog,
    ToolTip,
    insert_in_focus_widget,
    OkApplyCancelDialog,
)


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
        ttk.Checkbutton(
            appearance_frame,
            text="Display Line Numbers",
            variable=PersistentBoolean(PrefKey.LINE_NUMBERS),
        ).grid(column=0, row=3, sticky="NEW", pady=5)
        ttk.Checkbutton(
            appearance_frame,
            text="Automatically show current page image",
            variable=PersistentBoolean(PrefKey.AUTO_IMAGE),
        ).grid(column=0, row=4, sticky="NEW", pady=5)
        bell_frame = ttk.Frame(appearance_frame)
        bell_frame.grid(column=0, row=5, sticky="NEW", pady=(5, 0))
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


class ComposeSequenceDialog(OkApplyCancelDialog):
    """Dialog to enter Compose Sequences."""

    def __init__(self) -> None:
        """Initialize compose sequence dialog."""
        super().__init__("Compose Sequence", resize_x=False, resize_y=False)
        ttk.Label(self.top_frame, text="Compose: ").grid(column=0, row=0, sticky="NSEW")
        self.string = tk.StringVar()
        entry = ttk.Entry(self.top_frame, textvariable=self.string, name="entry1")
        entry.grid(column=1, row=0, sticky="NSEW")
        # In tkinter, binding order is widget, class, toplevel, all
        # Swap first two, so that class binding has time to set textvariable
        # before the widget binding below is executed.
        bindings = entry.bindtags()
        entry.bindtags((bindings[1], bindings[0], bindings[2], bindings[3]))
        entry.bind("<Key>", lambda _event: self.interpret_and_insert())
        entry.focus()

    def apply_changes(self) -> bool:
        """Overridden function called when Apply/OK buttons are pressed.

        Call to attempt to interpret compose sequence

        Returns:
            Always returns True, meaning OK button (or Return key) will close dialog.
        """
        self.interpret_and_insert(force=True)
        self.string.set("")
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
        # Allow 0x, \x, x or U+ as optional prefix to hex Unicode ordinal
        if match := re.fullmatch(
            r"(0x|\\x|x|U\+)?([0-9a-f]{4})", sequence, re.IGNORECASE
        ):
            # If 4 hex digits, it's complete
            char = chr(int(match[2], 16))
        elif force:
            if match := re.fullmatch(
                r"(0x|\\x|x|U\+)?([0-9a-fA-F]{2,4})", sequence, re.IGNORECASE
            ):
                # Or user can force conversion with fewer than 4 hex digits
                char = chr(int(match[2], 16))
            elif match := re.fullmatch(r"#(\d{2,})", sequence):
                # Or specify in decimal following '#' character
                char = chr(int(match[1]))
        # Unprintable characters shouldn't be inserted
        if not char or not char.isprintable():
            return
        insert_in_focus_widget(char)
        if not force:
            self.destroy()
