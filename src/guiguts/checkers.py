"""Support running of checking tools"""

from enum import Enum, IntEnum, StrEnum, auto
import logging
import math
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional, Callable

import regex as re

from guiguts.maintext import maintext, HighlightTag
from guiguts.mainwindow import ScrolledReadOnlyText, menubar_metadata
from guiguts.preferences import PrefKey, preferences, PersistentBoolean
from guiguts.root import root
from guiguts.utilities import (
    IndexRowCol,
    IndexRange,
    is_mac,
    sing_plur,
    cmd_ctrl_string,
)
from guiguts.widgets import ToplevelDialog, TlDlg, mouse_bind, Busy, ToolTip

logger = logging.getLogger(__package__)

MARK_ENTRY_TO_SELECT = "MarkEntryToSelect"
REFRESH_MESSAGE = "Click this message to refresh after Undo/Redo"


class CheckerMatchType(Enum):
    """Enum class to store Checker Dialog match types."""

    ALL_MESSAGES = auto()  # Match all messages
    WHOLE = auto()  # Match whole of message text
    HIGHLIGHT = auto()  # Match highlighted text
    ERROR_PREFIX = auto()  # Match error prefix


class CheckerEntryType(Enum):
    """Enum class to store Checker Entry types."""

    HEADER = auto()
    CONTENT = auto()
    FOOTER = auto()


class CheckerEntrySeverity(IntEnum):
    """Enum class to store severity of Checker Entry (info/warning/error/etc).

    IntEnums can be used as integers, and auto() allocates incrementing values,
    so code such as `severity > CheckerEntrySeverity.INFO` is valid.

    The list below must be in order of increasing severity.
    """

    OTHER = auto()  # Headers, blank lines, etc.
    INFO = auto()  # Messages that do not indicate a problem
    ERROR = auto()  # Messages that do indicate a problem


class CheckerEntry:
    """Class to hold one entry in the Checker dialog.

    Current implementation enforces (on creation) and assumes (in use) that
    no section contains Entries of more than one type.
    """

    def __init__(
        self,
        text: str,
        text_range: Optional[IndexRange],
        hilite_start: Optional[int],
        hilite_end: Optional[int],
        section: int,
        initial_pos: int,
        entry_type: CheckerEntryType,
        error_prefix: str,
        ep_index: int,
        severity: CheckerEntrySeverity,
    ) -> None:
        """Initialize CheckerEntry object.

        Args:
            text: Single line of text to display in checker dialog.
            text_range: Optional start and end of point of interest in main text widget.
            hilite_start: Optional column to begin higlighting entry in dialog.
            hilite_end: Optional column to end higlighting entry in dialog.
            section: Section entry belongs to.
            initial_pos: Position of entry during initial creation.
            entry_type: Type of entry: header, footer, content, etc.
            error_prefix: Prefix string indicating an error.
            ep_index: Error prefix index (to control color) - must be 0, 1 or 2
        """
        self.text = text
        self.text_range = text_range
        self.hilite_start = hilite_start
        self.hilite_end = hilite_end
        self.section = section
        self.initial_pos = initial_pos
        self.entry_type = entry_type
        self.severity = severity
        self.error_prefix = error_prefix
        assert ep_index in range(3)
        self.ep_index = ep_index
        self.custom_data: Optional[Any] = None

    def error_prefix_tag(self) -> HighlightTag:
        """Return which tag to use to highlight error prefix."""
        assert self.ep_index in range(3)
        if self.ep_index == 1:
            return HighlightTag.CHECKER_ERROR_PREFIX_1
        if self.ep_index == 2:
            return HighlightTag.CHECKER_WARNING
        return HighlightTag.CHECKER_ERROR_PREFIX


class CheckerSortType(StrEnum):
    """Enum class to store Checker Dialog sort types."""

    ALPHABETIC = auto()
    ROWCOL = auto()
    CUSTOM = auto()


class CheckerFilter:
    """Class to store a single filter used for View Options."""

    def __init__(self, label: str, regex: str, on: bool = True) -> None:
        """Initialize checker filter class.

        Args:
            on: Whether filter is turned on.
        """
        self.label = label
        self.regex = re.compile(regex)
        self.on = on

    def matches(self, entry: CheckerEntry) -> bool:
        """Return whether filter matches given entry."""
        raise NotImplementedError()


class CheckerFilterText(CheckerFilter):
    """Filter based on checker entry text."""

    def matches(self, entry: CheckerEntry) -> bool:
        """Return whether filter matches given entry."""
        return bool(self.regex.fullmatch(entry.text))


class CheckerFilterErrorPrefix(CheckerFilter):
    """Filter based on checker entry error prefix."""

    def matches(self, entry: CheckerEntry) -> bool:
        """Return whether filter matches given entry."""
        return bool(self.regex.fullmatch(entry.error_prefix))


class CheckerViewOptionsDialog(ToplevelDialog):
    """Dialog to allow user to show/hide checker message types."""

    def __init__(
        self,
        checker_dialog: "CheckerDialog",
    ) -> None:
        """Create View Options dialog.

        Args:
            checker_dialog: The checker dialog that this dialog belongs to.
        """
        super().__init__(
            f"{checker_dialog.title()} - View Options", resize_x=False, resize_y=False
        )
        self.checker_dialog = checker_dialog

        self.flags: list[tk.BooleanVar] = []
        self.checkbuttons: list[ttk.Checkbutton] = []
        check_frame = ttk.Frame(self.top_frame)
        check_frame.grid(row=0, column=0)
        max_columns = 3  # Don't want too many columns
        max_rows = 15  # Don't want too many checkbuttons per column
        n_items = len(self.checker_dialog.view_options_filters)
        columns = min(max_columns, math.ceil(n_items / max_rows))
        max_height = math.ceil(n_items / columns)

        def btn_clicked(
            idx: int,
            var: tk.BooleanVar,
            wgt: ttk.Checkbutton,
        ) -> None:
            """Called when filter setting is changed."""
            self.checker_dialog.view_options_filters[idx].on = var.get()
            self.checker_dialog.display_entries()
            wgt.focus()

        for row, option_filter in enumerate(self.checker_dialog.view_options_filters):

            check_var = tk.BooleanVar(value=option_filter.on)

            btn = ttk.Checkbutton(
                check_frame,
                text=f"{option_filter.label} (0)",
                variable=check_var,
            )
            btn["command"] = lambda r=row, v=check_var, b=btn: btn_clicked(r, v, b)
            btn.grid(row=row % max_height, column=row // max_height, sticky="NSW")
            if row == 0:
                btn.focus()
            self.flags.append(check_var)
            self.checkbuttons.append(btn)

        btn_frame = ttk.Frame(self.top_frame)
        btn_frame.grid(row=1, column=0, pady=(5, 0))
        ttk.Button(btn_frame, text="Show All", command=lambda: self.set_all(True)).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(
            btn_frame, text="Hide All", command=lambda: self.set_all(False)
        ).grid(row=0, column=1, padx=5)
        ttk.Checkbutton(
            btn_frame,
            text="Gray out options with no matches",
            command=self.refresh_checkboxes,
            variable=PersistentBoolean(PrefKey.CHECKER_GRAY_UNUSED_OPTIONS),
        ).grid(row=0, column=2, padx=(40, 0))
        self.refresh_checkboxes()

    def set_all(self, value: bool) -> None:
        """Set all the checkbuttons to the given value."""
        for flag in self.flags:
            flag.set(value)
        for row, _ in enumerate(self.checker_dialog.view_options_filters):
            self.checker_dialog.view_options_filters[row].on = value
        self.checker_dialog.display_entries()

    def refresh_checkboxes(self) -> None:
        """Set status of checkboxes based on if any messages of that type, and
        update the (count) at the end of the label."""
        for row, option_filter in enumerate(self.checker_dialog.view_options_filters):
            matches = self.filter_matches(option_filter)
            self.checkbuttons[row]["text"] = re.sub(
                r"\(\d+\)$", f"({matches})", self.checkbuttons[row]["text"]
            )
            self.checkbuttons[row]["state"] = (
                tk.DISABLED
                if preferences.get(PrefKey.CHECKER_GRAY_UNUSED_OPTIONS) and matches == 0
                else tk.NORMAL
            )
            self.flags[row].set(option_filter.on)

    def filter_matches(self, option_filter: CheckerFilter) -> int:
        """Return how many messages match the given filter.

        Args:
            filter: Filter to be checked.

        Returns: Number of matching messages.
        """
        matches = 0
        for entry in self.checker_dialog.entries:
            if option_filter.matches(entry):
                matches += 1
        return matches

    def on_destroy(self) -> None:
        if self.checker_dialog.winfo_exists():
            self.checker_dialog.lift()
            self.checker_dialog.view_options_dialog = None
        super().on_destroy()


class CheckerDialog(ToplevelDialog):
    """Dialog to show results of running a check."""

    # Slight complexity needed.
    # 1. Each type of checker dialog needs its own selection_on_clear flag
    # 2. Flag should be persistent across different instances of dialog, since
    #    some dialogs are deleted & recreated
    # Therefore store as a dict class variable keyed on class name
    selection_on_clear: dict[str, Optional[int]] = {}

    def __init__(
        self,
        title: str,
        rerun_command: Callable[[], None],
        tooltip: str,
        process_command: Optional[Callable[[CheckerEntry], None]] = None,
        sort_key_rowcol: Optional[Callable[[CheckerEntry], tuple]] = None,
        sort_key_alpha: Optional[Callable[[CheckerEntry], tuple]] = None,
        sort_key_custom: Optional[Callable[[CheckerEntry], tuple]] = None,
        sort_custom_label: str = "",
        show_suspects_only: bool = False,
        clear_on_undo_redo: bool = False,
        view_options_dialog_class: Optional[type[CheckerViewOptionsDialog]] = None,
        view_options_filters: Optional[list[CheckerFilter]] = None,
        switch_focus_when_clicked: Optional[bool] = None,
        show_hide_buttons: bool = True,
        show_process_buttons: bool = True,
        show_all_buttons: bool = True,
        match_on_highlight: CheckerMatchType = CheckerMatchType.WHOLE,
        reverse_mark_gravities: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the dialog.

        Args:
            title: Title for dialog.
            rerun_command: Function to call to re-run the check.
            tooltip: Tooltip to show in messages text widget.
            process_command: Function to call to "process" the current error, e.g. swap he/be.
            sort_key_rowcol: Function to sort by row & column.
            sort_key_alpha: Function to sort by alpha/type.
            sort_key_custom: Function to sort by custom values.
            sort_custom_label: Label for custom sort radio button.
            show_suspects_only: True to show "Suspects only" checkbutton.
            clear_on_undo_redo: True to cause dialog to be cleared if Undo/Redo are used.
            view_options_dialog_class: Class to use for a View Options dialog.
            view_options_filters: List of filters to control which messages are shown.
            switch_focus_when_clicked: Whether to switch focus to main window when message is clicked.
                `None` gives default behavior, i.e. False on macOS, True elsewhere.
            show_remove_buttons: Set to False to hide generic Hide/Hide All buttons.
            show_process_buttons: Set to False to hide all generic Fix buttons.
            show_all_buttons: Set to False to hide generic buttons that hide/fix "All".
                Subordinate to `show_remove_buttons` and `show_process_buttons`.
            match_on_highlight: Type of matching for "Fix All", etc.
        """
        super().__init__(title, **kwargs)
        self.top_frame.rowconfigure(0, weight=0)

        # At top of dialog, header Frame to hold "count" label and Re-run button
        count_header_frame = ttk.Frame(
            self.top_frame,
            padding=2,
            borderwidth=1,
            relief=tk.GROOVE,
        )
        count_header_frame.grid(row=0, column=0, sticky="NSEW")
        count_header_frame.rowconfigure(0, weight=1)
        count_header_frame.columnconfigure(2, weight=1)

        self.count_label = ttk.Label(count_header_frame, text="No results")
        self.count_label.grid(row=0, column=0, sticky="NSW")

        self.suspects_only_btn: Optional[ttk.Checkbutton]
        if show_suspects_only:
            # Can't use a PersistentBoolean directly, since we save this value for each checker dialog
            suspects_only_var = tk.BooleanVar(
                self, self.get_dialog_pref(PrefKey.CHECKERDIALOG_SUSPECTS_ONLY_DICT)
            )

            def suspects_only_changed() -> None:
                self.save_dialog_pref(
                    PrefKey.CHECKERDIALOG_SUSPECTS_ONLY_DICT, suspects_only_var.get()
                )
                self.display_entries()

            self.suspects_only_btn = ttk.Checkbutton(
                count_header_frame,
                text="Suspects Only",
                variable=suspects_only_var,
                command=suspects_only_changed,
            )
            self.suspects_only_btn.grid(row=0, column=1, sticky="NSW", padx=(10, 0))
        else:
            self.suspects_only_btn = None

        sort_frame = ttk.Frame(count_header_frame)
        sort_frame.grid(row=0, column=2, sticky="NS", pady=5)
        sort_frame.rowconfigure(0, weight=1)
        for cc in range(0, 2):
            sort_frame.columnconfigure(cc, weight=1)
        ttk.Label(
            sort_frame,
            text="Sort:",
        ).grid(row=0, column=0, sticky="NS", padx=5)

        # Can't use a PersistentString directly, since we save this value for each checker dialog
        sort_type = tk.StringVar(
            self,
            self.get_dialog_pref(PrefKey.CHECKERDIALOG_SORT_TYPE_DICT)
            or CheckerSortType.ROWCOL,
        )

        def sort_type_changed() -> None:
            self.save_dialog_pref(PrefKey.CHECKERDIALOG_SORT_TYPE_DICT, sort_type.get())
            self.display_entries()

        self.rowcol_radio = ttk.Radiobutton(
            sort_frame,
            text="Line & Col",
            command=sort_type_changed,
            variable=sort_type,
            value=CheckerSortType.ROWCOL,
        )
        self.rowcol_radio.grid(row=0, column=1, sticky="NS", padx=2)
        ttk.Radiobutton(
            sort_frame,
            text="Alpha/Type",
            command=sort_type_changed,
            variable=sort_type,
            value=CheckerSortType.ALPHABETIC,
        ).grid(row=0, column=2, sticky="NS", padx=2)
        if sort_custom_label:
            ttk.Radiobutton(
                sort_frame,
                text=sort_custom_label,
                command=sort_type_changed,
                variable=sort_type,
                value=CheckerSortType.CUSTOM,
            ).grid(row=0, column=3, sticky="NS", padx=2)

        def copy_errors() -> None:
            """Copy text messages to clipboard."""
            maintext().clipboard_clear()
            maintext().clipboard_append(self.text.get("1.0", tk.END))

        copy_button = ttk.Button(
            count_header_frame, text="Copy Results", command=copy_errors
        )
        copy_button.grid(row=0, column=3, sticky="NSE")

        def rerunner() -> None:
            Busy.busy()
            self.selection_on_clear[self.get_dlg_name()] = None
            self.rerun_command()
            self.refresh_view_options()

        self.rerun_command = rerun_command
        self.rerun_button = ttk.Button(
            count_header_frame, text="Re-run", command=rerunner
        )
        self.rerun_button.grid(row=0, column=4, sticky="NSE", padx=(10, 0))

        # Next a custom frame with contents determined by the dialog, e.g. Footnote tools
        self.custom_frame = ttk.Frame(
            self.top_frame, padding=2, borderwidth=1, relief=tk.GROOVE
        )
        self.custom_frame.grid(row=1, column=0, sticky="NSEW")

        # Next controls relating to the message list
        self.message_controls_frame = ttk.Frame(
            self.top_frame, padding=2, borderwidth=1, relief=tk.GROOVE
        )
        self.message_controls_frame.grid(row=2, column=0, sticky="NSEW")
        self.message_controls_frame.rowconfigure(0, weight=1)
        for col in range(6):
            self.message_controls_frame.columnconfigure(col, weight=1)

        if match_on_highlight == CheckerMatchType.ALL_MESSAGES:
            all_string = "all listed problems"
        elif match_on_highlight == CheckerMatchType.ERROR_PREFIX:
            all_string = "all with matching type"
        elif match_on_highlight == CheckerMatchType.HIGHLIGHT:
            all_string = "all with matching highlighted portion of message"
        else:
            all_string = "all that exactly match selected message"
        column = 0
        if show_hide_buttons:
            self.rem_btn = ttk.Button(
                self.message_controls_frame,
                text="Hide",
                command=lambda: self.remove_entry_current(all_matching=False),
            )
            self.rem_btn.grid(row=0, column=column, sticky="NSEW")
            ToolTip(self.rem_btn, "Hide selected message (right-click)")
            if show_all_buttons:
                self.remall_btn = ttk.Button(
                    self.message_controls_frame,
                    text="Hide All",
                    command=lambda: self.remove_entry_current(all_matching=True),
                )
                column += 1
                self.remall_btn.grid(row=0, column=column, sticky="NSEW")
                ToolTip(
                    self.remall_btn,
                    f"Hide {all_string} (Shift right-click)",
                )

        self.match_on_highlight = match_on_highlight
        if show_process_buttons:
            if process_command is not None:
                self.fix_btn = ttk.Button(
                    self.message_controls_frame,
                    text="Fix",
                    command=lambda: self.process_entry_current(all_matching=False),
                )
                column += 1
                self.fix_btn.grid(row=0, column=column, sticky="NSEW")
                ToolTip(
                    self.fix_btn,
                    f"Fix selected problem ({cmd_ctrl_string()} left-click)",
                )
                if show_all_buttons:
                    self.fixall_btn = ttk.Button(
                        self.message_controls_frame,
                        text="Fix All",
                        command=lambda: self.process_entry_current(all_matching=True),
                    )
                    column += 1
                    self.fixall_btn.grid(row=0, column=column, sticky="NSEW")
                    ToolTip(
                        self.fixall_btn,
                        f"Fix {all_string} (Shift {cmd_ctrl_string()} left-click)",
                    )
                self.fixrem_btn = ttk.Button(
                    self.message_controls_frame,
                    text="Fix&Hide",
                    command=lambda: self.process_remove_entry_current(
                        all_matching=False
                    ),
                )
                column += 1
                self.fixrem_btn.grid(row=0, column=column, sticky="NSEW")
                ToolTip(
                    self.fixrem_btn,
                    f"Fix selected problem & hide message ({cmd_ctrl_string()} right-click)",
                )
                if show_all_buttons:
                    self.fixremall_btn = ttk.Button(
                        self.message_controls_frame,
                        text="Fix&Hide All",
                        command=lambda: self.process_remove_entry_current(
                            all_matching=True
                        ),
                    )
                    column += 1
                    self.fixremall_btn.grid(row=0, column=column, sticky="NSEW")
                    ToolTip(
                        self.fixremall_btn,
                        f"Fix and hide {all_string} (Shift {cmd_ctrl_string()} right-click)",
                    )

        updown_frame = ttk.Frame(self.message_controls_frame)
        updown_frame.grid(row=0, column=6, sticky="NSE")
        updown_frame.rowconfigure(0, weight=1)
        full_search_btn = ttk.Checkbutton(
            updown_frame,
            text="Full🔎",
            variable=PersistentBoolean(PrefKey.CHECKERDIALOG_FULL_SEARCH),
            command=lambda: self.select_entry_by_arrow(0),
        )
        full_search_btn.grid(row=0, column=0, sticky="NS", padx=5)
        ToolTip(
            full_search_btn,
            "When checked, typing will match against full message text, not just start",
        )
        ttk.Button(
            updown_frame,
            text="⇑",
            width=2,
            command=lambda: self.select_entry_by_arrow(-1),
        ).grid(row=0, column=1, sticky="NS")
        ttk.Button(
            updown_frame,
            text="⇓",
            width=2,
            command=lambda: self.select_entry_by_arrow(1),
        ).grid(row=0, column=2, sticky="NS")

        self.view_options_dialog: Optional[CheckerViewOptionsDialog] = None

        def show_view_options() -> None:
            """Show the view options dialog."""
            assert view_options_dialog_class is not None
            self.view_options_dialog = view_options_dialog_class.show_dialog(
                checker_dialog=self
            )

        self.has_view_options = bool(view_options_dialog_class is not None)
        self.view_options_label = tk.StringVar(self, "")
        self.view_options_crit = tk.StringVar(self, "")
        if self.has_view_options:
            self.view_options_frame = ttk.Frame(self.message_controls_frame)
            self.view_options_frame.grid(row=1, column=0, sticky="NSW", columnspan=8)
            ttk.Button(
                self.view_options_frame,
                text="View Options",
                command=show_view_options,
            ).grid(row=0, column=0, sticky="NS")
            ttk.Button(
                self.view_options_frame,
                text="Prev. Option",
                command=lambda: self.prev_next_view_option(-1),
            ).grid(row=0, column=1, sticky="NS", padx=(10, 0))
            ttk.Button(
                self.view_options_frame,
                text="Next Option",
                command=lambda: self.prev_next_view_option(1),
            ).grid(row=0, column=2, sticky="NS", padx=(0, 10))
            ttk.Label(
                self.view_options_frame, textvariable=self.view_options_label
            ).grid(
                row=0,
                column=3,
                sticky="NS",
            )
            ttk.Label(
                self.view_options_frame,
                textvariable=self.view_options_crit,
                foreground="red",
            ).grid(row=0, column=4, sticky="NS")
        if view_options_filters is None:
            view_options_filters = []
        self.view_options_filters = view_options_filters

        # Next the message list itself
        self.top_frame.rowconfigure(3, weight=1)
        self.text = ScrolledReadOnlyText(
            self.top_frame,
            context_menu=False,
            wrap=tk.NONE,
            font=maintext().font,
        )
        self.text.grid(row=3, column=0, sticky="NSEW")
        ToolTip(self.text, tooltip, use_pointer_pos=True)

        # 3 binary choices:
        #     remove/not_remove (just select) - controlled by button 3 or button 1
        #     process/not_process - controlled by Cmd/Ctrl pressed or not
        #     match/not_match - controlled by Shift pressed or not
        # Only 7 of the 8 possibilities needed, since "select not_process match" makes no sense
        mouse_bind(self.text, "1", self.select_entry_by_click)
        mouse_bind(self.text, "3", self.remove_entry_by_click)
        mouse_bind(
            self.text,
            "Shift+3",
            lambda event: self.remove_entry_by_click(event, all_matching=True),
        )
        mouse_bind(self.text, "Cmd/Ctrl+1", self.process_entry_by_click)
        mouse_bind(
            self.text,
            "Shift+Cmd/Ctrl+1",
            lambda event: self.process_entry_by_click(event, all_matching=True),
        )
        mouse_bind(self.text, "Cmd/Ctrl+3", self.process_remove_entry_by_click)
        mouse_bind(
            self.text,
            "Shift+Cmd/Ctrl+3",
            lambda event: self.process_remove_entry_by_click(event, all_matching=True),
        )
        self.bind("<Up>", lambda _e: self.select_entry_by_arrow(-1))
        self.bind("<Down>", lambda _e: self.select_entry_by_arrow(1))

        self.text.bind("<Home>", lambda _e: self.select_entry_by_index(0))
        self.text.bind("<Shift-Home>", lambda _e: self.select_entry_by_index(0))
        self.text.bind(
            "<End>", lambda _e: self.select_entry_by_index(len(self.entries) - 1)
        )
        self.text.bind(
            "<Shift-End>", lambda _e: self.select_entry_by_index(len(self.entries) - 1)
        )
        # Bind same keys as main window uses for top/bottom on Mac.
        # Above bindings work already for Windows
        if is_mac():
            self.text.bind("<Command-Up>", lambda _e: self.select_entry_by_index(0))
            self.text.bind(
                "<Shift-Command-Up>", lambda _e: self.select_entry_by_index(0)
            )
            self.text.bind(
                "<Command-Down>",
                lambda _e: self.select_entry_by_index(len(self.entries) - 1),
            )
            self.text.bind(
                "<Shift-Command-Down>",
                lambda _e: self.select_entry_by_index(len(self.entries) - 1),
            )

        # Bind keystrokes to search function
        self.text.bind("<Key>", self.select_entry_by_letters)
        self.search_buffer = ""
        self.reset_timer_id = ""

        self.process_command = process_command
        self.rowcol_key = sort_key_rowcol or CheckerDialog.sort_key_rowcol
        self.alpha_key = sort_key_alpha or CheckerDialog.sort_key_alpha
        self.custom_key = sort_key_custom or CheckerDialog.sort_key_custom

        def do_clear_on_undo_redo() -> None:
            """If undo/redo operation should trigger user to Re-run tool, clear dialog."""
            self.selection_on_clear[self.get_dlg_name()] = self.current_entry_index()
            self.reset()
            self.text.insert(tk.END, REFRESH_MESSAGE)
            self.update_count_label()

        # Ensure this class has an entry in `selection_on_clear`
        # Only if not there already, because we don't want to overwrite it
        # if this is a new instance of a previously existing dialog, with the old
        # one destroyed and this one created due to a refresh/re-run.
        if self.get_dlg_name() not in self.selection_on_clear:
            self.selection_on_clear[self.get_dlg_name()] = None
        # If this dialog should be cleared on undo/redo, add callback to maintext
        if clear_on_undo_redo:
            maintext().add_undo_redo_callback(
                self.get_dlg_name(), do_clear_on_undo_redo
            )

        if switch_focus_when_clicked is None:
            switch_focus_when_clicked = False
        self.switch_focus_when_clicked = switch_focus_when_clicked

        self.count_linked_entries = 0  # Not the same as len(self.entries)
        self.count_suspects = 0
        self.section_count = 0
        self.selected_text = ""
        self.selected_text_range: Optional[IndexRange] = None
        self.reverse_mark_gravities = reverse_mark_gravities
        self.reset()

    def __new__(cls, *args: Any, **kwargs: Any) -> "CheckerDialog":
        """Ensure CheckerDialogs are not instantiated directly."""
        if cls is CheckerDialog:
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
            args: Optional args to pass to dialog constructor.
            kwargs: Optional kwargs to pass to dialog constructor.
        """
        Busy.busy()
        return super().show_dialog(**kwargs)

    @classmethod
    def sort_key_rowcol(
        cls,
        entry: CheckerEntry,
    ) -> tuple[int, int, int]:
        """Default sort key function to sort entries by row/col.

        Preserve entries in sections.
        If header/footer, then preserve original order
        If no row/col, place content lines before those with row/col
        If row/col, sort by row, then col.
        """
        if entry.entry_type == CheckerEntryType.HEADER:
            return (entry.section, entry.initial_pos, 0)
        if entry.entry_type == CheckerEntryType.FOOTER:
            return (entry.section, entry.initial_pos, 0)

        # Content without row/col comes before content with, and preserves its original order
        if entry.text_range is None:
            return (entry.section, 0, entry.initial_pos)
        # Content with row/col is ordered by row, then col
        return (
            entry.section,
            entry.text_range.start.row,
            entry.text_range.start.col,
        )

    @classmethod
    def sort_key_alpha(
        cls,
        entry: CheckerEntry,
    ) -> tuple[int, str, str, int, int]:
        """Default sort key function to sort entries by error_prefix & text,
        putting identical upper and lower case versions together.

        If text is highlighted, use that, otherwise use whole line of text
        Preserve entries in sections.
        If header/footer, then preserve original order, putting header first & footer last.
        Place text with no row/col before identical text with row/col.
        """
        # Force header before content, and footer after content (though should be
        # unnecessary since in different sections) preserving original order
        if entry.entry_type == CheckerEntryType.HEADER:
            return (
                entry.section,
                "",
                "",
                0,
                entry.initial_pos,
            )
        if entry.entry_type == CheckerEntryType.FOOTER:
            return (
                entry.section,
                "\ufeff",
                "\ufeff",
                0,
                entry.initial_pos,
            )

        # Get text for comparison
        if entry.hilite_start is None:
            text = entry.error_prefix + entry.text
        else:
            text = (
                entry.error_prefix + entry.text[entry.hilite_start : entry.hilite_end]
            )
        text_low = text.lower()

        # Content without row/col comes before identical content with row/col
        if entry.text_range is None:
            return (entry.section, text_low, text, 0, 0)
        return (
            entry.section,
            text_low,
            text,
            entry.text_range.start.row,
            entry.text_range.start.col,
        )

    @classmethod
    def sort_key_custom(
        cls,
        entry: CheckerEntry,
    ) -> tuple[int, Any, str, str, int, int]:
        """Default sort key function to sort entries by custom data, then same as
        sort_key_alpha."""
        (sec, low, txt, row, col) = CheckerDialog.sort_key_alpha(entry)
        return (sec, entry.custom_data, low, txt, row, col)

    @classmethod
    def checker_orphan_wrapper(
        cls, method_name: str, *args: Any, **kwargs: Any
    ) -> Callable:
        """Return a wrapper to simplify calls to add_button_orphan.

        Args:
            method_name: Name of method to be called when command is executed.
            args: Positional args for `method_name` method.
            kwargs: Named args for `method_name` method.
        """

        def wrapper() -> None:
            """Get focused CheckerDialog and run method on that."""
            focus = root().focus_get()
            if focus is None:
                return
            tl_widget = focus.winfo_toplevel()
            if isinstance(tl_widget, CheckerDialog):
                getattr(tl_widget, method_name)(*args, **kwargs)

        return wrapper

    @classmethod
    def checker_button_orphan_wrapper(
        cls, button_name: str, method_name: str, *args: Any, **kwargs: Any
    ) -> Callable:
        """Return a wrapper to simplify calls to add_button_orphan.

        Args:
            method_name: Name of method to be called when command is executed.
            args: Positional args for `method_name` method.
            kwargs: Named args for `method_name` method.
        """

        def wrapper() -> None:
            """Get focused CheckerDialog and if given button name exists,
            run given method on the dialog."""
            focus = root().focus_get()
            if focus is None:
                return
            tl_widget = focus.winfo_toplevel()
            if isinstance(tl_widget, CheckerDialog):
                # If button doesn't exist, do nothing and return
                try:
                    getattr(tl_widget, button_name)
                except AttributeError:
                    return
                # Button does exist, so run the method
                getattr(tl_widget, method_name)(*args, **kwargs)

        return wrapper

    @classmethod
    def add_checker_orphan_commands(cls) -> None:
        """Add orphan commands to command palette."""
        menubar_metadata().add_button_orphan(
            "Checker, Select Next Message",
            cls.checker_orphan_wrapper("select_entry_by_arrow", 1),
        )
        menubar_metadata().add_button_orphan(
            "Checker, Select Previous Message",
            cls.checker_orphan_wrapper("select_entry_by_arrow", -1),
        )
        menubar_metadata().add_button_orphan(
            "Checker, Hide",
            cls.checker_button_orphan_wrapper(
                "rem_btn", "remove_entry_current", all_matching=False
            ),
        )
        menubar_metadata().add_button_orphan(
            "Checker, Hide All",
            cls.checker_button_orphan_wrapper(
                "remall_btn", "remove_entry_current", all_matching=True
            ),
        )
        menubar_metadata().add_button_orphan(
            "Checker, Fix",
            cls.checker_button_orphan_wrapper(
                "fix_btn", "process_entry_current", all_matching=False
            ),
        )
        menubar_metadata().add_button_orphan(
            "Checker, Fix All",
            cls.checker_button_orphan_wrapper(
                "fixall_btn", "process_entry_current", all_matching=True
            ),
        )
        menubar_metadata().add_button_orphan(
            "Checker, Fix & Hide",
            cls.checker_button_orphan_wrapper(
                "fixrem_btn", "process_remove_entry_current", all_matching=False
            ),
        )
        menubar_metadata().add_button_orphan(
            "Checker, Fix & Hide All",
            cls.checker_button_orphan_wrapper(
                "fixremall_btn", "process_remove_entry_current", all_matching=True
            ),
        )

    def reset(self) -> None:
        """Reset dialog and associated structures & marks."""
        super().reset()
        self.entries: list[CheckerEntry] = []
        self.count_linked_entries = 0
        self.count_suspects = 0
        self.section_count = 0
        self.selected_text = ""
        self.selected_text_range = None
        self.update_count_label(working=True)
        if self.text.winfo_exists():
            self.text.delete("1.0", tk.END)
            self.update()
        if maintext().winfo_exists():
            maintext().clear_marks(self.get_dlg_name())
            maintext().remove_spotlights()

    def select_entry_after_undo_redo(self) -> None:
        """Select the saved entry, if any, after a re-run following undo/redo."""
        entry_index = self.selection_on_clear[self.get_dlg_name()]
        if entry_index is not None:
            self.select_entry_by_index(entry_index)

    def on_destroy(self) -> None:
        """Override method that tidies up when the dialog is destroyed.

        Needs to remove the undo_redo callback if there is one.
        Also the View Options dialog if it is popped.
        """
        super().on_destroy()
        maintext().remove_undo_redo_callback(self.get_dlg_name())
        if (
            self.view_options_dialog is not None
            and self.view_options_dialog.winfo_exists()
        ):
            self.view_options_dialog.destroy()
            self.view_options_dialog = None

    def refresh_view_options(self) -> None:
        """Update view options dialog if it's visible."""
        if (
            self.view_options_dialog is not None
            and self.view_options_dialog.winfo_exists()
        ):
            self.view_options_dialog.refresh_checkboxes()

    def update_view_options_label(self) -> None:
        """Update label showing which View Options are active."""
        if not self.has_view_options:
            return

        n_filters = len(self.view_options_filters)
        count_on, on_index = self.get_view_options_count_index()
        if count_on == 1:
            crit = re.sub("[ :]*$", "", self.view_options_filters[on_index].label)
            self.view_options_label.set(
                f"Option {on_index + 1} enabled (of {n_filters}): "
            )
            self.view_options_crit.set(crit)
        else:
            self.view_options_label.set(f"{count_on} (of {n_filters}) options enabled")
            self.view_options_crit.set("")

    def prev_next_view_option(self, direction: int) -> None:
        """Select the previous/next view option.

        Args:
            direction: -1 for prev; +1 for next."""
        n_filters = len(self.view_options_filters)
        count_on, on_index = self.get_view_options_count_index()

        def n_matches(option_filter: CheckerFilter) -> int:
            """Return how many matches for filter there are in the list."""
            return sum(1 for entry in self.entries if option_filter.matches(entry))

        # If not just one selected, pretend the first/last is selected for prev/next
        if count_on != 1:
            on_index = 0 if direction < 0 else n_filters - 1
        gray_unused = preferences.get(PrefKey.CHECKER_GRAY_UNUSED_OPTIONS)
        for n in range(0, n_filters):
            # Loop round once in given direction from starting point
            idx = (on_index + (n + 1) * direction + n_filters) % n_filters
            # If "gray unused" is checked then we haven't found the one we want
            # to progress to, unless it has matching messages
            if not gray_unused or n_matches(self.view_options_filters[idx]) > 0:
                on_index = idx
                break
        else:
            # Didn't find any matching messages, so just select first/last for next/prev
            on_index = 0 if direction > 0 else n_filters - 1

        for option_filter in self.view_options_filters:
            option_filter.on = False
        self.view_options_filters[on_index].on = True
        self.display_entries()
        self.refresh_view_options()

    def get_view_options_count_index(self) -> tuple[int, int]:
        """Count how many are on, and the index of the only one if there is one."""
        count_on = 0
        on_index = -1
        for i, f in enumerate(self.view_options_filters):
            if f.on:
                count_on += 1
                on_index = i
        return count_on, on_index

    def new_section(self) -> None:
        """Start a new section in the dialog.

        When entries are sorted, entries within a section remain in the section.
        It's not a problem if a section is empty.
        """
        self.section_count += 1

    def _add_headfoot(self, hf_type: CheckerEntryType, *headfoot_lines: str) -> None:
        """Internal method to add header or footer to dialog.

        Args:
            hf_type: Either header or footer type
            headfoot_lines: Section header or footer lines
        """
        assert hf_type in (CheckerEntryType.HEADER, CheckerEntryType.FOOTER)
        self.new_section()
        for line in headfoot_lines:
            self.add_entry(line, None, None, None, hf_type)
        self.new_section()

    def add_header(self, *header_lines: str) -> None:
        """Add header to dialog.

        Args:
            header_lines: Strings to add as header lines
        """
        self._add_headfoot(CheckerEntryType.HEADER, *header_lines)

    def add_footer(self, *footer_lines: str) -> None:
        """Add footer to dialog.

        Args:
            footer_lines: Strings to add as footer lines
        """
        self._add_headfoot(CheckerEntryType.FOOTER, *footer_lines)

    def add_entry(
        self,
        msg: str,
        text_range: Optional[IndexRange] = None,
        hilite_start: Optional[int] = None,
        hilite_end: Optional[int] = None,
        entry_type: CheckerEntryType = CheckerEntryType.CONTENT,
        error_prefix: str = "",
        ep_index: int = 0,
        severity: Optional[CheckerEntrySeverity] = None,
    ) -> None:
        """Add an entry ready to be displayed in the dialog.

        Also set marks in main text at locations of start & end of point of interest.
        Use this for content; use add_header & add_footer for headers & footers.

        Args:
            msg: Entry to be displayed - newline characters are replaced with "⏎".
            text_range: Optional start & end of point of interest in main text widget.
            hilite_start: Optional column to begin higlighting entry in dialog.
            hilite_end: Optional column to end higlighting entry in dialog.
            entry_type: Defaults to content.
            error_prefix: Prefix string indicating an error.
            ep_index: Error prefix index (to control color) - must be 0 or 1
            severity: Optional severity of error to override default determination.
        """
        assert ep_index in (0, 1)
        # Default determination of severity
        if severity is None:
            if text_range is None:
                severity = CheckerEntrySeverity.OTHER
            elif error_prefix:
                severity = CheckerEntrySeverity.ERROR
            else:
                severity = CheckerEntrySeverity.INFO

        line = re.sub("\n", "⏎", msg)
        entry = CheckerEntry(
            line,
            text_range,
            hilite_start,
            hilite_end,
            self.section_count,
            len(self.entries),
            entry_type,
            error_prefix,
            ep_index,
            severity,
        )
        self.entries.append(entry)

        if text_range is not None:
            maintext().set_mark_position(
                self.mark_from_rowcol(text_range.start),
                text_range.start,
                gravity=tk.RIGHT if self.reverse_mark_gravities else tk.LEFT,
            )
            maintext().set_mark_position(
                self.mark_from_rowcol(text_range.end),
                text_range.end,
                gravity=tk.LEFT if self.reverse_mark_gravities else tk.RIGHT,
            )

    def display_entries(
        self, auto_select_line: bool = True, complete_msg: bool = True
    ) -> None:
        """Display all the stored entries in the dialog according to
        the sort setting.

        Args:
            auto_select_line: Default True. Set to False if calling routine takes
            responsibility for selecting a line in the dialog.
            complete_msg: Set to False if "Check complete" message not wanted.
        """

        Busy.busy()
        try:
            self.do_display_entries(auto_select_line, complete_msg)
        except tk.TclError:
            logger.debug("Tcl error: Dialog closed while tool was running?")
        Busy.unbusy()

    def do_display_entries(
        self, auto_select_line: bool = True, complete_msg: bool = True
    ) -> None:
        """Display all the stored entries in the dialog according to
        the sort setting.

        Args:
            auto_select_line: Default True. Set to False if calling routine takes
            responsibility for selecting a line in the dialog.
            complete_msg: Set to False if "Check complete" message not wanted.
        """

        sort_key: Callable[[CheckerEntry], tuple]
        sort_type = self.get_dialog_pref(PrefKey.CHECKERDIALOG_SORT_TYPE_DICT)
        if sort_type == CheckerSortType.ALPHABETIC:
            sort_key = self.alpha_key
        elif sort_type == CheckerSortType.CUSTOM:
            sort_key = self.custom_key
        else:  # Default to ROWCOL (None if dialog has never changed its sort setting)
            sort_key = self.rowcol_key
        self.entries.sort(key=sort_key)
        self.text.delete("1.0", tk.END)
        self.count_linked_entries = 0
        self.count_suspects = 0

        # Find longest line & col strings to aid formatting
        maxrow = 0
        maxcol = 0
        for entry in self.entries:
            if self.skip_entry(entry):
                continue
            if entry.text_range is not None:
                maxrow = max(maxrow, entry.text_range.start.row)
                maxcol = max(maxcol, entry.text_range.start.col)
        maxrowlen = len(str(maxrow))
        maxcollen = len(str(maxcol)) + 2  # Always colon & at least 1 space after col

        # If exactly one View Option enabled, hide error prefix,
        # since it will be displayed in the View Options label, if View Options frame visible
        hide_ep = (
            self.get_view_options_count_index()[0] == 1
            and self.view_options_frame.winfo_ismapped()
        )

        for entry in self.entries:
            if self.skip_entry(entry):
                continue
            rowcol_str = ""
            if entry.severity >= CheckerEntrySeverity.INFO:
                self.count_linked_entries += 1
            if entry.severity >= CheckerEntrySeverity.ERROR:
                self.count_suspects += 1
            if entry.text_range is not None:
                colstr = f"{entry.text_range.start.col}:"
                rowcol_str = (
                    f"{entry.text_range.start.row:>{maxrowlen}}.{colstr:<{maxcollen}}"
                )
            ep = "" if hide_ep else entry.error_prefix
            self.text.insert(tk.END, rowcol_str + ep + entry.text + "\n")
            if entry.hilite_start is not None and entry.hilite_end is not None:
                start_rowcol = IndexRowCol(self.text.index(tk.END + "-2line"))
                start_rowcol.col = entry.hilite_start + len(rowcol_str) + len(ep)
                end_rowcol = IndexRowCol(
                    start_rowcol.row,
                    entry.hilite_end + len(rowcol_str) + len(ep),
                )
                self.text.tag_add(
                    HighlightTag.CHECKER_HIGHLIGHT,
                    start_rowcol.index(),
                    end_rowcol.index(),
                )
            if ep:
                start_rowcol = IndexRowCol(self.text.index(tk.END + "-2line"))
                start_rowcol.col = len(rowcol_str)
                end_rowcol = IndexRowCol(start_rowcol.row, len(rowcol_str) + len(ep))
                self.text.tag_add(
                    entry.error_prefix_tag(),
                    start_rowcol.index(),
                    end_rowcol.index(),
                )
        # Output "Check complete", so user knows it's done
        if complete_msg:
            self.text.insert(tk.END, "\nCheck complete\n")

        # The default automatic highlighting of previously selected line, or if none
        # the first suitable line, is undesirable when an application immediately
        # selects a different line after displaying the entries. Highlighting will
        # 'jump' before it settles on the newly selected line.
        #
        # To avoid this, an application can disable the default automatic highlighting
        # and handle the selection and highlighting itself; e.g. illo_sn_fixup.py.
        if auto_select_line:
            # Highlight previously selected line, or if none, the first suitable line
            selection_made = False
            if self.selected_text:
                for index, entry in enumerate(self.entries):
                    if (
                        entry.text == self.selected_text
                        and entry.text_range == self.selected_text_range
                        and not self.skip_entry(entry)
                    ):
                        self.select_entry_by_index(index)
                        selection_made = True
                        break
            if not selection_made:
                for index, entry in enumerate(self.entries):
                    if self.skip_entry(entry):
                        continue
                    if entry.text_range:
                        self.select_entry_by_index(index)
                        break
        self.update_count_label()
        self.update_view_options_label()

    def showing_suspects_only(self) -> bool:
        """Return whether dialog is showing Suspects Only.

        Returns: True if there's a Suspects Only button that is switched on.
        """
        return self.suspects_only_btn is not None and self.get_dialog_pref(
            PrefKey.CHECKERDIALOG_SUSPECTS_ONLY_DICT
        )

    def skip_entry(self, entry: CheckerEntry) -> bool:
        """Return whether to skip an entry either due to Suspects Only,
        or due to View Options.

        Args:
            entry: Entry to be checked.

        Returns: True if showing Suspects Only but the entry isn't a suspect,
                 or if entry is hidden by View Options settings.
        """
        return (
            self.showing_suspects_only()
            and entry.severity < CheckerEntrySeverity.ERROR
            or self.hide_entry(entry)
        )

    def hide_entry(self, entry: CheckerEntry) -> bool:
        """Return whether to hide entry based upon View Options.

        Args:
            entry: Entry to be checked.

        Returns: True if entry is hidden by View Options settings.
        """
        for view_option_filter in self.view_options_filters:
            if not view_option_filter.on and view_option_filter.matches(entry):
                return True
        return False

    def update_count_label(self, working: bool = False) -> None:
        """Update the label showing how many linked entries & suspects are in dialog.

        Args:
            working: If set to True, display a "Working..." label instead.
        """
        if self.count_label.winfo_exists():
            if working:
                self.count_label["text"] = "Working..."
                self.count_label.update()
                return
            es = sing_plur(self.count_linked_entries, "Entry", "Entries")
            ss = sing_plur(self.count_suspects, "Suspect")
            s_label = f" ({ss})" if self.count_suspects > 0 else ""
            if self.count_suspects == self.count_linked_entries > 0 or (
                self.count_suspects == 0
                and self.get_dialog_pref(PrefKey.CHECKERDIALOG_SUSPECTS_ONLY_DICT)
            ):
                self.count_label["text"] = ss
            else:
                self.count_label["text"] = f"{es}{s_label}"

    def select_entry_by_arrow(self, increment: int) -> None:
        """Select next/previous line in dialog, and jump to the line in the
        main text widget that corresponds to it.

        Args:
            increment: +1 to move to next line, -1 to move to previous line.
        """
        line_num = self.text.get_select_line_num()
        if line_num is None:
            return
        try:
            entry_index = self.entry_index_from_linenum(line_num + increment)
        except IndexError:
            return
        self.select_entry_by_index(entry_index, focus=False)

    def select_entry_by_click(self, event: tk.Event) -> str:
        """Select clicked line in dialog, and jump to the line in the
        main text widget that corresponds to it.

        Args:
            event: Event object containing mouse click position.

        Returns:
            "break" to avoid calling other callbacks.
        """
        try:
            entry_index = self.entry_index_from_click(event)
        except IndexError:
            return "break"
        self.select_entry_by_index(entry_index)
        return "break"

    def select_entry_by_letters(self, event: tk.Event) -> str:
        """Go to first occurrence of word beginning with typed character(s).

        Args:
            event: Event containing keystroke.

        Returns:
            "break" to stop further processing of events if valid character
        """
        if not event.char or not event.char.isprintable():
            return ""
        # If modifiers other than Shift, Caps Lock, Num Lock, ScrollLock don't goto word - allow default processing
        if int(event.state) & ~(0x0001 | 0x0002 | 0x0010 | 0x0080 | 0x0100) != 0:
            return ""
        low_char = event.char.lower()

        def reset_buffer() -> None:
            """Reset the search buffer and the reset timer"""
            self.reset_timer_id = ""
            self.search_buffer = ""

        # If timer running, cancel it - new one is started below
        if self.reset_timer_id:
            self.after_cancel(self.reset_timer_id)
            self.reset_timer_id = ""

        # If user doesn't press another key within 1 second, reset the search buffer
        self.reset_timer_id = self.after(1000, reset_buffer)

        n_entries = len(self.entries)
        self.search_buffer += low_char
        full_search = preferences.get(PrefKey.CHECKERDIALOG_FULL_SEARCH)
        # If nothing selected, pretend last item was selected
        selected = self.current_entry_index() or n_entries - 1
        # If first keypress, start from next entry, so we don't re-find selected one
        if len(self.search_buffer) == 1:
            selected = selected + 1
        # Search from selected to end of list & wrap to beginning
        for loop in range(n_entries):
            idx = (selected + loop) % n_entries
            entry = self.entries[idx]
            if self.skip_entry(entry):
                continue
            low_text = entry.text.lower()
            if full_search:
                found = self.search_buffer in low_text
            else:
                found = low_text.startswith(self.search_buffer)
            if found:
                self.select_entry_by_index(idx, focus=False)
                return "break"
        return ""

    def process_entry_by_click(
        self, event: tk.Event, all_matching: bool = False
    ) -> str:
        """Select clicked line in dialog, and jump to the line in the
        main text widget that corresponds to it. Finally call the
        "process" callback function, if any.

        Args:
            event: Event object containing mouse click position.

        Returns:
            "break" to avoid calling other callbacks.
        """
        try:
            entry_index = self.entry_index_from_click(event)
        except IndexError:
            return "break"
        self.select_entry_by_index(entry_index)
        self.process_entry_current(all_matching=all_matching)
        return "break"

    def remove_entry_by_click(self, event: tk.Event, all_matching: bool = False) -> str:
        """Remove the entry that was clicked in the dialog.

        Args:
            event: Event object containing mouse click position.
            all_matching: If True remove all other entries that have the same
                message as the chosen entry (e.g. same spelling error)

        Returns:
            "break" to avoid calling other callbacks.
        """
        try:
            entry_index = self.entry_index_from_click(event)
        except IndexError:
            return "break"
        self.select_entry_by_index(entry_index)
        self.remove_entry_current(all_matching=all_matching)
        return "break"

    def process_remove_entry_by_click(
        self, event: tk.Event, all_matching: bool = False
    ) -> str:
        """Select clicked line in dialog, and jump to the line in the
        main text widget that corresponds to it. Call the
        "process" callback function, if any, then remove the entry.

        Args:
            event: Event object containing mouse click position.
            all_matching: If True remove all other entries that have the same
                message as the chosen entry (e.g. same spelling error)

        Returns:
            "break" to avoid calling other callbacks.
        """
        try:
            entry_index = self.entry_index_from_click(event)
        except IndexError:
            return "break"
        self.select_entry_by_index(entry_index)
        self.process_remove_entry_current(all_matching=all_matching)
        return "break"

    def entry_index_from_click(self, event: tk.Event) -> int:
        """Get the index into the list of entries based on the mouse position
        in the click event.

        Args:
            event: Event object containing mouse click position.

        Returns:
            Index into self.entries list
            Raises IndexError exception if out of range
        """
        linenum = self.linenum_from_click(event)

        # Convenient place to intercept mouse click and see if user
        # was actually requesting a refresh
        if linenum == 1 and self.text.get("1.0", "1.end") == REFRESH_MESSAGE:
            self.rerun_command()
            self.selection_on_clear[self.get_dlg_name()] = None
            raise IndexError  # No valid index selected

        return self.entry_index_from_linenum(linenum)

    def linenum_from_click(self, event: tk.Event) -> int:
        """Get the line number based on the mouse position in the click event.

        Args:
            event: Event object containing mouse click position.

        Returns:
            Line number that was clicked in the list of entries
        """
        return IndexRowCol(self.text.index(f"@{event.x},{event.y}")).row

    def entry_index_from_linenum(self, linenum: int) -> int:
        """Get the index into the entries array from a line number in the list,
        taking into account "Suspects Only" setting.

        Args:
            linenum: Line number in the list of entries.

        Returns:
            Index into entries array.
            Raises IndexError exception if out of range.
        """
        count = 0
        for index, entry in enumerate(self.entries):
            if self.skip_entry(entry):
                continue
            count += 1
            if linenum == count:
                return index
        raise IndexError

    def linenum_from_entry_index(self, entry_index: int) -> int:
        """Get the line number in the list, from the entry_index,
        taking into account "Suspects Only" setting.

        Args:
            entry_index: Index into entries array.

        Returns:
            Line number in the list of entries, or 0 if not in range.
        """
        linenum = 0
        for index, entry in enumerate(self.entries):
            if self.skip_entry(entry):
                continue
            linenum += 1
            if index == entry_index:
                return linenum
        return 0

    def process_remove_entries(
        self, process: bool, remove: bool, all_matching: bool
    ) -> None:
        """Process and/or remove the current entry, if any.

        Args:
            process: If True, process the current entry.
            remove: If True, remove the current entry.
            all_matching: If True, repeat for all entries that have the same
                message as the current entry (e.g. same spelling error).
        """
        Busy.busy()
        maintext().undo_block_begin()
        entry_index = self.current_entry_index()
        if entry_index is None:
            Busy.unbusy()
            return
        linenum = self.text.get_select_line_num()
        # If doing Fix All with an "ALL_MESSAGES" match, it's OK to not have a selection
        if (
            self.match_on_highlight == CheckerMatchType.ALL_MESSAGES
            and all_matching
            and not linenum
        ):
            linenum = self.linenum_from_entry_index(0)
        if not linenum:
            Busy.unbusy()
            return
        # Mark before starting so location can be selected later
        self.text.mark_set(MARK_ENTRY_TO_SELECT, f"{linenum}.0")
        match_text = self.get_match_text(
            self.entries[entry_index], self.match_on_highlight
        )
        if all_matching:
            # Work in reverse since may be deleting from list while iterating
            indices = range(len(self.entries) - 1, -1, -1)
        else:
            indices = range(entry_index, entry_index + 1)
        match_indices = [
            ii
            for ii in indices
            if self.get_match_text(self.entries[ii], self.match_on_highlight)
            == match_text
        ]
        count = len(match_indices)
        # Set up bool to hold whether processing is actually taking place
        # A user might Cmd/Ctrl click an entry even when there is no process_command
        # in which case process would be True, but we want process_bool to be False
        process_bool = bool(process and self.process_command)
        process_remove = (
            "process & remove"
            if process_bool and remove
            else "process" if process_bool else "remove"
        )
        if count <= 1000 or messagebox.askyesno(
            title="Bulk processing",
            message=f"This will {process_remove} {count} dialog entries and may take more than a few seconds to complete.",
            detail="Are you sure you want to continue?",
            default=messagebox.NO,
            icon=messagebox.WARNING,
        ):
            for ii in match_indices:
                if process_bool:
                    assert self.process_command is not None
                    self.process_command(self.entries[ii])
                if remove:
                    if self.entries[ii].severity >= CheckerEntrySeverity.INFO:
                        self.count_linked_entries -= 1
                    if self.entries[ii].severity >= CheckerEntrySeverity.ERROR:
                        self.count_suspects -= 1
                    linenum = self.linenum_from_entry_index(ii)
                    self.text.delete(f"{linenum}.0", f"{linenum + 1}.0")
                    del self.entries[ii]
        self.report_fix_removes(process_bool, remove, count)
        self.update_count_label()
        self.refresh_view_options()
        # Select line that is now where the first processed/removed line was
        entry_rowcol = IndexRowCol(self.text.index(MARK_ENTRY_TO_SELECT))
        last_row = IndexRowCol(self.text.index(tk.END)).row - 1
        if last_row > 0:
            try:
                entry_index = self.entry_index_from_linenum(
                    min(entry_rowcol.row, last_row)
                )
            except IndexError:
                Busy.unbusy()
                return
            self.select_entry_by_index(entry_index)
        Busy.unbusy()

    def report_fix_removes(self, process: bool, remove: bool, num: int) -> None:
        """Report how many removals and fixes were made."""
        if process and remove:
            op = "Fixed and hid"
        elif process:
            op = "Fixed"
        elif remove:
            op = "Hid"
        else:
            return
        logger.info(f"{op} {sing_plur(num, 'entry', 'entries')}")

    def process_entry_current(self, all_matching: bool = False) -> None:
        """Call the "process" callback function, if any, on the
        currently selected entry, if any.

        Args:
            all_matching: If True process all other entries that have the same
                message as the chosen entry
        """
        self.process_remove_entries(
            process=True, remove=False, all_matching=all_matching
        )

    def remove_entry_current(self, all_matching: bool = False) -> None:
        """Remove the current entry, if any.

        Args:
            all_matching: If True remove all other entries that have the same
                message as the chosen entry
        """
        self.process_remove_entries(
            process=False, remove=True, all_matching=all_matching
        )

    def process_remove_entry_current(self, all_matching: bool = False) -> None:
        """Call the "process" callback function, if any, for the current entry, if any,
        then remove the entry.

        Args:
            all_matching: If True process & remove all other entries that have the same
                message as the chosen entry
        """
        self.process_remove_entries(
            process=True, remove=True, all_matching=all_matching
        )

    def current_entry_index(self) -> Optional[int]:
        """Get the index entry of the currently selected error message.

        Returns:
            Index into self.entries array, or None if no message selected.
        """
        line_num = self.text.get_select_line_num()
        return None if line_num is None else self.entry_index_from_linenum(line_num)

    def select_entry_by_index(self, entry_index: int, focus: bool = True) -> None:
        """Select line in dialog corresponding to given entry index,
        and jump to the line in the main text widget that corresponds to it.

        Args:
            entry_index: Index of chosen entry.
            focus: Whether to switch focus to text window.
        """
        if not self.text.winfo_exists():
            return
        linenum = self.linenum_from_entry_index(entry_index)
        self.text.select_line(linenum)
        self.text.mark_set(tk.INSERT, f"{linenum}.0")
        self.text.focus_set()
        self.text.tag_remove("sel", "1.0", tk.END)
        try:
            entry = self.entries[entry_index]
        except IndexError:
            self.lift()
            return  # OK if index is no longer valid
        self.selected_text = entry.text
        self.selected_text_range = entry.text_range
        maintext().remove_spotlights()
        if entry.text_range is not None:
            if root().state() == "iconic":
                root().deiconify()
            start = maintext().index(self.mark_from_rowcol(entry.text_range.start))
            end = maintext().index(self.mark_from_rowcol(entry.text_range.end))
            maintext().spotlight_range(IndexRange(start, end))
            maintext().clear_selection()
        self.lift()
        if (
            self.view_options_dialog is not None
            and self.view_options_dialog.winfo_exists()
        ):
            self.view_options_dialog.lift()
        self.set_insert_from_entry(entry_index, focus)

    def set_insert_from_entry(self, entry_index: int, focus: bool) -> None:
        """Set insert position in text window based on selected entry."""
        entry = self.entries[entry_index]
        if entry.text_range is None:
            return
        start = maintext().index(self.mark_from_rowcol(entry.text_range.start))
        end = maintext().index(self.mark_from_rowcol(entry.text_range.end))
        if entry.text_range is not None:
            maintext().set_insert_index(
                IndexRowCol(start),
                focus=(focus and self.switch_focus_when_clicked),
                see_end_rowcol=IndexRowCol(end),
            )

    @classmethod
    def mark_from_rowcol(cls, rowcol: IndexRowCol) -> str:
        """Return name to use to mark given location in text file.

        Args:
            rowcol: Location in text file to be marked.

        Returns:
            Name for mark, e.g. "Checker123.45"
        """
        return f"{cls.get_dlg_name()}{rowcol.index()}"

    def get_match_text(
        self, entry: CheckerEntry, match_on_highlight: CheckerMatchType
    ) -> str:
        """Return portion of message text for matching.

        Args:
            match_on_highlight: Match type.

        Returns:
            Portion of message to match with
        """
        if match_on_highlight == CheckerMatchType.ALL_MESSAGES:
            return "Match all"
        if match_on_highlight == CheckerMatchType.ERROR_PREFIX:
            return entry.error_prefix
        if (
            match_on_highlight == CheckerMatchType.HIGHLIGHT
            and entry.hilite_start is not None
            and entry.hilite_end is not None
        ):
            return entry.text[entry.hilite_start : entry.hilite_end]
        return entry.text
