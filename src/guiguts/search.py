"""Search/Replace functionality"""

import tkinter as tk
from tkinter import ttk
from typing import Any

from guiguts.widgets import ToplevelDialog


class SearchDialog(ToplevelDialog):
    """A Toplevel dialog that allows the user to search/replace."""

    def __init__(self, parent: tk.Tk, *args: Any, **kwargs: Any) -> None:
        """Initialize Search dialog."""
        super().__init__(parent, "Search & Replace", *args, **kwargs)
        search_frame = ttk.Frame(self.top_frame)
        search_frame.grid(row=0, column=0, sticky="NSEW")
        search_frame.columnconfigure(0, weight=1)
        search_frame.rowconfigure(0, weight=1)
        self.search_box = ttk.Combobox(search_frame)
        self.search_box.grid(row=0, column=0, sticky="NSEW")
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

    def search_clicked(self) -> None:
        """Callback when Search button clicked."""
        pass

    def count_clicked(self) -> None:
        """Callback when Count button clicked."""
        pass

    def findall_clicked(self) -> None:
        """Callback when Find All button clicked."""
        pass
