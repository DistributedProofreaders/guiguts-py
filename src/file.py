"""Handle file operations"""

import os.path
from tkinter import filedialog, messagebox

from mainwindow import maintext


class File:
    """Handle data and actions relating to the main text file"""

    def __init__(self, filename_callback):
        """
        Args:
            filename_callback: function to be called whenever filename is set.
        """
        self._filename = ""
        self._filename_callback = filename_callback

    @property
    def filename(self):
        """Name of currently loaded file

        When assigned to, executes callback function to update interface"""
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value
        self._filename_callback()

    def open_file(self, *args):
        """Open and load a text file."""
        if self.check_save():
            fn = filedialog.askopenfilename(
                filetypes=(("Text files", "*.txt *.html *.htm"), ("All files", "*.*"))
            )
            if fn:
                self.filename = fn
                maintext().do_open(self.filename)

    def save_file(self, *args):
        """Save the current file.

        Returns:
            Current filename or None if save is cancelled
        """
        if self.filename:
            maintext().do_save(self.filename)
            return self.filename
        else:
            return self.save_as_file()

    def save_as_file(self, *args):
        """Save current text as new file.

        Returns:
            Chosen filename or None if save is cancelled
        """
        fn = filedialog.asksaveasfilename(
            initialfile=os.path.basename(self.filename),
            initialdir=os.path.dirname(self.filename),
            filetypes=[("All files", "*")],
        )
        if fn:
            self.filename = fn
            maintext().do_save(self.filename)
        return fn

    def check_save(self):
        """If file has been edited, check if user wants to save,
        or discard, or cancel the intended operation.

        Returns:
            True if OK to continue with intended operation.
        """
        if not maintext().is_modified():
            return True

        save = messagebox.askyesnocancel(
            title="Save document?",
            message="Save changes to document first?",
            detail="Your changes will be lost if you don't save them.",
            icon=messagebox.WARNING,
        )
        # Trap Cancel from messagebox
        if save is None:
            return False
        # Trap Cancel from save-as dialog
        if save and not self.save_file():
            return False
        return True
