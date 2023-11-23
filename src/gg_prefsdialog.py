# GGprefsdialog class is a ttk simple dialog

import tkinter as tk

from gg_prefs import GGprefs


class GGprefsdialog(tk.simpledialog.Dialog):
    def __init__(self, parent, title):
        self.labels = {}
        self.entries = {}
        super().__init__(parent, title)

    # Show all prefs keys/values
    def body(self, frame):
        # Does not cope with non-string values,
        # since converted to string for display in dialog
        for row, key in enumerate(GGprefs().keys()):
            self.labels[key] = tk.Label(frame, text=key)
            self.labels[key].grid(row=row, column=0)
            self.entries[key] = tk.Entry(frame, width=12)
            self.entries[key].insert(tk.END, str(GGprefs().get(key)))
            self.entries[key].grid(row=row, column=1)
        return frame

    def ok_pressed(self):
        # Does not cope with non-string values,
        # since get() always return string
        for key in GGprefs().keys():
            GGprefs().set(key, self.entries[key].get())
        GGprefs().save()
        self.destroy()

    def cancel_pressed(self):
        self.destroy()

    def buttonbox(self):
        self.ok_button = tk.Button(self, text="OK", width=5, command=self.ok_pressed)
        self.ok_button.pack(side="left")
        cancel_button = tk.Button(
            self, text="Cancel", width=5, command=self.cancel_pressed
        )
        cancel_button.pack(side="right")
        self.bind("<Return>", lambda event: self.ok_pressed())
        self.bind("<Escape>", lambda event: self.cancel_pressed())
