"""Handle preferences"""

import json
import os

from utilities import is_x11


class Preferences:
    """Handle setting/getting/saving/loading/defaulting preferences."""

    def __init__(self):
        """Initialize by loading from JSON file."""
        self.dict = {}
        self.defaults = {}
        if is_x11():
            self.prefsdir = os.path.join(os.path.expanduser("~"), ".ggpreferences")
        else:
            self.prefsdir = os.path.join(
                os.path.expanduser("~"), "Documents", "Preferences"
            )
        self.prefsfile = os.path.join(self.prefsdir, "Preferences.json")
        self.load()

    def set_default(self, key, default):
        """Set default preference value

        Args:
            key: Name of preference.
            default: Default value for preference.
        """
        self.defaults[key] = default

    def get_default(self, key):
        """Get default preference value

        Args:
            key: Name of preference.

        Returns:
            Default value for preference; ``None`` if no default for ``key``
        """
        return self.defaults.get(key)

    def set(self, key, value):
        """Set preference value and save to file

        Args:
            key: Name of preference.
            value: Value for preference.
        """
        self.dict[key] = value
        self.save()

    def get(self, key):
        """Get default preference value using key

        Args:
            key: Name of preference.

        Returns:
            Preferences value; default for ``key`` if no preference set;
            ``None`` if no default for ``key``.
        """
        return self.dict.get(key, self.get_default(key))

    def keys(self):
        """Return list of preferences keys"""
        return self.dict.keys()

    def save(self):
        """Save preferences dictionary to JSON file"""
        if not os.path.isdir(self.prefsdir):
            os.mkdir(self.prefsdir)
        with open(self.prefsfile, "w") as fp:
            json.dump(self.dict, fp, indent=2)

    def load(self):
        """Load preferences dictionary from JSON file"""
        if os.path.isfile(self.prefsfile):
            with open(self.prefsfile, "r") as fp:
                self.dict = json.load(fp)


preferences = Preferences()
