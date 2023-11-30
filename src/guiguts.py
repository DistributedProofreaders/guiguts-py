"""Guiguts - application to support creation of books for PG"""


import datetime
import os.path
import re
import subprocess
from tkinter import filedialog, messagebox
import webbrowser

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
    """Top level Guiguts application.

    Attributes:
        filename: name of the loaded file.
    """

    def __init__(self):
        """Initialize Guiguts class.

        Creates windows and sets default preferences."""

        self.set_preferences_defaults()

        MainWindow()

        self.init_menus(menubar())

        self.init_statusbar(statusbar())

        self.filename = ""
        self.update_filename_labels()

        maintext().focus_set()
        maintext().add_modified_callback(self.update_title)

    def run(self):
        """Run the app."""
        root().mainloop()

    def update_title(self):
        """Update the window title to reflect current status."""
        modtitle = " - edited" if maintext().is_modified() else ""
        filetitle = " - " + self.filename if self.filename else ""
        root().title("Guiguts 2.0" + modtitle + filetitle)

    def open_file(self, *args):
        """Open and load a text file."""
        fn = filedialog.askopenfilename(
            filetypes=(("Text files", "*.txt *.html *.htm"), ("All files", "*.*"))
        )
        if fn:
            self.filename = fn
            maintext().do_open(self.filename)
            self.update_filename_labels()

    def save_file(self, *args):
        """Save the current file."""
        if self.filename:
            maintext().do_save(self.filename)
        else:
            self.save_as_file()

    def save_as_file(self, *args):
        """Save current text as new file."""
        fn = filedialog.asksaveasfilename(
            initialfile=os.path.basename(self.filename),
            initialdir=os.path.dirname(self.filename),
            filetypes=[("All files", "*")],
        )
        if fn:
            self.filename = fn
            maintext().do_save(self.filename)
            self.update_filename_labels()

    def quit_program(self, *args):
        """Exit the program."""
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
        filename = args[0]
        maintext().do_open(filename)
        self.update_filename_labels()

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

    def update_filename_labels(self):
        """Update places where the filename is displayed."""
        self.update_title()
        statusbar().set("filename", os.path.basename(self.filename))

    def set_preferences_defaults(self):
        """Set default preferences - will be overridden by any values set
        in the Preferences file.
        """
        preferences.set_default("ImageWindow", "Docked")

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
        menu_file.add_button("~Open...", self.open_file, "Cmd/Ctrl+O")
        menu_file.add_button("~Save", self.save_file, "Cmd/Ctrl+S")
        menu_file.add_button("Save ~As...", self.save_as_file, "Cmd/Ctrl+Shift+S")
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
        menu_edit.add_button("Pre~ferences...", self.show_preferences_dialog)

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

    def init_statusbar(self, statusbar):
        """Add labels to initialie the statusbar"""
        statusbar.add(
            "rowcol",
            lambda: re.sub(r"(\d)\.(\d)", r"L:\1 C:\2", maintext().get_insert_index()),
            width=10,
        )
        statusbar.add("filename", width=12)
        statusbar.add(
            "time", lambda: datetime.datetime.now().strftime("%H:%M:%S"), width=8
        )


if __name__ == "__main__":
    Guiguts().run()
