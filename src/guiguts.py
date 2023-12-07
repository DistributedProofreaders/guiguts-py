"""Guiguts - application to support creation of books for PG"""


import re
import subprocess
from tkinter import messagebox
import webbrowser

import file
from file import File
from mainwindow import (
    root,
    MainWindow,
    Menu,
    mainimage,
    maintext,
    menubar,
    statusbar,
)
from preferences import preferences
from preferences_dialog import PreferencesDialog
from utilities import is_mac


class Guiguts:
    """Top level Guiguts application."""

    def __init__(self):
        """Initialize Guiguts class.

        Creates windows and sets default preferences."""

        self.set_preferences_defaults()

        self.file = File(self.update_title)

        MainWindow()
        self.update_title()

        self.init_menus(menubar())

        self.init_statusbar(statusbar())

        maintext().focus_set()
        maintext().add_modified_callback(self.update_title)

    def run(self):
        """Run the app."""
        root().mainloop()

    def update_title(self):
        """Update the window title to reflect current status."""
        modtitle = " - edited" if maintext().is_modified() else ""
        filetitle = " - " + self.file.filename if self.file.filename else ""
        root().title("Guiguts 2.0" + modtitle + filetitle)

    def quit_program(self, *args):
        """Exit the program."""
        if self.file.check_save():
            root().quit()

    def help_about(self, *args):
        """Display a 'Help About' dialog."""
        messagebox.showinfo(
            title="About Guiguts", message="Here's some information about Guiguts"
        )

    def show_preferences_dialog(self, *args):
        """Show the preferences display/edit dialog."""
        PreferencesDialog(root())

    def open_document(self, args):
        """Handle drag/drop on Macs.

        Accepts a list of filenames, but only loads the first.
        """
        file.load_file(args[0])

    def show_help_manual(self, *args):
        """Display the manual."""
        webbrowser.open("https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_Manual")

    def load_image(self, *args):
        """Load the image for the current page."""
        filename = maintext().get_image_filename()
        mainimage().load_image(filename)
        if preferences.get("ImageWindow") == "Docked":
            mainimage().dock_image()
        else:
            mainimage().float_image()

    def spawn_process(self, *args):
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

    def set_preferences_defaults(self):
        """Set default preferences - will be overridden by any values set
        in the Preferences file.
        """
        preferences.set_default("ImageWindow", "Docked")

    # Lay out menus
    def init_menus(self, menubar):
        """Create all the menus."""
        self.init_file_menu(menubar)
        self.init_edit_menu(menubar)
        self.init_view_menu(menubar)
        self.init_help_menu(menubar)
        self.init_os_menu(menubar)

        if is_mac():
            root().createcommand(
                "tk::mac::ShowPreferences", self.show_preferences_dialog
            )
            root().createcommand("tk::mac::OpenDocument", self.open_document)
            root().createcommand("tk::mac::Quit", self.quit_program)

    def init_file_menu(self, parent):
        """Create the File menu."""
        menu_file = Menu(parent, "~File")
        menu_file.add_button("~Open...", self.file.open_file, "Cmd/Ctrl+O")
        menu_file.add_button("~Save", self.file.save_file, "Cmd/Ctrl+S")
        menu_file.add_button("Save ~As...", self.file.save_as_file, "Cmd/Ctrl+Shift+S")
        menu_file.add_separator()
        menu_file.add_button("Spawn ~Process", self.spawn_process)
        menu_file.add_separator()
        menu_file.add_button("~Quit", self.quit_program, "Cmd+Q" if is_mac() else "")

    def init_edit_menu(self, parent):
        """Create the Edit menu."""
        menu_edit = Menu(parent, "~Edit")
        menu_edit.add_button("~Undo", "<<Undo>>", "Cmd/Ctrl+Z")
        menu_edit.add_button(
            "~Redo", "<<Redo>>", "Cmd+Shift+Z" if is_mac() else "Ctrl+Y"
        )
        menu_edit.add_separator()
        menu_edit.add_cut_copy_paste()
        menu_edit.add_separator()
        menu_edit.add_button("Select ~All", "<<SelectAll>>", "Cmd/Ctrl+A")
        menu_edit.add_separator()
        menu_edit.add_button("Pre~ferences...", lambda: PreferencesDialog(root()))

    def init_view_menu(self, parent):
        """Create the View menu."""
        menu_view = Menu(parent, "~View")
        menu_view.add_button("~Dock", mainimage().dock_image, "Cmd/Ctrl+D")
        menu_view.add_button("~Float", mainimage().float_image, "Cmd/Ctrl+F")
        menu_view.add_button("~Load Image", self.load_image, "Cmd/Ctrl+L")

    def init_help_menu(self, parent):
        """Create the Help menu."""
        menu_help = Menu(parent, "~Help")
        menu_help.add_button("Guiguts ~Manual", self.show_help_manual)
        menu_help.add_button("About ~Guiguts", self.help_about)

    def init_os_menu(self, parent):
        """Create the OS-specific menu.

        Currently only does anything on Macs
        """
        if is_mac():
            # Apple menu
            menu_app = Menu(parent, "", name="apple")
            menu_app.add_button("About ~Guiguts", self.help_about)
            menu_app.add_separator()
            # Window menu
            Menu(parent, "Window", name="window")
        else:
            menu_app = None

    # Lay out statusbar
    def init_statusbar(self, statusbar):
        """Add labels to initialize the statusbar"""
        pattern = re.compile(r"(\d+)\.(\d+)")
        statusbar.add(
            "rowcol",
            lambda: pattern.sub(r"L:\1 C:\2", maintext().get_insert_index()),
            width=10,
        )
        statusbar.add(
            "img",
            lambda: "Img: " + self.file.get_current_image_name(),
            # width=10,
        )


if __name__ == "__main__":
    Guiguts().run()
