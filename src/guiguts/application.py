#!/usr/bin/env python
"""Guiguts - an application to support creation of ebooks for PG"""


import argparse
import logging
import importlib.resources
from importlib.metadata import version
from typing import Optional
import unicodedata
import webbrowser
import darkdetect  # type: ignore[import-untyped]

from guiguts.ascii_tables import JustifyStyle
from guiguts.data import themes
from guiguts.file import File, the_file, NUM_RECENT_FILES
from guiguts.footnotes import footnote_check, FootnoteIndexStyle
from guiguts.html_convert import HTMLGeneratorDialog, HTMLMarkupTypes
from guiguts.html_tools import (
    HTMLImageDialog,
    HTMLValidator,
    HTMLLinkChecker,
    CSSValidator,
    EbookmakerChecker,
)
from guiguts.illo_sn_fixup import illosn_check

from guiguts.ascii_tables import ASCIITableDialog
from guiguts.maintext import maintext
from guiguts.mainwindow import (
    MainWindow,
    Menu,
    menubar,
    StatusBar,
    statusbar,
    ErrorHandler,
    process_accel,
    mainimage,
    AutoImageState,
    image_autofit_width_callback,
    image_autofit_height_callback,
    CustomMenuDialog,
)
from guiguts.misc_dialogs import (
    PreferencesDialog,
    ComposeSequenceDialog,
    ComposeHelpDialog,
    UnicodeBlockDialog,
    UnicodeSearchDialog,
    HelpAboutDialog,
    CommandPaletteDialog,
)
from guiguts.misc_tools import (
    basic_fixup_check,
    page_separator_fixup,
    PageSepAutoType,
    unmatched_dp_markup,
    unmatched_html_markup,
    unmatched_brackets,
    unmatched_curly_quotes,
    unmatched_block_markup,
    FractionConvertType,
    fraction_convert,
    unicode_normalize,
    proofer_comment_check,
    asterisk_check,
    TextMarkupConvertorDialog,
    stealth_scannos,
    DEFAULT_SCANNOS_DIR,
    DEFAULT_REGEX_SCANNOS,
    DEFAULT_STEALTH_SCANNOS,
    DEFAULT_MISSPELLED_SCANNOS,
    convert_to_curly_quotes,
    check_curly_quotes,
)
from guiguts.page_details import PageDetailsDialog
from guiguts.preferences import preferences, PrefKey, PersistentBoolean
from guiguts.root import root
from guiguts.search import show_search_dialog, find_next
from guiguts.spell import spell_check
from guiguts.tools.bookloupe import bookloupe_check
from guiguts.tools.jeebies import jeebies_check, JeebiesParanoiaLevel
from guiguts.tools.levenshtein import levenshtein_check, LevenshteinEditDistance
from guiguts.tools.pptxt import pptxt
from guiguts.tools.pphtml import PPhtmlChecker
from guiguts.utilities import is_mac, is_windows, is_x11, folder_dir_str
from guiguts.widgets import (
    themed_style,
    theme_name_internal_from_user,
    menubar_metadata,
)
from guiguts.word_frequency import word_frequency, WFDisplayType, WFSortType

logger = logging.getLogger(__package__)

MESSAGE_FORMAT = "%(asctime)s: %(levelname)s - %(message)s"
DEBUG_FORMAT = "%(asctime)s: %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
THEMES_DIR = importlib.resources.files(themes)


class Guiguts:
    """Top level Guiguts application."""

    def __init__(self) -> None:
        """Initialize Guiguts class.

        Creates windows and sets default preferences."""

        self.parse_args()

        self.logging_init()
        logger.info("Guiguts started")

        self.initialize_preferences()

        self.file = File(self.filename_changed, self.languages_changed)
        the_file(self.file)

        self.mainwindow = MainWindow()
        self.file.mainwindow = self.mainwindow
        self.update_title()

        theme_path = THEMES_DIR.joinpath("awthemes-10.4.0")
        root().tk.call("lappend", "auto_path", theme_path)
        root().tk.call("package", "require", "awdark")
        root().tk.call("package", "require", "awlight")

        # Recent menu is saved to allow deletion & re-creation when files loaded/saved
        self.recent_menu: Optional[Menu] = None
        # Similarly for custom menu when it is customized
        self.custom_menu: Optional[Menu] = None
        self.init_menus()

        self.init_statusbar(statusbar())

        self.file.languages = preferences.get(PrefKey.DEFAULT_LANGUAGES)

        maintext().focus_set()
        maintext().add_modified_callback(self.update_title)
        maintext().add_config_callback(self.update_title)

        # Known tkinter issue - must call this before any dialogs can get created,
        # or focus will not return to maintext on Windows
        root().update_idletasks()

        # After menus, etc., have been created, set the zoomed/fullscreen state
        root().set_zoom_fullscreen()

        self.logging_add_gui()
        logger.info("GUI initialized")

        preferences.run_callbacks()

        self.load_file_if_given()

        def check_save_and_destroy() -> None:
            if self.file.check_save():
                root().destroy()

        root().protocol("WM_DELETE_WINDOW", check_save_and_destroy)

        # Start autodetect loop for OS dark mode, if appropriate
        self.update_theme()

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
        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="Run in debug mode",
        )
        parser.add_argument(
            "--nohome",
            action="store_true",
            help="Do not load the Preferences file",
        )
        self.args = parser.parse_args()

    def load_file_if_given(self) -> None:
        """If filename, or recent number, given on command line
        load the relevant file."""

        if self.args.filename:
            self.file.load_file(self.args.filename)
        elif self.args.recent:
            index = self.args.recent - 1
            try:
                self.file.load_file(preferences.get(PrefKey.RECENT_FILES)[index])
            except IndexError:
                pass  # Not enough recent files to load the requested one

    def auto_image_callback(self, value: bool) -> None:
        """Callback when auto_image preference is changed."""
        statusbar().set("see img", "Auto Img" if value else "See Img")
        if value:
            mainimage().auto_image_state(AutoImageState.NORMAL)
            self.file.image_dir_check()
            self.file.auto_image_check()

    def see_image(self) -> None:
        """Show the image corresponding to current location."""
        self.file.image_dir_check()
        self.mainwindow.load_image(self.file.get_current_image_path())

    def show_image_viewer(self) -> None:
        """Show the image viewer."""
        self.file.image_dir_check()
        self.mainwindow.load_image(self.file.get_current_image_path(), force_show=True)

    def hide_image_viewer(self) -> None:
        """Hide the image viewer."""
        self.mainwindow.hide_image()

    def run(self) -> None:
        """Run the app."""
        root().mainloop()

    def filename_changed(self) -> None:
        """Handle side effects needed when filename changes."""
        self.populate_recent_menu()  # Recreate menu to reflect recent files
        self.update_title()
        CustomMenuDialog.store_filename(self.file.filename)
        maintext().after_idle(maintext().focus_set)

    def languages_changed(self) -> None:
        """Handle side effects needed when languages change."""
        statusbar().set("languages label", "Lang: " + (self.file.languages or ""))

    def update_title(self) -> None:
        """Update the window title to reflect current status."""
        modtitle = " - edited" if maintext().is_modified() else ""
        filetitle = self.file.filename
        # Restrict filepath to rightmost W characters where W is maintext's visible width
        len_title = len(filetitle) + len(modtitle) + len("...")
        if len_title > 0:
            max_width = int(maintext().winfo_width() / maintext().font.measure("0"))
            if len_title > max_width:
                filetitle = "..." + filetitle[len_title - max_width :]
            if filetitle:
                filetitle = " - " + filetitle
        root().title(f"Guiguts {version('guiguts')}" + modtitle + filetitle)
        if is_mac():
            root().wm_attributes("-modified", maintext().is_modified())

    def quit_program(self) -> None:
        """Exit the program."""
        if self.file.check_save():
            root().quit()

    def show_page_details_dialog(self) -> None:
        """Show the page details display/edit dialog."""
        PageDetailsDialog.show_dialog(page_details=self.file.page_details)

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

    def close_command(self) -> None:
        """Close top-level dialog with focus, or close the file if it's
        the main window."""
        focus_widget = maintext().focus_get()
        if focus_widget is None:
            return
        focus_tl = focus_widget.winfo_toplevel()
        if focus_tl == maintext().winfo_toplevel():
            self.close_file()
        else:
            focus_tl.destroy()

    def close_file(self) -> None:
        """Close currently loaded file and associated image."""
        self.file.close_file()
        self.mainwindow.clear_image()

    def show_help_manual(self) -> None:
        """Display the manual."""
        webbrowser.open("https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_2_Manual")

    def show_help_regex(self) -> None:
        """Display the regex cheat sheet."""
        webbrowser.open(
            "https://www.pgdp.net/wiki/PPTools/Guiguts/Guiguts_2_Manual/Help_Menu#Regular_Expression_Quick_Reference"
        )

    def highlight_quotbrac_callback(self, value: bool) -> None:
        """Callback when highlight_quotbrac preference is changed."""
        if value:
            maintext().highlight_quotbrac()
        else:
            maintext().remove_highlights_quotbrac()

    def highlight_proofercomment_callback(self, value: bool) -> None:
        """Callback when highlight_proofercomment preference is changed."""
        if value:
            maintext().highlight_proofercomment()
        else:
            maintext().remove_highlights_proofercomment()

    def initialize_preferences(self) -> None:
        """Set default preferences and load settings from the GGPrefs file."""
        preferences.set_default(PrefKey.AUTO_IMAGE, False)
        preferences.set_callback(PrefKey.AUTO_IMAGE, self.auto_image_callback)
        preferences.set_default(PrefKey.BELL_AUDIBLE, True)
        preferences.set_default(PrefKey.BELL_VISUAL, True)
        preferences.set_default(PrefKey.IMAGE_WINDOW_DOCKED, True)
        preferences.set_default(PrefKey.RECENT_FILES, [])
        preferences.set_default(PrefKey.LINE_NUMBERS, True)
        preferences.set_default(PrefKey.ORDINAL_NAMES, True)
        preferences.set_callback(
            PrefKey.LINE_NUMBERS, lambda value: maintext().show_line_numbers(value)
        )
        preferences.set_default(PrefKey.SEARCH_HISTORY, [])
        preferences.set_default(PrefKey.REPLACE_HISTORY, [])
        preferences.set_default(PrefKey.SEARCHDIALOG_REVERSE, False)
        preferences.set_default(PrefKey.SEARCHDIALOG_MATCH_CASE, False)
        preferences.set_default(PrefKey.SEARCHDIALOG_WHOLE_WORD, False)
        preferences.set_default(PrefKey.SEARCHDIALOG_WRAP, True)
        preferences.set_default(PrefKey.SEARCHDIALOG_REGEX, False)
        preferences.set_default(PrefKey.SEARCHDIALOG_MULTI_REPLACE, False)
        preferences.set_default(PrefKey.DIALOG_GEOMETRY, {})
        preferences.set_default(PrefKey.ROOT_GEOMETRY, "800x400")
        preferences.set_default(PrefKey.ROOT_GEOMETRY_STATE, "normal")
        preferences.set_default(PrefKey.DEFAULT_LANGUAGES, "en")
        preferences.set_default(PrefKey.WFDIALOG_SUSPECTS_ONLY, False)
        preferences.set_default(PrefKey.WFDIALOG_IGNORE_CASE, False)
        preferences.set_default(PrefKey.WFDIALOG_DISPLAY_TYPE, WFDisplayType.ALL_WORDS)
        preferences.set_default(PrefKey.WFDIALOG_SORT_TYPE, WFSortType.ALPHABETIC)
        preferences.set_default(PrefKey.CHECKERDIALOG_SORT_TYPE_DICT, {})
        preferences.set_default(PrefKey.CHECKERDIALOG_SUSPECTS_ONLY_DICT, {})
        preferences.set_default(PrefKey.WFDIALOG_ITALIC_THRESHOLD, ["4"])
        preferences.set_default(PrefKey.WFDIALOG_REGEX, [])
        preferences.set_default(
            PrefKey.JEEBIES_PARANOIA_LEVEL, JeebiesParanoiaLevel.NORMAL
        )
        preferences.set_default(
            PrefKey.LEVENSHTEIN_DISTANCE, LevenshteinEditDistance.ONE
        )
        preferences.set_default(PrefKey.FOOTNOTE_INDEX_STYLE, FootnoteIndexStyle.NUMBER)
        preferences.set_default(PrefKey.SHOW_TOOLTIPS, True)
        preferences.set_default(PrefKey.WRAP_LEFT_MARGIN, 0)
        preferences.set_default(PrefKey.WRAP_RIGHT_MARGIN, 72)
        preferences.set_default(PrefKey.WRAP_BLOCKQUOTE_INDENT, 2)
        preferences.set_default(PrefKey.WRAP_BLOCKQUOTE_RIGHT_MARGIN, 72)
        preferences.set_default(PrefKey.WRAP_BLOCK_INDENT, 2)
        preferences.set_default(PrefKey.WRAP_POETRY_INDENT, 4)
        preferences.set_default(PrefKey.WRAP_INDEX_MAIN_MARGIN, 2)
        preferences.set_default(PrefKey.WRAP_INDEX_WRAP_MARGIN, 8)
        preferences.set_default(PrefKey.WRAP_INDEX_RIGHT_MARGIN, 72)
        preferences.set_default(PrefKey.TEXT_MARKUP_ITALIC, "_")
        preferences.set_default(PrefKey.TEXT_MARKUP_BOLD, "=")
        preferences.set_default(PrefKey.TEXT_MARKUP_SMALLCAPS, "+")
        preferences.set_default(PrefKey.TEXT_MARKUP_GESPERRT, "~")
        preferences.set_default(PrefKey.TEXT_MARKUP_FONT, "=")
        preferences.set_default(PrefKey.PAGESEP_AUTO_TYPE, PageSepAutoType.AUTO_FIX)
        preferences.set_default(PrefKey.THEME_NAME, "Default")
        preferences.set_callback(PrefKey.THEME_NAME, self.theme_name_callback)
        preferences.set_default(PrefKey.TEAROFF_MENUS, False)
        preferences.set_default(PrefKey.COMPOSE_HISTORY, [])
        # Since fonts aren't available until Tk has initialized, set default font family
        # to be empty string here, and set the true default later in MainText.
        preferences.set_default(PrefKey.TEXT_FONT_FAMILY, "")
        preferences.set_callback(
            PrefKey.TEXT_FONT_FAMILY,
            lambda *value: maintext().set_font(),
        )
        preferences.set_default(PrefKey.TEXT_FONT_SIZE, 12)
        preferences.set_callback(
            PrefKey.TEXT_FONT_SIZE,
            lambda *value: maintext().set_font(),
        )
        # For some reason line spacing on Mac is very tight, so pad a bit here
        preferences.set_default(PrefKey.TEXT_LINE_SPACING, 4 if is_mac() else 0)
        preferences.set_callback(
            PrefKey.TEXT_LINE_SPACING,
            lambda *value: maintext().set_spacing1(),
        )
        preferences.set_default(PrefKey.TEXT_CURSOR_WIDTH, 2)
        preferences.set_callback(
            PrefKey.TEXT_CURSOR_WIDTH,
            lambda *value: maintext().set_insertwidth(),
        )
        preferences.set_default(PrefKey.PREF_TAB_CURRENT, 0)
        preferences.set_default(PrefKey.SPELL_THRESHOLD, 3)
        preferences.set_default(PrefKey.UNMATCHED_NESTABLE, False)
        preferences.set_default(
            PrefKey.UNICODE_BLOCK, UnicodeBlockDialog.commonly_used_characters_name
        )
        preferences.set_default(PrefKey.UNICODE_SEARCH_HISTORY, [])
        preferences.set_default(PrefKey.SPLIT_TEXT_WINDOW, False)
        preferences.set_default(PrefKey.SPLIT_TEXT_SASH_COORD, 0)
        preferences.set_default(PrefKey.IMAGE_INVERT, False)
        preferences.set_default(PrefKey.IMAGE_FLOAT_GEOMETRY, "400x600+100+100")
        preferences.set_default(PrefKey.IMAGE_DOCK_SASH_COORD, 300)
        preferences.set_default(PrefKey.IMAGE_SCALE_FACTOR, 0.5)
        preferences.set_default(PrefKey.IMAGE_VIEWER_ALERT, True)
        preferences.set_default(PrefKey.HIGH_CONTRAST, False)
        preferences.set_callback(PrefKey.HIGH_CONTRAST, self.high_contrast_callback)
        preferences.set_default(PrefKey.IMAGE_WINDOW_SHOW, False)
        preferences.set_default(PrefKey.IMAGE_VIEWER_EXTERNAL, False)
        preferences.set_default(PrefKey.IMAGE_VIEWER_EXTERNAL_PATH, "")
        preferences.set_default(PrefKey.IMAGE_VIEWER_INTERNAL, False)
        preferences.set_default(
            PrefKey.SCANNOS_FILENAME,
            str(DEFAULT_SCANNOS_DIR.joinpath(DEFAULT_REGEX_SCANNOS)),
        )
        preferences.set_default(
            PrefKey.SCANNOS_HISTORY,
            [
                str(DEFAULT_SCANNOS_DIR.joinpath(DEFAULT_REGEX_SCANNOS)),
                str(DEFAULT_SCANNOS_DIR.joinpath(DEFAULT_STEALTH_SCANNOS)),
                str(DEFAULT_SCANNOS_DIR.joinpath(DEFAULT_MISSPELLED_SCANNOS)),
            ],
        )
        preferences.set_default(PrefKey.HIGHLIGHT_QUOTBRAC, False)
        preferences.set_callback(
            PrefKey.HIGHLIGHT_QUOTBRAC, self.highlight_quotbrac_callback
        )
        preferences.set_default(PrefKey.HIGHLIGHT_HTML_TAGS, False)
        preferences.set_default(PrefKey.HIGHLIGHT_CURSOR_LINE, True)
        preferences.set_callback(
            PrefKey.HIGHLIGHT_CURSOR_LINE, lambda _: maintext().highlight_cursor_line()
        )
        preferences.set_default(PrefKey.COLUMN_NUMBERS, False)
        preferences.set_callback(
            PrefKey.COLUMN_NUMBERS, lambda value: maintext().show_column_numbers(value)
        )
        preferences.set_default(PrefKey.HTML_ITALIC_MARKUP, HTMLMarkupTypes.KEEP)
        preferences.set_default(PrefKey.HTML_BOLD_MARKUP, HTMLMarkupTypes.KEEP)
        preferences.set_default(PrefKey.HTML_GESPERRT_MARKUP, HTMLMarkupTypes.EM_CLASS)
        preferences.set_default(PrefKey.HTML_FONT_MARKUP, HTMLMarkupTypes.SPAN_CLASS)
        preferences.set_default(
            PrefKey.HTML_UNDERLINE_MARKUP, HTMLMarkupTypes.SPAN_CLASS
        )
        preferences.set_default(PrefKey.HTML_SHOW_PAGE_NUMBERS, True)
        preferences.set_default(PrefKey.HTML_IMAGE_UNIT, "%")
        preferences.set_default(PrefKey.HTML_IMAGE_OVERRIDE_EPUB, True)
        preferences.set_default(PrefKey.HTML_IMAGE_ALIGNMENT, "center")
        preferences.set_default(PrefKey.CSS_VALIDATION_LEVEL, "css3")
        preferences.set_default(PrefKey.PPHTML_VERBOSE, False)
        preferences.set_default(PrefKey.HIGHLIGHT_PROOFERCOMMENT, True)
        preferences.set_callback(
            PrefKey.HIGHLIGHT_PROOFERCOMMENT, self.highlight_proofercomment_callback
        )
        preferences.set_default(PrefKey.IMAGE_AUTOFIT_WIDTH, False)
        preferences.set_callback(
            PrefKey.IMAGE_AUTOFIT_WIDTH, image_autofit_width_callback
        )
        preferences.set_default(PrefKey.IMAGE_AUTOFIT_HEIGHT, False)
        preferences.set_callback(
            PrefKey.IMAGE_AUTOFIT_HEIGHT, image_autofit_height_callback
        )
        preferences.set_default(PrefKey.CHECKER_GRAY_UNUSED_OPTIONS, False)
        # Retain the RTL fix Pref for now, even though it is not in the Prefs dialog
        # For debugging etc, it can be manually edited in the GGprefs file.
        if is_windows():
            preferences.set_default(PrefKey.AUTOFIX_RTL_TEXT, "word")
        elif is_x11():
            preferences.set_default(PrefKey.AUTOFIX_RTL_TEXT, "char")
        else:
            preferences.set_default(PrefKey.AUTOFIX_RTL_TEXT, "off")
        preferences.set_default(
            PrefKey.CUSTOM_MENU_ENTRIES,
            [
                ["View HTML in browser", 'start "$f"' if is_windows() else 'open "$f"'],
                ["Onelook.com (several dictionaries)", "https://www.onelook.com/?w=$t"],
                [
                    "Google Books Ngram Viewer",
                    "https://books.google.com/ngrams/graph?content=$t",
                ],
                [
                    "Shape Catcher (Unicode character finder)",
                    "https://shapecatcher.com",
                ],
                ["Ebookmaker online", "https://ebookmaker.pglaf.org"],
            ],
        )
        preferences.set_default(PrefKey.EBOOKMAKER_PATH, "")
        preferences.set_default(PrefKey.EBOOKMAKER_EPUB2, True)
        preferences.set_default(PrefKey.EBOOKMAKER_EPUB3, True)
        preferences.set_default(PrefKey.EBOOKMAKER_KINDLE, False)
        preferences.set_default(PrefKey.EBOOKMAKER_KF8, False)
        preferences.set_default(PrefKey.EBOOKMAKER_VERBOSE_OUTPUT, False)
        preferences.set_default(PrefKey.BACKUPS_ENABLED, True)
        preferences.set_default(PrefKey.AUTOSAVE_ENABLED, False)
        preferences.set_default(PrefKey.AUTOSAVE_INTERVAL, 5)
        preferences.set_default(PrefKey.ASCII_TABLE_HANGING, True)
        preferences.set_default(PrefKey.ASCII_TABLE_INDENT, 1)
        preferences.set_default(PrefKey.ASCII_TABLE_REWRAP, False)
        preferences.set_default(PrefKey.ASCII_TABLE_JUSTIFY, JustifyStyle.LEFT)
        preferences.set_default(PrefKey.ASCII_TABLE_FILL_CHAR, "@")
        preferences.set_default(PrefKey.ASCII_TABLE_RIGHT_COL, 70)
        preferences.set_default(PrefKey.COMMAND_PALETTE_HISTORY, [])

        # Check all preferences have a default
        for pref_key in PrefKey:
            assert preferences.get_default(pref_key) is not None

        # If `--nohome` argument given, Prefs are not loaded & saved in Prefs file
        preferences.set_permanent(not self.args.nohome)
        preferences.load()

    # Lay out menus
    def init_menus(self) -> None:
        """Create all the menus."""
        self.init_file_menu()
        self.init_edit_menu()
        self.init_search_menu()
        self.init_tools_menu()
        self.init_text_menu()
        self.init_html_menu()
        self.init_view_menu()
        self.init_custom_menu()
        self.init_help_menu()
        self.init_os_menu()

        # Orphan commands to be included in Command Palette
        menubar_metadata().add_checkbox(
            None,
            "Line Numbers",
            "",
            PersistentBoolean(PrefKey.LINE_NUMBERS),
            None,
            None,
        )
        menubar_metadata().add_checkbox(
            None,
            "Column Numbers",
            "",
            PersistentBoolean(PrefKey.COLUMN_NUMBERS),
            None,
            None,
        )

        if is_mac():
            root().createcommand(
                "tk::mac::ShowPreferences", PreferencesDialog.show_dialog
            )
            root().createcommand("tk::mac::OpenDocument", self.open_document)
            root().createcommand("tk::mac::Quit", self.quit_program)

    def init_file_menu(self) -> None:
        """(Re-)create the File menu."""
        file_menu = Menu(menubar(), "~File")
        file_menu.add_button("~Open...", self.open_file, "Cmd/Ctrl+O")
        self.init_file_recent_menu(file_menu)
        file_menu.add_button("~Save", self.file.save_file, "Cmd/Ctrl+S")
        file_menu.add_button("Save ~As...", self.file.save_as_file, "Cmd/Ctrl+Shift+S")
        file_menu.add_button("Sa~ve a Copy As...", self.file.save_copy_as_file)
        file_menu.add_button("~Close", self.close_command, "Cmd+W" if is_mac() else "")
        self.init_file_project_menu(file_menu)
        if not is_mac():
            file_menu.add_separator()
            file_menu.add_button("E~xit", self.quit_program, "")

    def init_file_recent_menu(self, parent: Menu) -> None:
        """Create the Recent Documents menu."""
        self.recent_menu = Menu(parent, "Recent Doc~uments")
        self.populate_recent_menu()

    def populate_recent_menu(self) -> None:
        """Populate recent menu with recent filenames"""
        assert self.recent_menu is not None
        self.recent_menu.delete(0, "end")
        for count, file in enumerate(preferences.get(PrefKey.RECENT_FILES), start=1):
            self.recent_menu.add_button(
                f"~{count}: {file}",
                lambda fn=file: self.open_file(fn),  # type:ignore[misc]
                add_to_command_palette=False,
            )

    def init_file_project_menu(self, parent: Menu) -> None:
        """Create the File->Project menu."""
        project_menu = Menu(parent, "~Project")
        project_menu.add_button(
            "Add ~Good/Bad Words to Project Dictionary",
            self.file.add_good_and_bad_words,
        )
        project_menu.add_button(
            f"Set ~Scan Image {folder_dir_str()}...",
            self.file.choose_image_dir,
        )
        project_menu.add_button("Set ~Language(s)...", self.file.set_languages)
        project_menu.add_separator()
        project_menu.add_button(
            "~Configure Page Labels...", self.show_page_details_dialog
        )
        project_menu.add_separator()
        project_menu.add_button("~Add Page Marker Flags", self.file.add_page_flags)
        project_menu.add_button(
            "~Remove Page Marker Flags", self.file.remove_page_flags
        )

    def init_edit_menu(self) -> None:
        """Create the Edit menu."""
        edit_menu = Menu(menubar(), "~Edit")
        edit_menu.add_button("~Undo", "<<Undo>>", "Cmd/Ctrl+Z")
        edit_menu.add_button(
            "~Redo", "<<Redo>>", "Cmd+Shift+Z" if is_mac() else "Ctrl+Y"
        )
        edit_menu.add_separator()
        edit_menu.add_cut_copy_paste()
        edit_menu.add_button(
            "R~estore Selection",
            maintext().restore_selection_ranges,
        )
        edit_menu.add_separator()
        edit_menu.add_button(
            "Co~lumn Cut", maintext().columnize_cut, "Cmd/Ctrl+Shift+X"
        )
        edit_menu.add_button(
            "C~olumn Copy", maintext().columnize_copy, "Cmd/Ctrl+Shift+C"
        )
        edit_menu.add_button(
            "Colu~mn Paste", maintext().columnize_paste, "Cmd/Ctrl+Shift+V"
        )
        edit_menu.add_button(
            "To~ggle Column/Regular Selection",
            maintext().toggle_selection_type,
        )
        edit_menu.add_separator()
        rtl_menu = Menu(edit_menu, "Right-to-left Te~xt")
        if not is_mac():
            rtl_menu.add_button(
                (
                    "Paste ~Hebrew & spaces only (no punctuation)"
                    if is_windows()
                    else "Paste ~Hebrew, Arabic & spaces only (no punctuation)"
                ),
                maintext().paste_rtl,
            )
        rtl_menu.add_button(
            "~Surround selected text with RLM...LRM markers",
            maintext().surround_rtl,
        )
        edit_menu.add_separator()
        case_menu = Menu(edit_menu, "C~hange Case")
        case_menu.add_button(
            "~lowercase selection",
            lambda: maintext().transform_selection(str.lower),
            "",
        )
        case_menu.add_button(
            "~Sentence case selection",
            lambda: maintext().transform_selection(
                maintext().sentence_case_transformer
            ),
            "",
        )
        case_menu.add_button(
            "~Title Case Selection",
            lambda: maintext().transform_selection(maintext().title_case_transformer),
            "",
        )
        case_menu.add_button(
            "~UPPERCASE SELECTION",
            lambda: maintext().transform_selection(str.upper),
            "",
        )
        if not is_mac():
            edit_menu.add_separator()
            edit_menu.add_button("Pre~ferences...", PreferencesDialog.show_dialog)

    def init_search_menu(self) -> None:
        """Create the Search menu."""
        search_menu = Menu(menubar(), "~Search")
        search_menu.add_button(
            "~Search & Replace...",
            show_search_dialog,
            "Cmd/Ctrl+F",
        )
        search_menu.add_button(
            "Find Ne~xt",
            find_next,
            "Cmd+G" if is_mac() else "F3",
        )
        search_menu.add_button(
            "Find Pre~vious",
            lambda: find_next(backwards=True),
            "Cmd+Shift+G" if is_mac() else "Shift+F3",
        )
        search_menu.add_separator()
        self.init_search_goto_menu(search_menu)
        search_menu.add_separator()
        search_menu.add_button(
            "Find Proofer ~Comments",
            proofer_comment_check,
        )
        search_menu.add_button(
            "Find ~Asterisks w/o Slash",
            asterisk_check,
        )
        search_menu.add_separator()
        search_menu.add_button(
            "Highlight Single ~Quotes in Selection",
            maintext().highlight_single_quotes,
        )
        search_menu.add_button(
            "Highlight ~Double Quotes in Selection",
            maintext().highlight_double_quotes,
        )
        search_menu.add_button(
            "~Remove Highlights",
            maintext().remove_highlights,
        )
        search_menu.add_separator()
        search_menu.add_checkbox(
            "Highlight S~urrounding Quotes & Brackets",
            root().highlight_quotbrac,
        )
        search_menu.add_checkbox(
            "Highlight Al~ignment Column",
            maintext().aligncol_active,
            lambda: maintext().highlight_aligncol_callback(True),
            lambda: maintext().highlight_aligncol_callback(False),
        )
        search_menu.add_checkbox(
            "Highlight ~Proofer Comments",
            root().highlight_proofercomment,
        )
        search_menu.add_checkbox(
            "Highlight ~HTML tags",
            PersistentBoolean(PrefKey.HIGHLIGHT_HTML_TAGS),
            lambda: maintext().highlight_html_tags_callback(True),
            lambda: maintext().highlight_html_tags_callback(False),
        )
        search_menu.add_separator()
        self.init_bookmark_menu(search_menu)

    def init_search_goto_menu(self, parent: Menu) -> None:
        """Create the Search->Goto menu."""
        goto_menu = Menu(parent, "~Goto")
        goto_menu.add_button(
            "~Line Number...",
            self.file.goto_line,
        )
        goto_menu.add_button(
            "Pa~ge (png)...",
            self.file.goto_image,
        )
        goto_menu.add_button(
            "Page La~bel...",
            self.file.goto_page,
        )
        goto_menu.add_button(
            "~Previous Page",
            self.file.prev_page,
        )
        goto_menu.add_button(
            "~Next Page",
            self.file.next_page,
        )

    def init_bookmark_menu(self, parent: Menu) -> None:
        """Create the Bookmarks menu."""
        bookmark_menu = Menu(parent, "~Bookmarks")
        # Because keyboard layouts are different, need to bind to several keys for some bookmarks
        shortcuts = [
            ("exclam",),
            ("at", "quotedbl"),
            ("numbersign", "sterling", "section", "periodcentered"),
            ("dollar", "currency"),
            ("percent",),
        ]
        # Shift+Cmd+number no good for Mac due to clash with screen capture shortcuts
        # Ctrl+number could also clash on Mac with virtual desktop switching, but
        # the best option we have that works at the moment.
        modifier = "Shift"
        for bm, keys in enumerate(shortcuts, start=1):
            bookmark_menu.add_button(
                f"Set Bookmark {bm}",
                lambda num=bm: self.file.set_bookmark(num),  # type:ignore[misc]
                f"{modifier}+Ctrl+Key-{bm}",
            )
            # Add extra shortcuts to cope with keyboard layout differences
            for key in keys:
                (_, key_event) = process_accel(f"{modifier}+Ctrl+{key}")
                maintext().key_bind(
                    key_event,
                    lambda _event, num=bm: self.file.set_bookmark(  # type:ignore[misc]
                        num
                    ),
                    bind_all=True,
                )

        for bm in range(1, 6):
            bookmark_menu.add_button(
                f"Go To Bookmark {bm}",
                lambda num=bm: self.file.goto_bookmark(num),  # type:ignore[misc]
                f"Ctrl+Key-{bm}",
            )

    def init_tools_menu(self) -> None:
        """Create the Tools menu."""
        tools_menu = Menu(menubar(), "~Tools")
        tools_menu.add_button("Basic Fi~xup", basic_fixup_check)
        tools_menu.add_button("~Word Frequency", word_frequency)
        tools_menu.add_button("~Bookloupe", bookloupe_check)
        tools_menu.add_button(
            "~Spelling",
            lambda: spell_check(
                self.file.project_dict,
                self.file.add_good_word_to_project_dictionary,
                self.file.add_good_word_to_global_dictionary,
            ),
        )
        tools_menu.add_button("~Jeebies", jeebies_check)
        tools_menu.add_button("Stealth S~cannos", stealth_scannos)
        tools_menu.add_button(
            "Word ~Distance Check", lambda: levenshtein_check(self.file.project_dict)
        )
        tools_menu.add_separator()
        tools_menu.add_button("~Page Separator Fixup", page_separator_fixup)
        tools_menu.add_button("~Footnote Fixup", footnote_check)
        tools_menu.add_button("Side~note Fixup", lambda: illosn_check("Sidenote"))
        tools_menu.add_button(
            "~Illustration Fixup", lambda: illosn_check("Illustration")
        )
        tools_menu.add_separator()
        tools_menu.add_button("~Rewrap All", self.file.rewrap_all)
        tools_menu.add_button("R~ewrap Selection", self.file.rewrap_selection)
        tools_menu.add_button("C~lean Up Rewrap Markers", self.file.rewrap_cleanup)
        tools_menu.add_separator()
        tools_menu.add_button("Convert to Curly ~Quotes", convert_to_curly_quotes)
        tools_menu.add_button("Check Curly Quo~tes", check_curly_quotes)
        unmatched_menu = Menu(tools_menu, "Un~matched")
        unmatched_menu.add_button("Bloc~k Markup", unmatched_block_markup)
        unmatched_menu.add_button("~DP Markup", unmatched_dp_markup)
        unmatched_menu.add_button("~Brackets", unmatched_brackets)
        unmatched_menu.add_button("Curly ~Quotes", unmatched_curly_quotes)

        fraction_menu = Menu(tools_menu, "C~onvert Fractions")
        fraction_menu.add_button(
            "~Unicode Fractions Only",
            lambda: fraction_convert(FractionConvertType.UNICODE),
        )
        fraction_menu.add_button(
            "Unicode Fractions ~Or Super/Subscript",
            lambda: fraction_convert(FractionConvertType.MIXED),
        )
        fraction_menu.add_button(
            "All to ~Super/Subscript",
            lambda: fraction_convert(FractionConvertType.SUPSUB),
        )
        unicode_menu = Menu(tools_menu, "~Unicode")
        unicode_menu.add_button(
            "Unicode ~Search/Entry", UnicodeSearchDialog.show_dialog
        )
        unicode_menu.add_button("Unicode ~Blocks", UnicodeBlockDialog.show_dialog)
        unicode_menu.add_button(
            "~Normalize Selected Characters",
            unicode_normalize,
        )
        unicode_menu.add_button(
            "~Compose Sequence...",
            ComposeSequenceDialog.show_dialog,
            "Cmd/Ctrl+I",
        )
        tools_menu.add_separator()
        tools_menu.add_button(
            "PP Wor~kbench (opens in browser)",
            lambda: webbrowser.open("https://www.pgdp.net/ppwb/"),
        )

    def init_text_menu(self) -> None:
        """Create the Text menu."""
        text_menu = Menu(menubar(), "Te~xt")
        text_menu.add_button(
            "Convert ~Markup...", TextMarkupConvertorDialog.show_dialog
        )
        text_menu.add_button("~PPtxt", lambda: pptxt(self.file.project_dict))
        text_menu.add_button("ASCII ~Table Effects", ASCIITableDialog.show_dialog)

    def init_html_menu(self) -> None:
        """Create the HTML menu."""
        html_menu = Menu(menubar(), "HT~ML")
        html_menu.add_button("HTML ~Generator...", HTMLGeneratorDialog.show_dialog)
        html_menu.add_button("Auto-~Illustrations...", HTMLImageDialog.show_dialog)
        html_menu.add_separator()
        html_menu.add_button("~Unmatched HTML Tags", unmatched_html_markup)
        html_menu.add_button("HTML ~Link Checker", lambda: HTMLLinkChecker().run())
        html_menu.add_button("~PPhtml", lambda: PPhtmlChecker().run())
        html_menu.add_button("HTML5 ~Validator (online)", lambda: HTMLValidator().run())
        html_menu.add_button("~CSS Validator (online)", lambda: CSSValidator().run())
        html_menu.add_separator()
        html_menu.add_button(
            "~Ebookmaker generate/check", lambda: EbookmakerChecker().run()
        )

    def init_view_menu(self) -> None:
        """Create the View menu."""
        view_menu = Menu(menubar(), "~View")
        view_menu.add_checkbox(
            "Split ~Text Window",
            root().split_text_window,
            lambda: maintext().show_peer(),
            lambda: maintext().hide_peer(),
        )
        view_menu.add_separator()
        view_menu.add_checkbox(
            "Image Viewer",
            PersistentBoolean(PrefKey.IMAGE_VIEWER_INTERNAL),
            self.show_image_viewer,
            self.hide_image_viewer,
        )
        view_menu.add_checkbox(
            "~Dock Image Viewer",
            root().image_window_docked_state,
            self.mainwindow.dock_image,
            self.mainwindow.float_image,
        )
        view_menu.add_checkbox(
            "~Auto Image",
            root().auto_image_state,
        )
        view_menu.add_button("S~ee Image", self.see_image)
        view_menu.add_checkbox(
            "~Invert Image",
            root().invert_image_state,
            mainimage().show_image,
            mainimage().show_image,
        )
        view_menu.add_separator()
        view_menu.add_button("~Message Log", self.mainwindow.messagelog.show)
        view_menu.add_separator()
        if not is_mac():  # Full Screen behaves oddly on Macs
            view_menu.add_checkbox(
                "~Full Screen",
                root().full_screen_var,
                lambda: root().wm_attributes("-fullscreen", True),
                lambda: root().wm_attributes("-fullscreen", False),
            )

    def init_custom_menu(self) -> None:
        """Create the Custom menu."""
        self.custom_menu = Menu(menubar(), "~Custom")
        self.custom_menu.add_separator()
        self.custom_menu.add_button(
            "Customi~ze Menu",
            lambda: CustomMenuDialog.show_dialog(menu=self.custom_menu),
        )
        CustomMenuDialog.rewrite_custom_menu(self.custom_menu)

    def init_help_menu(self) -> None:
        """Create the Help menu."""
        help_menu = Menu(menubar(), "~Help")
        help_menu.add_button(
            "Guiguts ~Manual (opens in browser)",
            self.show_help_manual,
            "F1",
            force_main_only=True,
        )
        help_menu.add_button("About ~Guiguts", HelpAboutDialog.show_dialog)
        help_menu.add_button(
            "~Regex Quick Reference (opens in browser)", self.show_help_regex
        )
        help_menu.add_button(
            "List of ~Compose Sequences", ComposeHelpDialog.show_dialog
        )
        help_menu.add_separator()
        help_menu.add_button(
            "Command ~Palette", CommandPaletteDialog.show_dialog, "Cmd/Ctrl+Shift+P"
        )

    def init_os_menu(self) -> None:
        """Create the OS-specific menu.

        Currently only does anything on Macs
        """
        if is_mac():
            # Window menu
            Menu(menubar(), "Window", name="window")

    def init_statusbar(self, the_statusbar: StatusBar) -> None:
        """Add labels to initialize the statusbar.

        Functions are bound to Button Release, rather than Button Press, since
        that is how buttons normally operate.
        """

        def rowcol_str() -> str:
            """Format current insert index for statusbar."""
            row, col = maintext().get_insert_index().rowcol()
            return f"L:{row} C:{col}"

        the_statusbar.add(
            "rowcol",
            tooltip="Click: Go to line\nShift click: Toggle line numbers\nShift right-click: Toggle column numbers",
            update=rowcol_str,
        )
        the_statusbar.add_binding("rowcol", "ButtonRelease-1", self.file.goto_line)
        the_statusbar.add_binding(
            "rowcol",
            "Shift-ButtonRelease-1",
            lambda: preferences.toggle(PrefKey.LINE_NUMBERS),
        )
        the_statusbar.add_binding(
            "rowcol",
            "Shift-ButtonRelease-3",
            lambda: preferences.toggle(PrefKey.COLUMN_NUMBERS),
        )

        the_statusbar.add(
            "img",
            tooltip="Click: Go to image",
            update=lambda: "Img: " + maintext().get_current_image_name(),
        )
        the_statusbar.add_binding("img", "ButtonRelease-1", self.file.goto_image)

        the_statusbar.add(
            "prev img", tooltip="Click: Go to previous image", text="<", width=1
        )
        the_statusbar.add_binding("prev img", "ButtonRelease-1", self.file.prev_page)

        the_statusbar.add(
            "see img",
            tooltip="Click: See image\nShift click: Toggle auto-image",
            text="See Img",
            width=9,
        )
        the_statusbar.add_binding(
            "see img",
            "ButtonRelease-1",
            self.see_image,
        )
        the_statusbar.add_binding(
            "see img",
            "Shift-ButtonRelease-1",
            lambda: preferences.toggle(PrefKey.AUTO_IMAGE),
        )

        the_statusbar.add(
            "next img", tooltip="Click: Go to next image", text=">", width=1
        )
        the_statusbar.add_binding("next img", "ButtonRelease-1", self.file.next_page)

        the_statusbar.add(
            "page label",
            tooltip="Click: Go to page\nShift click: Configure page labels",
            text="Lbl: ",
            update=lambda: "Lbl: " + self.file.get_current_page_label(),
        )
        the_statusbar.add_binding("page label", "ButtonRelease-1", self.file.goto_page)
        the_statusbar.add_binding(
            "page label", "Shift-ButtonRelease-1", self.show_page_details_dialog
        )

        def selection_str() -> str:
            """Format current selection range for statusbar.

            Returns:
                "Start-End" for a regular selection, and "R:rows C:cols" for column selection.
            """
            maintext().selection_cursor()
            ranges = maintext().selected_ranges()
            maintext().save_selection_ranges()
            if not ranges:
                return "No selection"
            if len(ranges) == 1:
                return f"{ranges[0].start.index()}-{ranges[-1].end.index()}"
            row_diff = abs(ranges[-1].end.row - ranges[0].start.row) + 1
            col_diff = abs(ranges[-1].end.col - ranges[0].start.col)
            return f"R:{row_diff} C:{col_diff}"

        the_statusbar.add(
            "selection",
            tooltip="Click: Restore previous selection\nShift Click: Toggle column/regular selection",
            update=selection_str,
            width=16,
        )
        the_statusbar.add_binding(
            "selection", "ButtonRelease-1", maintext().restore_selection_ranges
        )
        the_statusbar.add_binding(
            "selection", "Shift-ButtonRelease-1", maintext().toggle_selection_type
        )

        the_statusbar.add(
            "languages label",
            tooltip="Click: Set language(s), e.g. 'en' or 'de fr'",
            text="Lang: ",
        )
        the_statusbar.add_binding(
            "languages label", "ButtonRelease-1", self.file.set_languages
        )

        def ordinal_name_display(force: Optional[bool] = None) -> None:
            """Set, unset, or toggle, name display in ordinal button.

            Args:
                Force: True to set, False to unset, omit to toggle.
            """
            if force is None:
                force = not preferences.get(PrefKey.ORDINAL_NAMES)
            preferences.set(PrefKey.ORDINAL_NAMES, force)

        def ordinal_str() -> str:
            """Format ordinal of single selected char, or char at current insert
            index for statusbar."""
            # Get character - display nothing if more than one char selected
            sel_ranges = maintext().selected_ranges()
            if len(sel_ranges) == 0:
                char = maintext().get(maintext().get_insert_index().index())
            elif len(sel_ranges) == 1:
                char = maintext().selected_text()
                if len(char) != 1:
                    return ""
            else:
                return ""
            # unicodedata.name fails to return name for "control" characters
            # but the only one we care about is line feed
            if preferences.get(PrefKey.ORDINAL_NAMES):
                try:
                    name = f": {unicodedata.name(char)}"
                except ValueError:
                    name = ": LINE FEED" if char == "\n" else ""
            else:
                name = ""
            return f"U+{ord(char):04x}{name}"

        the_statusbar.add(
            "ordinal",
            tooltip="Character after the cursor\nClick to toggle name display",
            update=ordinal_str,
        )
        the_statusbar.add_binding("ordinal", "ButtonRelease-1", ordinal_name_display)

    def logging_init(self) -> None:
        """Set up basic logger until GUI is ready."""
        if self.args.debug:
            log_level = logging.DEBUG
            console_log_level = logging.DEBUG
            formatter = logging.Formatter(DEBUG_FORMAT, "%H:%M:%S")
        else:
            log_level = logging.INFO
            console_log_level = logging.WARNING
            formatter = logging.Formatter(MESSAGE_FORMAT, "%H:%M:%S")
        logger.setLevel(log_level)
        # Output to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    def logging_add_gui(self) -> None:
        """Add handlers to display log messages via the GUI.

        Assumes mainwindow has created the message_log handler.
        """

        # Message log is approximate GUI equivalent to console output
        if self.args.debug:
            message_log_level = logging.DEBUG
            formatter = logging.Formatter(DEBUG_FORMAT, "%H:%M:%S")
        else:
            message_log_level = logging.INFO
            formatter = logging.Formatter(MESSAGE_FORMAT, "%H:%M:%S")
        self.mainwindow.messagelog.setLevel(message_log_level)
        self.mainwindow.messagelog.setFormatter(formatter)
        logger.addHandler(self.mainwindow.messagelog)

        # Alert is just for errors, e.g. unable to load file
        alert_handler = ErrorHandler()
        alert_handler.setLevel(logging.ERROR)
        alert_handler.setFormatter(formatter)
        logger.addHandler(alert_handler)

    def theme_name_callback(self, value: str) -> None:
        """Callback for when THEME_NAME preference is changed.

        Responsible for starting auto-dark-detection loop for Default theme,
        if theme was not Default at startup."""
        if value == "Default":
            self.update_theme()
        elif value in ("Light", "Dark"):
            themed_style().theme_use(theme_name_internal_from_user(value))

    def update_theme(self) -> None:
        """Self-calling method to check OS dark mode on a repeating cycle,
        updating application theme if necessary."""
        if preferences.get(PrefKey.THEME_NAME) == "Default":
            os_mode = darkdetect.theme()
            tk_theme = themed_style().theme_use()

            if os_mode == "Light" and tk_theme != "awlight":
                themed_style().theme_use("awlight")
            elif os_mode == "Dark" and tk_theme != "awdark":
                themed_style().theme_use("awdark")

            root().after(2500, self.update_theme)

    def high_contrast_callback(self, _value: bool) -> None:
        """Callback for when HIGH_CONTRAST preference is changed"""
        # re-display image
        mainimage().show_image(internal_only=True)
        # change theme colors for text areas
        for _widget in (maintext(), maintext().peer):
            maintext().theme_set_tk_widget_colors(_widget)


def main() -> None:
    """Main application function."""
    Guiguts().run()


if __name__ == "__main__":
    main()
