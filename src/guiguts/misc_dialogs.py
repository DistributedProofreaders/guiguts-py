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
        self.notebook = ttk.Notebook(self.top_frame, takefocus=False)
        self.notebook.grid(column=0, row=0, sticky="NSEW")
        self.notebook.enable_traversal()

        # Appearance tab
        appearance_frame = ttk.Frame(self.notebook, padding=10)
        ttk.Checkbutton(
            appearance_frame,
            text="Display Line Numbers",
            variable=PersistentBoolean(PrefKey.LINENUMBERS),
        ).grid(column=0, row=0, sticky="NEW")
        ttk.Checkbutton(
            appearance_frame,
            text="Automatically show current page image",
            variable=PersistentBoolean(PrefKey.AUTOIMAGE),
        ).grid(column=0, row=1, sticky="NEW")
        bell_frame = ttk.Frame(appearance_frame)
        bell_frame.grid(column=0, row=2, sticky="NEW")
        ttk.Label(bell_frame, text="Warning bell: ").grid(column=0, row=0, sticky="NEW")
        ttk.Checkbutton(
            bell_frame,
            text="Audible",
            variable=PersistentBoolean(PrefKey.BELLAUDIBLE),
        ).grid(column=1, row=0, sticky="NEW", padx=20)
        ttk.Checkbutton(
            bell_frame,
            text="Visual",
            variable=PersistentBoolean(PrefKey.BELLVISUAL),
        ).grid(column=2, row=0, sticky="NEW")
        self.notebook.add(appearance_frame, text="Appearance", underline=0)

        # Processing tab
        processing_frame = ttk.Frame(self.notebook, padding=10)
        ttk.Label(processing_frame, text="Nothing to see here yet").grid(
            column=0, row=0, sticky="NEW"
        )
        self.notebook.add(processing_frame, text="Processing", underline=0)
