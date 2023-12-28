"""Handle file operations"""

import json
import os.path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from guiguts.mainwindow import maintext, sound_bell
from guiguts.preferences import preferences
from guiguts.utilities import is_windows

FOLDER_DIR = "folder" if is_windows() else "directory"
NUM_RECENT_FILES = 9
PAGEMARK_PREFIX = "Pg"
BINFILE_SUFFIX = ".json"
BINFILE_KEY_PAGEMARKS = "pagemarks"
BINFILE_KEY_INSERTPOS = "insertpos"
BINFILE_KEY_IMAGEDIR = "imagedir"


class File:
    """Handle data and actions relating to the main text file.

    Attributes:
        _filename: Current filename.
        _filename_callback: Function to be called whenever filename is set.
        _image_dir: Directory containing scan images.
    """

    def __init__(self, filename_callback):
        """
        Args:
            filename_callback: Function to be called whenever filename is set.
        """
        self._filename = ""
        self._filename_callback = filename_callback
        self._image_dir = ""

    @property
    def filename(self):
        """Name of currently loaded file.

        When assigned to, executes callback function to update interface"""
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value
        self._filename_callback()

    @property
    def image_dir(self):
        """Directory containing scan images.

        If unset, defaults to pngs subdir of project dir"""
        if (not self._image_dir) and self.filename:
            self._image_dir = os.path.join(os.path.dirname(self.filename), "pngs")
        return self._image_dir

    @image_dir.setter
    def image_dir(self, value):
        self._image_dir = value

    def reset(self):
        """Reset file internals to defaults, e.g. filename, page markers, etc"""
        self.filename = ""
        self.image_dir = ""
        self.remove_page_marks()

    def open_file(self, *args):
        """Open and load a text file.

        Returns:
            Name of file opened - empty string if cancelled.
        """
        fn = ""
        if self.check_save():
            if fn := filedialog.askopenfilename(
                filetypes=(("Text files", "*.txt *.html *.htm"), ("All files", "*.*"))
            ):
                self.load_file(fn)
        return fn

    def close_file(self):
        """Close current file, leaving an empty file."""
        if self.check_save():
            self.reset()
            maintext().do_close()

    def load_file(self, filename):
        """Load file & bin file.

        Args:
            filename: Name of file to be loaded. Bin filename has ".bin" appended.
        """
        self.reset()
        maintext().do_open(filename)
        maintext().set_insert_index(1.0, see=True)
        self.load_bin(filename)
        if not self.contains_page_marks():
            self.mark_page_boundaries()
        self.store_recent_files(filename)
        # Load complete, so set filename (including side effects)
        self.filename = filename

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
        self.image_dir = bin_dict.get(BINFILE_KEY_IMAGEDIR)

    def create_bin(self):
        """From relevant variables, etc., create dictionary suitable for saving
        to bin file.

        Returns:
            Dictionary of settings to be saved in bin file
        """
        bin_dict = {}
        bin_dict[BINFILE_KEY_INSERTPOS] = maintext().get_insert_index()
        bin_dict[BINFILE_KEY_PAGEMARKS] = self.dict_from_page_marks()
        bin_dict[BINFILE_KEY_IMAGEDIR] = self.image_dir
        return bin_dict

    def store_recent_files(self, filename):
        """Store given filename in list of recent files.

        Args:
            filename: Name of new file to add to list.
        """
        recent_files = preferences["RecentFiles"]
        if filename in recent_files:
            recent_files.remove(filename)
        recent_files.append(filename)
        del recent_files[0:-NUM_RECENT_FILES]
        preferences["RecentFiles"] = recent_files

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
        """Set initial cursor position after file is loaded.

        Args:
            index: Location for insert cursor. If none, go to start.
        """
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
        """Find basename of the image file corresponding to where the
        insert cursor is.

        Returns:
            Basename of image file. Empty string if none found.
        """
        insert = maintext().get_insert_index()
        mark = insert
        good_mark = ""
        # First check for page marks at the current cursor position & return last one
        while (mark := maintext().mark_next(mark)) and maintext().compare(
            mark, "==", insert
        ):
            if is_page_mark(mark):
                good_mark = mark
        # If not, then find page mark before current position
        if not good_mark:
            mark = insert
            while mark := maintext().mark_previous(mark):
                if is_page_mark(mark):
                    good_mark = mark
                    break
        # If not, then maybe we're before the first page mark, so search forward
        if not good_mark:
            mark = insert
            while mark := maintext().mark_next(mark):
                if is_page_mark(mark):
                    good_mark = mark
                    break

        return img_from_page_mark(good_mark)

    def get_current_image_path(self):
        """Return the path of the image file for the page where the insert
        cursor is located.

        Returns:
            Name of the image file for the current page, or the empty string
            if unable to get image file name.
        """
        basename = self.get_current_image_name()
        if self.image_dir and basename:
            basename += ".png"
            path = os.path.join(self.image_dir, basename)
            if os.path.exists(path):
                return path
        return ""

    def choose_image_dir(self):
        """Allow user to select directory containing png image files"""
        self.image_dir = filedialog.askdirectory(
            mustexist=True, title="Select " + FOLDER_DIR + " containing scans"
        )

    def goto_line(self):
        """Go to the line number the user enters"""
        line_num = simpledialog.askinteger(
            "Go To Line", "Line number", parent=maintext()
        )
        if line_num is not None:
            maintext().set_insert_index(f"{line_num}.0", see=True)

    def goto_page(self):
        """Go to the page the user enters"""
        page_num = simpledialog.askstring(
            "Go To Page", "Image number", parent=maintext()
        )
        if page_num is not None:
            try:
                index = maintext().index(PAGEMARK_PREFIX + page_num)
            except tk._tkinter.TclError:
                # Bad page number
                return
            maintext().set_insert_index(index, see=True)

    def prev_page(self):
        """Go to the start of the previous page"""
        self._next_prev_page(-1)

    def next_page(self):
        """Go to the start of the next page"""
        self._next_prev_page(1)

    def _next_prev_page(self, direction):
        """Go to the page before/after the current one

        Always moves backward/forward in file, even if cursor and page mark(s)
        are coincident or multiple coincident page marks. Will not remain in
        the same location unless no further page marks are found.

        Args:
            direction: Positive to go to next page; negative for previous page
        """
        if direction < 0:
            mark_next_previous = maintext().mark_previous
        else:
            mark_next_previous = maintext().mark_next

        insert = maintext().get_insert_index()
        cur_page = self.get_current_image_name()
        mark = PAGEMARK_PREFIX + cur_page if cur_page else insert
        while mark := mark_next_previous(mark):
            if is_page_mark(mark) and maintext().compare(mark, "!=", insert):
                maintext().set_insert_index(mark, see=True)
                return
        sound_bell()


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
          Does not check if mark is a page mark. If it is not, the
          full string is returned.

    Returns:
        Image name.
    """
    return mark.removeprefix(PAGEMARK_PREFIX)


def bin_name(basename):
    """Get the name of the bin file associated with a text file.

    Args:
        basename: Name of text file.

    Returns:
        Name of associated bin file.
    """
    return basename + BINFILE_SUFFIX
