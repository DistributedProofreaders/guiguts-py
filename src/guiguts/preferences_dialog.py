"""Dialog to handle preferences"""

import tkinter as tk
from tkinter import ttk

from guiguts.dialogs import OkCancelDialog
from guiguts.preferences import preferences


class PreferencesDialog(OkCancelDialog):
    """A Tk simpledialog that allows the user to view/edit all preferences.

    Attributes:
        labels: Dictionary of ``Label`` widgets showing preference keys.
        entries: Dictionary of ``Entry`` widgets showing preference values.
    """

    def __init__(self, parent: tk.Tk) -> None:
        """Initialize ``labels`` and ``entries`` to empty dictionaries."""
        self.labels: dict[str, ttk.Label] = {}
        self.entries: dict[str, ttk.Entry] = {}
        super().__init__(parent, "Set Preferences")

    def body(self, frame: tk.Frame) -> tk.Frame:
        """Override default to construct widgets needed to show all
        preferences keys/values.

        Note: Does not cope with non-string values at the moment, since values
        are converted to string for display in dialog.
        """
        frame["borderwidth"] = 2
        frame["relief"] = "groove"
        frame["padx"] = 5
        frame["pady"] = 5
        for row, key in enumerate(preferences.keys()):
            self.labels[key] = ttk.Label(frame, text=key)
            self.labels[key].grid(row=row, column=0)
            self.entries[key] = ttk.Entry(frame, width=20)
            self.entries[key].insert(tk.END, str(preferences.get(key)))
            self.entries[key].grid(row=row, column=1)
        return frame

    def ok_press_complete(self) -> bool:
        """Overridden to update all preferences from the corresponding
        ``Entry``` widget.

        Does not cope with non-string values at the moment, since get()
        always returns a string.
        """
        for key in preferences.keys():
            preferences.set(key, self.entries[key].get())
        preferences.save()
        return True
