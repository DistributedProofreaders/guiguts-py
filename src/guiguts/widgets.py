"""Common code/classes relating to Tk widgets."""

import tkinter as tk
from tkinter import ttk
from tkinter import font as tk_font
from typing import Any, Optional, TypeVar, Callable
import webbrowser

import darkdetect  # type: ignore[import-untyped]
import regex as re

from guiguts.preferences import (
    preferences,
    PrefKey,
    PersistentString,
)
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

    # Location of manual page for most recently focused dialog
    context_help = ""
    manual_page: Optional[str] = None

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

        # Ensure manual page has been initialized in subclasses
        assert self.manual_page is not None

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

        # Keep a track of which dialog had focus last for help purposes
        self.bind("<FocusIn>", lambda _: self.got_focus())

        grab_focus(self)

    def __new__(cls, *args: Any, **kwargs: Any) -> "ToplevelDialog":
        """Ensure ToplevelDialogs are not instantiated directly."""
        if cls is ToplevelDialog:
            raise NotImplementedError
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
        dlg_name = cls.get_dlg_name()
        # Can we just deiconify dialog & reset it?
        if dlg := cls.get_dialog():
            dlg.deiconify()
            dlg.reset()
        # Or do we need to create it?
        if not cls.get_dialog():
            dlg = cls(**kwargs)
        ToplevelDialog._toplevel_dialogs[dlg_name] = dlg
        dlg.grab_focus()
        return dlg

    @classmethod
    def get_dialog(cls) -> Optional[TlDlg]:
        """Return the one occurrence of this dialog class if it exists.

        Returns:
            The one instance of this dialog type, or None if it's not currently shown.
        """
        dlg_name = cls.get_dlg_name()
        if (
            dlg_name in ToplevelDialog._toplevel_dialogs
            and ToplevelDialog._toplevel_dialogs[dlg_name].winfo_exists()
        ):
            return ToplevelDialog._toplevel_dialogs[dlg_name]  # type: ignore[return-value]
        return None

    @classmethod
    def get_dlg_name(cls) -> str:
        """Get reduced dialog name where a unique identifier for a dialog type is needed,
        such as prefix for mark names, keys in dictionaries, etc.
        """
        return cls.__name__.removesuffix("Dialog")

    def grab_focus(self) -> None:
        """Grab focus and raise to top (if permitted by window manager)."""
        if is_x11():
            grab_focus(self)

    def got_focus(self) -> None:
        """Called when dialog gets focus."""
        assert self.manual_page is not None
        ToplevelDialog.context_help = self.manual_page

    def register_tooltip(self, tooltip: "ToolTip") -> None:
        """Register a tooltip as being attached to a widget in this
        ToplevelDialog so it can be destroyed when the dialog is destroyed.

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
        config_dict[self.get_dlg_name()] = value
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
            return config_dict[self.get_dlg_name()]
        except KeyError:
            return None

    @classmethod
    def show_manual_page(cls) -> None:
        """Show the manual page for the dialog."""
        sub_page = f"/{cls.context_help}" if cls.context_help else ""
        webbrowser.open(
            f"https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_2_Manual{sub_page}"
        )

    @classmethod
    def orphan_wrapper(cls, method_name: str, *args: Any, **kwargs: Any) -> Callable:
        """Return a wrapper to simplify calls to add_button_orphan.

        Args:
            method_name: Name of method to be called when command is executed.
            args: Positional args for `method_name` method.
            kwargs: Named args for `method_name` method.
        """

        def wrapper() -> None:
            if dlg := cls.get_dialog():
                getattr(dlg, method_name)(*args, **kwargs)

        assert hasattr(cls, method_name)
        return wrapper


class OkApplyCancelDialog(ToplevelDialog):
    """A ToplevelDialog with OK, Apply & Cancel buttons."""

    def __init__(self, title: str, display_apply: bool = True, **kwargs: Any) -> None:
        """Initialize the dialog.

        Args:
            title: Title for dialog.
            display_apply: Set to False if Apply button not required.
        """
        super().__init__(title, **kwargs)
        self.display_apply = display_apply
        outer_button_frame = ttk.Frame(self, padding=5)
        outer_button_frame.grid(row=1, column=0, sticky="NSEW")
        outer_button_frame.columnconfigure(0, weight=1)
        button_frame = ttk.Frame(outer_button_frame)
        button_frame.grid(row=1, column=0)
        column = 0
        self.ok_btn = ttk.Button(
            button_frame,
            text="OK",
            default="active",
            command=self.ok_pressed,
        )
        self.ok_btn.grid(row=0, column=column, padx=5)
        self.bind("<Return>", lambda event: self.ok_pressed())
        if self.display_apply:
            column += 1
            self.apply_btn = ttk.Button(
                button_frame,
                text="Apply",
                default="normal",
                command=self.apply_changes,
            )
            self.apply_btn.grid(row=0, column=column, padx=5)
            self.bind("<Shift-Return>", lambda event: self.apply_changes())
        column += 1
        ttk.Button(
            button_frame,
            text="Cancel",
            default="normal",
            command=self.cancel_pressed,
        ).grid(row=0, column=column, padx=5)
        self.bind("<Escape>", lambda event: self.cancel_pressed())

    def enable_ok_apply(self, enable: bool) -> None:
        """Enable/disable the OK/Apply buttons."""
        state = "normal" if enable else "disable"
        self.ok_btn["state"] = state
        self.apply_btn["state"] = state

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


class OkCancelDialog(OkApplyCancelDialog):
    """A ToplevelDialog with OK & Cancel buttons."""

    def __init__(self, title: str, **kwargs: Any) -> None:
        """Initialize the dialog.

        Args:
            title: Title for dialog.
        """
        kwargs["display_apply"] = False
        super().__init__(title, **kwargs)


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
        try:  # Tk8 structure
            self.tk.call(f"{popdown}.f.l", "configure", "-font", self["font"])
        except tk.TclError:  # Tk9 structure
            self.tk.call(f"{popdown}.menu", "configure", "-font", self["font"])

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

        themed_style().configure("TCombobox", postoffset=(0, 0, width, 0))
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


class TreeviewList(ttk.Treeview):
    """Treeview to be used as a single-selection list."""

    def __init__(self, parent: tk.Widget, *args: Any, **kwargs: Any) -> None:
        """Initialize TreeviewList - standard ttk.Treeview in "browse" mode with extra bindings."""
        if "show" not in kwargs:
            kwargs["show"] = "headings"
        if "height" not in kwargs:
            kwargs["height"] = 10
        kwargs["selectmode"] = tk.BROWSE

        # Use background color of selected row as the focus border color
        bg_color = themed_style().lookup(
            "Treeview", "background", ("selected", "focus")
        )
        # Fallback blues in case the above fails with some themes
        # Fallbacks are based on awdark/light selected row background colors
        if not bg_color:
            bg_color = "#215d9c" if themed_style().is_dark_theme() else "#1a497c"
        themed_style().map(
            "Custom.Treeview",
            bordercolor=[("focus", bg_color)],
            relief=[("focus", "solid")],
        )

        super().__init__(parent, style="Custom.Treeview", *args, **kwargs)
        self.bind("<Home>", lambda _e: self.select_and_focus_by_index(0))
        self.bind("<End>", lambda _e: self.select_and_focus_by_index(-1))
        if is_mac():
            self.bind("<Command-Up>", lambda _e: self.select_and_focus_by_index(0))
            self.bind("<Command-Down>", lambda _e: self.select_and_focus_by_index(-1))

    def select_and_focus_by_child(self, item: str) -> None:
        """Select and set focus to the given item.

        Although for the "browse" select mode used in this TreeView, there is
        only one selected item, there can be several items selected in other
        TreeViews, and one item can have focus. Since user can use mouse & arrow
        keys to change selection, and we also change it programmatically to
        support use of Home/End keys, it's necessary to ensure the selection and
        the focus always point to the same item. Otherwise using Home to go to
        top of list then arrow key to move to second item will not work.

        Args:
            item: The item to be selected/focused.
        """
        children = self.get_children()
        if not children:
            return
        self.selection_set(item)
        self.focus(item)
        iid = self.index(item)
        self.see(item)
        # "see" puts item at top, so alsosee the position a few earlier
        self.see(children[max(0, iid - 3)])

    def select_and_focus_by_index(self, idx: int) -> None:
        """Select and set focus to the given index.

        Args:
            idx: The index of the item to be selected/focused.
        """
        children = self.get_children()
        if abs(idx) >= len(children):
            return
        self.select_and_focus_by_child(children[idx])

    def clear(self) -> None:
        """Clear list of all children."""
        children = self.get_children()
        for child in children:
            self.delete(child)

    def identify_rowcol(self, event: tk.Event) -> tuple[str, str]:
        """Get row and column from mouse click event x & y.

        Returns:
            Tuple of row and column IDs."""
        row_id = self.identify_row(event.y)
        col_id = self.identify_column(event.x)
        return row_id, col_id


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
        if preferences.get(PrefKey.SHOW_TOOLTIPS):
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


def handle_mouse_wheel(widget: tk.Widget, event: tk.Event, vertical: bool) -> None:
    """Cross platform scroll wheel event.

    Args:
        widget: Widget to be scrolled.
        event: Event containing scroll delta.
        vertical: True for vertical scroll, False for horizontal.
    """
    assert isinstance(widget, (tk.Canvas, tk.Text))
    scroll_func = widget.yview_scroll if vertical else widget.xview_scroll
    if is_windows():
        scroll_func(int(-1 * (event.delta / 120)), "units")
    elif is_mac():
        scroll_func(int(-1 * event.delta), "units")
    else:
        if event.num == 4:
            scroll_func(-1, "units")
        elif event.num == 5:
            scroll_func(1, "units")


def bind_mouse_wheel(
    bind_widget: tk.Widget, scroll_widget: Optional[tk.Widget] = None
) -> None:
    """Bind wheel events when the cursor enters the control.
    Necessary to use bind_all to catch events on bind_widget's children,
    hence the need to bind/unbind on Enter/Leave"""
    if scroll_widget is None:
        scroll_widget = bind_widget
    if is_x11():
        bind_widget.bind_all(
            "<Button-4>", lambda evt: handle_mouse_wheel(scroll_widget, evt, True)
        )
        bind_widget.bind_all(
            "<Button-5>", lambda evt: handle_mouse_wheel(scroll_widget, evt, True)
        )
        bind_widget.bind_all(
            "<Shift-Button-4>",
            lambda evt: handle_mouse_wheel(scroll_widget, evt, False),
        )
        bind_widget.bind_all(
            "<Shift-Button-5>",
            lambda evt: handle_mouse_wheel(scroll_widget, evt, False),
        )
    else:
        bind_widget.bind_all(
            "<MouseWheel>", lambda evt: handle_mouse_wheel(scroll_widget, evt, True)
        )
        bind_widget.bind_all(
            "<Shift-MouseWheel>",
            lambda evt: handle_mouse_wheel(scroll_widget, evt, False),
        )


def unbind_mouse_wheel(bind_widget: tk.Widget) -> None:
    """Unbind wheel events when the cursor enters the control.
    Necessary to use bind_all to catch events on bind_widget's children,
    hence the need to bind/unbind on Enter/Leave"""
    if is_x11():
        bind_widget.unbind_all("<Button-4>")
        bind_widget.unbind_all("<Button-5>")
    else:
        bind_widget.unbind_all("<MouseWheel>")


# For convenient access, store the single Style instance here,
# with a function to set/query it.
# Also store the default colors for a Text widget that are not
# altered by the default themes.
_SINGLE_STYLE = None


class ThemedStyle(ttk.Style):
    """Tk9-safe version of ttk.Style."""

    def theme_use(self, themename: Optional[str] = None) -> Optional[str]:  # type: ignore[override]
        """Overridden, to avoid crash with Tk9.

        If themename is None, returns the theme in use, otherwise, set
        the current theme to themename, refreshes all widgets and emits
        a <<ThemeChanged>> event."""
        if themename is None:
            # OLD CODE
            # # Starting on Tk 8.6, checking this global is no longer needed
            # # since it allows doing self.tk.call(self._name, "theme", "use")
            # return self.tk.eval("return $ttk::currentTheme")

            # NEW CODE
            # Above line fails with Tk9, since $ttk::currentTheme doesn't exist,
            # so replaced with line below as suggested in above comment.
            return self.tk.call(self._name, "theme", "use")  # type:ignore[attr-defined]
        super().theme_use(themename)
        return None

    def is_dark_theme(self) -> bool:
        """Returns True if theme is set to awdark."""
        if self.theme_use() == "awdark":
            return True
        return False


def themed_style(style: Optional[ThemedStyle] = None) -> ThemedStyle:
    """Store and return the single Style object"""
    global _SINGLE_STYLE
    if style is not None:
        assert _SINGLE_STYLE is None
        _SINGLE_STYLE = style
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


def focus_next_widget(event: tk.Event) -> str:
    """Focus on next widget, as a <Tab> keystroke would."""
    event.widget.tk_focusNext().focus_set()
    return "break"


def focus_prev_widget(event: tk.Event) -> str:
    """Focus on previous widget, as a <Shift-Tab> keystroke would."""
    event.widget.tk_focusPrev().focus_set()
    return "break"


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


class ScrollableFrame(ttk.Frame):
    """A scrollable ttk.Frame."""

    def __init__(self, parent: tk.Widget, *args: Any, **kwargs: Any) -> None:
        # Create a containing frame (not visible to the user of this widget)
        self._container = ttk.Frame(parent)
        self._container.grid(row=0, column=0, sticky="NSEW")
        self._container.columnconfigure(0, weight=1)
        self._container.rowconfigure(0, weight=1)

        # Initialize the visible frame (the one user interacts with)
        self.canvas = tk.Canvas(self._container, highlightthickness=0)
        self._v_scrollbar = ttk.Scrollbar(
            self._container, orient="vertical", command=self.canvas.yview
        )
        self._h_scrollbar = ttk.Scrollbar(
            self._container, orient="horizontal", command=self.canvas.xview
        )

        # Call ttk.Frame.__init__ with the internal scrollable frame as self
        super().__init__(self.canvas, *args, **kwargs)
        self._bg = str(ttk.Style().lookup(self["style"], "background"))
        self.canvas["background"] = self._bg

        # Put self (the scrollable frame) into the canvas
        self.canvas.create_window((0, 0), window=self, anchor="nw")

        # Scroll configuration
        self.canvas.configure(yscrollcommand=self._v_scrollbar.set)
        self.canvas.configure(xscrollcommand=self._h_scrollbar.set)

        # Grid everything
        self.canvas.grid(column=0, row=0, sticky="NSEW")
        self._v_scrollbar.grid(column=1, row=0, sticky="NS")
        self._h_scrollbar.grid(column=0, row=1, sticky="EW")

        # Bind scroll region and mouse entry
        self.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Enter>", lambda _: bind_mouse_wheel(self.canvas))
        self.canvas.bind("<Leave>", lambda _: unbind_mouse_wheel(self.canvas))

        def set_bg(_: tk.Event) -> None:
            """Set the Canvas to have the same background as the Frame whenever
            the theme is changed.
            """
            bg = themed_style().lookup("TFrame", "background")
            self.canvas["background"] = bg

        self.bind("<<ThemeChanged>>", set_bg)

    def grid(self, *args: Any, **kwargs: Any) -> None:
        """Delegate grid to the container."""
        self._container.grid(*args, **kwargs)

    def reset_scroll(self) -> None:
        """Scroll canvas to top left position."""
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)
