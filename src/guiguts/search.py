"""Search/Replace functionality"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Tuple, Optional

import regex as re

from guiguts.checkers import CheckerDialog
from guiguts.maintext import maintext, TclRegexCompileError
from guiguts.preferences import preferences, PersistentBoolean, PrefKey
from guiguts.utilities import (
    sound_bell,
    IndexRowCol,
    IndexRange,
    process_accel,
    is_mac,
    sing_plur,
)
from guiguts.widgets import ToplevelDialog, Combobox, mouse_bind

logger = logging.getLogger(__package__)

MARK_FOUND_START = "FoundStart"
MARK_FOUND_END = "FoundEnd"
MARK_END_RANGE = "SearchRangeEnd"


class SearchDialog(ToplevelDialog):
    """A Toplevel dialog that allows the user to search/replace.

    Attributes:
        reverse: True to search backwards.
        matchcase: True to ignore case.
        wrap: True to wrap search round beginning/end of file.
        regex: True to use regex search.
        selection: True to restrict counting, replacing, etc., to selected text.
    """

    # Cannot be initialized here, since Tk root may not yet be created yet
    reverse: PersistentBoolean
    matchcase: PersistentBoolean
    wholeword: PersistentBoolean
    wrap: PersistentBoolean
    regex: PersistentBoolean
    selection: tk.BooleanVar

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize Search dialog."""

        # Initialize class variables on first instantiation, then remember
        # values for subsequent uses of dialog.
        try:
            SearchDialog.reverse
        except AttributeError:
            SearchDialog.reverse = PersistentBoolean(PrefKey.SEARCHDIALOGREVERSE)
            SearchDialog.matchcase = PersistentBoolean(PrefKey.SEARCHDIALOGMATCHCASE)
            SearchDialog.wholeword = PersistentBoolean(PrefKey.SEARCHDIALOGWHOLEWORD)
            SearchDialog.wrap = PersistentBoolean(PrefKey.SEARCHDIALOGWRAP)
            SearchDialog.regex = PersistentBoolean(PrefKey.SEARCHDIALOGREGEX)
            SearchDialog.selection = tk.BooleanVar(value=False)

        kwargs["resize_y"] = False
        super().__init__("Search & Replace", *args, **kwargs)
        self.minsize(400, 100)

        # Frames
        self.top_frame.columnconfigure(0, weight=1)
        options_frame = ttk.Frame(
            self.top_frame, padding=3, borderwidth=1, relief=tk.GROOVE
        )
        options_frame.grid(row=0, column=0, columnspan=2, sticky="NSEW")
        options_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(1, weight=1)
        options_frame.columnconfigure(2, weight=1)
        search_frame1 = ttk.Frame(self.top_frame)
        search_frame1.grid(row=1, column=0, sticky="NSEW")
        search_frame1.columnconfigure(0, weight=1)
        search_frame2 = ttk.Frame(self.top_frame)
        search_frame2.grid(row=1, column=1, sticky="SEW")
        search_frame2.columnconfigure(0, weight=1)
        selection_frame = ttk.Frame(
            self.top_frame, padding=1, borderwidth=1, relief=tk.GROOVE
        )
        selection_frame.grid(row=0, column=2, rowspan=3, sticky="NSEW")
        message_frame = ttk.Frame(self.top_frame, padding=1)
        message_frame.grid(row=3, column=0, columnspan=3, sticky="NSEW")

        # Search
        self.search_box = Combobox(search_frame1, PrefKey.SEARCHHISTORY, width=30)
        self.search_box.grid(row=0, column=0, padx=2, pady=(5, 0), sticky="NSEW")
        self.search_box.focus()

        search_button = ttk.Button(
            search_frame1,
            text="Search",
            default="active",
            takefocus=False,
            command=self.search_clicked,
        )
        search_button.grid(row=0, column=1, pady=(5, 0), sticky="NSEW")
        mouse_bind(
            search_button,
            "Shift+1",
            lambda *args: self.search_clicked(opposite_dir=True),
        )
        self.bind("<Return>", lambda *args: self.search_clicked())
        self.bind(
            "<Shift-Return>", lambda *args: self.search_clicked(opposite_dir=True)
        )

        # Count & Find All
        ttk.Button(
            selection_frame,
            text="Count",
            takefocus=False,
            command=self.count_clicked,
        ).grid(row=1, column=0, padx=2, pady=(3, 2), sticky="NSEW")
        ttk.Button(
            selection_frame,
            text="Find All",
            takefocus=False,
            command=self.findall_clicked,
        ).grid(row=2, column=0, padx=2, pady=2, sticky="NSEW")

        # Options
        ttk.Checkbutton(
            options_frame,
            text="Reverse",
            variable=SearchDialog.reverse,
            takefocus=False,
        ).grid(row=0, column=0, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Match case",
            variable=SearchDialog.matchcase,
            takefocus=False,
        ).grid(row=0, column=1, padx=2, columnspan=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Whole word",
            variable=SearchDialog.wholeword,
            takefocus=False,
        ).grid(row=1, column=0, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Wrap around",
            variable=SearchDialog.wrap,
            takefocus=False,
        ).grid(row=1, column=1, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Regex",
            variable=SearchDialog.regex,
            takefocus=False,
        ).grid(row=1, column=2, padx=2, sticky="NSEW")
        ttk.Checkbutton(
            selection_frame,
            text="In selection",
            variable=SearchDialog.selection,
            takefocus=False,
        ).grid(row=0, column=0, sticky="NSE")

        # Replace
        self.replace_box = Combobox(search_frame1, PrefKey.REPLACEHISTORY, width=30)
        self.replace_box.grid(row=1, column=0, padx=2, pady=(4, 6), sticky="NSEW")

        ttk.Button(
            search_frame1,
            text="Replace",
            takefocus=False,
            command=self.replace_clicked,
        ).grid(row=1, column=1, pady=(4, 6), sticky="NSEW")
        rands_button = ttk.Button(
            search_frame2,
            text="R & S",
            takefocus=False,
            command=lambda *args: self.replace_clicked(search_again=True),
        )
        rands_button.grid(row=0, column=0, padx=(0, 2), pady=(2, 6), sticky="NSEW")
        mouse_bind(
            rands_button,
            "Shift+1",
            lambda *args: self.replace_clicked(opposite_dir=True, search_again=True),
        )
        ttk.Button(
            selection_frame,
            text="Replace All",
            takefocus=False,
            command=self.replaceall_clicked,
        ).grid(row=3, column=0, padx=2, pady=2, sticky="NSEW")

        # Message (e.g. count)
        self.message = ttk.Label(message_frame)
        self.message.grid(row=0, column=0, sticky="NSW")

        # Bindings for when focus is in Search dialog
        if is_mac():
            _, event = process_accel("Cmd+G")
            self.bind(event, lambda *args: find_next())
            _, event = process_accel("Cmd+g")
            self.bind(event, lambda *args: find_next())
            _, event = process_accel("Cmd+Shift+G")
            self.bind(event, lambda *args: find_next(backwards=True))
            _, event = process_accel("Cmd+Shift+g")
            self.bind(event, lambda *args: find_next(backwards=True))
        else:
            _, event = process_accel("F3")
            self.bind(event, lambda *args: find_next())
            _, event = process_accel("Shift+F3")
            self.bind(event, lambda *args: find_next(backwards=True))

        # Now dialog geometry is set up, set width to user pref, leaving height as it is
        self.config_width()

    def search_box_set(self, search_string: str) -> None:
        """Set string in search box.

        Also selects the string, and places the cursor at the end

        Args:
            search_string: String to put in search box.
        """
        self.search_box.set(search_string)
        self.search_box.select_range(0, tk.END)
        self.search_box.icursor(tk.END)

    def search_clicked(self, opposite_dir: bool = False) -> str:
        """Search for the string in the search box.

        Args:
            opposite_dir: True to search in opposite direction to reverse flag setting
        Returns:
            "break" to avoid calling other callbacks
        """
        search_string = self.search_box.get()
        if not search_string:
            return "break"
        self.search_box.add_to_history(search_string)

        # "Reverse flag XOR Shift-key" searches backwards
        backwards = SearchDialog.reverse.get() ^ opposite_dir
        start_rowcol = get_search_start(backwards)
        stop_rowcol = maintext().start() if backwards else maintext().end()
        message = ""
        try:
            _do_find_next(
                search_string, backwards, IndexRange(start_rowcol, stop_rowcol)
            )
        except TclRegexCompileError as exc:
            message = str(exc)
        self.display_message(message)
        return "break"

    def search_forwards(self) -> str:
        """Force forward search regardless of reverse flag.

        Returns:
            "break" to avoid calling other callbacks
        """
        self.search_clicked(opposite_dir=SearchDialog.reverse.get())
        return "break"

    def search_backwards(self) -> str:
        """Force backward search regardless of reverse flag.

        Returns:
            "break" to avoid calling other callbacks
        """
        self.search_clicked(opposite_dir=not SearchDialog.reverse.get())
        return "break"

    def count_clicked(self) -> None:
        """Count how many times search string occurs in file (or selection).

        Display count in Search dialog.
        """
        search_string = self.search_box.get()
        if not search_string:
            return
        self.search_box.add_to_history(search_string)

        count_range, range_name = get_search_range()
        if count_range:
            try:
                matches = maintext().find_matches(
                    search_string,
                    count_range,
                    nocase=not SearchDialog.matchcase.get(),
                    regexp=SearchDialog.regex.get(),
                    wholeword=SearchDialog.wholeword.get(),
                )
            except TclRegexCompileError as exc:
                self.display_message(str(exc))
                sound_bell()
                return
            count = len(matches)
            match_str = sing_plur(count, "match", "matches")
            self.display_message(f"Count: {match_str} {range_name}")
        else:
            self.display_message('No text selected for "In selection" count')
            sound_bell()

    def findall_clicked(self) -> None:
        """Callback when Find All button clicked."""
        search_string = self.search_box.get()
        if not search_string:
            return
        self.search_box.add_to_history(search_string)

        find_range, range_name = get_search_range()
        if find_range:
            try:
                matches = maintext().find_matches(
                    search_string,
                    find_range,
                    nocase=not SearchDialog.matchcase.get(),
                    regexp=SearchDialog.regex.get(),
                    wholeword=SearchDialog.wholeword.get(),
                )
            except TclRegexCompileError as exc:
                self.display_message(str(exc))
                sound_bell()
                return
            count = len(matches)
            match_str = sing_plur(count, "match", "matches")
            self.display_message(f"Found: {match_str} {range_name}")
        else:
            matches = []
            self.display_message('No text selected for "In selection" find')
            sound_bell()
            return

        class FindAllCheckerDialog(CheckerDialog):
            """Minimal class inheriting from CheckerDialog so that it can exist
            simultaneously with other checker dialogs."""

        checker_dialog = FindAllCheckerDialog.show_dialog(
            "Search Results", rerun_command=self.findall_clicked
        )
        checker_dialog.reset()
        # Construct opening line describing the search
        desc_reg = "regex" if SearchDialog.regex.get() else "string"
        prefix = f'Search for {desc_reg} "'
        desc = f'{prefix}{search_string}"'
        if SearchDialog.matchcase.get():
            desc += ", matching case"
        if SearchDialog.wholeword.get():
            desc += ", whole words only"
        if SearchDialog.selection.get():
            desc += ", within selection"
        checker_dialog.add_entry(desc, None, len(prefix), len(prefix + search_string))
        checker_dialog.add_entry("")

        for match in matches:
            line = maintext().get(
                f"{match.rowcol.index()} linestart", f"{match.rowcol.index()} lineend"
            )
            end_rowcol = IndexRowCol(
                maintext().index(match.rowcol.index() + f"+{match.count}c")
            )
            hilite_start = match.rowcol.col
            if end_rowcol.row > match.rowcol.row:
                hilite_end = len(line)
            else:
                hilite_end = end_rowcol.col
            checker_dialog.add_entry(
                line, IndexRange(match.rowcol, end_rowcol), hilite_start, hilite_end
            )
        checker_dialog.add_entry("")
        checker_dialog.add_entry("End of search results")

    def replace_clicked(
        self, opposite_dir: bool = False, search_again: bool = False
    ) -> str:
        """Replace the found string with the replacement in the replace box.

        Args:
            opposite_dir: True to go in opposite direction to the "Reverse" flag.
            search_again: True to find next match after replacement.

        Returns:
            "break" to avoid calling other callbacks
        """
        search_string = self.search_box.get()
        replace_string = self.replace_box.get()
        self.replace_box.add_to_history(replace_string)

        try:
            start_index = maintext().index(MARK_FOUND_START)
            end_index = maintext().index(MARK_FOUND_END)
        except tk.TclError:
            sound_bell()
            self.display_message("No text found to replace")
            return "break"

        match_text = maintext().get(start_index, end_index)
        if SearchDialog.regex.get():
            replace_string = get_regex_replacement(
                search_string, replace_string, match_text
            )
        maintext().replace(start_index, end_index, replace_string)
        # "Reverse flag XOR Shift-key" searches backwards
        backwards = SearchDialog.reverse.get() ^ opposite_dir
        # Replace leaves cursor at end of string - if going backwards
        # need to position it at beginning or search could find
        # the same match again.
        if backwards:
            maintext().set_insert_index(IndexRowCol(start_index), focus=False)
        maintext().mark_unset(MARK_FOUND_START, MARK_FOUND_END)
        if search_again:
            find_next(backwards=backwards)
        self.display_message()
        return "break"

    def replaceall_clicked(self) -> None:
        """Callback when Replace All button clicked.

        Replace in whole file or just in selection.
        """
        search_string = self.search_box.get()
        replace_string = self.replace_box.get()
        self.replace_box.add_to_history(replace_string)

        replace_range, range_name = get_search_range()

        if replace_range:
            replace_match = replace_string
            count = 0
            # Use a mark for the end of the range, otherwise early replacements with longer
            # or shorter strings will invalidate the index of the range end.
            maintext().mark_set(MARK_END_RANGE, replace_range.end.index())
            while True:
                try:
                    match = maintext().find_match(
                        search_string,
                        replace_range,
                        nocase=not SearchDialog.matchcase.get(),
                        regexp=SearchDialog.regex.get(),
                        wholeword=SearchDialog.wholeword.get(),
                        backwards=False,
                    )
                except TclRegexCompileError as exc:
                    self.display_message(str(exc))
                    sound_bell()
                    return

                if not match:
                    break
                start_index = match.rowcol.index()
                end_index = maintext().index(start_index + f"+{match.count}c")
                match_text = maintext().get(start_index, end_index)
                if SearchDialog.regex.get():
                    replace_match = get_regex_replacement(
                        search_string, replace_string, match_text
                    )
                maintext().replace(start_index, end_index, replace_match)
                repl_len = len(replace_match)
                maintext().mark_unset(MARK_FOUND_START, MARK_FOUND_END)
                replace_range.start = maintext().rowcol(start_index + f"+{repl_len}c")
                replace_range.end = maintext().rowcol(
                    MARK_END_RANGE
                )  # Refresh end index
                count += 1
            match_str = sing_plur(count, "match", "matches")
            self.display_message(f"Replaced: {match_str} {range_name}")
        else:
            self.display_message('No text selected for "In selection" replace')
            sound_bell()

    def display_message(self, message: str = "") -> None:
        """Display message in Search dialog.

        Args:
            message: Message to be displayed - clears message if arg omitted
        """
        self.message["text"] = message


def show_search_dialog() -> None:
    """Show the Search dialog and set the string in search box
    to the selected text if any (up to first newline)."""
    dlg = SearchDialog.show_dialog()
    dlg.search_box_set(maintext().selected_text().split("\n", 1)[0])


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
        SearchDialog.reverse
    except AttributeError:
        sound_bell()
        return  # Dialog has never been instantiated

    search_string = ""
    # If dialog is visible, then string in search box takes priority over
    # previously-searched-for string.
    if dlg := SearchDialog.get_dialog():
        search_string = dlg.search_box.get()
        dlg.search_box.add_to_history(search_string)
    if not search_string:
        try:
            search_string = preferences.get(PrefKey.SEARCHHISTORY)[0]
        except IndexError:
            sound_bell()
            return  # No Search History

    start_rowcol = get_search_start(backwards)
    stop_rowcol = maintext().start() if backwards else maintext().end()
    try:
        _do_find_next(search_string, backwards, IndexRange(start_rowcol, stop_rowcol))
    except TclRegexCompileError as exc:
        logger.error(str(exc))


def _do_find_next(
    search_string: str, backwards: bool, search_limits: IndexRange
) -> None:
    """Find next occurrence of string from start_point.

    Args:
        search_string: String to search for.
        backwards: True to search backwards.
        start_point: Point to search from.
    """
    try:
        match = maintext().find_match(
            search_string,
            search_limits.start if SearchDialog.wrap.get() else search_limits,
            nocase=not SearchDialog.matchcase.get(),
            regexp=SearchDialog.regex.get(),
            wholeword=SearchDialog.wholeword.get(),
            backwards=backwards,
        )
    except tk.TclError:
        pass
    if match:
        rowcol_end = maintext().rowcol(match.rowcol.index() + f"+{match.count}c")
        maintext().set_insert_index(match.rowcol, focus=False)
        maintext().do_select(IndexRange(match.rowcol, rowcol_end))
        maintext().set_mark_position(MARK_FOUND_START, match.rowcol, gravity=tk.LEFT)
        maintext().set_mark_position(MARK_FOUND_END, rowcol_end, gravity=tk.RIGHT)
    else:
        sound_bell()


def get_search_start(backwards: bool) -> IndexRowCol:
    """Find point to start searching from.

    Start from current insert point unless the following are true:
    We are searching forward;
    Current insert point is at start of previously found match;
    Start of previous match is still selected
    If all are true, advance 1 character to avoid re-finding match.

    Args:
        backwards: True if searching backwards.
    """
    start_rowcol = maintext().get_insert_index()
    if not backwards:
        start_index = start_rowcol.index()
        try:
            at_previous_match = maintext().compare(MARK_FOUND_START, "==", start_index)
        except tk.TclError:
            at_previous_match = False  # MARK not found
        if at_previous_match:
            if sel_ranges := maintext().selected_ranges():
                if maintext().compare(sel_ranges[0].start.index(), "==", start_index):
                    start_rowcol = maintext().rowcol(start_index + "+1c")
    return start_rowcol


def get_regex_replacement(
    search_regex: str, replace_regex: str, match_text: str
) -> str:
    """Find actual replacement string, given the search & replace regexes
    and the matching text.

    Args:
        search_regex:
        replace_regex:
        match_text:

    Returns:
        Replacement string.
    """
    flags = 0 if SearchDialog.matchcase.get() else re.IGNORECASE
    return re.sub(search_regex, replace_regex, match_text, flags=flags)


def get_search_range() -> Tuple[Optional[IndexRange], str]:
    """Get range to search over, based on checkbox settings.

    Returns:
        Range to search over, and string to describe the range.
    """
    replace_range = None
    range_name = ""
    if SearchDialog.selection.get():
        range_name = "in selection"
        if sel_ranges := maintext().selected_ranges():
            replace_range = sel_ranges[0]
    else:
        if SearchDialog.wrap.get():
            range_name = "in entire file"
            replace_range = IndexRange(maintext().start(), maintext().end())
        elif SearchDialog.reverse.get():
            range_name = "from start of file to current location"
            replace_range = IndexRange(
                maintext().start(), maintext().get_insert_index()
            )
        else:
            range_name = "from current location to end of file"
            replace_range = IndexRange(maintext().get_insert_index(), maintext().end())
    return replace_range, range_name
