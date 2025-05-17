"""Define key components of main window"""

from enum import Enum, auto
from idlelib.redirector import WidgetRedirector  # type: ignore[import-not-found, import-untyped]
import logging
import os.path
from string import ascii_uppercase
import shlex
import subprocess
import time
import tkinter as tk
from tkinter import ttk, messagebox, EventType
from typing import Any, Callable, Optional
from pathlib import Path

from PIL import Image, ImageTk, ImageChops
import regex as re

from guiguts.maintext import MainText, maintext, menubar_metadata, MenuMetadata
from guiguts.preferences import preferences, PrefKey, PersistentBoolean
from guiguts.root import Root, root
from guiguts.utilities import (
    is_mac,
    is_x11,
    is_windows,
    bell_set_callback,
    process_accel,
    process_label,
    IndexRowCol,
    sound_bell,
)
from guiguts.widgets import (
    ToplevelDialog,
    mouse_bind,
    ToolTip,
    themed_style,
    Busy,
    focus_next_widget,
    focus_prev_widget,
    ThemedStyle,
    TreeviewList,
)

logger = logging.getLogger(__package__)

TEXTIMAGE_WINDOW_ROW = 0
TEXTIMAGE_WINDOW_COL = 0
SEPARATOR_ROW = 1
SEPARATOR_COL = 0
STATUS_ROW = 2
STATUS_COL = 0
MIN_PANE_WIDTH = 20


class Menu(tk.Menu):
    """Extend ``tk.Menu`` to make adding buttons with accelerators simpler."""

    def __init__(self, parent: tk.Widget, label: str, **kwargs: Any) -> None:
        """Initialize menu and add to parent

        Args:
            parent: Parent menu/menubar, or another widget if context menu.
            label: Label string for menu, including tilde for keyboard
              navigation, e.g. "~File".
            **kwargs: Optional additional keywords args for ``tk.Menu``.
        """

        super().__init__(parent, **kwargs)
        command_args: dict[str, Any] = {"menu": self}
        label_txt = ""
        if label:
            (label_tilde, label_txt) = process_label(label)
            command_args["label"] = label_txt
            if label_tilde >= 0:
                command_args["underline"] = label_tilde
        # Only needs cascade if a child of menu/menubar, not if a context popup menu
        if isinstance(parent, tk.Menu):
            parent.add_cascade(command_args)

    def add_button(
        self,
        label: str,
        callback: Callable[[], Any],
        accel: str = "",
        bind_all: bool = True,
    ) -> None:
        """Add a button to the menu.

        Args:
            label: Label string for button, including tilde for keyboard
              navigation, e.g. "~Save".
            callback: Callback function.
            accel: String describing optional accelerator key, used when a
              callback function is passed in as ``handler``. Will be displayed
              on the button, and will be bound to the same action as the menu
              button. "Cmd/Ctrl" means `Cmd` key on Mac; `Ctrl` key on
              Windows/Linux.
            bind_all: Set False to only bind to maintext.
        """
        Menu.bind_button(callback, accel, bind_all)

        (label_tilde, label_txt) = process_label(label)
        accel = process_accel(accel)[0]
        command_args = {
            "label": label_txt,
            "command": callback,
            "accelerator": accel,
        }
        if label_tilde >= 0:
            command_args["underline"] = label_tilde
        self.add_command(command_args)

    @classmethod
    def bind_button(
        cls,
        callback: Callable[[], Any],
        accel: str = "",
        bind_all: bool = True,
    ) -> None:
        """Bind callback to shortcut."""
        key_event = process_accel(accel)[1]

        if accel:
            maintext().key_bind(key_event, lambda _: callback(), bind_all=bind_all)

    def add_checkbox(
        self,
        label: str,
        bool_var: PersistentBoolean,
        handler_on: Optional[Callable[[], None]] = None,
        handler_off: Optional[Callable[[], None]] = None,
        accel: str = "",
    ) -> None:
        """Add a checkbox to the menu.

        Args:
            label: Label string for button, including tilde for keyboard
              navigation, e.g. "~Save".
            bool_var: Tk variable to keep track of state or set it from elsewhere
            handler_on: Callback function for when checkbox gets checked
            handler_off: Callback function for when checkbox gets checked
            accel: String describing optional accelerator key, used when a
              callback function is passed in as ``handler``. Will be displayed
              on the button, and will be bound to the same action as the menu
              button. "Cmd/Ctrl" means `Cmd` key on Mac; `Ctrl` key on
              Windows/Linux.
        """
        Menu.bind_checkbox(bool_var.pref_key, handler_on, handler_off, accel)

        label_tilde, label_txt = process_label(label)
        accel = process_accel(accel)[0]
        command_args = {
            "label": label_txt,
            "command": lambda: Menu.checkbox_clicked(
                bool_var.pref_key, handler_on, handler_off
            ),
            "variable": bool_var,
            "accelerator": accel,
        }
        if label_tilde >= 0:
            command_args["underline"] = label_tilde
        self.add_checkbutton(command_args)

    @classmethod
    def checkbox_clicked(
        cls,
        pref_key: PrefKey,
        handler_on: Optional[Callable[[], None]] = None,
        handler_off: Optional[Callable[[], None]] = None,
    ) -> None:
        """Callback when checkbox is clicked.

        Call appropriate handler depending on setting."""
        if preferences.get(pref_key):
            if handler_on is not None:
                handler_on()
        else:
            if handler_off is not None:
                handler_off()

    @classmethod
    def bind_checkbox(
        cls,
        pref_key: PrefKey,
        handler_on: Optional[Callable[[], None]] = None,
        handler_off: Optional[Callable[[], None]] = None,
        accel: str = "",
    ) -> None:
        """Bind callback to shortcut."""
        _, key_event = process_accel(accel)

        def accel_command(_: tk.Event) -> None:
            """Command to simulate checkbox click via shortcut key.

            Because key hasn't been clicked, variable hasn't been toggled.
            """
            preferences.set(pref_key, not preferences.get(pref_key))
            Menu.checkbox_clicked(pref_key, handler_on, handler_off)

        if accel:
            maintext().key_bind(key_event, accel_command, bind_all=True)

    def add_button_virtual_event(
        self, label: str, virtual_event: str, accel: str = ""
    ) -> None:
        """Add a button to this menu to call virtual event."""

        def command() -> None:
            widget = maintext().winfo_toplevel().focus_get()
            if widget is None:
                widget = maintext().focus_widget()
            widget.event_generate(virtual_event)

        self.add_button(label, command, accel, bind_all=False)

    def add_cut_copy_paste(self, read_only: bool = False) -> None:
        """Add cut/copy/paste buttons to this menu"""
        if not read_only:
            self.add_button_virtual_event("Cu~t", "<<Cut>>", "Cmd/Ctrl+X")
        self.add_button_virtual_event("~Copy", "<<Copy>>", "Cmd/Ctrl+C")
        if not read_only:
            self.add_button_virtual_event("~Paste", "<<Paste>>", "Cmd/Ctrl+V")
        self.add_separator()
        self.add_button_virtual_event("Select ~All", "<<SelectAll>>", "Cmd/Ctrl+A")


class CustomMenuDialog(ToplevelDialog):
    """A dialog to customize the Custom menu."""

    manual_page = "Custom_Menu"
    filename = ""
    recreate_menus_callback: Optional[Callable] = None

    def __init__(self, menu: MenuMetadata) -> None:
        """Initialize the Custom Menu dialog.

        Args:
            menu: The Custom menu.
        """
        super().__init__("Customize Menu")
        self.menu = menu
        # Stored in prefs file as list of [label, command] pairs
        self.menu_entries: list[list[str]] = preferences.get(
            PrefKey.CUSTOM_MENU_ENTRIES
        )

        # Treeview Frame with border
        treeview_frame = ttk.Frame(
            self.top_frame, padding=5, borderwidth=1, relief=tk.GROOVE
        )
        treeview_frame.grid(row=0, column=0, pady=5, padx=5, sticky="NSEW")

        # Treeview setup with scrollbar
        self.list = TreeviewList(
            treeview_frame,
            columns=("Label", "Command"),
        )
        self.list.heading("Label", text="Label")
        self.list.column("Label", minwidth=10, width=200)
        self.list.heading("Command", text="Command")
        self.list.column("Command", minwidth=10, width=500)
        self.list.grid(row=0, column=0, sticky="NSEW")

        scrollbar = ttk.Scrollbar(
            treeview_frame, orient="vertical", command=self.list.yview
        )
        self.list.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        treeview_frame.grid_columnconfigure(0, weight=1)
        treeview_frame.grid_rowconfigure(0, weight=1)

        # Move Up and Move Down Buttons
        move_button_frame = ttk.Frame(self.top_frame)
        move_button_frame.grid(row=1, column=0, pady=5)

        ttk.Button(
            move_button_frame,
            text="Move Up",
            command=lambda: self.move_up_down(-1),
        ).grid(row=0, column=0, padx=2)
        ttk.Button(
            move_button_frame,
            text="Move Down",
            command=lambda: self.move_up_down(1),
        ).grid(row=0, column=1, padx=2)

        # Edit LabelFrame
        edit_frame = ttk.LabelFrame(self.top_frame, padding=3, text="Edit")
        edit_frame.grid(row=2, column=0, pady=5, padx=5, sticky="NSEW")
        edit_frame.columnconfigure(1, weight=1)

        ttk.Label(edit_frame, text="Label:").grid(
            row=0, column=0, padx=5, pady=2, sticky="NSE"
        )
        self.label_entry = ttk.Entry(edit_frame)
        self.label_entry.grid(row=0, column=1, padx=5, pady=2, sticky="NSEW")

        ttk.Label(edit_frame, text="Command:").grid(
            row=1, column=0, padx=5, pady=2, sticky="NSE"
        )
        self.command_entry = ttk.Entry(edit_frame)
        self.command_entry.grid(row=1, column=1, padx=5, pady=2, sticky="NSEW")

        # Buttons inside Edit LabelFrame
        button_frame = ttk.Frame(edit_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=5)

        ttk.Button(button_frame, text="Add Entry", command=self.add_entry).grid(
            row=0, column=0, padx=2
        )
        ttk.Button(
            button_frame,
            text="Update Entry",
            command=self.update_entry,
        ).grid(row=0, column=1, padx=2)
        ttk.Button(
            button_frame,
            text="Remove Entry",
            command=self.remove_entry,
        ).grid(row=0, column=2, padx=2)

        # Help LabelFrame
        start_open = "start" if is_windows() else "open"
        help_frame = ttk.LabelFrame(self.top_frame, padding=3, text="Help")
        help_frame.grid(row=3, column=0, pady=5, padx=5, sticky="NSEW")
        help_frame.columnconfigure(0, weight=1)
        given_app_str = "" if is_x11() else ", or a given app,"
        help_label = ttk.Label(
            help_frame,
            text=f"""\
The command for each menu entry may be an app on your computer, or the "{start_open}" command. \
Typically, "{start_open}" will use the default app{given_app_str} to open the given file type. \
Alternatively, if a URL is given with no command, it will be displayed using your default \
browser via "{start_open}". To use a different browser, specify that browser as part of your command. \
Enclose commands or filenames that may contain spaces in "double quotes".

The following variables are available for use in commands:
$f: full pathname of the current File
$p: Png name of current image, e.g. 007 for 007.png
$s: Sequence number of current page, e.g. 7 for 7th png, regardless of numbering
$t: selected Text (only the first line if column selection)
$u: Unicode codepoint of current character from status bar, e.g. "0041" for capital A.

To assist in opening a hi-res scan for the current page, $s can also be given an offset, \
e.g. $(s+5) would give 12 for the 5th png.
""",
        )
        help_label.grid(row=0, column=0, padx=5, pady=2, sticky="NSEW")
        help_label.bind(
            "<Configure>",
            lambda e: help_label.config(wraplength=help_label.winfo_width() - 20),
        )

        self.list.bind("<<TreeviewSelect>>", self.on_select)
        self.list.bind("<Down>", lambda _: self.change_selection(1))
        self.list.bind("<Up>", lambda _: self.change_selection(-1))
        self.save_and_refresh()
        self.list.focus_force()

    @classmethod
    def rewrite_custom_menu(cls, menu: MenuMetadata) -> None:
        """Rewrite the Custom menu, given as an argument."""

        def subst_in_token(token: str) -> str:
            """Substitute values for "variables" in token.
            $f: full pathname of file
            $p: png name of current image
            $s: sequence number of current page from start of file
            $t: selected text (only first part if column selection)
            $u: unicode codepoint of current char

            Args:
                token: The token to make substitutions in.

            Returns:
                Substituted token.
            """

            # Png file name
            token = token.replace("$p", maintext().get_current_image_name())
            # Text/HTML file name
            token = token.replace("$f", cls.filename)
            # Offset png sequence number
            token = re.sub(
                r"\$\(s(-|\+)(\d+)\)",
                lambda m: str(
                    sequence_number() + (int(m[2]) if m[1] == "+" else -int(m[2]))
                ),
                token,
            )
            # Non-offset png sequence number
            token = token.replace("$s", str(sequence_number()))
            # Selected text
            token = token.replace("$t", re.sub(r"\s+", " ", maintext().selected_text()))
            # Unicode codepoint of current char (single selected char, or char following cursor)
            cur = maintext().current_character()
            token = token.replace("$u", f"{ord(cur):04x}" if cur else "")
            return token

        def sequence_number() -> int:
            """Return sequence number of current page."""
            sequence_number = 0
            cur_pos = maintext().get_insert_index().index()
            mark = "1.0"
            while mark := maintext().page_mark_next(mark):
                if maintext().compare(mark, ">", cur_pos):
                    break
                sequence_number += 1
            return max(1, sequence_number)

        def run_command(cmd_string: str) -> None:
            """Run command in subprocess. Copes with command containing
            quoted strings.

            Args:
                cmd_string: Command as single string.
            """
            cmd = shlex.split(cmd_string)
            if not cmd:
                return
            # Check if tokens require substitutions
            for itok, token in enumerate(cmd):
                cmd[itok] = subst_in_token(token)

            # If first token is a URL, insert `open`/`start`
            if cmd[0].startswith("http"):
                cmd.insert(0, "start" if is_windows() else "open")

            shell = False
            run_func: Callable = subprocess.run
            # Windows needs shell and a dummy arg with `start` command
            if is_windows() and cmd[0] == "start":
                cmd.insert(1, "")
                shell = True
                # `&` in URLs need escaping with `^` for the shell in Windows
                for itok, token in enumerate(cmd):
                    if token.startswith("http"):
                        cmd[itok] = token.replace("&", "^&")

            # Linux/Windows using app name rather than `open`/`start`
            # need `Popen` instead of `run` to avoid blocking
            if not is_mac() and cmd[0] not in ("start", "open"):
                run_func = subprocess.Popen

            try:
                run_func(cmd, shell=shell)  # pylint: disable=subprocess-run-check
            except OSError:
                logger.error(f"Unable to execute {cmd_string}")

        def add_custom_button(count: int, entry: list[str]) -> None:
            # 1 - 9 have numbers (& Alt-key shorcuts)
            if count < 10:
                count_str = f"~{count}: "
            # 10 - 34 have letters. Omit Z for use in "Customi~ze Menu" button
            elif count - 10 < len(ascii_uppercase) - 1:
                count_str = f"~{ascii_uppercase[count - 10]}: "
            else:
                count_str = ""
            menu.add_button(
                f"{count_str}{entry[0]}",
                lambda: run_command(entry[1]),
                add_to_command_palette=False,
            )

        menu.entries = []
        for count, entry in enumerate(
            preferences.get(PrefKey.CUSTOM_MENU_ENTRIES), start=1
        ):
            add_custom_button(count, entry)
        menu.add_separator()
        menu.add_button(
            "Customi~ze Menu",
            lambda: CustomMenuDialog.show_dialog(menu=menu),
        )

    @classmethod
    def store_filename(cls, filename: str) -> None:
        """Store current filename in class variable."""
        cls.filename = filename

    @classmethod
    def store_recreate_menus_callback(cls, callback: Callable) -> None:
        """Store function to be called to recreate menus."""
        cls.recreate_menus_callback = callback

    def move_up_down(self, direction: int) -> None:
        """Move the selected entry up/down in the list.

        Args:
            direction: +1 for down, -1 for up.
        """
        selected_item = self.list.selection()
        if not selected_item:
            return
        index = self.list.index(selected_item[0])
        new_index = index + direction
        if 0 <= index < len(self.menu_entries) and 0 <= new_index < len(
            self.menu_entries
        ):
            self.menu_entries[index], self.menu_entries[new_index] = (
                self.menu_entries[new_index],
                self.menu_entries[index],
            )
            self.save_and_refresh()
            self.list.select_and_focus_by_index(index + direction)

    def save_and_refresh(self) -> None:
        """Save entries in Prefs, reconfigure the Custom menu, and
        refresh the dialog view of the custom entries."""
        try:
            sel_index = self.list.index(self.list.selection()[0])
        except IndexError:
            sel_index = 0

        # Refresh the list
        self.list.delete(*self.list.get_children())
        for entry in self.menu_entries:
            self.list.insert("", tk.END, values=entry)
        if sel_index >= len(self.menu_entries):
            sel_index = len(self.menu_entries) - 1
        if sel_index >= 0:
            self.list.select_and_focus_by_index(sel_index)

        # Save to prefs file
        preferences.set(PrefKey.CUSTOM_MENU_ENTRIES, self.menu_entries)

        # Rewrite the menu
        self.rewrite_custom_menu(self.menu)
        assert CustomMenuDialog.recreate_menus_callback is not None
        CustomMenuDialog.recreate_menus_callback()  # pylint: disable=not-callable

    def change_selection(self, direction: int) -> str:
        """Change which is the selected entry in the list.

        Args:
            direction: +1 to move down, -1 to move up.
        """
        current_selection = self.list.selection()
        if current_selection:
            list_len = len(self.list.get_children())
            current_index = self.list.index(current_selection[0])
            new_index = current_index + direction
            if 0 <= new_index < list_len:
                self.list.select_and_focus_by_index(new_index)
        return "break"

    def add_entry(self) -> None:
        """Add an entry to the list."""
        label: str = self.label_entry.get().strip()
        command: str = self.command_entry.get().strip()
        if label and command:
            self.menu_entries.append([label, command])
            self.save_and_refresh()
            iid = self.list.get_children()[-1]
            self.list.selection_set(iid)

    def update_entry(self) -> None:
        """Update the current entry in the list."""
        selected_item = self.list.selection()
        if not selected_item:
            return
        index: int = self.list.index(selected_item[0])
        self.menu_entries[index] = [
            self.label_entry.get().strip(),
            self.command_entry.get().strip(),
        ]
        self.save_and_refresh()

    def remove_entry(self) -> None:
        """Remove the current entry from the list."""
        selected_item = self.list.selection()
        if not selected_item:
            return
        index: int = self.list.index(selected_item[0])
        del self.menu_entries[index]
        self.save_and_refresh()

    def on_select(self, _: tk.Event) -> None:
        """Display the values for the current entry."""
        selected_item = self.list.selection()
        if selected_item:
            values = self.list.item(selected_item[0], "values")
            self.label_entry.delete(0, tk.END)
            self.label_entry.insert(0, values[0])
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, values[1])


class AutoImageState(Enum):
    """Enum class to store AutoImage states to facilitate pausing
    and restarting AutoImage when needed."""

    NORMAL = auto()
    PAUSED = auto()
    RESTARTING = auto()


class MainImage(tk.Frame):
    """MainImage is a Frame, containing a Canvas which can display a png/jpeg file.

    Also contains scrollbars, and can be scrolled with mousewheel (vertically),
    Shift-mousewheel (horizontally) and zoomed with Control-mousewheel.

    MainImage can be docked or floating. Floating is not supported with ttk.Frame,
    hence inherits from tk.Frame.

    Attributes:
        hbar: Horizontal scrollbar.
        vbar: Vertical scrollbar.
        canvas: Canvas widget.
        image: Whole loaded image (or None)
        image_scale: Zoom scale at which image should be drawn.
        scale_delta: Ratio to multiply/divide scale when Control-scrolling mouse wheel.
    """

    def __init__(
        self,
        parent: tk.PanedWindow,
        hide_func: Callable[[], None],
        float_func: Callable[[Any], None],
        dock_func: Callable[[Any], None],
    ) -> None:
        """Initialize the MainImage to contain an empty Canvas with scrollbars.

        Args:
            hide_func: Function to hide the image viewer.
            float_func: Function to float the image viewer.
            dock_func: Function to dock the image viewer.
        """
        tk.Frame.__init__(self, parent, name=" Image Viewer")
        self.parent = parent
        self.hide_func = hide_func
        self.float_func = float_func
        self.dock_func = dock_func
        self.allow_geometry_storage = False
        self.short_name = ""
        self.short_name_label = tk.StringVar(self, "<no image>")
        self.rotation_details: dict[str, int] = {}

        # Introduce an apparently superfluous Frame to contain everything.
        # This is because when MainImage is undocked, Tk converts it to a
        # Toplevel widget. Any bindings on the MainImage are then reapplied
        # to the Toplevel widget, and Toplevel widgets apply their bindings
        # to all their children. So an Enter/Leave binding on MainImage would
        # cause an Enter/Leave to trigger when the mouse enters/leaves a button,
        # for example. Binding to top_frame instead means that the binding
        # doesn't get reapplied to the Toplevel widget, and it continues to
        # behave as required.
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="NSEW")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        control_frame = ttk.Frame(top_frame)
        control_frame.grid(row=0, column=0, columnspan=2, sticky="NSEW")
        control_frame.columnconfigure(9, weight=1)

        min_button_width = 1 if is_mac() else 2

        self.prev_img_button = ttk.Button(
            control_frame,
            text="<",
            width=min_button_width,
            command=lambda: self.next_image(reverse=True),
        )
        self.prev_img_button.grid(row=0, column=0, sticky="NSEW")
        ToolTip(self.prev_img_button, use_pointer_pos=True, msg="Previous image")

        def focus_prev(evt: tk.Event) -> str:
            if preferences.get(PrefKey.IMAGE_WINDOW_DOCKED):
                statusbar().set_focus("ordinal")
            else:
                focus_prev_widget(evt)
            return "break"

        self.prev_img_button.bind("<Shift-Tab>", focus_prev)

        self.next_img_button = ttk.Button(
            control_frame,
            text=">",
            width=min_button_width,
            command=self.next_image,
        )
        self.next_img_button.grid(row=0, column=1, sticky="NSEW")
        ToolTip(self.next_img_button, use_pointer_pos=True, msg="Next image")

        ttk.Label(control_frame, textvariable=self.short_name_label).grid(
            row=0, column=2, sticky="NSEW", padx=5
        )

        self.zoom_in_btn = ttk.Button(
            control_frame,
            text="+",
            width=min_button_width,
            command=lambda: self.image_zoom(zoom_in=True),
        )
        self.zoom_in_btn.grid(row=0, column=3, sticky="NSEW", padx=(10, 0))
        ToolTip(self.zoom_in_btn, use_pointer_pos=True, msg="Zoom in")

        self.zoom_out_btn = ttk.Button(
            control_frame,
            text="-",
            width=min_button_width,
            command=lambda: self.image_zoom(zoom_in=False),
        )
        self.zoom_out_btn.grid(row=0, column=4, sticky="NSEW")
        ToolTip(self.zoom_out_btn, use_pointer_pos=True, msg="Zoom out")

        self.rotate_btn = ttk.Button(
            control_frame,
            text="↺",
            width=min_button_width + 1 if is_mac() else min_button_width,
            command=self.rotate,
        )
        self.rotate_btn.grid(row=0, column=5, sticky="NSEW", padx=(10, 0))
        ToolTip(
            self.rotate_btn, use_pointer_pos=True, msg="Rotate 90º counter-clockwise"
        )

        self.ftw_btn = ttk.Checkbutton(
            control_frame,
            text="Fit ←→",
            variable=PersistentBoolean(PrefKey.IMAGE_AUTOFIT_WIDTH),
        )
        self.ftw_btn.grid(row=0, column=6, sticky="NSEW", padx=(10, 0))
        ToolTip(self.ftw_btn, use_pointer_pos=True, msg="Fit image to viewer width")

        self.fth_btn = ttk.Checkbutton(
            control_frame,
            text="Fit ↑↓",
            variable=PersistentBoolean(PrefKey.IMAGE_AUTOFIT_HEIGHT),
        )
        self.fth_btn.grid(row=0, column=7, sticky="NSEW", padx=(10, 0))
        ToolTip(self.fth_btn, use_pointer_pos=True, msg="Fit image to viewer height")

        self.invert_btn = ttk.Checkbutton(
            control_frame,
            text="Invert",
            command=self.show_image,
            variable=PersistentBoolean(PrefKey.IMAGE_INVERT),
        )
        self.invert_btn.grid(row=0, column=8, sticky="NSEW", padx=(10, 0))
        ToolTip(self.invert_btn, use_pointer_pos=True, msg="Invert image colors")

        self.dock_btn = ttk.Checkbutton(
            control_frame,
            text="Dock",
            command=self.set_image_docking,
            variable=PersistentBoolean(PrefKey.IMAGE_WINDOW_DOCKED),
        )
        self.dock_btn.grid(row=0, column=9, sticky="NSEW", padx=(10, 0))
        ToolTip(
            self.dock_btn,
            use_pointer_pos=True,
            msg="Dock / undock image viewer from main window",
        )

        self.close_btn = ttk.Button(
            control_frame,
            text="×",
            width=min_button_width,
            command=self.hide_func,
        )
        self.close_btn.grid(row=0, column=10, sticky="NSE")
        ToolTip(self.close_btn, use_pointer_pos=True, msg="Hide image viewer")

        def close_tab(evt: tk.Event) -> str:
            if preferences.get(PrefKey.IMAGE_WINDOW_DOCKED):
                maintext().focus()
            else:
                focus_next_widget(evt)
            return "break"

        self.close_btn.bind("<Tab>", close_tab)
        self.close_btn.bind("<Shift-Tab>", focus_prev_widget)

        # By default Tab is accepted by text widget, but we want it to move focus
        def text_reverse_tab(_: tk.Event) -> str:
            if preferences.get(PrefKey.IMAGE_VIEWER_INTERNAL) and preferences.get(
                PrefKey.IMAGE_WINDOW_DOCKED
            ):
                self.close_btn.focus()
            else:
                statusbar().set_focus("ordinal")
            return "break"

        def text_tab(_: tk.Event) -> str:
            """Switch focus from main text to peer widget."""
            if preferences.get(PrefKey.SPLIT_TEXT_WINDOW):
                maintext().peer.focus()
            else:
                statusbar().set_focus("rowcol")
            return "break"

        def peer_reverse_tab(_: tk.Event) -> str:
            """Switch focus from peer widget to main text."""
            maintext().focus()
            return "break"

        maintext().bind("<Tab>", text_tab)
        maintext().bind("<Shift-Tab>", text_reverse_tab)
        maintext().peer.bind("<Tab>", focus_next_widget)
        maintext().peer.bind("<Shift-Tab>", peer_reverse_tab)

        self.hbar = ttk.Scrollbar(top_frame, orient=tk.HORIZONTAL)
        self.hbar.grid(row=3, column=0, sticky="EW")
        self.hbar.configure(command=self.scroll_x)
        self.vbar = ttk.Scrollbar(top_frame, orient=tk.VERTICAL)
        self.vbar.grid(row=2, column=1, sticky="NS")
        self.vbar.configure(command=self.scroll_y)

        self.canvas = tk.Canvas(
            top_frame,
            xscrollcommand=self.hbar.set,
            yscrollcommand=self.vbar.set,
            highlightthickness=0,
            highlightbackground="darkorange",
        )
        self.canvas.grid(row=2, column=0, sticky="NSEW")
        top_frame.rowconfigure(2, weight=1)
        top_frame.columnconfigure(0, weight=1)

        self.canvas.bind("<Configure>", self.handle_configure)
        top_frame.bind("<Enter>", self.handle_enter)
        top_frame.bind("<Leave>", self.handle_leave)
        self.canvas.bind("<ButtonPress-1>", self.move_from)
        self.canvas.bind("<B1-Motion>", self.move_to)
        if is_x11():
            self.canvas.bind("<Control-Button-5>", self.wheel_zoom)
            self.canvas.bind("<Control-Button-4>", self.wheel_zoom)
            self.canvas.bind("<Button-5>", self.wheel_scroll)
            self.canvas.bind("<Button-4>", self.wheel_scroll)
        else:
            _, cm = process_accel("Cmd/Ctrl+MouseWheel")
            self.canvas.bind(cm, self.wheel_zoom)
            self.canvas.bind("<MouseWheel>", self.wheel_scroll)
            try:
                self.canvas.bind("<TouchpadScroll>", self.touchpad_scroll)
            except tk.TclError:
                pass  # OK if TouchpadScroll not supported (Tk <= 8.6)

        self.image_scale = float(preferences.get(PrefKey.IMAGE_SCALE_FACTOR))
        self.scale_delta = 1.1
        self.image: Optional[Image.Image] = None
        self.imageid = 0
        self.imagetk: Optional[ImageTk.PhotoImage] = None
        self.filename = ""
        self.width = 0
        self.height = 0
        # May want to pause auto image if user clicks prev/next file buttons
        self._auto_image_state = AutoImageState.NORMAL

    def add_orphan_commands(self) -> None:
        """Add orphan (i.e. not in menu) commands to command palette."""
        menubar_metadata().add_checkbutton_orphan(
            "Image AutoFit ←→", PrefKey.IMAGE_AUTOFIT_WIDTH
        )
        menubar_metadata().add_checkbutton_orphan(
            "Image AutoFit ↑↓",
            PrefKey.IMAGE_AUTOFIT_HEIGHT,
        )
        menubar_metadata().add_button_orphan(
            "Image Scroll ↑",
            lambda: self.canvas.yview_scroll(1, "units"),
        )
        menubar_metadata().add_button_orphan(
            "Image Scroll ↓",
            lambda: self.canvas.yview_scroll(-1, "units"),
        )
        menubar_metadata().add_button_orphan(
            "Image Scroll ←",
            lambda: self.canvas.xview_scroll(1, "units"),
        )
        menubar_metadata().add_button_orphan(
            "Image Scroll →",
            lambda: self.canvas.xview_scroll(-1, "units"),
        )
        menubar_metadata().add_button_orphan(
            "Image Zoom In", lambda: self.image_zoom(zoom_in=True), "Cmd/Ctrl+plus"
        )
        menubar_metadata().add_button_orphan(
            "Image Zoom In ", lambda: self.image_zoom(zoom_in=True), "Cmd/Ctrl+equal"
        )
        menubar_metadata().add_button_orphan(
            "Image Zoom Out", lambda: self.image_zoom(zoom_in=False), "Cmd/Ctrl+minus"
        )
        menubar_metadata().add_button_orphan(
            "Image Fit ↑↓",
            lambda: self.image_zoom_to_height(disable_autofit=True),
            "Cmd/Ctrl+0",
        )

    def scroll_y(self, *args: Any, **kwargs: Any) -> None:
        """Scroll canvas vertically and redraw the image"""
        self.canvas.yview(*args, **kwargs)
        self.show_image()

    def scroll_x(self, *args: Any, **kwargs: Any) -> None:
        """Scroll canvas horizontally and redraw the image."""
        self.canvas.xview(*args, **kwargs)
        self.show_image()

    def move_from(self, event: tk.Event) -> None:
        """Remember previous coordinates for dragging with the mouse."""
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event: tk.Event) -> None:
        """Drag canvas to the new position."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.show_image()

    def wheel_zoom(self, event: tk.Event) -> None:
        """Zoom with mouse wheel.

        Args:
            event: Event containing mouse wheel info.
        """
        # Respond to Linux (event.num) or Windows/MacOS (event.delta) wheel event
        if event.num == 5 or event.delta < 0:
            self.zoom_out_btn.invoke()
        if event.num == 4 or event.delta > 0:
            self.zoom_in_btn.invoke()

    def image_zoom(self, zoom_in: bool) -> None:
        """Zoom the image in or out.

        Args:
            zoom_in: True to zoom in, False to zoom out.
        """
        # If user zooms manually, turn off the autofit modes to avoid
        # unexpected weird behaviors and confusion.
        preferences.set(PrefKey.IMAGE_AUTOFIT_WIDTH, False)
        preferences.set(PrefKey.IMAGE_AUTOFIT_HEIGHT, False)
        if zoom_in:
            if self.image_scale < 3:
                self.image_scale *= self.scale_delta
        else:
            if self.image_scale > 0.1:
                self.image_scale /= self.scale_delta
        preferences.set(PrefKey.IMAGE_SCALE_FACTOR, self.image_scale)
        self.show_image()

    def image_zoom_to_width(self) -> None:
        """Zoom image to fit to width of image window."""
        if not self.imageid:
            return
        bbox_image = self.canvas.bbox(self.imageid)
        scale_factor = (
            self.canvas.canvasx(self.canvas.winfo_width()) - self.canvas.canvasx(0)
        ) / (bbox_image[2] - bbox_image[0])
        self.image_zoom_by_factor(scale_factor)

    def image_zoom_to_height(self, disable_autofit: bool = False) -> None:
        """Zoom image to fit to height of image window."""
        if not self.imageid:
            return
        if disable_autofit:
            preferences.set(PrefKey.IMAGE_AUTOFIT_WIDTH, False)
            preferences.set(PrefKey.IMAGE_AUTOFIT_HEIGHT, False)
        bbox_image = self.canvas.bbox(self.imageid)
        scale_factor = (
            self.canvas.canvasy(self.canvas.winfo_height()) - self.canvas.canvasy(0)
        ) / (bbox_image[3] - bbox_image[1])
        self.image_zoom_by_factor(scale_factor)

    def image_zoom_by_factor(self, scale_factor: float) -> None:
        """Zoom image by the given scale factor.

        Args:
            scale_factor: Factor to zoom by.
        """
        self.image_scale *= scale_factor
        preferences.set(PrefKey.IMAGE_SCALE_FACTOR, self.image_scale)
        self.show_image()

    def show_image(self, internal_only: bool = False) -> None:
        """Show image on the Canvas.

        Args:
            internal_only: Whether to only reload internal viewer."""
        # If using external viewer, spawn a process to run it
        # If internal viewer is shown, image will be loaded in that too
        if preferences.get(PrefKey.IMAGE_VIEWER_EXTERNAL) and not internal_only:
            viewer_path = preferences.get(PrefKey.IMAGE_VIEWER_EXTERNAL_PATH)

            # All 3 OSes can open a file with the default viewer or specific app:
            # Windows (default):  `start "" <filename>`
            # Windows (with app): `<app> <filename>`
            # macOS (default):    `open -g <filename>`
            # macOS (with app):   `open -g [-a <app>] <filename>`
            # Linux (default):    `open <filename>`
            # Linux (with app):   `<app> <filename>`

            # Only Windows needs `shell=True` arg to use with `start`
            shell = False
            # Linux/Windows using `<app>` need `Popen` instead of `run` to avoid blocking
            run_func: Callable[..., Any] = subprocess.run

            if is_windows():
                if viewer_path:
                    cmd = [viewer_path]
                    run_func = subprocess.Popen
                else:
                    cmd = ["start", ""]
                    shell = True
            elif is_mac():
                cmd = ["open", "-g"]  # `-g` to avoid bringing app to foreground
                if viewer_path:
                    cmd += ["-a"] + viewer_path.split()
            else:
                if viewer_path:
                    cmd = viewer_path.split()
                    run_func = subprocess.Popen
                else:
                    cmd = ["open"]
            cmd.append(self.filename)

            focus_widget = root().focus_get()
            try:
                run_func(cmd, shell=shell)  # pylint: disable=subprocess-run-check
            except OSError:
                logger.error(
                    f"Unable to execute {cmd}\nTry configuring viewer in Preferences dialog."
                )
            # Try to get focus back for 200 milliseconds
            if not is_mac():
                self.regrab_focus(focus_widget, 200)

        # Get image area & remove 1 pixel shift
        if self.image is None:
            return
        self.canvas["background"] = themed_style().lookup("TButton", "background")
        image = self.image
        self.image_scale = max(self.image_scale, 50 / image.width, 50 / image.height)
        preferences.set(PrefKey.IMAGE_SCALE_FACTOR, self.image_scale)
        scaled_width = int(self.image_scale * image.width + 1)
        scaled_height = int(self.image_scale * image.height + 1)
        if preferences.get(PrefKey.IMAGE_INVERT):
            image = ImageChops.invert(self.image)
        if self.imagetk:
            del self.imagetk
        image = image.resize(
            size=(scaled_width, scaled_height), resample=Image.Resampling.LANCZOS
        )
        if not preferences.get(PrefKey.HIGH_CONTRAST):
            alpha_value = 180 if themed_style().is_dark_theme() else 200
            image.putalpha(alpha_value)  # Adjust contrast using transparency
        self.imagetk = ImageTk.PhotoImage(image)
        if self.imageid:
            self.canvas.delete(self.imageid)
        self.imageid = self.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.imagetk,
        )
        self.canvas.configure(scrollregion=self.canvas.bbox(self.imageid))

    def regrab_focus(
        self, focus_widget: Optional[tk.Misc], remaining_period: int
    ) -> None:
        """Grab focus back from external image viewer.

        Args:
            focus_widget: Widget to return focus to
            remaining_period: Number of milliseconds remaining in regrab period
        """
        # If focus widget no longer exists, then focus in main text instead
        if focus_widget is None or not focus_widget.winfo_exists():
            focus_widget = maintext()
        focus_widget.focus_force()
        remaining_period -= 10
        if remaining_period >= 0:
            self.after(10, lambda: self.regrab_focus(focus_widget, remaining_period))

    def wheel_scroll(self, evt: tk.Event) -> None:
        """Scroll image up/down using mouse wheel."""
        if evt.state == 0:
            if is_mac() and tk.TkVersion < 3.7:
                self.canvas.yview_scroll(int(-1 * evt.delta), "units")
            else:
                self.canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")
        if evt.state == 1:
            if is_mac() and tk.TkVersion < 3.7:
                self.canvas.xview_scroll(int(-1 * evt.delta), "units")
            else:
                self.canvas.xview_scroll(int(-1 * (evt.delta / 120)), "units")
        self.show_image()

    def touchpad_scroll(self, evt: tk.Event) -> None:
        """Scroll image using touchpad."""

        def to_signed_16(n: int) -> int:
            return n if n < 0x8000 else n - 0x10000

        xscr = to_signed_16((evt.delta >> 16) & 0xFFFF)
        yscr = to_signed_16(evt.delta & 0xFFFF)
        # Only act on the given fraction of events
        scroll_rate_numerator = 1
        scroll_rate_denominator = 3
        if abs(evt.serial % scroll_rate_denominator) >= scroll_rate_numerator:
            return
        absy = abs(yscr)
        absx = abs(xscr)
        wiggle_tolerance = 2
        # To try to avoid slight wiggling while attempting unidirectional scroll,
        # only scroll bidirectionally if lesser change is more than wiggle_tolerance.
        # Also scroll bidirectionally if x & y change equal
        if (
            (absy > absx > wiggle_tolerance)
            or (absx > absy > wiggle_tolerance)
            or absx == absy
        ):
            self.canvas.xview_scroll(-xscr, "units")
            self.canvas.yview_scroll(-yscr, "units")
        # Lesser change is within wiggle_tolerance, so suppress it
        elif absy > absx:
            self.canvas.yview_scroll(-yscr, "units")
        elif absx > absy:
            self.canvas.xview_scroll(-xscr, "units")

    def load_image(self, filename: Optional[str] = None) -> bool:
        """Load or clear the given image file.

        Args:
            filename: Optional name of image file. If none given, clear image.

        Returns:
            True if new file was loaded, False otherwise
        """
        if filename == self.filename:
            return False

        if filename and os.path.isfile(filename):
            self.filename = filename
            self.image = Image.open(filename).convert("RGB")
            self.width, self.height = self.image.size
            self.canvas.yview_moveto(0)
            self.canvas.xview_moveto(0)
            self.set_short_name()
            if self.short_name in self.rotation_details:
                if self.rotation_details[self.short_name] != 0:
                    self.image = self.image.rotate(
                        self.rotation_details[self.short_name], expand=True
                    )
            self.show_image()
            if preferences.get(PrefKey.IMAGE_AUTOFIT_WIDTH):
                mainimage().image_zoom_to_width()
            elif preferences.get(PrefKey.IMAGE_AUTOFIT_HEIGHT):
                mainimage().image_zoom_to_height()
        else:
            self.clear_image()
        return True

    def clear_image(self) -> None:
        """Clear the image and reset variables accordingly."""
        self.filename = ""
        self.image = None
        if self.imageid:
            self.canvas.delete(self.imageid)
        self.imageid = 0
        self.set_short_name()

    def set_image_docking(self) -> None:
        """Float/dock image depending on flag."""
        if preferences.get(PrefKey.IMAGE_WINDOW_DOCKED):
            self.dock_func(None)
        else:
            self.float_func(None)

    def is_image_loaded(self) -> bool:
        """Return if an image is currently loaded."""
        return self.image is not None

    def enable_geometry_storage(self) -> None:
        """Permit storage of image viewer geometry.

        Don't want to allow it right at start in case window manager places
        dialog, causing a config event and overwriting the stored geometry.
        """
        try:
            tk.Wm.geometry(self, preferences.get(PrefKey.IMAGE_FLOAT_GEOMETRY))  # type: ignore[call-overload]
        except tk.TclError:
            pass
        self.allow_geometry_storage = True

    def handle_configure(self, evt: Optional[tk.Event]) -> None:
        """Handle configure event."""
        if preferences.get(PrefKey.IMAGE_WINDOW_DOCKED):
            try:  # In case unlucky timing means it tries to configure during undocking & finds sash doesn't exist
                preferences.set(
                    PrefKey.IMAGE_DOCK_SASH_COORD, self.parent.sash_coord(0)[0]
                )
            except tk.TclError:
                pass
        elif self.allow_geometry_storage:
            try:  # In case unlucky timing means it tries to configure during docking & widget isn't a toplevel
                preferences.set(PrefKey.IMAGE_FLOAT_GEOMETRY, tk.Wm.geometry(self))  # type: ignore[call-overload]
            except tk.TclError:
                pass
        if evt and evt.type == EventType.Configure:
            if preferences.get(PrefKey.IMAGE_AUTOFIT_WIDTH):
                mainimage().image_zoom_to_width()
            elif preferences.get(PrefKey.IMAGE_AUTOFIT_HEIGHT):
                mainimage().image_zoom_to_height()

    def handle_enter(self, _event: tk.Event) -> None:
        """Handle enter event."""
        self.auto_image_state(AutoImageState.NORMAL)

    def handle_leave(self, _event: tk.Event) -> None:
        """Handle leave event."""
        # Restart auto img
        if self.auto_image_state() == AutoImageState.PAUSED:
            self.auto_image_state(AutoImageState.RESTARTING)

    def alert_user(self) -> None:
        """Flash the image border if preference enabled."""
        if not preferences.get(PrefKey.IMAGE_VIEWER_ALERT):
            return

        def set_canvas_highlight(thickness: int) -> None:
            """Set highlightthickness for canvas"""
            self.canvas["highlightthickness"] = thickness

        set_canvas_highlight(4)
        self.after(500, lambda: set_canvas_highlight(0))

    def auto_image_state(
        self, value: Optional[AutoImageState] = None
    ) -> AutoImageState:
        """Set or query whether auto_image is paused or restarting."""
        if value is not None:
            self._auto_image_state = value
        return self._auto_image_state

    def next_image(self, reverse: bool = False) -> None:
        """Load the next image alphabetically.

        Args:
            reverse: True to load previous image instead.
        """
        if not self.filename:
            sound_bell()
            return

        # Check current directory is valid
        current_dir = os.path.dirname(self.filename)
        if not os.path.isdir(current_dir):
            logger.error(f"Image directory invalid: {current_dir}")
            return

        current_basename = os.path.basename(self.filename)
        found = False
        for fn in sorted(os.listdir(current_dir), reverse=reverse):
            # Skip non-image files by checking extension
            if os.path.splitext(fn)[1] not in (".jpg", ".gif", ".png"):
                continue
            # If found on previous time through loop, this is the file we want
            if found:
                self.load_image(os.path.join(current_dir, fn))
                self.auto_image_state(AutoImageState.PAUSED)
                return
            if fn == current_basename:
                found = True

        # Reached end of dir listing without finding next file
        sound_bell()

    def set_short_name(self) -> None:
        """Extract a short name from the full image path to use as a label
        in the image viewer. When no image is loaded, returns a placeholder
        '<no image>'."""
        if self.filename:
            self.short_name = Path(self.filename).stem
            self.short_name_label.set(self.short_name)
        else:
            self.short_name = ""
            self.short_name_label.set("<no image>")

    def rotate(self) -> None:
        """Rotate the current image counter-clockwise."""
        if self.image:
            current_rotation = self.get_current_rotation()
            if current_rotation == 270:
                self.rotation_details[self.short_name] = 0
            else:
                if self.short_name in self.rotation_details:
                    self.rotation_details[self.short_name] += 90
                else:
                    self.rotation_details[self.short_name] = 90

            self.image = self.image.rotate(90, expand=True)
            maintext().set_modified(True)
            self.show_image()

            if preferences.get(PrefKey.IMAGE_AUTOFIT_WIDTH):
                mainimage().image_zoom_to_width()
            elif preferences.get(PrefKey.IMAGE_AUTOFIT_HEIGHT):
                mainimage().image_zoom_to_height()

    def get_current_rotation(self) -> int:
        """Return the current rotation for one image"""
        if self.image:
            if self.short_name in self.rotation_details:
                return self.rotation_details[self.short_name]

        # Default rotation is 0; return even if there's not an image loaded
        return 0

    def reset_rotation_details(self) -> None:
        """Reset rotation state for the mainimage widget"""
        self.rotation_details = {}


class StatusBar(ttk.Frame):
    """Statusbar at the bottom of the screen.

    Fields in statusbar can be automatically or manually updated.
    """

    BTN_1 = "ButtonRelease-1"
    BTN_3 = "ButtonRelease-3"
    SHIFT_BTN_1 = "Shift-ButtonRelease-1"
    SHIFT_BTN_3 = "Shift-ButtonRelease-3"

    def __init__(self, parent: ttk.Frame) -> None:
        """Initialize statusbar within given frame.

        Args:
            parent: Frame to contain status bar.
        """
        super().__init__(parent)
        self.fields: dict[str, ttk.Button] = {}
        self.callbacks: dict[str, Optional[Callable[[], str]]] = {}
        self._update()

    def add(
        self,
        key: str,
        tooltip: str = "",
        update: Optional[Callable[[], str]] = None,
        **kwargs: Any,
    ) -> None:
        """Add field to status bar

        Args:
            key: Key to use to refer to field.
            update: Optional callback function that returns a string.
              If supplied, field will be regularly updated automatically with
              the string returned by ``update()``. If argument not given,
              application is responsible for updating, using ``set(key)``.
        """
        self.fields[key] = ttk.Button(self, **kwargs)
        self.callbacks[key] = update
        self.fields[key].grid(column=len(self.fields), row=0)
        if tooltip:
            ToolTip(self.fields[key], msg=tooltip)

    def set(self, key: str, value: str) -> None:
        """Set field in statusbar to given value.

        Args:
            key: Key to refer to field.
            value: String to use to update field.
        """
        self.fields[key].config(text=value)

    def _update(self) -> None:
        """Update fields in statusbar that have callbacks. Updates every
        200 milliseconds.
        """
        for key in self.fields:
            func = self.callbacks[key]
            if func is not None:
                self.set(key, func())
        self.after(200, self._update)

    def add_binding(self, key: str, event: str, callback: Callable[[], Any]) -> None:
        """Add an action to be executed when the given event occurs

        Args:
            key: Key to refer to field.
            callback: Function to be called when event occurs.
            event: Event to trigger action. Use button release to avoid
              clash with button activate appearance behavior.
              Also bind Space to do same as button 1;
              Cmd/Ctrl+button 1 and Cmd/Ctrl+space as button 3,
              all with optional Shift key modifier
        """
        mouse_bind(self.fields[key], event, lambda _: callback())
        if event == StatusBar.BTN_1:
            mouse_bind(self.fields[key], "space", lambda _: callback())
        elif event == StatusBar.SHIFT_BTN_1:
            mouse_bind(self.fields[key], "Shift+space", lambda _: callback())
        if event == StatusBar.BTN_3:
            mouse_bind(self.fields[key], "Ctrl+ButtonRelease-1", lambda _: callback())
            mouse_bind(self.fields[key], "Ctrl+space", lambda _: callback())
        elif event == StatusBar.SHIFT_BTN_3:
            mouse_bind(
                self.fields[key], "Shift+Ctrl+ButtonRelease-1", lambda _: callback()
            )
            mouse_bind(self.fields[key], "Shift+Ctrl+space", lambda _: callback())

    def set_last_tab_behavior(self, key: str, wgt: tk.Widget) -> None:
        """Set up tab bindings for last status bar button.

        Args:
            key: Key of button to bind to.
            wgt: Widget to focus on when Tab is pressed.
        """

        def focus_next(_: tk.Event) -> str:
            if preferences.get(PrefKey.IMAGE_VIEWER_INTERNAL) and preferences.get(
                PrefKey.IMAGE_WINDOW_DOCKED
            ):
                wgt.focus()
            else:
                maintext().focus()
            return "break"

        self.fields[key].bind("<Tab>", focus_next)
        self.fields[key].bind("<Shift-Tab>", focus_prev_widget)

    def set_first_tab_behavior(self, key: str) -> None:
        """Set up tab bindings for first status bar button.

        Args:
            key: Key of button to bind to.
        """

        def focus_prev(_: tk.Event) -> str:
            if preferences.get(PrefKey.SPLIT_TEXT_WINDOW):
                maintext().peer.focus()
            else:
                maintext().focus()
            return "break"

        self.fields[key].bind("<Tab>", focus_next_widget)
        self.fields[key].bind("<Shift-Tab>", focus_prev)

    def set_focus(self, key: str) -> None:
        """Set focus to given statusbar button."""
        self.fields[key].focus()


class ScrolledReadOnlyText(tk.Text):
    """Implement a read only mode text editor class with scroll bar.

    Done by replacing the bindings for the insert and delete events. From:
    http://stackoverflow.com/questions/3842155/is-there-a-way-to-make-the-tkinter-text-widget-read-only
    """

    # Tag can be used to select a line of text, and to search for the selected line
    # Can't use standard selection since that would interfere with user trying to copy/paste, etc.
    SELECT_TAG_NAME = "chk_select"

    def __init__(self, parent: tk.Widget, context_menu: bool = True, **kwargs: Any):
        """Init the class and set the insert and delete event bindings."""

        self.frame = ttk.Frame(parent)
        self.frame.grid(row=0, column=0, sticky="NSEW")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        super().__init__(self.frame, spacing1=maintext()["spacing1"], **kwargs)
        super().grid(column=0, row=0, sticky="NSEW")
        self.redirector = WidgetRedirector(self)
        self.insert = self.redirector.register("insert", lambda *args, **kw: "break")  # type: ignore[method-assign]
        self.delete = self.redirector.register("delete", lambda *args, **kw: "break")  # type: ignore[method-assign]

        hscroll = ttk.Scrollbar(self.frame, orient=tk.HORIZONTAL, command=self.xview)
        hscroll.grid(column=0, row=1, sticky="NSEW")
        self["xscrollcommand"] = hscroll.set
        vscroll = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.yview)
        vscroll.grid(column=1, row=0, sticky="NSEW")
        self["yscrollcommand"] = vscroll.set

        self["inactiveselect"] = self["selectbackground"]

        self.tag_configure(
            ScrolledReadOnlyText.SELECT_TAG_NAME,
            background="#dddddd",
            foreground="#000000",
        )

        self["cursor"] = "arrow"

        # Since Text widgets don't normally listen to theme changes,
        # need to do it explicitly here.
        super().bind(
            "<<ThemeChanged>>",
            lambda _event: maintext().theme_set_tk_widget_colors(self),
        )
        # Also on creation, so it's correct for the current theme
        maintext().theme_set_tk_widget_colors(self)

        # By default Tab is accepted by text widget, but we want it to move focus
        self.bind("<Tab>", focus_next_widget)
        self.bind("<Shift-Tab>", focus_prev_widget)

        # Redirect attempts to undo & redo to main text window
        # Keystrokes match those in Undo/Redo menu buttons, with case handled manually here
        _, key_event = process_accel("Cmd/Ctrl+Z")
        super().bind(key_event, lambda _event: maintext().event_generate("<<Undo>>"))
        _, key_event = process_accel("Cmd/Ctrl+z")
        super().bind(key_event, lambda _event: maintext().event_generate("<<Undo>>"))
        _, key_event = process_accel("Cmd+Shift+Z" if is_mac() else "Ctrl+Y")
        super().bind(key_event, lambda _event: maintext().event_generate("<<Redo>>"))
        _, key_event = process_accel("Cmd+Shift+z" if is_mac() else "Ctrl+y")
        super().bind(key_event, lambda _event: maintext().event_generate("<<Redo>>"))

        # Intercept copy/cut to queue macOS fix before default copy/cut behavior
        def copy_fix(_e: tk.Event) -> str:
            maintext().clipboard_fix()
            return ""  # Permit default behavior to happen

        super().bind("<<Copy>>", copy_fix)
        super().bind("<<Cut>>", copy_fix)

        if context_menu:
            add_text_context_menu(self, read_only=True)

    def grid(self, *args: Any, **kwargs: Any) -> None:
        """Override ``grid``, so placing Text actually places surrounding Frame"""
        return self.frame.grid(*args, **kwargs)

    def select_line(self, line_num: int) -> None:
        """Highlight the line_num'th line of text, removing any other highlights.

        Args:
            line_num: Line number to be highlighted - assumed valid.
        """
        self.tag_remove(ScrolledReadOnlyText.SELECT_TAG_NAME, "1.0", tk.END)
        self.tag_add(
            ScrolledReadOnlyText.SELECT_TAG_NAME, f"{line_num}.0", f"{line_num + 1}.0"
        )
        self.see(f"{line_num}.0")

    def get_select_line_num(self) -> Optional[int]:
        """Get the line number of the currently selected line.

        Returns:
            Line number of selected line, or None if no line selected.
        """
        if tag_range := self.tag_nextrange(ScrolledReadOnlyText.SELECT_TAG_NAME, "1.0"):
            return IndexRowCol(tag_range[0]).row
        return None


class MessageLogDialog(ToplevelDialog):
    """A dialog that displays error/info messages."""

    manual_page = "View_Menu#Message_Log"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize messagelog dialog."""
        super().__init__("Message Log", *args, **kwargs)
        self.messagelog = ScrolledReadOnlyText(self.top_frame, wrap=tk.NONE)
        self.messagelog.grid(column=0, row=0, sticky="NSEW")

    def append(self, message: str) -> None:
        """Append a message to the message log dialog."""
        self.messagelog.insert("end", message)


class ErrorHandler(logging.Handler):
    """Handle GUI output of error messages."""

    def __init__(self, *args: Any) -> None:
        """Initialize error logging handler."""
        super().__init__(*args)

    def emit(self, record: logging.LogRecord) -> None:
        """Output error message to message box.

        Args:
            record: Record containing error message.
        """
        messagebox.showerror(title=record.levelname, message=record.getMessage())


class MessageLog(logging.Handler):
    """Handle GUI output of all messages."""

    def __init__(self, *args: Any) -> None:
        """Initialize the message log handler."""
        super().__init__(*args)
        self._messagelog: str = ""
        self.dialog: MessageLogDialog

    def emit(self, record: logging.LogRecord) -> None:
        """Log message in message log.

        Args:
            record: Record containing message.
        """
        message = self.format(record) + "\n"
        self._messagelog += message

        # If dialog is visible, append error
        if hasattr(self, "dialog") and self.dialog.winfo_exists():
            self.dialog.append(message)
            self.dialog.lift()

    def show(self) -> None:
        """Show the message log dialog."""
        already_shown = hasattr(self, "dialog") and self.dialog.winfo_exists()
        self.dialog = MessageLogDialog.show_dialog()
        if not already_shown:
            self.dialog.append(self._messagelog)
        self.dialog.lift()


class MainWindow:
    """Handles the construction of the main window with its basic widgets

    These class variables are set in ``__init__`` to store the single instance
    of these main window items. They are exposed externally via convenience
    functions with the same names, e.g. ``root()`` returns ``MainWindow.root``
    """

    menubar: tk.Menu
    mainimage: MainImage
    statusbar: StatusBar
    messagelog: MessageLog
    busy_widget: ttk.Label

    def __init__(self) -> None:
        Root()
        # Themes
        themed_style(ThemedStyle())

        MainWindow.menubar = tk.Menu()
        root()["menu"] = menubar()
        MainWindow.messagelog = MessageLog()

        status_frame = ttk.Frame(root())
        status_frame.grid(
            column=STATUS_COL,
            row=STATUS_ROW,
            sticky="NSEW",
        )
        status_frame.columnconfigure(0, weight=1)
        MainWindow.statusbar = StatusBar(status_frame)
        MainWindow.statusbar.grid(
            column=0,
            row=0,
            sticky="NSW",
        )
        MainWindow.busy_widget = ttk.Label(status_frame, foreground="red")
        MainWindow.busy_widget.grid(
            column=1,
            row=0,
            sticky="NSE",
            padx=10,
        )
        Busy.busy_widget_setup(MainWindow.busy_widget)

        ttk.Separator(root()).grid(
            column=SEPARATOR_COL,
            row=SEPARATOR_ROW,
            sticky="NSEW",
        )

        self.paned_window = tk.PanedWindow(
            root(),
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief=tk.RIDGE,
            showhandle=True,
            handlesize=10,
        )
        self.paned_window.grid(
            column=TEXTIMAGE_WINDOW_COL, row=TEXTIMAGE_WINDOW_ROW, sticky="NSEW"
        )

        self.paned_text_window = tk.PanedWindow(
            self.paned_window,
            orient=tk.VERTICAL,
            sashwidth=4,
            sashrelief=tk.RIDGE,
            showhandle=True,
            handlesize=10,
        )
        self.paned_text_window.grid(
            column=TEXTIMAGE_WINDOW_COL, row=TEXTIMAGE_WINDOW_ROW, sticky="NSEW"
        )

        MainText(
            self.paned_text_window,
            root(),
            undo=True,
            wrap="none",
            autoseparators=True,
            maxundo=-1,
            highlightthickness=2,
        )

        self.paned_window.add(self.paned_text_window, minsize=MIN_PANE_WIDTH)
        add_text_context_menu(maintext())
        add_text_context_menu(maintext().peer)

        MainWindow.mainimage = MainImage(
            self.paned_window,
            hide_func=self.hide_image,
            float_func=self.float_image,
            dock_func=self.dock_image,
        )
        if preferences.get(PrefKey.IMAGE_VIEWER_INTERNAL):
            root().after_idle(lambda: self.load_image("", force_show=True))

    def hide_image(self) -> None:
        """Stop showing the current image."""
        # If only showing internal viewer, then closing it also requires
        # turning off AutoImg, or it will just be shown again
        # If external viewer is on, then AutoImg can remain on, and
        # display images in external viewer once internal viewer is closed.
        if not preferences.get(PrefKey.IMAGE_VIEWER_EXTERNAL):
            preferences.set(PrefKey.AUTO_IMAGE, False)
        self.clear_image()
        root().wm_forget(mainimage())  # type: ignore[arg-type]
        self.paned_window.forget(mainimage())
        preferences.set(PrefKey.IMAGE_VIEWER_INTERNAL, False)

    def float_image(self, _event: Optional[tk.Event] = None) -> None:
        """Float the image into a separate window"""
        mainimage().grid_remove()
        root().wm_manage(mainimage())
        mainimage().lift()
        # Obscure tk.Wm calls needed because although mainimage has been converted
        # to a toplevel by Tk, it doesn't appear as though tkinter knows about it,
        # so can't call mainimage().wm_geometry() or set the size via normal config
        # methods.
        tk.Wm.geometry(mainimage(), preferences.get(PrefKey.IMAGE_FLOAT_GEOMETRY))  # type: ignore[call-overload]
        tk.Wm.protocol(mainimage(), "WM_DELETE_WINDOW", self.hide_image)  # type: ignore[call-overload]
        preferences.set(PrefKey.IMAGE_VIEWER_INTERNAL, True)

        # It is OK to save image viewer geometry from now on
        mainimage().enable_geometry_storage()

    def dock_image(self, _event: Optional[tk.Event] = None) -> None:
        """Dock the image back into the main window"""
        root().wm_forget(mainimage())  # type: ignore[arg-type]
        self.paned_window.add(mainimage(), minsize=MIN_PANE_WIDTH)
        self.paned_window.sash_place(
            0, preferences.get(PrefKey.IMAGE_DOCK_SASH_COORD), 0
        )
        preferences.set(PrefKey.IMAGE_VIEWER_INTERNAL, True)
        preferences.set(PrefKey.IMAGE_WINDOW_DOCKED, True)

    def load_image(self, filename: str, force_show: bool = False) -> None:
        """Load the image for the given page.

        Args:
            filename: Path to image file.
            force_show: True to force dock or float image
        """
        image_already_loaded = mainimage().is_image_loaded()
        if force_show or mainimage().load_image(filename) and not image_already_loaded:
            if preferences.get(PrefKey.IMAGE_VIEWER_EXTERNAL) and not force_show:
                return  # External viewer launched from MainImage
            if preferences.get(PrefKey.IMAGE_WINDOW_DOCKED):
                self.dock_image()
            else:
                self.float_image()

    def clear_image(self) -> None:
        """Clear the image currently being shown."""
        mainimage().clear_image()


def do_sound_bell() -> None:
    """Sound warning bell audibly and/or visually.

    Audible uses the default system bell sound.
    Visible flashes the first statusbar button (must be ttk.Button)
    """
    if preferences.get(PrefKey.BELL_AUDIBLE):
        root().bell()
    if preferences.get(PrefKey.BELL_VISUAL):
        bell_button = statusbar().fields["rowcol"]
        # Belt & suspenders: uses the "disabled" state of button in temporary style,
        # but also restores setting in temporary style, and restores default style.
        style = ttk.Style()
        # Set temporary style's disabled bg to red
        style.map("W.TButton", foreground=[("disabled", "red")])
        # Save current disabled bg default for buttons
        save_bg = style.lookup("TButton", "background", state=["disabled"])
        # Save style currently used by button
        cur_style = bell_button["style"]
        # Set button to use temporary style
        bell_button.configure(style="W.TButton")
        # Flash 3 times
        for state in ("disabled", "normal", "disabled", "normal", "disabled", "normal"):
            bell_button["state"] = state
            bell_button.update()
            time.sleep(0.08)
        # Set button to use its previous style again
        bell_button.configure(style=cur_style)
        # Just in case, set the temporary style back to the default
        style.map("W.TButton", background=[("disabled", save_bg)])


bell_set_callback(do_sound_bell)


def add_text_context_menu(text_widget: tk.Text, read_only: bool = False) -> None:
    """Add a context menu to a Text widget.

    Puts Cut, Copy, Paste, Select All menu buttons in a context menu.

    Args:
        read_only: True if text is read-only, so does not require Cut & Paste options.
    """
    menu_context = Menu(text_widget, "")
    menu_context.add_cut_copy_paste(read_only=read_only)

    def post_context_menu(event: tk.Event) -> None:
        event.widget.focus_set()
        menu_context.post(event.x_root, event.y_root)

    mouse_bind(text_widget, "3", post_context_menu)


def mainimage() -> MainImage:
    """Return the single MainImage widget"""
    assert MainWindow.mainimage is not None
    return MainWindow.mainimage


def menubar() -> tk.Menu:
    """Return the single Menu widget used as the menubar"""
    assert MainWindow.menubar is not None
    return MainWindow.menubar


def statusbar() -> StatusBar:
    """Return the single StatusBar widget"""
    assert MainWindow.statusbar is not None
    return MainWindow.statusbar


def image_autofit_width_callback(value: bool) -> None:
    """Callback when fit-to-width checkbox is clicked.

    Deactivates the other mode (due to mutual exclusivity), then
    activates the appropriate zoom mode."""
    if value:
        preferences.set(PrefKey.IMAGE_AUTOFIT_HEIGHT, False)
        mainimage().image_zoom_to_width()


def image_autofit_height_callback(value: bool) -> None:
    """Callback when fit-to-height checkbox is clicked.

    Deactivates the other mode (due to mutual exclusivity), then
    activates the appropriate zoom mode."""
    if value:
        preferences.set(PrefKey.IMAGE_AUTOFIT_WIDTH, False)
        mainimage().image_zoom_to_height()
