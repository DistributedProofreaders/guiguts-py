"""Common code/classes relating to Tk widgets."""

import regex as re
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


TlDlg = TypeVar("TlDlg", bound="ToplevelDialog")


class ToplevelDialog(tk.Toplevel):
    """Basic dialog with a frame - to avoid duplicated code.

    Dialogs inheriting from ToplevelDialog can add widgets inside
    `self.frame` (which resizes with the dialog)

    Attributes:
        top_frame: Frame widget in grid(0,0) position to contain widgets.
    """

    # Dictionary of ToplevelDialog objects, keyed by class name.
    # Used to ensure only one instance of any dialog is created.
    _toplevel_dialogs: dict[str, "ToplevelDialog"] = {}

    def __init__(
        self,
        title: str,
        resize_x: bool = True,
        resize_y: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the dialog.

        Args:
            title: Dialog title.
            resize_x: True(default) to allow resizing and remembering of the dialog width.
            resize_y: True(default) to allow resizing and remembering of the dialog height.
        """
        super().__init__(*args, **kwargs)
        self.bind("<Escape>", lambda event: self.destroy())
        self.title(title)
        self.resizable(resize_x, resize_y)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.top_frame: ttk.Frame = ttk.Frame(self, padding=5)
        self.top_frame.columnconfigure(0, weight=1)
        self.top_frame.rowconfigure(0, weight=1)
        self.top_frame.grid(row=0, column=0, sticky="NSEW")

        self._do_config()
        self.save_config = False
        self.bind("<Configure>", self._handle_config)

        grab_focus(self)

    @classmethod
    def show_dialog(cls, dlg_cls: type[TlDlg], title: Optional[str] = None) -> TlDlg:
        """Show the given dialog, or create it if it doesn't exist.

        Args:
            dlg_cls: Class of dialog to be created - subclass of ToplevelDialog.
            title: Dialog title.
        """
        dlg_name = dlg_cls.__name__
        if cls.get_dialog(dlg_cls):
            ToplevelDialog._toplevel_dialogs[dlg_name].deiconify()
        else:
            if title is not None:
                ToplevelDialog._toplevel_dialogs[dlg_name] = dlg_cls(title)  # type: ignore[call-arg]
            else:
                ToplevelDialog._toplevel_dialogs[dlg_name] = dlg_cls()  # type: ignore[call-arg]
        return ToplevelDialog._toplevel_dialogs[dlg_name]  # type: ignore[return-value]

    @classmethod
    def get_dialog(cls, dlg_cls: type[TlDlg]) -> Optional[TlDlg]:
        """Return the given dialog if it exists.

        Args:
            dlg_cls: Class of dialog to be created - subclass of ToplevelDialog.
        """
        dlg_name = dlg_cls.__name__
        if (
            dlg_name in ToplevelDialog._toplevel_dialogs
            and ToplevelDialog._toplevel_dialogs[dlg_name].winfo_exists()
        ):
            return ToplevelDialog._toplevel_dialogs[dlg_name]  # type: ignore[return-value]
        else:
            return None

    def _do_config(self) -> None:
        """Configure the geometry of the ToplevelDialog.

        It is not possible (easy) to set just the width or height at this point,
        since the `geometry` method doesn't support that, and the current width
        or height can't be queried (in order to keep it unchanged) because the
        dialog doesn't yet have any contents, so no size.

        The parent dialog is responsible for setting the size correctly in the
        case of a dialog that is only resizable in one direction, using
        the config_width/config_height methods.
        """
        if geometry := self._get_pref_geometry():
            x_resize, y_resize = self.resizable()
            if not (x_resize and y_resize):
                geometry = re.sub(r"^\d+x\d+", "", geometry)
            self.geometry(geometry)

    def config_width(self) -> None:
        """Configure the width of the dialog to the Prefs value,
        leaving the height unchanged.

        This must not be called until all the contents of the dialog have
        been created & managed.
        """
        if geometry := self._get_pref_geometry():
            width = re.sub(r"x.+", "", geometry)
            self.update()  # Needed before querying geometry
            new_geometry = re.sub(r"^\d+", width, self.geometry())
            self.geometry(new_geometry)

    def config_height(self) -> None:
        """Configure the height of the dialog to the Prefs value,
        leaving the width unchanged.

        This must not be called until all the contents of the dialog have
        been created & managed.
        """
        if geometry := self._get_pref_geometry():
            height = re.sub(r"^\d+x(\d+).+", r"\1", geometry)
            self.update()  # Needed before querying geometry
            new_geometry = re.sub(r"(?<=x)\d+", height, self.geometry())
            self.geometry(new_geometry)

    def _get_pref_geometry(self) -> str:
        """Get preferred dialog geometry from Prefs file.

        Returns:
            String containing geometry, or empty string if none stored.
        """
        config_dict = preferences.get("DialogGeometry")
        try:
            return config_dict[self.__class__.__name__]
        except KeyError:
            return ""

    def _handle_config(self, event: tk.Event) -> None:
        """Callback from dialog <Configure> event.

        By setting flag now, and queuing calls to _save_config,
        we ensure the flag will be true for the first call to
        _save_config when process becomes idle."""
        self.save_config = True
        self.after_idle(self._save_config)

    def _save_config(self) -> None:
        """Only save geometry when process becomes idle.

        Several calls to this may be queued by config changes during
        dialog creation and resizing. Only the first will actually
        do a save, because the flag will only be true on the first call."""
        if self.save_config:
            config_dict = preferences.get("DialogGeometry")
            key = self.__class__.__name__
            config_dict[key] = self.geometry()
            preferences.set("DialogGeometry", config_dict)
            self.save_config = False


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
