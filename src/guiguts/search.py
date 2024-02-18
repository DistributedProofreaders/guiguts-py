"""Search/Replace functionality"""

import regex as re
import tkinter as tk
from tkinter import ttk
from typing import Any

from guiguts.checkers import CheckerDialog
from guiguts.maintext import maintext
from guiguts.preferences import preferences
from guiguts.utilities import sound_bell, IndexRowCol, IndexRange, process_accel, is_mac
from guiguts.widgets import ToplevelDialog, Combobox

MARK_FOUND_START = "FoundStart"
MARK_FOUND_END = "FoundEnd"


class SearchDialog(ToplevelDialog):
    """A Toplevel dialog that allows the user to search/replace.

    Attributes:
        reverse: True to search backwards.
        nocase: True to ignore case.
        wrap: True to wrap search round beginning/end of file.
        regex: True to use regex search.
        selection: True to restrict counting, replacing, etc., to selected text.
    """

    # Cannot be initialized here, since Tk root may not yet be created yet
    reverse: tk.BooleanVar
    nocase: tk.BooleanVar
    wholeword: tk.BooleanVar
    wrap: tk.BooleanVar
    regex: tk.BooleanVar
    selection: tk.BooleanVar

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize Search dialog.

        Args:
            root: Tk root
        """

        # Initialize class variables on first instantiation, then remember
        # values for subsequent uses of dialog.
        try:
            SearchDialog.reverse
        except AttributeError:
            SearchDialog.reverse = tk.BooleanVar(value=False)
            SearchDialog.nocase = tk.BooleanVar(value=False)
            SearchDialog.wholeword = tk.BooleanVar(value=False)
            SearchDialog.wrap = tk.BooleanVar(value=False)
            SearchDialog.regex = tk.BooleanVar(value=False)
            SearchDialog.selection = tk.BooleanVar(value=False)

        super().__init__("Search & Replace", *args, **kwargs)

        # Frames
        self.top_frame.rowconfigure(0, weight=0)
        search_frame = ttk.Frame(self.top_frame, padding=1)
        search_frame.grid(row=0, column=0, sticky="NSEW")
        search_frame.columnconfigure(0, weight=1)
        selection_sep = ttk.Separator(self.top_frame, orient=tk.VERTICAL)
        selection_sep.grid(row=0, column=1, rowspan=3, padx=2, sticky="NSEW")
        search2_frame = ttk.Frame(self.top_frame, padding=1)
        search2_frame.grid(row=0, column=2, sticky="NSEW")
        options_frame = ttk.Frame(self.top_frame, padding=1)
        options_frame.grid(row=1, column=0, sticky="NSEW")
        for col in range(0, 5):
            options_frame.columnconfigure(col, weight=1)
        options2_frame = ttk.Frame(self.top_frame, padding=1)
        options2_frame.grid(row=1, column=2, sticky="NSEW")
        options2_frame.columnconfigure(0, weight=1)
        replace_frame = ttk.Frame(self.top_frame, padding=1)
        replace_frame.grid(row=2, column=0, sticky="NSEW")
        replace_frame.columnconfigure(0, weight=1)
        replace2_frame = ttk.Frame(self.top_frame, padding=1)
        replace2_frame.grid(row=2, column=2, sticky="NSEW")
        message_frame = ttk.Frame(self.top_frame, padding=1)
        message_frame.grid(row=3, column=0, columnspan=3, sticky="NSE")

        # Search
        self.search_box = Combobox(search_frame, "SearchHistory")
        self.search_box.grid(row=0, column=0, sticky="NSEW")
        self.search_box.focus()

        search_button = ttk.Button(
            search_frame,
            text="Search",
            default="active",
            takefocus=False,
            command=self.search_clicked,
        )
        search_button.grid(row=0, column=1, sticky="NSEW")
        search_button.bind(
            "<Shift-Button-1>",
            lambda *args: self.search_clicked(opposite_dir=True),
        )
        self.bind("<Return>", lambda *args: self.search_clicked())
        self.bind(
            "<Shift-Return>", lambda *args: self.search_clicked(opposite_dir=True)
        )

        # Count & Find All
        ttk.Button(
            search2_frame,
            text="Find All",
            takefocus=False,
            command=self.findall_clicked,
        ).grid(row=0, column=0, sticky="NSEW")
        ttk.Button(
            search2_frame,
            text="Count",
            takefocus=False,
            command=self.count_clicked,
        ).grid(row=0, column=1, sticky="NSEW")

        # Options
        ttk.Checkbutton(
            options_frame,
            text="Reverse",
            variable=SearchDialog.reverse,
            takefocus=False,
        ).grid(row=0, column=0, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Case insensitive",
            variable=SearchDialog.nocase,
            takefocus=False,
        ).grid(row=0, column=1, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Whole word",
            variable=SearchDialog.wholeword,
            takefocus=False,
        ).grid(row=0, column=2, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Wrap around",
            variable=SearchDialog.wrap,
            takefocus=False,
        ).grid(row=0, column=3, sticky="NSEW")
        ttk.Checkbutton(
            options_frame,
            text="Regex",
            variable=SearchDialog.regex,
            takefocus=False,
        ).grid(row=0, column=4, sticky="NSEW")
        ttk.Checkbutton(
            options2_frame,
            text="In selection",
            variable=SearchDialog.selection,
            takefocus=False,
        ).grid(row=0, column=0)

        # Replace
        self.replace_box = Combobox(replace_frame, "ReplaceHistory")
        self.replace_box.grid(row=0, column=0, sticky="NSEW")

        replace_button = ttk.Button(
            replace_frame,
            text="Replace",
            takefocus=False,
            command=self.replace_clicked,
        )
        replace_button.grid(row=0, column=1, sticky="NSEW")
        replace_button.bind(
            "<Shift-Button-1>",
            lambda *args: self.replace_clicked(opposite_dir=True),
        )

        ttk.Button(
            replace2_frame,
            text="Replace All",
            takefocus=False,
            command=self.replaceall_clicked,
        ).grid(row=0, column=0, sticky="NSEW")

        # Message (e.g. count)
        self.message = ttk.Label(message_frame)
        self.message.grid(row=0, column=0, sticky="NSE")

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
        _do_find_next(search_string, backwards, IndexRange(start_rowcol, stop_rowcol))
        self.message["text"] = ""
        return "break"

    def count_clicked(self) -> None:
        """Count how many times search string occurs in file (or selection).

        Display count in Search dialog.
        """
        search_string = self.search_box.get()
        if not search_string:
            return
        self.search_box.add_to_history(search_string)

        range = None
        count = 0
        if SearchDialog.selection.get():
            range_name = "selection"
            if sel_ranges := maintext().selected_ranges():
                range = sel_ranges[0]
        else:
            range_name = "file"
            range = IndexRange(maintext().start(), maintext().end())
        if range:
            matches = maintext().find_matches(
                search_string,
                range,
                nocase=SearchDialog.nocase.get(),
                regexp=SearchDialog.regex.get(),
                wholeword=SearchDialog.wholeword.get(),
            )
            count = len(matches)
            match_str = "match" if count == 1 else "matches"
            self.message["text"] = f"Count: {count} {match_str} in {range_name}"
        else:
            self.message["text"] = "No text selected"
            sound_bell()

    def findall_clicked(self) -> None:
        """Callback when Find All button clicked."""
        search_string = self.search_box.get()
        if not search_string:
            return
        self.search_box.add_to_history(search_string)

        range = None
        if SearchDialog.selection.get():
            if sel_ranges := maintext().selected_ranges():
                range = sel_ranges[0]
        else:
            range = IndexRange(maintext().start(), maintext().end())
        if range:
            matches = maintext().find_matches(
                search_string,
                range,
                nocase=SearchDialog.nocase.get(),
                regexp=SearchDialog.regex.get(),
                wholeword=SearchDialog.wholeword.get(),
            )
        else:
            matches = []
            sound_bell()

        checker_dialog = ToplevelDialog.show_dialog(CheckerDialog, "Search Results")
        checker_dialog.reset()
        for match in matches:
            line = maintext().get(
                f"{match.rowcol.index()} linestart", f"{match.rowcol.index()} lineend"
            )
            line_prefix = f"{match.rowcol.row}.{match.rowcol.col}: "
            result = line_prefix + line
            end_rowcol = IndexRowCol(
                maintext().index(match.rowcol.index() + f"+{match.count}c")
            )
            hilite_start = match.rowcol.col + len(line_prefix)
            if end_rowcol.row > match.rowcol.row:
                hilite_end = len(result)
            else:
                hilite_end = end_rowcol.col + len(line_prefix)
            checker_dialog.add_entry(
                IndexRange(match.rowcol, end_rowcol), result, hilite_start, hilite_end
            )

    def replace_clicked(self, opposite_dir: bool = False) -> str:
        """Replace the found string with the replacement in the replace box.

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
            return "break"  # No match marked in text, so can't replace

        match_text = maintext().get(start_index, end_index)
        if SearchDialog.regex.get():
            replace_string = replace_regex(search_string, replace_string, match_text)
        maintext().replace(start_index, end_index, replace_string)

        maintext().mark_unset(MARK_FOUND_START, MARK_FOUND_END)
        # "Reverse flag XOR Shift-key" searches backwards
        find_next(backwards=SearchDialog.reverse.get() ^ opposite_dir)
        return "break"

    def replaceall_clicked(self) -> None:
        """Callback when Replace All button clicked.

        Replace in whole file or just in selection.
        """
        search_string = self.search_box.get()
        replace_string = self.replace_box.get()
        self.replace_box.add_to_history(replace_string)

        replace_range = None
        if SearchDialog.selection.get():
            if sel_ranges := maintext().selected_ranges():
                replace_range = sel_ranges[0]
        else:
            replace_range = IndexRange(maintext().start(), maintext().end())

        if replace_range:
            replace_match = replace_string
            while match := maintext().find_match(
                search_string,
                replace_range,
                nocase=SearchDialog.nocase.get(),
                regexp=SearchDialog.regex.get(),
                wholeword=SearchDialog.wholeword.get(),
                backwards=False,
            ):
                start_index = match.rowcol.index()
                end_index = maintext().index(start_index + f"+{match.count}c")
                match_text = maintext().get(start_index, end_index)
                if SearchDialog.regex.get():
                    replace_match = replace_regex(
                        search_string, replace_string, match_text
                    )
                maintext().replace(start_index, end_index, replace_match)
                maintext().mark_unset(MARK_FOUND_START, MARK_FOUND_END)
                replace_range.start = maintext().get_index(start_index + "+1c")
        else:
            sound_bell()


def show_search_dialog() -> None:
    """Show the Search dialog and set the string in search box
    to the selected text if any (up to first newline)."""
    dlg = ToplevelDialog.show_dialog(SearchDialog)
    dlg.search_box_set(maintext().selected_text().split("\n", 1)[0])


def find_next(backwards: bool = False) -> None:
    """Find next occurrence of most recent search string.

    Takes account of current wrap, nocase, regex & wholeword flag settings
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

    try:
        search_string = preferences.get("SearchHistory")[0]
    except IndexError:
        sound_bell()
        return  # No Search History

    start_rowcol = get_search_start(backwards)
    stop_rowcol = maintext().start() if backwards else maintext().end()
    _do_find_next(search_string, backwards, IndexRange(start_rowcol, stop_rowcol))


def _do_find_next(
    search_string: str, backwards: bool, search_limits: IndexRange
) -> None:
    """Find next occurrence of string from start_point.

    Args:
        search_string: String to search for.
        backwards: True to search backwards.
        start_point: Point to search from.
    """
    match = maintext().find_match(
        search_string,
        search_limits.start if SearchDialog.wrap.get() else search_limits,
        nocase=SearchDialog.nocase.get(),
        regexp=SearchDialog.regex.get(),
        wholeword=SearchDialog.wholeword.get(),
        backwards=backwards,
    )
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
                    start_rowcol = maintext().get_index(start_index + "+1c")
    return start_rowcol


def replace_regex(search_regex: str, replace_regex: str, match_text: str) -> str:
    """Find actual replacement string, given the search & replace regexes
    and the matching text.

    Args:
        search_regex:
        replace_regex:
        match_text:

    Returns:
        Replacement string.
    """
    return re.sub(search_regex, replace_regex, match_text)
