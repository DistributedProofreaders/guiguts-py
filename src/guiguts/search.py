"""Search/Replace functionality"""

import tkinter as tk
from tkinter import ttk
from typing import Any

from guiguts.maintext import maintext, IndexRowCol, IndexRange
from guiguts.utilities import sound_bell
from guiguts.widgets import ToplevelDialog


class SearchDialog(ToplevelDialog):
    """A Toplevel dialog that allows the user to search/replace."""

    reverse: tk.BooleanVar
    nocase: tk.BooleanVar
    wrap: tk.BooleanVar
    regex: tk.BooleanVar

    def __init__(self, parent: tk.Tk, *args: Any, **kwargs: Any) -> None:
        """Initialize Search dialog."""
        super().__init__(parent, "Search & Replace", *args, **kwargs)
        search_frame = ttk.Frame(self.top_frame)
        search_frame.grid(row=0, column=0, sticky="NSEW")
        search_frame.columnconfigure(0, weight=1)
        search_frame.rowconfigure(0, weight=1)
        self.search_box = ttk.Combobox(search_frame)
        self.search_box.grid(row=0, column=0, sticky="NSEW")
        self.search_box.focus()
        search_button = ttk.Button(
            search_frame, text="Search", default="active", command=self.search_clicked
        )
        search_button.grid(row=0, column=1, sticky="NSEW")
        count_button = ttk.Button(
            search_frame, text="Count", default="normal", command=self.count_clicked
        )
        count_button.grid(row=0, column=2, sticky="NSEW")
        findall_button = ttk.Button(
            search_frame,
            text="Find All",
            default="normal",
            command=self.findall_clicked,
        )
        findall_button.grid(row=0, column=3, sticky="NSEW")
        self.bind("<Return>", self.search_clicked)
        self.bind("<Shift-Return>", self.opposite_dir_search)
        search_button.bind("<Shift-ButtonRelease-1>", self.opposite_dir_search)

        SearchDialog.reverse = tk.BooleanVar(value=False)
        SearchDialog.nocase = tk.BooleanVar(value=False)
        SearchDialog.wrap = tk.BooleanVar(value=False)
        SearchDialog.regex = tk.BooleanVar(value=False)

        options_frame = ttk.Frame(self.top_frame)
        options_frame.grid(row=1, column=0, sticky="NSEW")
        reverse_check = ttk.Checkbutton(
            options_frame, text="Reverse", variable=SearchDialog.reverse
        )
        reverse_check.grid(row=0, column=0, sticky="NSEW")
        nocase_check = ttk.Checkbutton(
            options_frame, text="Case Insensitive", variable=SearchDialog.nocase
        )
        nocase_check.grid(row=0, column=1, sticky="NSEW")
        wrap_check = ttk.Checkbutton(
            options_frame, text="Wrap", variable=SearchDialog.wrap
        )
        wrap_check.grid(row=0, column=2, sticky="NSEW")
        regex_check = ttk.Checkbutton(
            options_frame, text="Regex", variable=SearchDialog.regex
        )
        regex_check.grid(row=0, column=3, sticky="NSEW")

    def search_clicked(self, *args: Any) -> None:
        """Callback when Search button clicked."""
        search_string = self.search_box.get()
        count_var = tk.IntVar()
        if SearchDialog.reverse.get():
            incr = ""
            stopindex = "" if SearchDialog.wrap.get() else "1.0"
            backwards = True
        else:
            incr = "+1c"
            stopindex = "" if SearchDialog.wrap.get() else "end"
            backwards = False
        startindex = maintext().get_insert_index().index() + incr
        found_start = maintext().search(
            search_string,
            startindex,
            stopindex=stopindex,
            count=count_var,
            nocase=SearchDialog.nocase.get(),
            regexp=SearchDialog.regex.get(),
            backwards=backwards,
        )
        if found_start:
            rowcol_start = IndexRowCol(found_start)
            rowcol_end = IndexRowCol(
                maintext().index(found_start + f"+{count_var.get()}c")
            )
            maintext().set_insert_index(rowcol_start, focus=False)
            maintext().do_select(IndexRange(rowcol_start, rowcol_end))
        else:
            sound_bell()

    def opposite_dir_search(self, *args: Any) -> str:
        """Search in direction opposite to "reverse flag" setting.

        Returns:
            "break" so that Button-1 callback is not executed"""
        SearchDialog.reverse.set(not SearchDialog.reverse.get())
        self.search_clicked()
        SearchDialog.reverse.set(not SearchDialog.reverse.get())
        return "break"

    def count_clicked(self) -> None:
        """Callback when Count button clicked."""
        pass

    def findall_clicked(self) -> None:
        """Callback when Find All button clicked."""
        pass
