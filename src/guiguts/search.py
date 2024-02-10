"""Search/Replace functionality"""

import tkinter as tk
from tkinter import ttk
from typing import Any

from guiguts.checkers import CheckerDialog
from guiguts.maintext import maintext
from guiguts.utilities import sound_bell, IndexRowCol, IndexRange
from guiguts.widgets import ToplevelDialog, Combobox, show_toplevel_dialog


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
    wrap: tk.BooleanVar
    regex: tk.BooleanVar
    selection: tk.BooleanVar

    def __init__(self, root: tk.Tk, *args: Any, **kwargs: Any) -> None:
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
            SearchDialog.wrap = tk.BooleanVar(value=False)
            SearchDialog.regex = tk.BooleanVar(value=False)
            SearchDialog.selection = tk.BooleanVar(value=False)

        self.root = root
        super().__init__(root, "Search & Replace", *args, **kwargs)

        # Frames
        self.top_frame.rowconfigure(0, weight=0)
        search_frame = ttk.Frame(self.top_frame, padding=1)
        search_frame.grid(row=0, column=0, sticky="NSEW")
        search_frame.columnconfigure(0, weight=1)
        search_frame.rowconfigure(0, weight=1)
        selection_frame = ttk.Frame(
            self.top_frame, padding=1, borderwidth=1, relief="groove"
        )
        selection_frame.grid(row=0, column=1, rowspan=2, sticky="NSEW")
        options_frame = ttk.Frame(self.top_frame, padding=1)
        options_frame.grid(row=1, column=0, sticky="NSEW")
        message_frame = ttk.Frame(self.top_frame, padding=1)
        message_frame.grid(row=2, column=0, columnspan=2, sticky="NSE")

        # Search
        self.search_box = Combobox(search_frame, "SearchHistory")
        self.search_box.grid(row=0, column=0, sticky="NSEW")
        self.search_box.focus()
        # Prepopulate search box with selected text (up to first newline)
        search_string = maintext().selected_text().split("\n", 1)[0]
        self.search_box.set(search_string)
        self.search_box.select_range(0, tk.END)
        self.search_box.icursor(tk.END)

        search_button = ttk.Button(
            search_frame,
            text="Search",
            default="active",
            takefocus=False,
            command=self.search_clicked,
        )
        search_button.grid(row=0, column=1, sticky="NSEW")

        self.bind("<Return>", lambda *args: self.search_clicked())
        self.bind(
            "<Shift-Return>", lambda *args: self.search_clicked(opposite_dir=True)
        )
        search_button.bind(
            "<Shift-ButtonRelease-1>",
            lambda *args: self.search_clicked(opposite_dir=True),
        )

        # Count & Find All (optionally limited to selection)
        count_button = ttk.Button(
            selection_frame,
            text="Count",
            default="normal",
            takefocus=False,
            command=self.count_clicked,
        )
        count_button.grid(row=0, column=0, sticky="NSEW")
        findall_button = ttk.Button(
            selection_frame,
            text="Find All",
            default="normal",
            takefocus=False,
            command=self.findall_clicked,
        )
        findall_button.grid(row=0, column=1, sticky="NSEW")
        selection_check = ttk.Checkbutton(
            selection_frame,
            text="In selection",
            variable=SearchDialog.selection,
            takefocus=False,
        )
        selection_check.grid(row=1, column=0, columnspan=2)

        # Options
        reverse_check = ttk.Checkbutton(
            options_frame,
            text="Reverse",
            variable=SearchDialog.reverse,
            takefocus=False,
        )
        reverse_check.grid(row=0, column=0, sticky="NSEW")
        nocase_check = ttk.Checkbutton(
            options_frame,
            text="Case Insensitive",
            variable=SearchDialog.nocase,
            takefocus=False,
        )
        nocase_check.grid(row=0, column=1, sticky="NSEW")
        wrap_check = ttk.Checkbutton(
            options_frame,
            text="Wrap",
            variable=SearchDialog.wrap,
            takefocus=False,
        )
        wrap_check.grid(row=0, column=2, sticky="NSEW")
        regex_check = ttk.Checkbutton(
            options_frame,
            text="Regex",
            variable=SearchDialog.regex,
            takefocus=False,
        )
        regex_check.grid(row=0, column=3, sticky="NSEW")

        # Message (e.g. count)
        self.message = ttk.Label(message_frame)
        self.message.grid(row=0, column=0, sticky="NSE")

    def search_clicked(self, opposite_dir: bool = False, *args: Any) -> str:
        """Search for the string in the search box.

        Returns:
            "break" to avoid calling other callbacks
        """
        search_string = self.search_box.get()
        if not search_string:
            return "break"
        self.search_box.add_to_history(search_string)

        # "Reverse flag XOR Shift-key" searches backwards
        if SearchDialog.reverse.get() ^ opposite_dir:
            incr = ""
            stop_rowcol = maintext().start()
            backwards = True
        else:
            incr = "+1c"
            stop_rowcol = maintext().end()
            backwards = False
        start_rowcol = maintext().rowcol(maintext().get_insert_index().index() + incr)
        # If wrapping, just give start point, not start & end
        search_range: IndexRowCol | IndexRange
        if SearchDialog.wrap.get():
            search_range = start_rowcol
        else:
            search_range = IndexRange(start_rowcol, stop_rowcol)
        match = maintext().find_match(
            search_string,
            search_range,
            nocase=SearchDialog.nocase.get(),
            regexp=SearchDialog.regex.get(),
            backwards=backwards,
        )
        if match:
            rowcol_end = maintext().rowcol(match.rowcol.index() + f"+{match.count}c")
            maintext().set_insert_index(match.rowcol, focus=False)
            maintext().do_select(IndexRange(match.rowcol, rowcol_end))
        else:
            sound_bell()
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
            )
        else:
            matches = []
            sound_bell()

        results = ""
        for match in matches:
            line = maintext().get(
                f"{match.rowcol.index()} linestart", f"{match.rowcol.index()} lineend"
            )
            results += f"{match.rowcol.row}.{match.rowcol.col}: {line}\n"

        self.destroy()
        checker_dialog = show_toplevel_dialog(
            CheckerDialog, self.root, "Search Results"
        )
        checker_dialog.set_text(results)
