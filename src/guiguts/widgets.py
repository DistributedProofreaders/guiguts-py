"""Common code/classes relating to Tk widgets."""

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from tkinter import font as tk_font
from typing import Any, Optional, TypeVar, Callable
import webbrowser

import darkdetect  # type: ignore[import-untyped]
import regex as re

from guiguts.preferences import preferences, PrefKey, PersistentString
from guiguts.root import root, RootWindowState
from guiguts.utilities import is_windows, is_mac, process_accel, cmd_ctrl_string, is_x11

NUM_HISTORY = 10


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
        disable_geometry_save: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the dialog.

        Args:
            title: Dialog title.
            resize_x: True(default) to allow resizing and remembering of the dialog width.
            resize_y: True(default) to allow resizing and remembering of the dialog height.
            disable_geometry_save: True to disable handling of configure events, i.e. so
                geometry will not be saved. For complex geometry handling, e.g. Search dialog,
                which can change size and has restrictions on resizability, set this to True,
                then create widgets in dialog, and only then call allow_geometry_save()
        """
        self.disable_geometry_save = disable_geometry_save

        super().__init__(**kwargs)
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

        # Bind help key to open obligatory manual page
        assert hasattr(self, "manual_page")
        self.bind("<F1>", lambda event: self.show_manual_page())

        self.wm_withdraw()
        self.wm_attributes("-fullscreen", False)
        # In fullscreen mode on macOS, dialogs become *tabs* on the root
        # window unless marked as transient. Side-effect of this is that
        # dialogs are always-on-top windows. Only mark as transient on Mac,
        # and then only when in fullscreen mode.
        if (
            is_mac()
            and preferences.get(PrefKey.ROOT_GEOMETRY_STATE)
            == RootWindowState.FULLSCREEN
        ):
            self.transient(root())
        self.wm_deiconify()

        self.tooltip_list: list[ToolTip] = []
        # Bind to top_frame being destroyed because if binding is to dialog,
        # function will be called for every child of dialog due to their
        # "top level" bind tag
        self.top_frame.bind("<Destroy>", lambda _: self.on_destroy())

        grab_focus(self)

    def __new__(cls, *args: Any, **kwargs: Any) -> "ToplevelDialog":
        """Ensure ToplevelDialogs are not instantiated directly."""
        if cls is ToplevelDialog:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls)

    @classmethod
    def show_dialog(
        cls: type[TlDlg],
        **kwargs: Any,
    ) -> TlDlg:
        """Show the instance of this dialog class, or create it if it doesn't exist.

        Args:
            title: Dialog title.
            kwargs: Optional kwargs to pass to dialog constructor.
        """
        # If dialog already exists, deiconify it
        dlg_name = cls.__name__
        # Can we just deiconify dialog & reset it?
        if dlg := cls.get_dialog():
            dlg.deiconify()
            dlg.reset()
        # Or do we need to create it?
        else:
            dlg = cls(**kwargs)
        ToplevelDialog._toplevel_dialogs[dlg_name] = dlg
        return dlg

    @classmethod
    def get_dialog(cls) -> Optional[TlDlg]:
        """Return the one occurrence of this dialog class if it exists.

        Returns:
            The one instance of this dialog type, or None if it's not currently shown.
        """
        dlg_name = cls.__name__
        if (
            dlg_name in ToplevelDialog._toplevel_dialogs
            and ToplevelDialog._toplevel_dialogs[dlg_name].winfo_exists()
        ):
            return ToplevelDialog._toplevel_dialogs[dlg_name]  # type: ignore[return-value]
        return None

    @classmethod
    def get_mark_prefix(cls) -> str:
        """Use reduced dialog name for common part of mark names.
        This ensures each dialog uses unique mark names and does not clash
        with another dialog.
        """
        return cls.__name__.removesuffix("Dialog")

    def register_tooltip(self, tooltip: "ToolTip") -> None:
        """Register a tooltip as being attached to a widget in this
        TopleveDialog so it can be destroyed when the dialog is destroyed.

        Args:
            tooltip - the ToolTip widget to register"""
        self.tooltip_list.append(tooltip)

    def key_bind(self, accel: str, handler: Callable[[], None]) -> None:
        """Convert given accelerator string to a key-event string and bind both
        the upper & lower case versions to the given handler.

        Args:
            accel: Accelerator string, e.g. "Cmd/Ctrl+Z", to trigger call to ``handler``.
            handler: Callback function to be bound to ``accel``.
        """
        _, key_event = process_accel(accel)
        lk = re.sub("[A-Z]>?$", lambda m: m.group(0).lower(), key_event)
        self.bind(lk, lambda _: handler())
        uk = re.sub("[a-z]>?$", lambda m: m.group(0).upper(), key_event)
        self.bind(uk, lambda _: handler())

    def on_destroy(self) -> None:
        """Tidy up when the dialog is destroyed.

        Also calls the reset method.
        """
        for tooltip in self.tooltip_list:
            tooltip.destroy()
        self.tooltip_list = []
        self.reset()

    def reset(self) -> None:
        """Reset the dialog.

        Can be overridden if derived dialog creates marks, tags, etc., that need removing.
        """

    @classmethod
    def close_all(cls) -> None:
        """Close all open ToplevelDialogs."""
        for dlg in ToplevelDialog._toplevel_dialogs.values():
            if dlg.winfo_exists():
                dlg.destroy()
                dlg.reset()
        ToplevelDialog._toplevel_dialogs.clear()

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
            cur_geometry = self.geometry()
            new_geometry = re.sub(r"^\d+", width, cur_geometry)
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
        return self.get_dialog_pref(PrefKey.DIALOG_GEOMETRY)

    def allow_geometry_save(self) -> None:
        """Enable the saving of geometry changes via Configure events.

        See __init__ docstring for details of use.
        """
        self.update()
        self.disable_geometry_save = False

    def _handle_config(self, _event: tk.Event) -> None:
        """Callback from dialog <Configure> event.

        By setting flag now, and queuing calls to _save_config,
        we ensure the flag will be true for the first call to
        _save_config when process becomes idle."""
        if self.disable_geometry_save:
            return
        self.save_config = True
        self.after_idle(self._save_config)

    def _save_config(self) -> None:
        """Only save geometry when process becomes idle.

        Several calls to this may be queued by config changes during
        dialog creation and resizing. Only the first will actually
        do a save, because the flag will only be true on the first call."""
        if self.save_config:
            self.save_dialog_pref(PrefKey.DIALOG_GEOMETRY, self.geometry())
            self.save_config = False

    def save_dialog_pref(self, key: PrefKey, value: Any) -> None:
        """Save a preference that is unique to the dialog class.

        Dictionary indexed by classname is saved in the prefs file,
        so a preference can be saved per dialog.

        Args:
            key: Preference to be saved.
            value: New value for preference.
        """
        config_dict = preferences.get(key)
        config_dict[self.__class__.__name__] = value
        preferences.set(key, config_dict)

    def get_dialog_pref(self, key: PrefKey) -> Any:
        """Get a preference that is unique to the dialog class.

        Dictionary in prefs file is indexed by classname,
        so a preference can be obtained per dialog.

        Args:
            key: Preference to be fetched.

        Returns:
            Preference value.
        """
        config_dict = preferences.get(key)
        try:
            return config_dict[self.__class__.__name__]
        except KeyError:
            return None

    def show_manual_page(self) -> None:
        """Show the manual page for the dialog."""
        try:
            suffix = type(self).manual_page  # type:ignore[attr-defined]
        except AttributeError:
            return
        prefix = "https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_2_Manual/"
        webbrowser.open(prefix + suffix)


class OkApplyCancelDialog(ToplevelDialog):
    """A ToplevelDialog with OK, Apply & Cancel buttons."""

    def __init__(self, title: str, **kwargs: Any) -> None:
        """Initialize the dialog."""
        super().__init__(title, **kwargs)
        button_frame = ttk.Frame(self, padding=5)
        button_frame.grid(row=1, column=0, sticky="NSEW")
        button_frame.columnconfigure(0, weight=1)
        ok_button = ttk.Button(
            button_frame,
            text="OK",
            default="active",
            command=self.ok_pressed,
            takefocus=False,
        )
        ok_button.grid(row=0, column=0)
        button_frame.columnconfigure(1, weight=1)
        apply_button = ttk.Button(
            button_frame,
            text="Apply",
            default="normal",
            command=self.apply_changes,
            takefocus=False,
        )
        apply_button.grid(row=0, column=1)
        button_frame.columnconfigure(2, weight=1)
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            default="normal",
            command=self.cancel_pressed,
            takefocus=False,
        )
        cancel_button.grid(row=0, column=2)
        self.bind("<Return>", lambda event: self.ok_pressed())
        self.bind("<Escape>", lambda event: self.cancel_pressed())

    def apply_changes(self) -> bool:
        """Complete processing needed when Apply/OK are pressed, e.g. storing
        dialog values in persistent variables.

        Will usually be overridden.

            Returns:
                True if OK to close dialog, False if not
        """
        return True

    def ok_pressed(self) -> None:
        """Apply changes and destroy dialog."""
        if self.apply_changes():
            self.destroy()

    def cancel_pressed(self) -> None:
        """Destroy dialog."""
        self.destroy()


class Combobox(ttk.Combobox):
    """A ttk Combobox with some convenience functions.

    Can also set font, which base ttk.Combobox can't.
    Uses code from https://stackoverflow.com/questions/43086378/how-to-modify-ttk-combobox-fonts

    Attributes:
        prefs_key: Key to saved history in prefs.
    """

    def __init__(
        self, parent: tk.Widget, prefs_key: PrefKey, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(parent, *args, **kwargs)
        self._handle_popdown_font()
        self.prefs_key = prefs_key
        self["values"] = preferences.get(self.prefs_key)
        # If user selects value from dropdown, add it to top of history list
        self.bind("<<ComboboxSelected>>", lambda *_: self.add_to_history(self.get()))

    def _handle_popdown_font(self) -> None:
        """Handle popdown font
        Note: https://github.com/nomad-software/tcltk/blob/master/dist/library/ttk/combobox.tcl#L270
        """
        #   grab (create a new one or get existing) popdown
        popdown = self.tk.eval(f"ttk::combobox::PopdownWindow {self}")
        #   configure popdown font
        self.tk.call(f"{popdown}.f.l", "configure", "-font", self["font"])

    def configure(  # type:ignore[override] # pylint: disable=signature-differs
        self, cnf: dict[str, Any], **kw: dict[str, Any]
    ) -> None:
        """Configure resources of a widget. Overridden!

        The values for resources are specified as keyword
        arguments. To get an overview about
        the allowed keyword arguments call the method keys.
        """

        #   default configure behavior
        self._configure("configure", cnf, kw)  # type:ignore[attr-defined]
        #   if font was configured - configure font for popdown as well
        if "font" in kw or "font" in cnf:
            self._handle_popdown_font()

    #   keep overridden shortcut
    config = configure  # type:ignore[assignment]

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

    def display_latest_value(self) -> None:
        """Display most recent value (if any) from history list."""
        try:
            self.current(0)
        except tk.TclError:
            self.set("")


class PathnameCombobox(Combobox):
    """A Combobox with better display for pathnames.

    Dropdown menu is wide enough to display all entries.
    Entry field displays the right-hand end of the pathname.
    Tooltip displays full contents of entry field.
    """

    def __init__(
        self,
        parent: tk.Widget,
        history_key: PrefKey,
        value_key: PrefKey,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize PathnameCombox widget.

        Args:
            parent: Parent widget.
            history_key: Key of preference to store history.
            value_key: Key of preference to store value.
        """
        kwargs["textvariable"] = PersistentString(value_key)
        super().__init__(parent, history_key, *args, **kwargs)
        self.bind("<ButtonPress>", lambda _e: self.dropdown_width_configure())
        self.bind("<Configure>", lambda _e: self.dropdown_width_configure())
        self.tooltip = ToolTip(self, "")
        # Set up callback whenever value preference is changed
        preferences.set_callback(value_key, self.update_callback)
        self.update_callback(preferences.get(value_key))

    def dropdown_width_configure(self) -> None:
        """Configure width of combo dropdown to be sufficient to
        display the widest entry, so all entries are visible.
        And show tail end of file path."""
        long: str = max(self.cget("values"), key=len)

        font = tk_font.nametofont(str(self.cget("font")))
        width = max(0, font.measure(long.strip() + "pad") - self.winfo_width())

        ttk.Style().configure("TCombobox", postoffset=(0, 0, width, 0))
        self.xview_moveto(1.0)

    def update_callback(self, value: str) -> None:
        """Update dropdown width and tooltip when value is updated."""
        if self.winfo_exists():
            self.dropdown_width_configure()
            try:
                self.tooltip.destroy()
            except tk.TclError:
                pass  # OK if tooltip doesn't exist
            self.tooltip = ToolTip(self, value)


class Notebook(ttk.Notebook):
    """A ttk Notebook with some additional bindings.

    In particular, provide keyboard bindings for switching tabs. Note that
    bindings are made to parent dialog, i.e. code assumes that there is
    nothing else in the dialog that the bindings will clash with.
    """

    def __init__(self, parent: tk.Widget, *args: Any, **kwargs: Any) -> None:
        """Initialize Notebook - standard ttk.Notebook with extra bindings."""
        super().__init__(parent, *args, **kwargs)
        self.toplevel = self.winfo_toplevel()

        # On Macs, bind Command-Option with Left/Right arrows to switch tabs
        # Standard Ctrl-tab & Shift-Ctrl-tab are inbuilt on all systems
        if is_mac():
            self.toplevel.bind(
                "<Command-Option-Left>",
                lambda _: self.select_tab((self.index(tk.CURRENT) - 1)),
            )
            self.toplevel.bind(
                "<Command-Option-Right>",
                lambda _: self.select_tab((self.index(tk.CURRENT) + 1)),
            )

    def add(self, child: tk.Widget, *args: Any, **kwargs: Any) -> None:
        """Override add method to bind Cmd/Ctrl-digit keyboard shortcuts."""
        super().add(child, *args, **kwargs)
        tab = self.index(tk.END)
        if 1 <= tab <= 9:
            self.toplevel.bind(
                f"<{cmd_ctrl_string()}-Key-{tab}>",
                lambda _, tab=tab: self.select_tab(tab - 1),  # type:ignore[misc]
            )

    def select_tab(self, tab: int) -> str:
        """Select specific tab (for use with keyboard bindings
        to avoid macOS bug).

        Args:
            tab: zero-based tab number, wraps around from last tab to first.

        Returns:
            "break" to avoid default behavior (bookmark shortcuts)
        """
        tab %= self.index(tk.END)
        self.select(tab)
        self.hide(tab)  # Hide then reselect forces macOS to display it
        self.select(tab)
        return "break"


class ToolTip:
    """Create a tooltip for a widget.

    Actual tooltip Toplevel window isn't created until it's needed."""

    def __init__(
        self,
        widget: tk.Widget,
        msg: str,
        use_pointer_pos: bool = False,
    ):
        """Create a ToolTip.

        Args:
            widget : The widget this tooltip is assigned to
            msg : String to display in tooltip
        """
        self.widget = widget
        self.widget_tl = widget.winfo_toplevel()

        # If widget part of a dialog, register so tooltip can be deleted when dialog destroyed
        if issubclass(type(self.widget_tl), ToplevelDialog):
            self.widget_tl.register_tooltip(self)  # type: ignore[union-attr]
        self.use_pointer_pos = use_pointer_pos

        self.delay = 0.5
        self.inside = False
        self.msg = msg
        self.width = self.height = 0
        self.tooltip_window: Optional[tk.Toplevel] = None
        self.enter_bind = self.widget.bind("<Enter>", self.on_enter, add="+")
        self.leave_bind = self.widget.bind("<Leave>", self.on_leave, add="+")
        self.press_bind = self.widget.bind("<ButtonRelease>", self.on_leave, add="+")

    def _create_tooltip(self) -> None:
        """Actually create the toolip if it doesn't exist"""
        if self.tooltip_window is not None:
            return
        self.tooltip_window = tk.Toplevel()
        self.tooltip_window.overrideredirect(True)
        # Make tooltip transparent initially, in case it appears briefly on startup
        self.tooltip_window.wm_attributes("-alpha", 0.0)
        # Move it off screen too - belt & suspenders - "alpha" not necessarily supported
        self.tooltip_window.geometry("+-1000+-1000")
        frame = ttk.Frame(self.tooltip_window, borderwidth=1, relief=tk.SOLID)
        frame.grid(padx=1, pady=1)
        ttk.Label(frame, text=self.msg).grid()
        self.tooltip_window.update_idletasks()
        self.width = self.tooltip_window.winfo_width()
        self.height = self.tooltip_window.winfo_height()
        # Hide tooltip then make non-transparent for later use
        self.tooltip_window.withdraw()
        self.tooltip_window.wm_attributes("-alpha", 1.0)

    def on_enter(self, _event: tk.Event) -> None:
        """When mouse enters widget, prepare to show tooltip"""
        self._create_tooltip()
        assert self.tooltip_window is not None
        self.inside = True
        self.tooltip_window.after(int(self.delay * 1000), self._show)

    def on_leave(self, _event: tk.Event | None = None) -> None:
        """Hides tooltip when mouse leaves, or button pressed."""
        self._create_tooltip()
        assert self.tooltip_window is not None
        self.inside = False
        if self.tooltip_window.winfo_exists():
            self.tooltip_window.withdraw()

    def _show(self) -> None:
        """Displays the ToolTip if mouse still inside."""
        if not (self.inside and self.widget.winfo_exists()):
            return
        self._create_tooltip()
        assert self.tooltip_window is not None
        if self.use_pointer_pos:
            x_pos = self.widget.winfo_pointerx() + 20
            y_pos = self.widget.winfo_pointery() + 10
        else:
            # Attempt to center horizontally below widget
            x_pos = self.widget.winfo_rootx() + int(
                self.widget.winfo_width() / 2 - self.width / 2
            )
            y_pos = self.widget.winfo_rooty() + int(self.widget.winfo_height())
            # Keep tooltip just inside main window/dialog horizontal limits
            x_pos = max(x_pos, self.widget_tl.winfo_rootx())
            if (
                x_pos + self.width
                > self.widget_tl.winfo_rootx() + self.widget_tl.winfo_width()
            ):
                x_pos = (
                    self.widget_tl.winfo_rootx()
                    + self.widget_tl.winfo_width()
                    - self.width
                )
            # If tooltip would go below bottom of main window or dialog
            # that widget is in, display it above the widget instead
            if (
                y_pos + self.height
                > self.widget_tl.winfo_rooty() + self.widget_tl.winfo_height()
            ):
                y_pos = self.widget.winfo_rooty() - self.height
        self.tooltip_window.geometry(f"+{x_pos}+{y_pos}")
        self.tooltip_window.deiconify()

    def destroy(self) -> None:
        """Destroy the ToolTip and unbind all the bindings."""
        try:
            if self.widget.winfo_exists():
                unbind_from(self.widget, "<Enter>", self.enter_bind)
                unbind_from(self.widget, "<Leave>", self.leave_bind)
                unbind_from(self.widget, "<ButtonPress>", self.press_bind)
        except KeyError:
            pass  # OK if binding hasn't happened yet
        if self.tooltip_window is not None:
            self.tooltip_window.destroy()


@dataclass
class EntryInfoMetadata:
    """Class to store info about a menu entry."""

    label: str
    menu: str
    shortcut: str

    def __lt__(self, other: "EntryInfoMetadata") -> bool:
        """Define "<" to support sorting by label."""
        return self.label < other.label

    def get_command(self) -> Callable:
        """Return command to be executed - must be overridden."""
        raise NotImplementedError()


@dataclass
class ButtonInfoMetadata(EntryInfoMetadata):
    """Class to store info about a command button."""

    command: Callable

    def get_command(self) -> Callable:
        """Return command to be executed."""
        return self.command


@dataclass
class CheckboxInfoMetadata(EntryInfoMetadata):
    """Class to store info about a checkbox."""

    bool_var: tk.BooleanVar
    command_on: Optional[Callable]
    command_off: Optional[Callable]

    def get_command(self) -> Callable:
        """Return command to be executed."""

        def toggle_command() -> None:
            """Function that will toggle boolean and call command."""
            if self.bool_var.get():
                self.bool_var.set(False)
                if self.command_off is not None:
                    self.command_off()
            else:
                self.bool_var.set(True)
                if self.command_on is not None:
                    self.command_on()

        return toggle_command


class EntryMetadata:
    """Store metadata about a menu entry."""

    def __init__(self, label: str) -> None:
        """Initialize EntryMetadata object."""
        self.label = label


class ButtonMetadata(EntryMetadata):
    """Store metadata about a menu button."""

    def __init__(self, label: str, shortcut: str, command: Callable) -> None:
        """Initialize ButtonMetadata object.

        Args:
            label: The text displayed for the button.
            shortcut: Keyboard shortcut for the command (empty string if none)
            command: The function to execute when clicked.
        """
        super().__init__(label)
        self.command = command
        self.shortcut = shortcut


class CheckboxMetadata(EntryMetadata):
    """Store metadata about a menu checkbox (checkbutton)."""

    def __init__(
        self,
        label: str,
        shortcut: str,
        bool_var: tk.BooleanVar,
        command_on: Optional[Callable[[], None]],
        command_off: Optional[Callable[[], None]],
    ) -> None:
        """Initialize ButtonMetadata object.

        Args:
            label: The text displayed for the button.
            shortcut: Keyboard shortcut for the command (empty string if none).
            bool_var: Tk variable holding state of checkbox.
            command_on: The function to execute when checkbox is checked.
            command_off: The function to execute when checkbox is unchecked.
        """
        super().__init__(f"Toggle {label}")
        self.shortcut = shortcut
        self.bool_var = bool_var
        self.command_on = command_on
        self.command_off = command_off


class MenuMetadata(EntryMetadata):
    """Store metadata about a menu item."""

    def __init__(self, label: str, widget: tk.Menu) -> None:
        """Initialize MenuMetadata object.

        Args:
            label: Label string for menu button.
            widget: The menu that is being added.
        """
        super().__init__(label)
        self.entries: list[EntryMetadata] = []
        self.widget = widget

    def get_submenu_metadata(self, submenu: tk.Menu) -> Optional["MenuMetadata"]:
        """Return the metadata for the given submenu."""
        for entry in self.entries:
            if isinstance(entry, MenuMetadata):
                if entry.widget == submenu:
                    return entry  # Found it!
                # Also recurse into submenus
                if metadata := entry.get_submenu_metadata(submenu):
                    return metadata
        return None

    def get_all_commands(self) -> list[EntryInfoMetadata]:
        """Recursively collect all entries (buttons & checkboxes) in this menu."""
        commands: list[EntryInfoMetadata] = []
        for entry in self.entries:
            if isinstance(entry, ButtonMetadata):
                commands.append(
                    ButtonInfoMetadata(
                        entry.label, self.label, entry.shortcut, entry.command
                    )
                )
            elif isinstance(entry, CheckboxMetadata):
                commands.append(
                    CheckboxInfoMetadata(
                        entry.label,
                        self.label,
                        entry.shortcut,
                        entry.bool_var,
                        entry.command_on,
                        entry.command_off,
                    )
                )
            elif isinstance(entry, MenuMetadata):
                commands.extend(entry.get_all_commands())
        return commands


class MenubarMetadata:
    """Store metadata about entries in the menu bar."""

    def __init__(self, menubar: tk.Menu) -> None:
        """Initialize MenubarMetadata object."""
        self.entries: list[MenuMetadata] = []
        self.orphans: list[EntryMetadata] = []
        self.widget = menubar

    def add_menu(self, menu: tk.Menu, parent: tk.Menu, label: str) -> None:
        """Add a menu to the structure.

        Args:
            menu: Menu widget to add to the structure.
            parent: If none, then adding to the menu bar, else to the parent menu
            label: Label string for menu button.
        """
        if parent == self.widget:
            self.entries.append(MenuMetadata(label, menu))
        else:
            parent_metadata = self.get_menu_metadata(parent)
            assert parent_metadata is not None
            parent_metadata.entries.append(MenuMetadata(label, menu))

    def get_menu_metadata(self, menu: tk.Menu) -> Optional[MenuMetadata]:
        """Return the metadata for the given menu."""
        for entry in self.entries:
            # May be asking for a top level menu, i.e. child of menubar
            if entry.widget == menu:
                return entry
            # If not, may be a submenu of a top level menu (checked recursively)
            if metadata := entry.get_submenu_metadata(menu):
                return metadata
        return None

    def add_button(
        self,
        parent: Optional[tk.Menu],
        label: str,
        shortcut: str,
        command: Callable,
    ) -> None:
        """Add a command button to the correct menu (or list of orphans).

        Args:
            parent: The parent menu widget (None if command not in menus).
            label: The text displayed for the button.
            shortcut: Keyboard shortcut for the command (empty string if none).
            command: The function to execute when clicked.
        """
        if parent is None:
            self.orphans.append(ButtonMetadata(label, shortcut, command))
        else:
            menu_metadata = self.get_menu_metadata(parent)
            if menu_metadata is not None:
                menu_metadata.entries.append(ButtonMetadata(label, shortcut, command))

    def add_checkbox(
        self,
        parent: Optional[tk.Menu],
        label: str,
        shortcut: str,
        bool_var: tk.BooleanVar,
        command_on: Optional[Callable],
        command_off: Optional[Callable],
    ) -> None:
        """Add a command button to the correct menu (or list of orphans).

        Args:
            parent: The parent menu widget (None if command not in menus).
            label: The text displayed for the button.
            shortcut: Keyboard shortcut for the command (empty string if none).
            command_on: The function to execute when checkbox turned on.
            command_off: The function to execute when checkbox turned off.
        """
        if parent is None:
            self.orphans.append(
                CheckboxMetadata(label, shortcut, bool_var, command_on, command_off)
            )
        else:
            menu_metadata = self.get_menu_metadata(parent)
            if menu_metadata is not None:
                menu_metadata.entries.append(
                    CheckboxMetadata(label, shortcut, bool_var, command_on, command_off)
                )

    def get_all_commands(self) -> list[EntryInfoMetadata]:
        """Collect all command buttons from the entire menu structure."""
        commands = []
        for entry in self.entries:
            commands.extend(entry.get_all_commands())
        for orphan in self.orphans:
            if isinstance(orphan, ButtonMetadata):
                commands.append(
                    ButtonInfoMetadata(
                        orphan.label, "", orphan.shortcut, orphan.command
                    )
                )
            elif isinstance(orphan, CheckboxMetadata):
                commands.append(
                    CheckboxInfoMetadata(
                        orphan.label,
                        "",
                        orphan.shortcut,
                        orphan.bool_var,
                        orphan.command_on,
                        orphan.command_off,
                    )
                )
        return commands


_MENUBAR_METADATA = None


def menubar_metadata(menubar: Optional[tk.Menu] = None) -> MenubarMetadata:
    """Return single instance of menubar metadata."""
    global _MENUBAR_METADATA
    if menubar is not None:
        assert _MENUBAR_METADATA is None
        _MENUBAR_METADATA = MenubarMetadata(menubar)
    assert _MENUBAR_METADATA is not None
    return _MENUBAR_METADATA


def unbind_from(widget: tk.Widget, sequence: str, func_id: str) -> None:
    """Unbind function associated with `func_id`.

    Based on: https://github.com/python/cpython/issues/75666#issuecomment-1877547466
    Necessary due to long-standing bug in tkinter: when `unbind` is called
    all bindings to the given sequence are removed, not just the one associated
    with `func_id`.

    Args:
        widget: Widget to unbind from.
        sequence: Sequence function was bound to.
        func_id: Function ID returned by original `bind` call.
    """
    # Make dictionary of all bindings to seq
    bindings = {
        x.split()[1][3:]: x for x in widget.bind(sequence).splitlines() if x.strip()
    }
    # Delete the binding associated with `funcid`
    del bindings[func_id]
    # Re-bind all the other bindings to the widget
    widget.bind(sequence, "\n".join(list(bindings.values())))


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
        icon_deicon: True if iconify/deiconify Windows hack required
    """
    toplevel.lift()
    if icon_deicon and is_windows():
        toplevel.iconify()
        toplevel.deiconify()
    toplevel.focus_force()
    if focus_widget is not None:
        focus_widget.focus_set()


def mouse_bind(
    widget: tk.Widget, event: str, callback: Callable[[tk.Event], object]
) -> None:
    """Bind mouse button callback to event on widget.

    If binding is to mouse button 3, then if on a Mac bind
    to mouse-2 and Control-mouse-1 instead

    Args:
        widget: Widget to bind to
        event: Event string to trigger callback
        callback: Function to be called when event occurs
    """
    assert not event.startswith("<") and not event.endswith(">")
    # Convert to event format and handle Cmd/Ctrl
    _, event = process_accel(event)

    if is_mac() and (match := re.match(r"<(.*)3>", event)):
        button2 = f"<{match[1]}2>"
        widget.bind(button2, callback)
        control1 = f"<Control-{match[1]}1>"
        widget.bind(control1, callback)
    else:
        widget.bind(event, callback)


def handle_mouse_wheel(widget: tk.Widget, event: tk.Event) -> None:
    """Cross platform scroll wheel event."""
    assert isinstance(widget, (tk.Canvas, tk.Text))
    if is_windows():
        widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
    elif is_mac():
        widget.yview_scroll(int(-1 * event.delta), "units")
    else:
        if event.num == 4:
            widget.yview_scroll(-1, "units")
        elif event.num == 5:
            widget.yview_scroll(1, "units")


def bind_mouse_wheel(
    bind_widget: tk.Widget, scroll_widget: Optional[tk.Widget] = None
) -> None:
    """Bind wheel events when the cursor enters the control."""
    if scroll_widget is None:
        scroll_widget = bind_widget
    if is_x11():
        bind_widget.bind(
            "<Button-4>",
            lambda evt, sw=scroll_widget: handle_mouse_wheel(  # type:ignore[misc]
                sw, evt
            ),
        )
        bind_widget.bind(
            "<Button-5>",
            lambda evt, sw=scroll_widget: handle_mouse_wheel(  # type:ignore[misc]
                sw, evt
            ),
        )
    else:
        bind_widget.bind(
            "<MouseWheel>",
            lambda evt, sw=scroll_widget: handle_mouse_wheel(  # type:ignore[misc]
                sw, evt
            ),
        )


def unbind_mouse_wheel(bind_widget: tk.Widget) -> None:
    """Unbind wheel events when the cursor leaves the control."""
    if is_x11():
        bind_widget.unbind("<Button-4>")
        bind_widget.unbind("<Button-5>")
    else:
        bind_widget.unbind("<MouseWheel>")


# For convenient access, store the single Style instance here,
# with a function to set/query it.
# Also store the default colors for a Text widget that are not
# altered by the default themes.
_SINGLE_STYLE = None
_THEME_DEFAULT_TEXT_BG = ""
_THEME_DEFAULT_TEXT_FG = ""
_THEME_DEFAULT_TEXT_IBG = ""


def themed_style(style: Optional[ttk.Style] = None) -> ttk.Style:
    """Store and return the single Style object"""
    global _SINGLE_STYLE
    if style is not None:
        assert _SINGLE_STYLE is None
        _SINGLE_STYLE = style
        _theme_init_tk_widget_colors()
    assert _SINGLE_STYLE is not None
    return _SINGLE_STYLE


def theme_name_internal_from_user(user_theme: str) -> str:
    """Return the internal theme name given the name the user will see.

    Args:
        user_theme: Name user will see in Preferences dialog.

    Returns:
        Internal name for theme.
    """
    match user_theme:
        case "Default":
            if darkdetect.theme() == "Light":
                return "awlight"
            if darkdetect.theme() == "Dark":
                return "awdark"
            assert False, "Error detecting OS theme"
        case "Dark":
            return "awdark"
        case "Light":
            return "awlight"
        case _:
            assert False, "Bad user theme name"


def _theme_init_tk_widget_colors() -> None:
    """Get default bg & fg colors of a Text (non-themed) widget,
    by creating one, getting the colors, then destroying it.

    Needs to be called before theme is changed from default theme.
    """
    global _THEME_DEFAULT_TEXT_BG, _THEME_DEFAULT_TEXT_FG, _THEME_DEFAULT_TEXT_IBG
    temp_text = tk.Text()
    _THEME_DEFAULT_TEXT_BG = temp_text.cget("background")
    _THEME_DEFAULT_TEXT_FG = temp_text.cget("foreground")
    _THEME_DEFAULT_TEXT_IBG = temp_text.cget("insertbackground")
    temp_text.destroy()


# Keep track of which Text/Entry widget of interest last had focus.
# "Of interest" means those we might want to paste special characters into,
# e.g. main text widget, search dialog fields, etc., but not the entry field
# in dialogs like Compose Sequence (which are used to create the special
# characters).

_text_focus_widget: Optional[tk.Widget] = None


def register_focus_widget(widget: tk.Entry | tk.Text) -> None:
    """Register a widget as being "of interest", i.e. to track when it gets focus.

    Args:
        widget: The widget whose focus is to be tracked.
    """
    global _text_focus_widget
    assert isinstance(widget, (tk.Entry, tk.Text))

    def set_focus_widget(event: tk.Event) -> None:
        """Store the widget that triggered the event."""
        global _text_focus_widget
        _text_focus_widget = event.widget

    widget.bind("<FocusIn>", set_focus_widget, add=True)
    if _text_focus_widget is None:
        _text_focus_widget = widget


def insert_in_focus_widget(string: str) -> None:
    """Insert given string in the text/entry widget of interest that most recently had focus.

    Args:
        string: String to be inserted.
    """
    if _text_focus_widget is None or not _text_focus_widget.winfo_exists():
        return
    assert isinstance(_text_focus_widget, (tk.Entry, tk.Text))

    if isinstance(_text_focus_widget, tk.Text):
        sel_ranges = _text_focus_widget.tag_ranges("sel")
        if sel_ranges:
            _text_focus_widget.mark_set(tk.INSERT, sel_ranges[0])
            _text_focus_widget.delete(sel_ranges[0], sel_ranges[1])
            _text_focus_widget.tag_remove("sel", "1.0", tk.END)
    elif isinstance(_text_focus_widget, tk.Entry):
        if _text_focus_widget.selection_present():
            _text_focus_widget.delete("sel.first", "sel.last")
    _text_focus_widget.insert(tk.INSERT, string)


class Busy:
    """Class to allow program to indicate to user that it is busy.

    1. Change the busy label (registered via `busy_widget_setup`) to say "Working".
    2. Change the mouse cursor to "watch" (widgets registered via `busy_cursor_setup`).
    """

    _busy_widget: Optional[ttk.Label] = None
    _busy_widget_cursors: dict[tk.Widget | tk.Tk | tk.Toplevel, str] = {}

    @classmethod
    def busy_widget_setup(cls, widget: ttk.Label) -> None:
        """Register the label widget that will show if process is busy.

        Args:
            widget: The label widget to use to show busyness."""
        assert Busy._busy_widget is None
        Busy._busy_widget = widget

    @classmethod
    def busy(cls) -> None:
        """Tell the user the process is busy.

        1. Change the busy label to say "Working".
        2. Change the mouse cursor to "watch".

        It is safe to call `busy` more than once during an operation.
        Before control returns to the user, `unbusy` must be called.
        """
        assert Busy._busy_widget is not None
        Busy._busy_widget.config(text="Working")
        Busy._busy_widget.update()

        def register_children(widget: tk.Widget | tk.Tk | tk.Toplevel) -> None:
            """Register the given widget & all its children by calling
            itself recursively.

            Args:
                widget: Widget to register.
            """
            # No need to register tooltips & menus  (nor their children).
            if isinstance(widget, (ToolTip, tk.Menu)):
                return
            # Don't re-register widgets, because first call will likely have the default cursor.
            # Also, No need to register frames, but do register their children
            if widget not in Busy._busy_widget_cursors and not isinstance(
                widget, ttk.Frame
            ):
                Busy._busy_widget_cursors[widget] = widget["cursor"]

            for child in widget.winfo_children():
                register_children(child)

        # Assume the "busy widget" is in the root window.
        register_children(Busy._busy_widget.winfo_toplevel())
        Busy._busy_set_cursors("watch")

    @classmethod
    def unbusy(cls) -> None:
        """Tell the user the process is no longer busy."""
        assert Busy._busy_widget is not None
        Busy._busy_widget.config(text="")
        Busy._busy_set_cursors("")

    @classmethod
    def _busy_set_cursors(cls, cursor: str) -> None:
        """Set/restore the cursor for the registered widgets.

        Args:
            cursor: Which cursor to use; empty string to restore defaults.
        """
        for widget in list(Busy._busy_widget_cursors.keys()):
            if widget.winfo_exists():
                widget["cursor"] = cursor or Busy._busy_widget_cursors[widget]
                widget.update()
            else:
                # Remove old widgets from register
                try:
                    del Busy._busy_widget_cursors[widget]
                except KeyError:
                    pass  # OK if widget has already been removed
