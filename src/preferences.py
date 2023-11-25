"""Handle preferences"""

import json
import os

from singleton import singleton
from tk_utilities import isX11


@singleton
class Preferences:
    """Singleton class to handle setting/getting/saving/loading/defaulting preferences"""

    #
    # Initialize prefs by loading from file
    def __init__(self):
        self.dict = {}
        self.defaults = {}
        if isX11():
            self.prefsdir = os.path.join(os.path.expanduser("~"), ".ggpreferences")
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
