#!/usr/bin/env python
"""Guiguts - an application to support creation of ebooks for PG"""


import argparse
import os.path
import re
import subprocess
from tkinter import messagebox
from typing import Any
import webbrowser

# Allow running this file directly during development
if __name__ == "__main__" and __package__ is None:
    __package__ == "guiguts"


from guiguts.file import File, NUM_RECENT_FILES
from guiguts.mainwindow import (
    root,
    MainWindow,
    Menu,
    maintext,
    menubar,
    StatusBar,
    statusbar,
)
from guiguts.preferences import preferences
from guiguts.preferences_dialog import PreferencesDialog
from guiguts.utilities import is_mac


class Guiguts:
    """Top level Guiguts application."""

    def __init__(self) -> None:
        """Initialize Guiguts class.

        Creates windows and sets default preferences."""

        self.parse_args()

        self.set_preferences_defaults()

        self.file = File(self.filename_changed)

        self.mainwindow = MainWindow()
        self.update_title()

        self.init_menus()

        self.init_statusbar(statusbar())

        maintext().focus_set()
        maintext().add_modified_callback(self.update_title)

        # Known tkinter issue - must call this before any dialogs can get created,
        # or focus will not return to maintext on Windows
        root().update_idletasks()

        preferences.run_callbacks()

        self.load_file_if_given()

        def check_save_and_destroy() -> None:
            if self.file.check_save():
                root().destroy()

        root().protocol("WM_DELETE_WINDOW", check_save_and_destroy)

    def parse_args(self) -> None:
        """Parse command line args"""
        parser = argparse.ArgumentParser(
            prog="guiguts", description="Guiguts is an ebook creation tool"
        )
        parser.add_argument(
            "filename", nargs="?", help="Optional name of file to be loaded"
        )
        parser.add_argument(
            "-r",
            "--recent",
            type=int,
            choices=range(1, NUM_RECENT_FILES + 1),
            help="Number of 'Recent File' to be loaded: 1 is most recent",
        )
        self.args = parser.parse_args()

    def load_file_if_given(self) -> None:
        """If filename, or recent number, given on command line
        load the relevant file."""

        if self.args.filename:
            self.file.load_file(self.args.filename)
        elif self.args.recent:
            index = self.args.recent - 1
            self.file.load_file(preferences["RecentFiles"][index])

    @property
    def auto_image(self) -> bool:
        """Auto image flag: setting causes side effects in UI
        & starts repeating check."""
        return preferences["AutoImage"]

    @auto_image.setter
    def auto_image(self, value: bool) -> None:
        preferences["AutoImage"] = value
        statusbar().set("see img", "Auto Img" if value else "See Img")
        if value:
            self.image_dir_check()
            self.auto_image_check()

    def auto_image_check(self) -> None:
        """Function called repeatedly to check whether an image needs loading."""
        if self.auto_image:
            self.mainwindow.load_image(self.file.get_current_image_path())
            root().after(200, self.auto_image_check)

    def toggle_auto_image(self) -> None:
        """Toggle the auto image flag."""
        self.auto_image = not self.auto_image

    def see_image(self) -> None:
        """Show the image corresponding to current location."""
        self.image_dir_check()
        self.mainwindow.load_image(self.file.get_current_image_path())

    def image_dir_check(self) -> None:
        """Check if image dir is set up correctly."""
        if self.file.filename and not (
            self.file.image_dir and os.path.exists(self.file.image_dir)
        ):
            self.file.choose_image_dir()

    def run(self) -> None:
        """Run the app."""
        root().mainloop()

    def filename_changed(self) -> None:
        """Handle side effects needed when filename changes."""
        self.init_file_menu()  # Recreate file menu to reflect recent files
        self.update_title()
        if self.auto_image:
            self.image_dir_check()
        maintext().after_idle(maintext().focus_set)

    def update_title(self) -> None:
        """Update the window title to reflect current status."""
        modtitle = " - edited" if maintext().is_modified() else ""
        filetitle = " - " + self.file.filename if self.file.filename else ""
        root().title("Guiguts 2.0" + modtitle + filetitle)

    def quit_program(self, *args: Any) -> None:
        """Exit the program."""
        if self.file.check_save():
            root().quit()

    def help_about(self, *args: Any) -> None:
        """Display a 'Help About' dialog."""
        help = """Guiguts - an application to support creation of ebooks for PG

Copyright Contributors to the Guiguts-py project.

This program is free software; you can redistribute it
and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even
the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public
License along with this program; if not, write to the
Free Software Foundation, Inc., 51 Franklin Street,
Fifth Floor, Boston, MA 02110-1301 USA."""

        messagebox.showinfo(title="About Guiguts", message=help)

    def show_preferences_dialog(self, *args: Any) -> None:
        """Show the preferences display/edit dialog."""
        PreferencesDialog(root())

    def open_document(self, args: list[str]) -> None:
        """Handle drag/drop on Macs.

        Accepts a list of filenames, but only loads the first.
        """
        self.file.load_file(args[0])

    def open_file(self, filename: str = "") -> None:
        """Open new file, close old image if open.

        Args:
            filename: Optional filename - prompt user if none given.
        """
        if self.file.open_file(filename):
            self.mainwindow.clear_image()

    def close_file(self) -> None:
        """Close currently loaded file and associated image."""
        self.file.close_file()
        self.mainwindow.clear_image()

    def load_current_image(self) -> None:
        """Load image corresponding to current cursor position"""
        self.mainwindow.load_image(self.file.get_current_image_path())

    def show_help_manual(self, *args: Any) -> None:
        """Display the manual."""
        webbrowser.open("https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_Manual")

    def spawn_process(self, *args: Any) -> None:
        """Spawn a subprocess.

        Executes a command, sends input to the process and captures
        stdout and stderr from the process.
        """
        try:
            result = subprocess.run(
                ["python", "child.py"],
                input="Convert me to uppercase",
                text=True,
                capture_output=True,
            )
        except FileNotFoundError:
            result = subprocess.run(
                ["python3", "child.py"],
                input="Convert me to uppercase",
                text=True,
                capture_output=True,
            )
        messagebox.showinfo(title="Spawn stdout", message=result.stdout)
        messagebox.showinfo(title="Spawn stderr", message=result.stderr)

    def set_preferences_defaults(self) -> None:
        """Set default preferences - will be overridden by any values set
        in the Preferences file.
        """

        def set_auto_image(value: bool) -> None:
            self.auto_image = value

        preferences.set_default("AutoImage", False)
        preferences.set_callback("AutoImage", set_auto_image)
        preferences.set_default("Bell", "VisibleAudible")
        preferences.set_default("ImageWindow", "Docked")
        preferences.set_default("RecentFiles", [])

    # Lay out menus
    def init_menus(self) -> None:
        """Create all the menus."""
        self.init_file_menu()
        self.init_edit_menu()
        self.init_view_menu()
        self.init_help_menu()
        self.init_os_menu()

        if is_mac():
            root().createcommand(
                "tk::mac::ShowPreferences", self.show_preferences_dialog
            )
            root().createcommand("tk::mac::OpenDocument", self.open_document)
            root().createcommand("tk::mac::Quit", self.quit_program)

    def init_file_menu(self) -> None:
        """(Re-)create the File menu."""
        try:
            self.menu_file.delete(0, "end")  # type:ignore[has-type]
        except AttributeError:
            self.menu_file = Menu(menubar(), "~File")
        self.menu_file.add_button(
            "~Open...", lambda *args: self.open_file(), "Cmd/Ctrl+O"
        )
        self.init_file_recent_menu(self.menu_file)
        self.menu_file.add_button("~Save", self.file.save_file, "Cmd/Ctrl+S")
        self.menu_file.add_button(
            "Save ~As...", self.file.save_as_file, "Cmd/Ctrl+Shift+S"
        )
        self.menu_file.add_button(
            "~Close", self.close_file, "Cmd+W" if is_mac() else ""
        )
        self.menu_file.add_separator()
        self.menu_file.add_button("Spawn ~Process", self.spawn_process)
        if not is_mac():
            self.menu_file.add_separator()
            self.menu_file.add_button("E~xit", self.quit_program, "")

    def init_file_recent_menu(self, parent: Menu) -> None:
        """Create the Recent Documents menu."""
        recent_menu = Menu(parent, "Recent Doc~uments")
        for count, file in enumerate(preferences["RecentFiles"], start=1):
            recent_menu.add_button(
                f"~{count}: {file}", lambda fn=file: self.open_file(fn)
            )

    def init_edit_menu(self) -> None:
        """Create the Edit menu."""
        menu_edit = Menu(menubar(), "~Edit")
        menu_edit.add_button("~Undo", "<<Undo>>", "Cmd/Ctrl+Z")
        menu_edit.add_button(
            "~Redo", "<<Redo>>", "Cmd+Shift+Z" if is_mac() else "Ctrl+Y"
        )
        menu_edit.add_separator()
        menu_edit.add_cut_copy_paste()
        menu_edit.add_separator()
        menu_edit.add_button("Pre~ferences...", lambda: PreferencesDialog(root()))

    def init_view_menu(self) -> None:
        """Create the View menu."""
        menu_view = Menu(menubar(), "~View")
        menu_view.add_button("~Dock", self.mainwindow.dock_image)
        menu_view.add_button("~Float", self.mainwindow.float_image)
        menu_view.add_button("~See Image", self.see_image)

    def init_help_menu(self) -> None:
        """Create the Help menu."""
        menu_help = Menu(menubar(), "~Help")
        menu_help.add_button("Guiguts ~Manual", self.show_help_manual)
        menu_help.add_button("About ~Guiguts", self.help_about)

    def init_os_menu(self) -> None:
        """Create the OS-specific menu.

        Currently only does anything on Macs
        """
        if is_mac():
            # Apple menu
            menu_app = Menu(menubar(), "", name="apple")
            menu_app.add_button("About ~Guiguts", self.help_about)
            menu_app.add_separator()
            # Window menu
            Menu(menubar(), "Window", name="window")
        else:
            menu_app = None

    # Lay out statusbar
    def init_statusbar(self, statusbar: StatusBar) -> None:
        """Add labels to initialize the statusbar"""

        index_pattern = re.compile(r"(\d+)\.(\d+)")
        statusbar.add(
            "rowcol",
            update=lambda: index_pattern.sub(
                r"L:\1 C:\2", maintext().get_insert_index()
            ),
        )
        statusbar.add_binding("rowcol", "<ButtonRelease-1>", self.file.goto_line)

        statusbar.add(
            "img",
            update=lambda: "Img: " + self.file.get_current_image_name(),
        )
        statusbar.add_binding("img", "<ButtonRelease-1>", self.file.goto_page)

        statusbar.add("prev img", text="<", width=1)
        statusbar.add_binding("prev img", "<ButtonRelease-1>", self.file.prev_page)

        statusbar.add("see img", text="See Img", width=9)
        statusbar.add_binding(
            "see img",
            "<ButtonRelease-1>",
            self.see_image,
        )
        statusbar.add_binding(
            "see img", "<ButtonRelease-3>", self.file.choose_image_dir
        )
        statusbar.add_binding("see img", "<Double-Button-1>", self.toggle_auto_image)

        statusbar.add("next img", text=">", width=1)
        statusbar.add_binding("next img", "<ButtonRelease-1>", self.file.next_page)


def main() -> None:
    """Main application function."""
    Guiguts().run()


if __name__ == "__main__":
    main()
