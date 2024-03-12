"""Handle preferences"""

import copy
import json
import logging
import os
import tkinter as tk
from typing import Any, Callable

from guiguts.utilities import is_x11, _called_from_test, load_dict_from_json


logger = logging.getLogger(__package__)


class Preferences:
    """Handle setting/getting/saving/loading/defaulting preferences.

    Call `add` to create/define each preference, giving its default value,
    and optionally a callback function, e.g. if loading a pref requires an
    initial UI setting. Once UI is ready, call `run_callbacks` to deal with
    all required side effects.

    Load/Save preferences in temporary file when testing.

    TODO: Currently 3 dictionaries: dict is the one loaded/save in JSON file.
    Consider whether one dictionary with each item consisting of default, value
    & callback would be better/safer.
    Consider whether exception should be raised if unknown key is used, rather
    than just returning None. Would probably need explicit call to load, rather
    than loading on instantiation. Also, may be less forward/backward compatible
    when new preferences are added in future releases.
    Consider whether get/set should be typed, to trap error if preference is
    expected to be a string, but is an int, for example.

    Attributes:
        dict: dictionary of values for prefs.
        defaults: dictionary of values for defaults.
        callbacks: dictionary of callbacks - typically a function to
          deal with initial side effect of loading the pref, which will be
          called after all prefs have been loaded and UI is ready. Not called
          each time pref is changed.
        prefsdir: directory containing user prefs & data files
    """

    def __init__(self) -> None:
        """Initialize by loading from JSON file."""
        self.dict: dict[str, Any] = {}
        self.defaults: dict[str, Any] = {}
        self.callbacks: dict[str, Callable[[Any], None]] = {}
        if is_x11():
            self.prefsdir = os.path.join(os.path.expanduser("~"), ".ggpreferences")
        else:
            self.prefsdir = os.path.join(
                os.path.expanduser("~"), "Documents", "GGprefs"
            )
        # If testing, use a test prefs file so tests and normal running do not interact
        if _called_from_test:
            prefs_name = "GGprefs_test.json"
        else:
            prefs_name = "GGprefs.json"
        self.prefsfile = os.path.join(self.prefsdir, prefs_name)

        self._remove_test_prefs_file()

    def get(self, key: str) -> Any:
        """Get preference value using key.

        Args:
            key: Name of preference.

        Returns:
            Preferences value; default for ``key`` if no preference set;
            ``None`` if no default for ``key``.
        """
        return copy.deepcopy(self.dict.get(key, self.defaults.get(key)))

    def set(self, key: str, value: Any) -> None:
        """Set preference value and save to file if value has changed.

        Args:
            key: Name of preference.
            value: Value for preference.
        """
        if self.get(key) != value:
            self.dict[key] = value
            self.save()

    def __del__(self) -> None:
        """Remove any test prefs file when finished."""
        self._remove_test_prefs_file()

    def set_default(self, key: str, default: Any) -> None:
        """Set default preference value.

        Args:
            key: Name of preference.
            default: Default value for preference.
        """
        self.defaults[key] = default

    def get_default(self, key: str) -> Any:
        """Get default preference value.

        Args:
            key: Name of preference.

        Returns:
            Default value for preference; ``None`` if no default for ``key``
        """
        return self.defaults.get(key)

    def set_callback(self, key: str, callback: Callable[[Any], None]) -> None:
        """Add a callback for preference. Callback will be run when all
          prefs are loaded and UI is ready.

        Args:
            key: Name of preference.
            callback: Function to call if side effect required, e.g. to
              update UI to reflect a setting.
        """
        self.callbacks[key] = callback

    def keys(self) -> list[str]:
        """Return list of preferences keys.

        Also includes preferences that have not been set, so only exist
        as defaults."""
        return list(set(list(self.dict.keys()) + list(self.defaults.keys())))

    def save(self) -> None:
        """Save preferences dictionary to JSON file."""
        if not os.path.isdir(self.prefsdir):
            os.mkdir(self.prefsdir)
        with open(self.prefsfile, "w") as fp:
            json.dump(self.dict, fp, indent=2, ensure_ascii=False)

    def load(self) -> None:
        """Load preferences dictionary from JSON file."""
        prefs_dict = load_dict_from_json(self.prefsfile)
        if prefs_dict is not None:
            self.dict = prefs_dict

    def run_callbacks(self) -> None:
        """Run all defined callbacks, passing value as argument.

        Should be called after prefs are loaded and UI is ready"""
        for key in self.callbacks.keys():
            callback = self.callbacks[key]
            if callback is not None:
                callback(self.get(key))

    def _remove_test_prefs_file(self) -> None:
        """Remove temporary JSON file used for prefs during testing."""
        if _called_from_test and os.path.exists(self.prefsfile):
            os.remove(self.prefsfile)


class PersistentBoolean(tk.BooleanVar):
    """Tk boolean variable whose value is stored in user prefs file.

    Note that, like all prefs, the default value must be set in
    `initialize_preferences`
    """

    def __init__(self, prefs_key: str) -> None:
        """Initialize persistent boolean.

        Args:
            prefs_key: Preferences key associated with the variable.
        """
        super().__init__(value=preferences.get(prefs_key))
        self.trace_add("write", lambda *args: preferences.set(prefs_key, self.get()))


preferences = Preferences()
