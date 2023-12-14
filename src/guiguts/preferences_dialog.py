"""Dialog to handle preferences"""

import tkinter as tk
from tkinter import simpledialog, ttk

from guiguts.preferences import preferences


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
        frame["borderwidth"] = 2
        frame["relief"] = "groove"
        frame["padx"] = 5
        frame["pady"] = 5
        for row, key in enumerate(preferences.keys()):
            self.labels[key] = ttk.Label(frame, text=key)
            self.labels[key].grid(row=row, column=0)
            self.entries[key] = ttk.Entry(frame, width=20)
            self.entries[key].insert(tk.END, str(preferences[key]))
            self.entries[key].grid(row=row, column=1)
        return frame

    def buttonbox(self):
        """Override default to set up OK and Cancel buttons."""
        frame = ttk.Frame(self, padding=5)
        frame.pack()
        ok_button = ttk.Button(
            frame, text="OK", default="active", command=self.ok_pressed
        )
        ok_button.grid(column=1, row=1)
        cancel_button = ttk.Button(
            frame, text="Cancel", default="normal", command=self.cancel_pressed
        )
        cancel_button.grid(column=2, row=1)
        self.bind("<Return>", lambda event: self.ok_pressed())
        self.bind("<Escape>", lambda event: self.cancel_pressed())

    def ok_pressed(self):
        """Update all preferences from the corresponding ``Entry``` widget.

        Does not cope with non-string values at the moment, since get()
        always returns a string.
        """
        for key in preferences.keys():
            preferences[key] = self.entries[key].get()
        preferences.save()
        self.destroy()

    def cancel_pressed(self):
        """Destroy dialog."""
        self.destroy()
