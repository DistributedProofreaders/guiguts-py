# Singleton class to handle setting/getting/saving/loading/defaulting preferences

import json
import os
import tkinter as tk

from tk_utilities import isX11


class Preferences:
    _self = None

    def __new__(cls):
        if cls._self is None:
            cls._self = super().__new__(cls)
            cls._self.initialize()
        return cls._self

    #
    # Initialize prefs by loading from file
    def initialize(self):
        self.dict = {}
        self.defaults = {}
        if isX11():
            self.prefsdir = os.path.join(os.path.expanduser("~"), ".Preferences")
        else:
            self.prefsdir = os.path.join(
                os.path.expanduser("~"), "Documents", "Preferences"
            )
        self.prefsfile = os.path.join(self.prefsdir, "Preferences.json")
        self.load()

    #
    # Set default prefs value using key
    # Default is returned if `get` fails to find key in dictionary
    def setDefault(self, key, default):
        self.defaults[key] = default

    #
    # Get default prefs value using key
    # None is returned if no default is set
    def getDefault(self, key):
        return self.defaults.get(key)

    #
    # Set prefs value using key
    # For now, always save when new value set
    def set(self, key, value):
        self.dict[key] = value
        self.save()

    #
    # Get prefs value; default if key not found; None if no default
    def get(self, key):
        return self.dict.get(key, self.getDefault(key))

    #
    # Get list of prefs keys
    def keys(self):
        return self.dict.keys()

    # Save prefs dictionary to JSON file
    def save(self):
        if not os.path.isdir(self.prefsdir):
            os.mkdir(self.prefsdir)
        with open(self.prefsfile, "w") as fp:
            json.dump(self.dict, fp, indent=2)

    # Load prefs dictionary from JSON file
    def load(self):
        if os.path.isfile(self.prefsfile):
            with open(self.prefsfile, "r") as fp:
                self.dict = json.load(fp)


# PreferencesDialog class is a tk simple dialog


class PreferencesDialog(tk.simpledialog.Dialog):
    def __init__(self, parent, title):
        self.labels = {}
        self.entries = {}
        super().__init__(parent, title)

    # Show all prefs keys/values
    def body(self, frame):
        # Does not cope with non-string values,
        # since converted to string for display in dialog
        for row, key in enumerate(Preferences().keys()):
            self.labels[key] = tk.Label(frame, text=key)
            self.labels[key].grid(row=row, column=0)
            self.entries[key] = tk.Entry(frame, width=12)
            self.entries[key].insert(tk.END, str(Preferences().get(key)))
            self.entries[key].grid(row=row, column=1)
        return frame

    def ok_pressed(self):
        # Does not cope with non-string values,
        # since get() always return string
        for key in Preferences().keys():
            Preferences().set(key, self.entries[key].get())
        Preferences().save()
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
