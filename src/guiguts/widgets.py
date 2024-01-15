"""Common code/classes relating to widgets."""

import tkinter as tk
from tkinter import simpledialog, ttk
from typing import Any, Optional


class OkCancelDialog(simpledialog.Dialog):
    """A Tk simpledialog with OK and Cancel buttons and some overridden
    methods to avoid duplicated application code.
    """

    def __init__(self, parent: tk.Tk, title: str) -> None:
        """Initialize the dialog."""
        super().__init__(parent, title)

    def buttonbox(self) -> None:
        """Override default to set up OK and Cancel buttons."""
        frame = ttk.Frame(self, padding=5)
        frame.pack()
        ok_button = ttk.Button(
            frame, text="OK", default="active", command=self.ok_pressed
        )
        ok_button.grid(column=1, row=1)
        cancel_button = ttk.Button(
            frame, text="Cancel", default="normal", command=self.cancel_pressed
        )
        cancel_button.grid(column=2, row=1)
        self.bind("<Return>", lambda event: self.ok_pressed())
        self.bind("<Escape>", lambda event: self.cancel_pressed())

    def ok_press_complete(self) -> bool:
        """Complete processing needed when OK is pressed, e.g. storing
        dialog values in persistent variables.

        Will usually be overridden.

            Returns:
                True if OK to close dialog, False if not
        """
        return True

    def ok_pressed(self) -> None:
        """Update page label settings from the dialog."""
        if self.ok_press_complete():
            self.destroy()

    def cancel_pressed(self) -> None:
        """Destroy dialog."""
        self.destroy()


class ToplevelDialog(tk.Toplevel):
    """Basic dialog with a frame - to avoid duplicated code.

    Dialogs inheriting from ToplevelDialog can add widgets inside
    `self.frame` (which resizes with the dialog)

    Attributes:
        top_frame: Frame widget in grid(0,0) position to contain widgets.
    """

    def __init__(self, root: tk.Tk, title: str, *args: Any, **kwargs: Any) -> None:
        """Initialize the dialog."""
        super().__init__(root, *args, **kwargs)
        self.root = root
        self.bind("<Escape>", lambda event: self.destroy())
        self.title(title)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.top_frame: ttk.Frame = ttk.Frame(self)
        self.top_frame.columnconfigure(0, weight=1)
        self.top_frame.rowconfigure(0, weight=1)
        self.top_frame.grid(row=0, column=0, sticky="NSEW")
        grab_focus(self, self.root)


def grab_focus(
    toplevel: tk.Toplevel | tk.Tk, root: tk.Tk, widget: Optional[tk.Widget] = None
) -> None:
    """Arcane calls to force window manager to put window
    to the front and make it active.

    Args:
        toplevel: Toplevel widget to receive focus
        root: Root window, required for iconify/deiconify hack
        widget: Optional widget within the toplevel tree to take keyboard focus
    """
    toplevel.lift()
    root.call("wm", "iconify", toplevel)
    root.call("wm", "deiconify", toplevel)
    toplevel.focus_force()
    if widget is not None:
        widget.focus_set()
