"""Miscellaneous dialogs."""

from tkinter import ttk

from guiguts.preferences import PrefKey, PersistentBoolean
from guiguts.widgets import ToplevelDialog


class PreferencesDialog(ToplevelDialog):
    """A dialog that displays settings/preferences."""

    def __init__(self) -> None:
        """Initialize preferences dialog."""
        super().__init__("Settings", resize_y=False)
        self.minsize(250, 10)

        # Appearance
        appearance_frame = ttk.LabelFrame(self.top_frame, text="Appearance", padding=10)
        appearance_frame.grid(column=0, row=0, sticky="NSEW")
        ttk.Checkbutton(
            appearance_frame,
            text="Display Line Numbers",
            variable=PersistentBoolean(PrefKey.LINE_NUMBERS),
        ).grid(column=0, row=0, sticky="NEW")
        ttk.Checkbutton(
            appearance_frame,
            text="Automatically show current page image",
            variable=PersistentBoolean(PrefKey.AUTO_IMAGE),
        ).grid(column=0, row=1, sticky="NEW")
        bell_frame = ttk.Frame(appearance_frame)
        bell_frame.grid(column=0, row=2, sticky="NEW")
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

        # Processing tab
        processing_frame = ttk.LabelFrame(self.top_frame, text="Processing", padding=10)
        processing_frame.grid(column=0, row=1, sticky="NSEW", pady=(10, 0))
        ttk.Label(processing_frame, text="Nothing to see here yet").grid(
            column=0, row=0, sticky="NEW"
        )
