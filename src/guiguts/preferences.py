"""Handle preferences"""

import copy
from enum import StrEnum, auto
import json
import logging
import os
import time
import tkinter as tk
from typing import Any, Callable, Optional

from guiguts.utilities import is_x11, is_windows, is_test, load_dict_from_json

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
    SEARCHDIALOG_MULTI_ROWS = auto()
    WFDIALOG_SUSPECTS_ONLY = auto()
    WFDIALOG_IGNORE_CASE = auto()
    WFDIALOG_DISPLAY_TYPE = auto()
    WFDIALOG_SORT_TYPE = auto()
    WFDIALOG_ITALIC_THRESHOLD = auto()
    WFDIALOG_REGEX = auto()
    WFDIALOG_HYPHEN_TWO_WORDS = auto()
    CHECKERDIALOG_SORT_TYPE_DICT = auto()
    CHECKERDIALOG_SUSPECTS_ONLY_DICT = auto()
    DIALOG_GEOMETRY = auto()
    ROOT_GEOMETRY = auto()
    ROOT_GEOMETRY_STATE = auto()
    ROOT_GEOMETRY_FULL_SCREEN = auto()
    DEFAULT_LANGUAGES = auto()
    JEEBIES_PARANOIA_LEVEL = auto()
    LEVENSHTEIN_DISTANCE = auto()
    FOOTNOTE_INDEX_STYLE = auto()
    FOOTNOTE_PER_LZ = auto()
    FOOTNOTE_SPLIT_WINDOW = auto()
    SHOW_TOOLTIPS = auto()
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
    TEAROFF_MENU_TYPE = auto()
    COMPOSE_HISTORY = auto()
    COMPOSE_HELP_SORT = auto()
    COMPOSE_HELP_HISTORY = auto()
    TEXT_FONT_FAMILY = auto()
    TEXT_FONT_SIZE = auto()
    GLOBAL_FONT_FAMILY = auto()
    GLOBAL_FONT_SIZE = auto()
    GLOBAL_FONT_SYSTEM = auto()
    TEXT_LINE_SPACING = auto()
    TEXT_CURSOR_WIDTH = auto()
    PREF_TAB_CURRENT = auto()
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
    HIGH_CONTRAST = auto()
    IMAGE_VIEWER_EXTERNAL = auto()
    IMAGE_VIEWER_EXTERNAL_PATH = auto()
    IMAGE_VIEWER_INTERNAL = auto()
    SCANNOS_FILENAME = auto()
    SCANNOS_HISTORY = auto()
    SCANNOS_AUTO_ADVANCE = auto()
    REGEX_LIBRARY_FILENAME = auto()
    REGEX_LIBRARY_HISTORY = auto()
    REGEX_LIBRARY_AUTO_ADVANCE = auto()
    HIGHLIGHT_QUOTBRAC = auto()
    HIGHLIGHT_HTML_TAGS = auto()
    HIGHLIGHT_CURSOR_LINE = auto()
    COLUMN_NUMBERS = auto()
    HTML_ITALIC_MARKUP = auto()
    HTML_BOLD_MARKUP = auto()
    HTML_GESPERRT_MARKUP = auto()
    HTML_FONT_MARKUP = auto()
    HTML_UNDERLINE_MARKUP = auto()
    HTML_SHOW_PAGE_NUMBERS = auto()
    HTML_MULTILINE_CHAPTER_HEADINGS = auto()
    HTML_SECTION_HEADINGS = auto()
    HTML_IMAGE_UNIT = auto()
    HTML_IMAGE_OVERRIDE_EPUB = auto()
    HTML_IMAGE_ALIGNMENT = auto()
    HTML_IMAGE_CAPTION_P = auto()
    HTML_LINKS_ALPHABETIC = auto()
    HTML_LINKS_HIDE_PAGE = auto()
    HTML_LINKS_HIDE_FOOTNOTE = auto()
    ALIGN_COL_ACTIVE = auto()
    PPHTML_VERBOSE = auto()
    CSS_VALIDATION_LEVEL = auto()
    HIGHLIGHT_PROOFERCOMMENT = auto()
    IMAGE_AUTOFIT_WIDTH = auto()
    IMAGE_AUTOFIT_HEIGHT = auto()
    CHECKER_GRAY_UNUSED_OPTIONS = auto()
    AUTOFIX_RTL_TEXT = auto()
    CUSTOM_MENU_ENTRIES = auto()
    EBOOKMAKER_PATH = auto()
    EBOOKMAKER_EPUB2 = auto()
    EBOOKMAKER_EPUB3 = auto()
    EBOOKMAKER_KINDLE = auto()
    EBOOKMAKER_KF8 = auto()
    EBOOKMAKER_VERBOSE_OUTPUT = auto()
    BACKUPS_ENABLED = auto()
    AUTOSAVE_ENABLED = auto()
    AUTOSAVE_INTERVAL = auto()
    ASCII_TABLE_HANGING = auto()
    ASCII_TABLE_INDENT = auto()
    ASCII_TABLE_REWRAP = auto()
    ASCII_TABLE_JUSTIFY = auto()
    ASCII_TABLE_FILL_CHAR = auto()
    ASCII_TABLE_RIGHT_COL = auto()
    COMMAND_PALETTE_HISTORY = auto()
    COMMAND_PALETTE_SORT = auto()
    KEYBOARD_SHORTCUTS_DICT = auto()
    AUTOTABLE_MULTILINE = auto()
    AUTOTABLE_WIDE_FLAG = auto()
    AUTOTABLE_DEFAULT_ALIGNMENT = auto()
    AUTOTABLE_COLUMN_ALIGNMENT = auto()
    AUTOTABLE_COLUMN_ALIGNMENT_HISTORY = auto()
    AUTOLIST_MULTILINE = auto()
    AUTOLIST_TYPE = auto()
    SURROUND_WITH_BEFORE = auto()
    SURROUND_WITH_BEFORE_HISTORY = auto()
    SURROUND_WITH_AFTER = auto()
    SURROUND_WITH_AFTER_HISTORY = auto()
    REGEX_TIMEOUT = auto()
    LEVENSHTEIN_DIGITS = auto()
    ILLO_MOVE_PAGE_MARKS = auto()
    CURLY_DOUBLE_QUOTE_EXCEPTION = auto()
    CURLY_SINGLE_QUOTE_STRICT = auto()
    CUSTOM_MARKUP_ATTRIBUTE_0 = auto()
    CUSTOM_MARKUP_ATTRIBUTE_1 = auto()
    CUSTOM_MARKUP_ATTRIBUTE_2 = auto()
    CUSTOM_MARKUP_ATTRIBUTE_3 = auto()
    CUSTOM_MARKUP_ATTRIBUTE_0_HISTORY = auto()
    CUSTOM_MARKUP_ATTRIBUTE_1_HISTORY = auto()
    CUSTOM_MARKUP_ATTRIBUTE_2_HISTORY = auto()
    CUSTOM_MARKUP_ATTRIBUTE_3_HISTORY = auto()
    CUSTOMIZABLE_COLORS = auto()
    IMAGE_VIEWER_DOCK_SIDE = auto()
    PPTXT_FILE_ANALYSIS_CHECK = auto()
    PPTXT_SPACING_CHECK = auto()
    PPTXT_REPEATED_WORDS_CHECK = auto()
    PPTXT_ELLIPSIS_CHECK = auto()
    PPTXT_CURLY_QUOTE_CHECK = auto()
    PPTXT_HYPHENATED_WORDS_CHECK = auto()
    PPTXT_ADJACENT_SPACES_CHECK = auto()
    PPTXT_DASH_REVIEW_CHECK = auto()
    PPTXT_SCANNO_CHECK = auto()
    PPTXT_WEIRD_CHARACTERS_CHECK = auto()
    PPTXT_HTML_CHECK = auto()
    PPTXT_UNICODE_NUMERIC_CHARACTER_CHECK = auto()
    PPTXT_SPECIALS_CHECK = auto()
    CHECKERDIALOG_FULL_SEARCH = auto()
    DIALOG_PIN_DICT = auto()
    CP_DEHYPH_USE_DICT = auto()
    CP_MULTIPLE_SPACES = auto()
    CP_SPACED_HYPHENS = auto()
    CP_SPACED_HYPHEN_EMDASH = auto()
    CP_SPACE_BEFORE_PUNC = auto()
    CP_SPACE_BEFORE_ELLIPSIS = auto()
    CP_SINGLE_QUOTES_DOUBLE = auto()
    CP_COMMON_LETTER_SCANNOS = auto()
    CP_1_TO_I = auto()
    CP_0_TO_O = auto()
    CP_L_TO_I = auto()
    CP_FRACTIONS = auto()
    CP_SUPER_SUB_SCRIPTS = auto()
    CP_UNDERSCORES_EMDASH = auto()
    CP_COMMAS_DOUBLE_QUOTE = auto()
    CP_SPACED_BRACKETS = auto()
    CP_SLASH_COMMA_APOSTROPHE = auto()
    CP_J_SEMICOLON = auto()
    CP_TO_HE_BE = auto()
    CP_PUNCT_START_END = auto()
    CP_BLANK_LINES_TOP = auto()
    CP_MULTI_BLANK_LINES = auto()
    CP_DUBIOUS_SPACED_QUOTES = auto()
    CP_SPACED_APOSTROPHES = auto()
    CP_WHITESPACE_TO_SPACE = auto()
    CP_DASHES_TO_HYPHEN = auto()
    CP_CURLY_QUOTES = auto()
    CP_PNG_CRUSH_COMMAND = auto()
    CP_HIGHLIGHT_CHARSUITE_ORPHANS = auto()
    INITIAL_DIR = auto()
    RELEASE_NOTES_SHOWN = auto()
    DID_YOU_KNOW_LAST_SHOWN = auto()
    DID_YOU_KNOW_INTERVAL = auto()
    DID_YOU_KNOW_INDEX = auto()
    NGRAM_PARAMETERS = auto()


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
          stored here so the variable(s) can be set whenever the pref is set. The Persistent
          classes below handle the reverse, i.e. they set the pref whenever a variable
          based on that pref is set.
        prefsdir: directory containing user prefs & data files
    """

    def __init__(self) -> None:
        """Initialize preferences class."""
        self.dict: dict[PrefKey, Any] = {}
        self.defaults: dict[PrefKey, Any] = {}
        self.callbacks: dict[PrefKey, Callable[[Any], None]] = {}
        self.persistent_vars: dict[PrefKey, list[tk.Variable]] = {}
        self.permanent = False
        self.prefsdir = ""
        self.prefsfile = ""

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
        # Deepcopy so that lists (of lists, etc) don't appear to be
        # unchanged in the test above, even though their contents have changed
        self.dict[key] = copy.deepcopy(value)
        self.save()
        if key in self.callbacks:
            self.callbacks[key](value)
        if key in self.persistent_vars:
            for var in self.persistent_vars[key]:
                var.set(value)

    def reset(self, key: PrefKey) -> None:
        """Reset a preference to its default.

        Args:
            key: Name of preference.
        """
        self.set(key, self.get_default(key))

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
        whenever the preference gets set. More than one variable may be
        linked to a preference.

        Args:
            key: Name of preference.
            var: Persistent variable to link to preference.
        """
        try:
            self.persistent_vars[key].append(var)
        except KeyError:
            self.persistent_vars[key] = [var]

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

        # Backup to "day" and "week" files if they are not too new.
        root, ext = os.path.splitext(self.prefsfile)
        day_backup = root + "_day" + ext
        week_backup = root + "_week" + ext

        def is_older_than(file: str, seconds: int) -> bool:
            """Return True if file is more than `seconds` old"""
            return (
                not os.path.exists(file)
                or (time.time() - os.path.getmtime(file)) > seconds
            )

        if is_older_than(week_backup, 7 * 86400):  # 7 days
            if os.path.exists(day_backup):
                try:
                    os.replace(day_backup, week_backup)
                except FileNotFoundError:
                    pass  # Nothing we can do

        if is_older_than(day_backup, 86400):  # 1 day
            if os.path.exists(self.prefsfile):
                try:
                    os.replace(self.prefsfile, day_backup)
                except FileNotFoundError:
                    pass  # Nothing we can do

        try:
            with open(self.prefsfile, "w", encoding="utf-8") as fp:
                json.dump(self.dict, fp, indent=2, ensure_ascii=False)
        except OSError:
            logger.error(f"Unable to save preferences to {self.prefsfile}")

    def load(self, prefs_basefile: Optional[str]) -> None:
        """Load dictionary from JSON file, and use PrefKeys
        to store values in preferences dictionary."""
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
        if is_test():
            prefs_name = "GGprefs_test.json"
        elif prefs_basefile is None:
            prefs_name = "GGprefs.json"
        else:
            prefs_name = f"{prefs_basefile}.json"
        self.prefsfile = os.path.join(self.prefsdir, prefs_name)

        self._remove_test_prefs_file()

        if not self.permanent:
            return

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
        if is_test() and os.path.exists(self.prefsfile):
            os.remove(self.prefsfile)


class PersistentBoolean(tk.BooleanVar):
    """Tk boolean variable whose value is stored in user prefs file.

    Note that, like all prefs, the default value must be set in
    `initialize_preferences`
    """

    def __init__(self, pref_key: PrefKey) -> None:
        """Initialize persistent boolean.

        Args:
            prefs_key: Preferences key associated with the variable.
        """
        super().__init__(value=preferences.get(pref_key))
        self.pref_key = pref_key
        self.trace_add("write", lambda *_args: preferences.set(pref_key, self.get()))
        preferences.link_persistent_var(pref_key, self)


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
