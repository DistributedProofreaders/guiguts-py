"""Handle file operations"""

import json
import os.path
import re
import tkinter as tk
from tkinter import filedialog, messagebox

from mainwindow import maintext

PAGEMARK_PREFIX = "Pg"
BINFILE_SUFFIX = ".bin"
BINFILE_KEY_PAGEMARKS = "pagemarks"
BINFILE_KEY_INSERTPOS = "insertpos"


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
            if fn := filedialog.askopenfilename(
                filetypes=(("Text files", "*.txt *.html *.htm"), ("All files", "*.*"))
            ):
                self.load_file(fn)

    def load_file(self, filename):
        """Load file & bin file.

        Args:
            filename: Name of file to be loaded. Bin filename has ".bin" appended.
        """
        self.filename = filename
        maintext().do_open(filename)
        self.load_bin(filename)
        if not self.contains_page_marks():
            self.mark_page_boundaries()

    def save_file(self, *args):
        """Save the current file.

        Returns:
            Current filename or None if save is cancelled
        """
        if self.filename:
            maintext().do_save(self.filename)
            self.save_bin(self.filename)
            return self.filename
        else:
            return self.save_as_file()

    def save_as_file(self, *args):
        """Save current text as new file.

        Returns:
            Chosen filename or None if save is cancelled
        """
        if fn := filedialog.asksaveasfilename(
            initialfile=os.path.basename(self.filename),
            initialdir=os.path.dirname(self.filename),
            filetypes=[("All files", "*")],
        ):
            self.filename = fn
            maintext().do_save(fn)
            self.save_bin(fn)
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

    def load_bin(self, basename):
        """Load bin file associated with current file.

        If bin file not found, returns silently.

        Args:
            basename - name of current text file - bin file has ".bin" appended.
        """
        binfile_name = bin_name(basename)
        if not os.path.isfile(binfile_name):
            return
        with open(binfile_name, "r") as fp:
            bin_dict = json.load(fp)
        self.interpret_bin(bin_dict)

    def save_bin(self, basename):
        """Save bin file associated with current file.

        Args:
            basename: name of current text file - bin file has ".bin" appended.
        """
        binfile_name = bin_name(basename)
        bin_dict = self.create_bin()
        with open(binfile_name, "w") as fp:
            json.dump(bin_dict, fp, indent=2)

    def interpret_bin(self, bin_dict):
        """Interpret bin file dictionary and set necessary variables, etc.

        Args:
            bin_dict: Dictionary loaded from bin file
        """
        self.set_initial_position(bin_dict.get(BINFILE_KEY_INSERTPOS))
        self.dict_to_page_marks(bin_dict.get(BINFILE_KEY_PAGEMARKS))

    def create_bin(self):
        """From relevant variables, etc., create dictionary suitable for saving
        to bin file.

        Returns:
            Dictionary of settings to be saved in bin file
        """
        bin_dict = {}
        bin_dict[BINFILE_KEY_INSERTPOS] = maintext().get_insert_index()
        bin_dict[BINFILE_KEY_PAGEMARKS] = self.dict_from_page_marks()
        return bin_dict

    def dict_to_page_marks(self, page_marks_dict):
        """Set page marks from keys/values in dictionary.

        Args:
            page_marks_dict: Dictionary of page mark indexes
        """
        self.remove_page_marks()
        if page_marks_dict:
            for mark, index in page_marks_dict.items():
                maintext().mark_set(mark, index)
                maintext().mark_gravity(mark, tk.LEFT)

    def set_initial_position(self, index):
        if not index:
            index = "1.0"
        maintext().set_insert_index(index, see=True)

    def dict_from_page_marks(self):
        """Create dictionary of page mark locations.

        Returns:
            Dictionary with marks as keys and indexes as values
        """
        page_marks_dict = {}
        mark = "1.0"
        while mark := maintext().mark_next(mark):
            if is_page_mark(mark):
                page_marks_dict[mark] = maintext().index(mark)
        return page_marks_dict

    def mark_page_boundaries(self):
        """Loop through whole file, ensuring all page separator lines
        are in standard format, and setting page marks at the
        start of each page separator line.
        """

        page_separator_regex = r"File:.+?([^/\\ ]+)\.(png|jpg)"
        pattern = re.compile(page_separator_regex)
        search_start = "1.0"
        while page_index := maintext().search(
            page_separator_regex, search_start, regexp=True, stopindex="end"
        ):
            line_start = page_index + " linestart"
            line_end = page_index + " lineend"
            line = maintext().get(line_start, line_end)
            if match := pattern.search(
                line
            ):  # Always matches since same regex as earlier search
                (page, ext) = match.group(1, 2)
                standard_line = f"-----File: {page}.{ext}"
                standard_line += "-" * (75 - len(standard_line))
                if line != standard_line:
                    maintext().delete(line_start, line_end)
                    maintext().insert(line_start, standard_line)
                page_mark = PAGEMARK_PREFIX + page
                maintext().mark_set(page_mark, line_start)
                maintext().mark_gravity(page_mark, tk.LEFT)

            search_start = line_end

    def remove_page_marks(self):
        """Remove any existing page marks."""
        marklist = []
        mark = "1.0"
        while mark := maintext().mark_next(mark):
            if is_page_mark(mark):
                marklist.append(mark)
        for mark in marklist:
            maintext().mark_unset(mark)

    def contains_page_marks(self):
        """Check whether file contains page marks.

        Returns:
            True if file contains page marks.
        """
        mark = "1.0"
        while mark := maintext().mark_next(mark):
            if is_page_mark(mark):
                return True
        return False

    def get_current_image_name(self):
        """Find name of the image file corresponding to where the
        insert cursor is.

        Returns:
            Basename of image file (= name of preceding page mark).
            Empty string if no page mark before insert cursor.
        """
        mark = maintext().get_insert_index()
        while mark := maintext().mark_previous(mark):
            if is_page_mark(mark):
                return img_from_page_mark(mark)
        return ""


def is_page_mark(mark):
    """Check whether mark is a page mark, e.g. "Pg027".

    Args:
        mark: String containing name of mark to be checked.

    Returns:
        True if string matches the format of page mark names.
    """
    return mark.startswith(PAGEMARK_PREFIX)


def img_from_page_mark(mark):
    """Get base image name from page mark, e.g. "Pg027" gives "027".

    Args:
        mark: String containing name of mark whose image is needed.
          Does not check if mark is a page mark

    Returns:
        True if string matches the format of page mark names.
    """
    return mark[len(PAGEMARK_PREFIX) :]


def bin_name(basename):
    """Get the name of the bin file associated with a text file.

    Args:
        basename: Name of text file.

    Returns:
        Name of associated bin file.
    """
    return basename + BINFILE_SUFFIX
