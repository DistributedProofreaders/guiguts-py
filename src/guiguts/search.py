"""Search/Replace functionality"""

import logging
import tkinter as tk
from tkinter import ttk
from tkinter import font as tk_font
import traceback
from typing import Any, Tuple, Optional

import regex as re

from guiguts.checkers import CheckerDialog
from guiguts.maintext import maintext, TclRegexCompileError, FindMatch, menubar_metadata
from guiguts.preferences import preferences, PersistentBoolean, PrefKey
from guiguts.utilities import (
    sound_bell,
    IndexRowCol,
    IndexRange,
    sing_plur,
    process_accel,
)
from guiguts.widgets import (
    ToplevelDialog,
    Combobox,
    mouse_bind,
    register_focus_widget,
    Busy,
)

logger = logging.getLogger(__package__)

MARK_FOUND_START = "FoundStart"
MARK_FOUND_END = "FoundEnd"
MARK_END_RANGE = "SearchRangeEnd"
PADX = 2
PADY = 2


class NoMatchFoundError(Exception):
    """Raised when no match is found for the search string."""


class SearchDialog(ToplevelDialog):
    """A Toplevel dialog that allows the user to search/replace.

    Attributes:
        reverse: True to search backwards.
        matchcase: True to ignore case.
        wrap: True to wrap search round beginning/end of file.
        regex: True to use regex search.
        selection: True to restrict counting, replacing, etc., to selected text.
    """

    manual_page = "Searching"
    # Cannot be initialized here, since Tk root may not be created yet
    selection: tk.BooleanVar

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize Search dialog."""

        # Initialize "Selection" variable on first instantiation.
        # Persistent only during this run of the program.
        try:
            SearchDialog.selection
        except AttributeError:
            SearchDialog.selection = tk.BooleanVar(value=False)
        kwargs["resize_y"] = False
        kwargs["disable_geometry_save"] = True
        super().__init__("Search & Replace", *args, **kwargs)
        self.minsize(400, 100)

        # Frames
        self.top_frame.columnconfigure(0, weight=1)
        for row in range(5):
            self.top_frame.rowconfigure(row, weight=0)
        self.top_frame.rowconfigure(6, weight=1)
        options_frame = ttk.Frame(
            self.top_frame, padding=3, borderwidth=1, relief=tk.GROOVE
        )
        options_frame.grid(
            row=0, column=0, columnspan=3, rowspan=2, ipady=5, sticky="NSEW"
        )
        options_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(1, weight=1)
        options_frame.columnconfigure(2, weight=1)
        options_frame.rowconfigure(0, weight=1)
        options_frame.rowconfigure(1, weight=1)
        message_frame = ttk.Frame(self.top_frame, padding=1)
        message_frame.grid(row=6, column=0, columnspan=5, sticky="NSEW", pady=(5, 0))
        self.separator = ttk.Separator(self.top_frame, orient=tk.VERTICAL)
        self.separator.grid(row=0, column=3, rowspan=6, padx=2, sticky="NSEW")

        # Search
        style = ttk.Style()
        new_col = "#ff8080" if maintext().is_dark_theme() else "#e60000"
        style.configure("BadRegex.TCombobox", foreground=new_col)

        self.font = tk_font.Font(
            family=maintext().font.cget("family"),
            size=maintext().font.cget("size"),
        )
        self.search_box = Combobox(
            self.top_frame,
            PrefKey.SEARCH_HISTORY,
            width=30,
            font=self.font,
            validate=tk.ALL,
            validatecommand=(self.register(self.is_valid_regex), "%P"),
        )
        self.search_box.grid(row=2, column=0, padx=PADX, pady=PADY, sticky="NSEW")
        # Register search box to have its focus tracked for inserting special characters
        register_focus_widget(self.search_box)
        self.search_box.focus()

        search_button = ttk.Button(
            self.top_frame,
            text="Search",
            default="active",
            takefocus=False,
            command=self.search_clicked,
        )
        search_button.grid(row=2, column=1, padx=PADX, pady=PADY, sticky="NSEW")
        mouse_bind(
            search_button,
            "Shift+1",
            lambda *args: self.search_clicked(opposite_dir=True),
        )
        self.bind("<Return>", lambda *args: self.search_clicked())
        self.bind(
            "<Shift-Return>", lambda *args: self.search_clicked(opposite_dir=True)
        )

        # First/Last button - find first/last occurrence in file
        self.first_button = ttk.Button(
            self.top_frame,
            text="Last" if preferences.get(PrefKey.SEARCHDIALOG_REVERSE) else "First",
            takefocus=False,
            command=lambda *args: self.search_clicked(first_last=True),
        )
        self.first_button.grid(row=2, column=2, padx=PADX, pady=PADY, sticky="NSEW")

        # Count & Find All
        self.count_btn = ttk.Button(
            self.top_frame,
            text="Count",
            takefocus=False,
            command=self.count_clicked,
        )
        self.count_btn.grid(row=1, column=4, padx=PADX, pady=PADY, sticky="NSEW")
        ttk.Button(
            self.top_frame,
            text="Find All",
            takefocus=False,
            command=self.findall_clicked,
        ).grid(row=2, column=4, padx=PADX, pady=PADY, sticky="NSEW")

        # Options
        ttk.Checkbutton(
            options_frame,
            text="Reverse",
            variable=PersistentBoolean(PrefKey.SEARCHDIALOG_REVERSE),
            command=self.set_first_last,
            takefocus=False,
        ).grid(row=0, column=0, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Match case",
            variable=PersistentBoolean(PrefKey.SEARCHDIALOG_MATCH_CASE),
            takefocus=False,
        ).grid(row=0, column=1, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Regex",
            variable=PersistentBoolean(PrefKey.SEARCHDIALOG_REGEX),
            takefocus=False,
            command=lambda: self.is_valid_regex(self.search_box.get()),
        ).grid(row=0, column=2, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Whole word",
            variable=PersistentBoolean(PrefKey.SEARCHDIALOG_WHOLE_WORD),
            takefocus=False,
        ).grid(row=1, column=0, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Wrap around",
            variable=PersistentBoolean(PrefKey.SEARCHDIALOG_WRAP),
            takefocus=False,
        ).grid(row=1, column=1, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Multi-replace",
            variable=PersistentBoolean(PrefKey.SEARCHDIALOG_MULTI_REPLACE),
            takefocus=False,
            command=self.show_multi_replace,
        ).grid(row=1, column=2, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            self.top_frame,
            text="In selection",
            variable=SearchDialog.selection,
            takefocus=False,
        ).grid(row=0, column=4, sticky="NSE")

        # Replace
        self.replace_box: list[Combobox] = []
        self.replace_btn: list[ttk.Button] = []
        self.rands_btn: list[ttk.Button] = []
        self.repl_all_btn: list[ttk.Button] = []
        for rep_num in range(3):
            cbox = Combobox(
                self.top_frame, PrefKey.REPLACE_HISTORY, width=30, font=self.font
            )
            cbox.grid(row=rep_num + 3, column=0, padx=PADX, pady=PADY, sticky="NSEW")
            self.replace_box.append(cbox)
            # Register replace box to have its focus tracked for inserting special characters
            register_focus_widget(cbox)

            r_btn = ttk.Button(
                self.top_frame,
                text="Replace",
                takefocus=False,
                command=lambda idx=rep_num: self.replace_clicked(idx),  # type: ignore[misc]
            )
            r_btn.grid(row=rep_num + 3, column=1, padx=PADX, pady=PADY, sticky="NSEW")
            self.replace_btn.append(r_btn)

            rands_button = ttk.Button(
                self.top_frame,
                text="R & S",
                takefocus=False,
                command=lambda idx=rep_num: self.replace_clicked(  # type: ignore[misc]
                    idx, search_again=True
                ),
            )
            rands_button.grid(
                row=rep_num + 3, column=2, padx=PADX, pady=PADY, sticky="NSEW"
            )
            mouse_bind(
                rands_button,
                "Shift+1",
                lambda _e, idx=rep_num: self.replace_clicked(  # type: ignore[misc]
                    idx, opposite_dir=True, search_again=True
                ),
            )
            self.rands_btn.append(rands_button)

            repl_all_btn = ttk.Button(
                self.top_frame,
                text="Replace All",
                takefocus=False,
                command=lambda idx=rep_num: self.replaceall_clicked(idx),  # type: ignore[misc]
            )
            repl_all_btn.grid(
                row=rep_num + 3, column=4, padx=PADX, pady=PADY, sticky="NSEW"
            )
            self.repl_all_btn.append(repl_all_btn)
        _, key_event = process_accel("Cmd/Ctrl+Return")
        self.bind(key_event, lambda *args: self.replace_clicked(0, search_again=True))
        _, key_event = process_accel("Cmd/Ctrl+Shift+Return")
        self.bind(
            key_event,
            lambda *args: self.replace_clicked(0, opposite_dir=True, search_again=True),
        )
        # Message (e.g. count)
        message_frame.columnconfigure(0, weight=1)
        self.message = ttk.Label(
            message_frame, borderwidth=1, relief="sunken", padding=5
        )
        self.message.grid(row=0, column=0, sticky="NSEW")

        self.show_multi_replace(resize=False)

        # Now dialog geometry is set up, set width to user pref, leaving height as it is
        self.config_width()
        self.allow_geometry_save()

    @classmethod
    def add_orphan_commands(cls) -> None:
        """Add orphan commands for Search dialog to command palette."""

        menubar_metadata().add_button_orphan(
            "S/R, Search", cls.orphan_wrapper("search_clicked")
        )
        menubar_metadata().add_button_orphan(
            "S/R, Search (reverse)",
            cls.orphan_wrapper("search_clicked", opposite_dir=True),
        )
        menubar_metadata().add_button_orphan(
            "S/R, Search (first/last)",
            cls.orphan_wrapper("search_clicked", first_last=True),
        )
        menubar_metadata().add_button_orphan(
            "S/R, Count", cls.orphan_wrapper("count_clicked")
        )
        menubar_metadata().add_button_orphan(
            "S/R, Find All", cls.orphan_wrapper("findall_clicked")
        )
        menubar_metadata().add_button_orphan(
            "S/R, Replace", cls.orphan_wrapper("replace_clicked", 0)
        )
        menubar_metadata().add_button_orphan(
            "S/R, Replace All", cls.orphan_wrapper("replaceall_clicked", 0)
        )
        menubar_metadata().add_button_orphan(
            "S/R, Replace & Search",
            cls.orphan_wrapper("replace_clicked", 0, search_again=True),
        )
        menubar_metadata().add_button_orphan(
            "S/R, Replace & Search (reverse)",
            cls.orphan_wrapper(
                "replace_clicked", 0, opposite_dir=True, search_again=True
            ),
        )
        menubar_metadata().add_checkbutton_orphan(
            "S/R, Reverse",
            PrefKey.SEARCHDIALOG_REVERSE,
            cls.orphan_wrapper("set_first_last"),
            cls.orphan_wrapper("set_first_last"),
        )
        menubar_metadata().add_checkbutton_orphan(
            "S/R, Match Case", PrefKey.SEARCHDIALOG_MATCH_CASE
        )
        menubar_metadata().add_checkbutton_orphan(
            "S/R, Regex",
            PrefKey.SEARCHDIALOG_REGEX,
            cls.orphan_wrapper("is_valid_regex"),
            cls.orphan_wrapper("is_valid_regex"),
        )
        menubar_metadata().add_checkbutton_orphan(
            "S/R, Whole Word", PrefKey.SEARCHDIALOG_WHOLE_WORD
        )
        menubar_metadata().add_checkbutton_orphan(
            "S/R, Wrap Around", PrefKey.SEARCHDIALOG_WRAP
        )
        menubar_metadata().add_checkbutton_orphan(
            "S/R, Multi-replace",
            PrefKey.SEARCHDIALOG_MULTI_REPLACE,
            cls.orphan_wrapper("show_multi_replace"),
            cls.orphan_wrapper("show_multi_replace"),
        )

    def reset(self) -> None:
        """Called when dialog is reset/destroyed - remove search highlights."""
        maintext().highlight_search_deactivate()

    def show_multi_replace(self, resize: bool = True) -> None:
        """Show or hide the multi-replace buttons, based on Pref

        Args:
            resize: True (default) to grow/shrink dialog to take account of show/hide
                When dialog first created, its size is stored in prefs, so won't need resize
        """
        show = preferences.get(PrefKey.SEARCHDIALOG_MULTI_REPLACE)
        for w_list in (
            self.replace_box,
            self.replace_btn,
            self.rands_btn,
            self.repl_all_btn,
        ):
            for widget in w_list[1:]:
                if show:
                    widget.grid()
                else:
                    widget.grid_remove()
        self.separator.grid(rowspan=6 if show else 4)

        if not resize:
            return

        # Height needs to grow/shrink by the space taken up by 2 entry fields
        offset = 2 * (self.replace_box[0].winfo_y() - self.search_box.winfo_y())
        geometry = self.geometry()
        height = int(re.sub(r"\d+x(\d+).+", r"\1", geometry))
        height += offset if show else -offset
        geometry = re.sub(r"(\d+x)\d+(.+)", rf"\g<1>{height}\g<2>", geometry)
        self.geometry(geometry)

    def is_valid_regex(self, new_value: Optional[str] = None) -> bool:
        """Validation routine for Search Combobox - check value is a valid regex.

        Note that it always returns True because we want user to be able to type
        the character. It just alerts the user by switching to the BadRegex style.

        Args:
            new_value: Value to be checked. If None, use value in search entry field.
        """
        if new_value is None:
            new_value = self.search_box.get()
        if preferences.get(PrefKey.SEARCHDIALOG_REGEX):
            try:
                re.compile(new_value)
                self.search_box["style"] = ""
            except re.error:
                self.search_box["style"] = "BadRegex.TCombobox"
        else:
            self.search_box["style"] = ""
        return True

    def set_first_last(self) -> None:
        """Set text in First/Last button depending on direction."""
        self.first_button["text"] = (
            "Last" if preferences.get(PrefKey.SEARCHDIALOG_REVERSE) else "First",
        )

    def search_box_set(self, search_string: str) -> None:
        """Set string in search box.

        Also selects the string, and places the cursor at the end

        Args:
            search_string: String to put in search box.
        """
        self.search_box.set(search_string)
        self.search_box.select_range(0, tk.END)
        self.search_box.icursor(tk.END)
        self.search_box.focus()

    def search_clicked(
        self, opposite_dir: bool = False, first_last: bool = False
    ) -> str:
        """Search for the string in the search box.

        Args:
            opposite_dir: True to search in opposite direction to reverse flag setting
            first_last: True to begin search at start/end of file
        Returns:
            "break" to avoid calling other callbacks
        """
        search_string = self.search_box.get()
        if not search_string:
            return "break"
        self.search_box.add_to_history(search_string)

        # "Reverse flag XOR Shift-key" searches backwards
        backwards = preferences.get(PrefKey.SEARCHDIALOG_REVERSE) ^ opposite_dir
        if first_last:
            start_rowcol = (
                maintext().end()
                if preferences.get(PrefKey.SEARCHDIALOG_REVERSE)
                else maintext().start()
            )
        else:
            start_rowcol = get_search_start(backwards)
        stop_rowcol = maintext().start() if backwards else maintext().end()
        message = ""

        try:
            maintext().search_pattern = self.search_box.get()
            maintext().search_highlight_active.set(True)

            # Now that "background" matches are highlighted, find the next match
            # and jump there as the "active" match. Uses the "sel" highlight.
            _do_find_next(
                search_string, backwards, IndexRange(start_rowcol, stop_rowcol)
            )
        except re.error as e:
            message = message_from_regex_exception(e)
        except NoMatchFoundError:
            message = "No matches found"
        self.display_message(message)
        return "break"

    def search_forwards(self) -> str:
        """Force forward search regardless of reverse flag.

        Returns:
            "break" to avoid calling other callbacks
        """
        self.search_clicked(opposite_dir=preferences.get(PrefKey.SEARCHDIALOG_REVERSE))
        return "break"

    def search_backwards(self) -> str:
        """Force backward search regardless of reverse flag.

        Returns:
            "break" to avoid calling other callbacks
        """
        self.search_clicked(
            opposite_dir=not preferences.get(PrefKey.SEARCHDIALOG_REVERSE)
        )
        return "break"

    def count_clicked(self) -> Optional[list[FindMatch]]:
        """Count how many times search string occurs in file (or selection).

        Display count in Search dialog.

        Returns:
            List of FindMatch objects (None if error).
        """
        search_string = self.search_box.get()
        if not search_string:
            return None
        self.search_box.add_to_history(search_string)

        find_ranges, range_name = get_search_ranges()
        if find_ranges is None:
            self.display_message('No text selected for "In selection" find')
            sound_bell()
            return None

        count = 0
        matches: list[FindMatch] = []
        for find_range in find_ranges:
            try:
                matches.extend(maintext().find_all(find_range, search_string))
            except re.error as e:
                self.display_message(message_from_regex_exception(e))
                return None
        count = len(matches)
        match_str = sing_plur(count, "match", "matches")
        self.display_message(f"Found: {match_str} {range_name}")
        return matches

    def findall_clicked(self) -> None:
        """Callback when Find All button clicked.

        Find & count occurrences, then display in dialog.
        """
        matches = self.count_clicked()
        if matches is None:
            return

        class FindAllCheckerDialog(CheckerDialog):
            """Find All dialog."""

            manual_page = "Searching#Find_All"

            def __init__(self, **kwargs: Any) -> None:
                """Initialize Find All dialog."""

                super().__init__(
                    "Search Results",
                    tooltip="\n".join(
                        [
                            "Left click: Select & find string",
                            "Right click: Hide string from this list",
                            "Shift Right click: Hide all occurrences of string in this list",
                        ]
                    ),
                    **kwargs,
                )

        checker_dialog = FindAllCheckerDialog.show_dialog(
            rerun_command=self.findall_clicked,
        )
        if not checker_dialog.winfo_exists() or not self.winfo_exists():
            Busy.unbusy()
            return

        # Construct opening line describing the search
        desc_reg = "regex" if preferences.get(PrefKey.SEARCHDIALOG_REGEX) else "string"
        prefix = f'Search for {desc_reg} "'
        desc = f'{prefix}{self.search_box.get()}"'
        if preferences.get(PrefKey.SEARCHDIALOG_MATCH_CASE):
            desc += ", matching case"
        if preferences.get(PrefKey.SEARCHDIALOG_WHOLE_WORD):
            desc += ", whole words only"
        if SearchDialog.selection.get():
            desc += ", within selection"
        checker_dialog.add_header(desc, "")

        for match in matches:
            line = maintext().get(
                f"{match.rowcol.index()} linestart",
                f"{match.rowcol.index()}+{match.count}c lineend",
            )
            end_rowcol = IndexRowCol(
                maintext().index(match.rowcol.index() + f"+{match.count}c")
            )
            hilite_start = match.rowcol.col
            # If multiline, lines will be concatenated, so adjust end hilite point
            if end_rowcol.row > match.rowcol.row:
                not_matched = maintext().get(
                    f"{match.rowcol.index()}+{match.count}c",
                    f"{match.rowcol.index()}+{match.count}c lineend",
                )
                hilite_end = len(line) - len(not_matched)
            else:
                hilite_end = end_rowcol.col
            checker_dialog.add_entry(
                line, IndexRange(match.rowcol, end_rowcol), hilite_start, hilite_end
            )
        checker_dialog.add_footer("", "End of search results")
        checker_dialog.display_entries()

    def replace_clicked(
        self, box_num: int, opposite_dir: bool = False, search_again: bool = False
    ) -> str:
        """Replace the found string with the replacement in the replace box.

        Args:
            box_num: Which replace box's Replace button was clicked.
            opposite_dir: True to go in opposite direction to the "Reverse" flag.
            search_again: True to find next match after replacement.

        Returns:
            "break" to avoid calling other callbacks
        """
        search_string = self.search_box.get()
        self.search_box.add_to_history(search_string)
        replace_string = self.replace_box[box_num].get()
        self.replace_box[box_num].add_to_history(replace_string)

        try:
            start_index = maintext().index(MARK_FOUND_START)
            end_index = maintext().index(MARK_FOUND_END)
        except tk.TclError:
            # If Replace & Search, then even if we can't Replace, do a Search
            if search_again:
                self.search_clicked(opposite_dir=opposite_dir)
            else:
                sound_bell()
                self.display_message("No text found to replace")
            return "break"

        match_text = maintext().get(start_index, end_index)
        if preferences.get(PrefKey.SEARCHDIALOG_REGEX):
            flags = (
                0 if preferences.get(PrefKey.SEARCHDIALOG_MATCH_CASE) else re.IGNORECASE
            )
            try:
                replace_string = get_regex_replacement(
                    search_string, replace_string, match_text, flags=flags
                )
            except re.error as e:
                self.display_message(f"Regex error: {str(e)}")
                sound_bell()
                return "break"
        maintext().undo_block_begin()
        maintext().replace(start_index, end_index, replace_string)
        # "Reverse flag XOR Shift-key" searches backwards
        backwards = preferences.get(PrefKey.SEARCHDIALOG_REVERSE) ^ opposite_dir
        # Ensure cursor is at correct end of replaced string - depends on direction.
        maintext().set_insert_index(
            maintext().rowcol(MARK_FOUND_START if backwards else MARK_FOUND_END),
            focus=False,
        )
        maintext().mark_unset(MARK_FOUND_START, MARK_FOUND_END)
        maintext().clear_selection()
        if search_again:
            find_next(backwards=backwards)
        return "break"

    def replaceall_clicked(self, box_num: int) -> None:
        """Callback when Replace All button clicked.

        Replace in whole file or just in selection.

        Args:
            box_num: Which replace box's Replace button was clicked.

        """
        search_string = self.search_box.get()
        if not search_string:
            return
        self.search_box.add_to_history(search_string)
        replace_string = self.replace_box[box_num].get()
        self.replace_box[box_num].add_to_history(replace_string)

        replace_ranges, range_name = get_search_ranges()
        if replace_ranges is None:
            self.display_message('No text selected for "In selection" replace')
            sound_bell()
            return

        if SearchDialog.selection.get():
            maintext().selection_ranges_store_with_marks()
        maintext().undo_block_begin()

        regexp = preferences.get(PrefKey.SEARCHDIALOG_REGEX)
        replace_match = replace_string
        match_count = 0

        for replace_range in replace_ranges:
            try:
                matches = maintext().find_all(replace_range, search_string)
            except re.error as e:
                self.display_message(message_from_regex_exception(e))
                return

            flags = (
                0 if preferences.get(PrefKey.SEARCHDIALOG_MATCH_CASE) else re.IGNORECASE
            )

            # Work backwards so replacements don't affect future match locations
            for match in reversed(matches):
                start_index = match.rowcol.index()
                end_index = maintext().index(start_index + f"+{match.count}c")
                match_text = maintext().get(start_index, end_index)
                if regexp:
                    try:
                        replace_match = get_regex_replacement(
                            search_string, replace_string, match_text, flags=flags
                        )
                    except re.error as e:
                        self.display_message(f"Regex error: {str(e)}")
                        sound_bell()
                        return
                maintext().replace(start_index, end_index, replace_match)
            match_count += len(matches)

        if SearchDialog.selection.get():
            maintext().selection_ranges_restore_from_marks()
        else:
            maintext().clear_selection()

        match_str = sing_plur(match_count, "match", "matches")
        self.display_message(f"Replaced: {match_str} {range_name}")

    def display_message(self, message: str = "") -> None:
        """Display message in Search dialog.

        Args:
            message: Message to be displayed - clears message if arg omitted
        """
        if self.message.winfo_exists():
            self.message["text"] = message


def show_search_dialog() -> None:
    """Show the Search dialog and set the string in search box
    to the selected text if any (up to first newline)."""
    dlg = SearchDialog.show_dialog()
    dlg.search_box_set(maintext().selected_text().split("\n", 1)[0])
    dlg.display_message()


def find_next(backwards: bool = False) -> None:
    """Find next occurrence of most recent search string.

    Takes account of current wrap, matchcase, regex & wholeword flag settings
    in Search dialog. If dialog hasn't been shown previously or there is
    no recent search string sounds bell and returns.

    Args:
        backwards: True to search backwards (not dependent on "Reverse"
            setting in dialog).
    """
    try:
        SearchDialog.selection
    except AttributeError:
        sound_bell()
        return  # Dialog has never been instantiated

    search_string = ""
    # If dialog is visible, then string in search box takes priority over
    # previously-searched-for string.
    if dlg := SearchDialog.get_dialog():
        search_string = dlg.search_box.get()
        dlg.search_box.add_to_history(search_string)
        dlg.display_message("")
    if not search_string:
        try:
            search_string = preferences.get(PrefKey.SEARCH_HISTORY)[0]
        except IndexError:
            sound_bell()
            return  # No Search History

    start_rowcol = get_search_start(backwards)
    stop_rowcol = maintext().start() if backwards else maintext().end()
    try:
        _do_find_next(search_string, backwards, IndexRange(start_rowcol, stop_rowcol))
    except TclRegexCompileError as exc:
        logger.error(str(exc))
    except NoMatchFoundError:
        if dlg:
            dlg.display_message("No more matches found")


def _do_find_next(
    search_string: str, backwards: bool, search_limits: IndexRange
) -> None:
    """Find next occurrence of string from start_point.

    Args:
        search_string: String to search for.
        backwards: True to search backwards.
        start_point: Point to search from.
    """
    match = maintext().find_match_user(
        search_string,
        search_limits.start,
        nocase=not preferences.get(PrefKey.SEARCHDIALOG_MATCH_CASE),
        wholeword=preferences.get(PrefKey.SEARCHDIALOG_WHOLE_WORD),
        regexp=preferences.get(PrefKey.SEARCHDIALOG_REGEX),
        backwards=backwards,
        wrap=preferences.get(PrefKey.SEARCHDIALOG_WRAP),
    )

    if match:
        rowcol_end = maintext().rowcol(match.rowcol.index() + f"+{match.count}c")
        maintext().set_insert_index(
            match.rowcol, focus=False, see_end_rowcol=rowcol_end
        )
        maintext().do_select(IndexRange(match.rowcol, rowcol_end))
        maintext().set_mark_position(MARK_FOUND_START, match.rowcol, gravity=tk.LEFT)
        maintext().set_mark_position(MARK_FOUND_END, rowcol_end, gravity=tk.RIGHT)
    else:
        maintext().highlight_search_deactivate()
        sound_bell()
        raise NoMatchFoundError


def get_search_start(backwards: bool) -> IndexRowCol:
    """Find point to start searching from.

    Start from current insert point unless following are true:
    We are searching forward;
    Current insert point is at start of previously found match;
    Start of previous match is still selected (or it was a zero-length match)
    If all are true, advance to end of match.

    Additionally, searching for zero-length matches when already at start
    or end of file, needs special handling

    Args:
        backwards: True if searching backwards.
    """
    start_rowcol = maintext().get_insert_index()
    start_index = start_rowcol.index()
    try:
        at_previous_match = maintext().compare(MARK_FOUND_START, "==", start_index)
    except tk.TclError:
        at_previous_match = False  # MARK not found
    # We've previously done a search, and are now doing another, so various special
    # cases needed to avoid getting stuck at a match
    if at_previous_match:
        zero_len = maintext().compare(MARK_FOUND_START, "==", MARK_FOUND_END)
        if backwards:
            if zero_len:
                # If at start of file, and wrapping, then next reverse search is from end,
                # otherwise, just go back one character
                if preferences.get(PrefKey.SEARCHDIALOG_WRAP) and maintext().compare(
                    MARK_FOUND_START, "==", "1.0"
                ):
                    start_rowcol = maintext().end()
                else:
                    start_rowcol = maintext().rowcol(start_index + "-1c")
        else:
            if zero_len:
                # If at end of file, and wrapping, then next search is from start,
                # otherwise, just go forward one character
                if preferences.get(PrefKey.SEARCHDIALOG_WRAP) and maintext().compare(
                    MARK_FOUND_START, "==", maintext().end().index()
                ):
                    start_rowcol = maintext().start()
                else:
                    start_rowcol = maintext().rowcol(start_index + "+1c")
            elif sel_ranges := maintext().selected_ranges():
                if maintext().compare(sel_ranges[0].start.index(), "==", start_index):
                    start_rowcol = maintext().rowcol(MARK_FOUND_END)
    return start_rowcol


def get_regex_replacement(
    search_regex: str,
    replace_regex: str,
    match_text: str,
    flags: int,
) -> str:
    """Find actual replacement string, given the search & replace regexes
    and the matching text.

    Raises re.error exception if regexes are bad

    Args:
        search_regex: Regex that was used for search
        replace_regex: Regex used for replacement
        match_text: The text that was actually matched
        flags: "re.sub" flags to pass when performing the regex substitution

    Returns:
        Replacement string.
    """
    temp_bs = "\x9f"
    # Unused character to temporarily replace backslash in `\C`, `\E`

    # Since below we do a sub on the match text, rather than the whole text, we need
    # to handle start/end word boundaries and look-behind/ahead by removing them.
    # At some point the sub will be done manually, handing groups, execution of
    # python code, etc., like in GG1. At that point, these fixes can probably go.
    search_regex = re.sub(r"^\(\?<=.*?\)", "", search_regex)
    search_regex = re.sub(r"\(\?=.*?\)$", "", search_regex)
    search_regex = search_regex.removeprefix(r"\b").removesuffix(r"\b")

    # Allow execution of python code
    replace_regex = replace_regex.replace(r"\C", f"{temp_bs}C")
    replace_regex = replace_regex.replace(r"\E", f"{temp_bs}E")
    replace_str = re.sub(search_regex, replace_regex, match_text, flags=flags)
    if f"{temp_bs}C" in replace_str:
        while True:
            c_index = replace_str.find(f"{temp_bs}C")
            if c_index < 0:
                break
            e_index = replace_str.find(f"{temp_bs}E", c_index)
            if e_index < 0:
                break
            python_in = replace_str[c_index + 2 : e_index]
            try:
                python_out = str(eval(python_in))  # pylint:disable=eval-used
            except Exception as exc:
                tb = re.sub(
                    r'.+File "<string>", line 1[^\n]*',
                    r"\\C...\\E - error in Python code",
                    traceback.format_exc(),
                    flags=re.DOTALL,
                )
                logger.error(tb)
                raise re.error("\\C...\\E error - see message log for details") from exc
            replace_str = (
                replace_str[:c_index] + python_out + replace_str[e_index + 2 :]
            )
    return replace_str


def get_search_ranges() -> Tuple[Optional[list[IndexRange]], str]:
    """Get ranges to search over, based on checkbox settings.

    Returns:
        List of ranges to search over, and string to describe the ranges.
    """
    replace_ranges = None
    range_name = ""
    if SearchDialog.selection.get():
        range_name = "in selection"
        if sel_ranges := maintext().selected_ranges():
            replace_ranges = sel_ranges
    else:
        if preferences.get(PrefKey.SEARCHDIALOG_WRAP):
            range_name = "in entire file"
            replace_ranges = [maintext().start_to_end()]
        elif preferences.get(PrefKey.SEARCHDIALOG_REVERSE):
            range_name = "from start of file to current location"
            replace_ranges = [
                IndexRange(maintext().start(), maintext().get_insert_index())
            ]
        else:
            range_name = "from current location to end of file"
            replace_ranges = [
                IndexRange(maintext().get_insert_index(), maintext().end())
            ]
    return replace_ranges, range_name


def message_from_regex_exception(exc: re.error) -> str:
    """Create error message from regex exception.

    Args:
        exc - The regex exception to describe.
    """
    message = str(exc)
    message = message[0].upper() + message[1:]
    return message + " in regex " + exc.pattern  # type:ignore[attr-defined]
