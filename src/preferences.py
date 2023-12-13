"""Handle preferences"""

import json
import os

import utilities


class Preferences:
    """Handle setting/getting/saving/loading/defaulting preferences.

    Load/Save preferences in temporary file when testing."""

    def __init__(self):
        """Initialize by loading from JSON file."""
        self.dict = {}
        self.defaults = {}
        if utilities.is_x11():
            self.prefsdir = os.path.join(os.path.expanduser("~"), ".ggpreferences")
        else:
            self.prefsdir = os.path.join(
                os.path.expanduser("~"), "Documents", "GGprefs"
            )
        # If testing, use a test prefs file so tests and normal running do not interact
        if utilities._called_from_test:
            prefs_name = "GGprefs_test.json"
        else:
            prefs_name = "GGprefs.json"
        self.prefsfile = os.path.join(self.prefsdir, prefs_name)

        self._remove_test_prefs_file()
        self.load()

    def __getitem__(self, key):
        """Get preference value using key.

        Provides `value = preferences[key]`

        Args:
            key: Name of preference.

        Returns:
            Preferences value; default for ``key`` if no preference set;
            ``None`` if no default for ``key``.
        """
        return self.dict.get(key, self.get_default(key))

    def __setitem__(self, key, value):
        """Set preference value and save to file.

        Provides `preferences[key] = value`

        Args:
            key: Name of preference.
            value: Value for preference.
        """
        self.dict[key] = value
        self.save()

    def __del__(self):
        """Remove any test prefs file when finished."""
        self._remove_test_prefs_file()

    def set_default(self, key, default):
        """Set default preference value.

        Args:
            key: Name of preference.
            default: Default value for preference.
        """
        self.defaults[key] = default

    def get_default(self, key):
        """Get default preference value.

        Args:
            key: Name of preference.

        Returns:
            Default value for preference; ``None`` if no default for ``key``
        """
        return self.defaults.get(key)

    def keys(self):
        """Return list of preferences keys.

        Also includes preferences that have not been set, so only exist
        as defaults."""
        return list(set(list(self.dict.keys()) + list(self.defaults.keys())))

    def save(self):
        """Save preferences dictionary to JSON file."""
        if not os.path.isdir(self.prefsdir):
            os.mkdir(self.prefsdir)
        with open(self.prefsfile, "w") as fp:
            json.dump(self.dict, fp, indent=2)

    def load(self):
        """Load preferences dictionary from JSON file."""
        if os.path.isfile(self.prefsfile):
            with open(self.prefsfile, "r") as fp:
                self.dict = json.load(fp)

    def _remove_test_prefs_file(self):
        """Remove temporary JSON file used for prefs during testing."""
        if utilities._called_from_test and os.path.exists(self.prefsfile):
            os.remove(self.prefsfile)


preferences = Preferences()
