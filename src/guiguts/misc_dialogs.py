"""Miscellaneous dialogs."""

from tkinter import ttk

from guiguts.preferences import (
    PrefKey,
    PersistentBoolean,
    PersistentInt,
    PersistentString,
)
from guiguts.widgets import ToplevelDialog, ToolTip


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
        ttk.Checkbutton(
            appearance_frame,
            text="Use Tear-Off Menus (requires restart)",
            variable=PersistentBoolean(PrefKey.TEAROFF_MENUS),
        ).grid(column=0, row=2, sticky="NEW", pady=5)
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
            0, "Left Margin:", PrefKey.WRAP_LEFT_MARGIN, "Left margin for normal text."
        )
        add_label_spinbox(
            1,
            "Right Margin:",
            PrefKey.WRAP_RIGHT_MARGIN,
            "Right margin for normal text.",
        )
        add_label_spinbox(
            2,
            "Blockquote Indent:",
            PrefKey.WRAP_BLOCKQUOTE_INDENT,
            "Extra indent for each level of blockquotes.",
        )
        add_label_spinbox(
            3,
            "Blockquote Right Margin:",
            PrefKey.WRAP_BLOCKQUOTE_RIGHT_MARGIN,
            "Right margin for blockquotes.",
        )
        add_label_spinbox(
            4,
            "Block Indent:",
            PrefKey.WRAP_BLOCK_INDENT,
            "Indent for /*, /P, /L blocks.",
        )
        add_label_spinbox(
            5,
            "Poetry Indent:",
            PrefKey.WRAP_POETRY_INDENT,
            "Indent for /P poetry blocks.",
        )
        add_label_spinbox(
            6,
            "Index Main Entry Margin:",
            PrefKey.WRAP_INDEX_MAIN_MARGIN,
            "Indent for main entries in index - sub-entries retain their indent relative to this.",
        )
        add_label_spinbox(
            8,
            "Index Wrap Margin:",
            PrefKey.WRAP_INDEX_WRAP_MARGIN,
            "Left margin for all lines rewrapped in index.",
        )
        add_label_spinbox(
            9,
            "Index Right Margin:",
            PrefKey.WRAP_INDEX_RIGHT_MARGIN,
            "Right margin for index entries.",
        )
