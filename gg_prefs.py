# Singleton class to handle setting/getting/saving/loading/defaulting preferences

import json
import os
import tkinter as tk

from gg_tkutils import isX11


class GGprefs:
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
            self.prefsdir = os.path.join(os.path.expanduser("~"), ".GGprefs")
        else:
            self.prefsdir = os.path.join(
                os.path.expanduser("~"), "Documents", "GGprefs"
            )
        self.prefsfile = os.path.join(self.prefsdir, "GGprefs.json")
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
        key = "mykey"
        if not os.path.isdir(self.prefsdir):
            os.mkdir(self.prefsdir)
        with open(self.prefsfile, "w") as fp:
            json.dump(self.dict, fp, indent=2)

    # Load prefs dictionary from JSON file
    def load(self):
        if os.path.isfile(self.prefsfile):
            with open(self.prefsfile, "r") as fp:
                self.dict = json.load(fp)
