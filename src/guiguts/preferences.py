"""Handle preferences"""

import copy
from enum import StrEnum, auto
import json
import logging
import os
import tkinter as tk
from typing import Any, Callable

from guiguts.utilities import is_x11, is_windows, called_from_test, load_dict_from_json

if is_windows():
    from win32com.shell import shell, shellcon  # type: ignore # pylint: disable=import-error, no-name-in-module


logger = logging.getLogger(__package__)


class PrefKey(StrEnum):
    """Enum class to store preferences keys."""

    AUTO_IMAGE = auto()
    BELL_AUDIBLE = auto()
    BELL_VISUAL = auto()
    IMAGE_WINDOW_DOCKED = auto()
    RECENT_FILES = auto()
    LINE_NUMBERS = auto()
    ORDINAL_NAMES = auto()
    SEARCH_HISTORY = auto()
    REPLACE_HISTORY = auto()
    SEARCHDIALOG_REVERSE = auto()
    SEARCHDIALOG_MATCH_CASE = auto()
    SEARCHDIALOG_WHOLE_WORD = auto()
    SEARCHDIALOG_WRAP = auto()
    SEARCHDIALOG_REGEX = auto()
    SEARCHDIALOG_MULTI_REPLACE = auto()
    WFDIALOG_SUSPECTS_ONLY = auto()
    WFDIALOG_IGNORE_CASE = auto()
    WFDIALOG_DISPLAY_TYPE = auto()
    WFDIALOG_SORT_TYPE = auto()
    WFDIALOG_ITALIC_THRESHOLD = auto()
    WFDIALOG_REGEX = auto()
    CHECKERDIALOG_SORT_TYPE_DICT = auto()
    CHECKERDIALOG_SUSPECTS_ONLY_DICT = auto()
    DIALOG_GEOMETRY = auto()
    ROOT_GEOMETRY = auto()
    ROOT_GEOMETRY_STATE = auto()
    DEFAULT_LANGUAGES = auto()
    JEEBIES_PARANOIA_LEVEL = auto()
    LEVENSHTEIN_DISTANCE = auto()
    FOOTNOTE_INDEX_STYLE = auto()
    WRAP_LEFT_MARGIN = auto()
    WRAP_RIGHT_MARGIN = auto()
    WRAP_BLOCKQUOTE_INDENT = auto()
    WRAP_BLOCKQUOTE_RIGHT_MARGIN = auto()
    WRAP_BLOCK_INDENT = auto()
    WRAP_POETRY_INDENT = auto()
    WRAP_INDEX_MAIN_MARGIN = auto()
    WRAP_INDEX_WRAP_MARGIN = auto()
    WRAP_INDEX_RIGHT_MARGIN = auto()
    TEXT_MARKUP_ITALIC = auto()
    TEXT_MARKUP_BOLD = auto()
    TEXT_MARKUP_SMALLCAPS = auto()
    TEXT_MARKUP_GESPERRT = auto()
    TEXT_MARKUP_FONT = auto()
    PAGESEP_AUTO_TYPE = auto()
    THEME_NAME = auto()
    TEAROFF_MENUS = auto()
    COMPOSE_HISTORY = auto()
    TEXT_FONT_FAMILY = auto()
    TEXT_FONT_SIZE = auto()
    SPELL_THRESHOLD = auto()
    UNMATCHED_NESTABLE = auto()
    UNICODE_BLOCK = auto()
    UNICODE_SEARCH_HISTORY = auto()
    SPLIT_TEXT_WINDOW = auto()
    SPLIT_TEXT_SASH_COORD = auto()
    IMAGE_INVERT = auto()
    IMAGE_FLOAT_GEOMETRY = auto()
    IMAGE_DOCK_SASH_COORD = auto()
    IMAGE_SCALE_FACTOR = auto()
    IMAGE_VIEWER_ALERT = auto()
    IMAGE_VIEWER_HI_CONTRAST = auto()
    IMAGE_WINDOW_SHOW = auto()
    IMAGE_VIEWER_EXTERNAL = auto()
    IMAGE_VIEWER_EXTERNAL_PATH = auto()
    IMAGE_VIEWER_INTERNAL = auto()
    SCANNOS_FILENAME = auto()
    SCANNOS_HISTORY = auto()
    HIGHLIGHT_QUOTBRAC = auto()
    HIGHLIGHT_HTML_TAGS = auto()
    COLUMN_NUMBERS = auto()
    HTML_ITALIC_MARKUP = auto()
    HTML_BOLD_MARKUP = auto()
    HTML_GESPERRT_MARKUP = auto()
    HTML_FONT_MARKUP = auto()
    HTML_UNDERLINE_MARKUP = auto()
    HTML_SHOW_PAGE_NUMBERS = auto()
    HTML_IMAGE_UNIT = auto()
    HTML_IMAGE_OVERRIDE_EPUB = auto()
    HTML_IMAGE_ALIGNMENT = auto()
    HIGHLIGHT_PROOFERCOMMENT = auto()


class Preferences:
    """Handle setting/getting/saving/loading/defaulting preferences.

    Call `add` to create/define each preference, giving its default value,
    and optionally a callback function, e.g. if loading or setting a pref
    requires a UI change or other side effect. Once UI is initially ready,
    call `run_callbacks` to deal with all required side effects from loading
    the GGprefs file.

    Load/Save preferences in temporary file when testing.

    Attributes:
        dict: dictionary of values for prefs.
        defaults: dictionary of values for defaults.
        callbacks: dictionary of callbacks - typically a function to
          deal with side effect of loading/setting the pref, which will be
          called after all prefs have been loaded and UI is ready. Also called
          each time pref is changed.
        persistent_vars: dictionary of Persistent variables (inherit from Tk.Variable),
          stored here so the variable can be set whenever the pref is set. The Persistent
          classes below handle the reverse, i.e. they set the pref whenever the variable
          is set.
        prefsdir: directory containing user prefs & data files
    """

    def __init__(self) -> None:
        """Initialize by loading from JSON file."""
        self.dict: dict[PrefKey, Any] = {}
        self.defaults: dict[PrefKey, Any] = {}
        self.callbacks: dict[PrefKey, Callable[[Any], None]] = {}
        self.persistent_vars: dict[PrefKey, tk.Variable] = {}
        if is_x11():
            self.prefsdir = os.path.join(os.path.expanduser("~"), ".ggpreferences")
        elif is_windows():
            self.prefsdir = os.path.join(
                shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, 0, 0), "GGprefs"
            )
        else:
            self.prefsdir = os.path.join(
                os.path.expanduser("~"), "Documents", "GGprefs"
            )
        # If testing, use a test prefs file so tests and normal running do not interact
        if called_from_test:
            prefs_name = "GGprefs_test.json"
        else:
            prefs_name = "GGprefs.json"
        self.prefsfile = os.path.join(self.prefsdir, prefs_name)

        self._remove_test_prefs_file()
        self.permanent = False

    def get(self, key: PrefKey) -> Any:
        """Get preference value using key.

        Args:
            key: Name of preference.

        Returns:
            Preferences value; default for ``key`` if no preference set;
            ``None`` if no default for ``key``.
        """
        return copy.deepcopy(self.dict.get(key, self.defaults.get(key)))

    def set(self, key: PrefKey, value: Any) -> None:
        """Set preference value and save to file if value has changed.

        If key has an associated callback, call it.

        Args:
            key: Name of preference.
            value: Value for preference.
        """
        if self.get(key) == value:
            return
        self.dict[key] = value
        self.save()
        if key in self.callbacks:
            self.callbacks[key](value)
        if key in self.persistent_vars:
            self.persistent_vars[key].set(value)

    def toggle(self, key: PrefKey) -> None:
        """Toggle the value of a boolean preference.

        Args:
            key: Name of preference.
        """
        self.set(key, not self.get(key))

    def __del__(self) -> None:
        """Remove any test prefs file when finished."""
        self._remove_test_prefs_file()

    def set_default(self, key: PrefKey, default: Any) -> None:
        """Set default preference value.

        Args:
            key: Name of preference.
            default: Default value for preference.
        """
        self.defaults[key] = default

    def get_default(self, key: PrefKey) -> Any:
        """Get default preference value.

        Args:
            key: Name of preference.

        Returns:
            Default value for preference; ``None`` (with assertion) if no default for ``key``
        """
        assert key in self.defaults  # Raise assertion if no default set
        try:
            return self.defaults[key]
        except KeyError:
            return None

    def set_callback(self, key: PrefKey, callback: Callable[[Any], None]) -> None:
        """Add a callback for preference. Callback will be run when all
          prefs are loaded and UI is ready.

        Args:
            key: Name of preference.
            callback: Function to call if side effect required, e.g. to
              update UI to reflect a setting.
        """
        self.callbacks[key] = callback

    def link_persistent_var(self, key: PrefKey, var: tk.Variable) -> None:
        """Link a persistent variable to a preference. Variable will be set
        whenever the preference gets set.

        Args:
            key: Name of preference.
            var: Persistent variable to link to preference.
        """
        self.persistent_vars[key] = var

    def keys(self) -> list[PrefKey]:
        """Return list of preferences keys.

        Also includes preferences that have not been set, so only exist
        as defaults."""
        return list(set(list(self.dict.keys()) + list(self.defaults.keys())))

    def set_permanent(self, permanent: bool) -> None:
        """Set whether prefs should be loaded from and saved to Prefs file
        for permanent storage.

        Args:
            permanent: True if Prefs file should be used.
        """
        self.permanent = permanent

    def save(self) -> None:
        """Save preferences dictionary to JSON file."""

        if not self.permanent:
            return

        # Create Prefs dir (including any parent dirs) if needed
        try:
            os.makedirs(self.prefsdir, exist_ok=True)
        except OSError:
            logger.error(f"Unable to create {self.prefsdir}")
            return

        try:
            with open(self.prefsfile, "w", encoding="utf-8") as fp:
                json.dump(self.dict, fp, indent=2, ensure_ascii=False)
        except OSError:
            logger.error(f"Unable to save preferences to {self.prefsfile}")

    def load(self) -> None:
        """Load dictionary from JSON file, and use PrefKeys
        to store values in preferences dictionary."""

        if not self.permanent:
            return

        self.dict = {}
        if loaded_dict := load_dict_from_json(self.prefsfile):
            for key, value in loaded_dict.items():
                try:
                    self.dict[PrefKey(key)] = value
                except ValueError:
                    logger.debug(f"'{key}' is not a valid PrefKey - ignored")

    def run_callbacks(self) -> None:
        """Run all defined callbacks, passing value as argument.

        Should be called after prefs are loaded and UI is ready"""
        for key, callback in self.callbacks.items():
            if callback is not None:
                callback(self.get(key))

    def _remove_test_prefs_file(self) -> None:
        """Remove temporary JSON file used for prefs during testing."""
        if called_from_test and os.path.exists(self.prefsfile):
            os.remove(self.prefsfile)


class PersistentBoolean(tk.BooleanVar):
    """Tk boolean variable whose value is stored in user prefs file.

    Note that, like all prefs, the default value must be set in
    `initialize_preferences`
    """

    def __init__(self, prefs_key: PrefKey) -> None:
        """Initialize persistent boolean.

        Args:
            prefs_key: Preferences key associated with the variable.
        """
        super().__init__(value=preferences.get(prefs_key))
        self.trace_add("write", lambda *_args: preferences.set(prefs_key, self.get()))
        preferences.link_persistent_var(prefs_key, self)


class PersistentInt(tk.IntVar):
    """Tk integer variable whose value is stored in user prefs file.

    Note that, like all prefs, the default value must be set in
    `initialize_preferences`
    """

    def __init__(self, prefs_key: PrefKey) -> None:
        """Initialize persistent boolean.

        Args:
            prefs_key: Preferences key associated with the variable.
        """
        super().__init__(value=preferences.get(prefs_key))

        def set_pref(*_args: Any) -> None:
            """Set the preference if the IntVar holds an int.

            If it's not, e.g. because the entry field it is linked to is empty,
            or contains non-digits, a tk exception occurs, and we don't set the pref.
            """
            try:
                preferences.set(prefs_key, self.get())
            except tk.TclError:
                pass

        self.trace_add("write", set_pref)
        preferences.link_persistent_var(prefs_key, self)


class PersistentString(tk.StringVar):
    """Tk string variable whose value is stored in user prefs file.

    Note that, like all prefs, the default value must be set in
    `initialize_preferences`
    """

    def __init__(self, prefs_key: PrefKey) -> None:
        """Initialize persistent string.

        Args:
            prefs_key: Preferences key associated with the variable.
        """
        super().__init__(value=preferences.get(prefs_key))
        self.trace_add("write", lambda *_args: preferences.set(prefs_key, self.get()))
        preferences.link_persistent_var(prefs_key, self)


preferences = Preferences()
