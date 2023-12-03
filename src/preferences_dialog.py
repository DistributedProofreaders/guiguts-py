"""Dialog to handle preferences"""

import tkinter as tk
from tkinter import simpledialog

from preferences import preferences


class PreferencesDialog(simpledialog.Dialog):
    """A Tk simpledialog that allows the user to view/edit all preferences.

    Attributes:
        labels: Dictionary of ``Label`` widgets showing preference keys.
        entries: Dictionary of ``Entry`` widgets showing preference values.
    """

    def __init__(self, parent):
        """Initialize ``labels`` and ``entries`` to empty dictionaries."""
        self.labels = {}
        self.entries = {}
        super().__init__(parent, "Set Preferences")

    def body(self, frame):
        """Override default to construct widgets needed to show all
        preferences keys/values.

        Note: Does not cope with non-string values at the moment, since values
        are converted to string for display in dialog.
        """
        for row, key in enumerate(preferences.keys()):
            self.labels[key] = tk.Label(frame, text=key)
            self.labels[key].grid(row=row, column=0)
            self.entries[key] = tk.Entry(frame, width=12)
            self.entries[key].insert(tk.END, str(preferences.get(key)))
            self.entries[key].grid(row=row, column=1)
        return frame

    def buttonbox(self):
        """Override default to set up OK and Cancel buttons."""
        self.ok_button = tk.Button(self, text="OK", width=5, command=self.ok_pressed)
        self.ok_button.pack(side="left", padx=5, pady=5)
        cancel_button = tk.Button(
            self, text="Cancel", width=5, command=self.cancel_pressed
        )
        cancel_button.pack(side="right", padx=5, pady=5)
        self.bind("<Return>", lambda event: self.ok_pressed())
        self.bind("<Escape>", lambda event: self.cancel_pressed())

    def ok_pressed(self):
        """Update all preferences from the corresponding ``Entry``` widget.

        Does not cope with non-string values at the moment, since get()
        always returns a string.
        """
        for key in preferences.keys():
            preferences.set(key, self.entries[key].get())
        preferences.save()
        self.destroy()

    def cancel_pressed(self):
        """Destroy dialog."""
        self.destroy()
