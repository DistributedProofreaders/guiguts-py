"""Common code/classes relating to Tk widgets."""

import tkinter as tk
from tkinter import simpledialog, ttk
from typing import Any, Optional, TypeVar

from guiguts.preferences import preferences

NUM_HISTORY = 10


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
        self.bind("<Escape>", lambda event: self.destroy())
        self.title(title)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.top_frame: ttk.Frame = ttk.Frame(self, padding=5)
        self.top_frame.columnconfigure(0, weight=1)
        self.top_frame.rowconfigure(0, weight=1)
        self.top_frame.grid(row=0, column=0, sticky="NSEW")
        grab_focus(self)


class Combobox(ttk.Combobox):
    """A ttk Combobox with some convenience functions.

    Attributes:
        prefs_key: Key to saved history in prefs.
    """

    def __init__(
        self, parent: tk.Widget, prefs_key: str, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(parent, *args, **kwargs)
        self.prefs_key = prefs_key
        self["values"] = preferences.get(self.prefs_key)

    def add_to_history(self, string: str) -> None:
        """Store given string in history list.

        Stores string in prefs as well as widget drop-down.

        Args:
            string: String to add to list.
        """
        if string:
            history = preferences.get(self.prefs_key)
            try:
                history.remove(string)
            except ValueError:
                pass  # OK if string wasn't in list
            history.insert(0, string)
            del history[NUM_HISTORY:]
            preferences.set(self.prefs_key, history)
            self["values"] = history


def grab_focus(
    toplevel: tk.Toplevel | tk.Tk,
    focus_widget: Optional[tk.Widget] = None,
    icon_deicon: bool = False,
) -> None:
    """Arcane calls to force window manager to put toplevel window
    to the front and make it active, optionally setting focus to
    specific widget.

    Args:
        toplevel: Toplevel widget to receive focus
        focus_widget: Optional widget within the toplevel tree to take keyboard focus
        icon_deicon: True if iconify/deiconify hack required
    """
    toplevel.lift()
    if icon_deicon:
        toplevel.iconify()
        toplevel.deiconify()
    toplevel.focus_force()
    if focus_widget is not None:
        focus_widget.focus_set()


# Dictionary of ToplevelDialog objects, keyed by class name.
# Used to ensure only one instance of any dialog is created.
_toplevel_dialogs: dict[str, ToplevelDialog] = {}

TlDlg = TypeVar("TlDlg", bound=ToplevelDialog)


def show_toplevel_dialog(dlg_cls: type[TlDlg], root: tk.Tk) -> TlDlg:
    """Show the given dialog, or create it if it doesn't exist.

    Args:
        dlg_cls: Class of dialog to be created - subclass of ToplevelDialog.
        root: Tk root.
    """
    global _toplevel_dialogs
    dlg_name = dlg_cls.__name__
    if dlg_name in _toplevel_dialogs and _toplevel_dialogs[dlg_name].winfo_exists():
        _toplevel_dialogs[dlg_name].deiconify()
    else:
        _toplevel_dialogs[dlg_name] = dlg_cls(root)  # type: ignore[call-arg]
    return _toplevel_dialogs[dlg_name]  # type: ignore[return-value]
