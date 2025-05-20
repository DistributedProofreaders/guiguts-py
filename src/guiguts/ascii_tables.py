"""ASCII table special effects functionality."""

import logging
from enum import StrEnum, auto
from textwrap import TextWrapper
import tkinter as tk
from tkinter import ttk
import regex as re

from guiguts.maintext import maintext, HighlightTag
from guiguts.preferences import (
    PrefKey,
    preferences,
    PersistentBoolean,
    PersistentInt,
    PersistentString,
)
from guiguts.widgets import ToplevelDialog, ToolTip
from guiguts.utilities import sound_bell, IndexRowCol, is_mac

logger = logging.getLogger(__package__)


class JustifyStyle(StrEnum):
    """Enum class to store justification style types."""

    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()


class ASCIITableCell:
    """Structure to hold ASCII table cell."""

    def __init__(self) -> None:
        """Initialize ASCII table row structure."""
        self.fragments: list[str] = []


class ASCIITableRow:
    """Structure to hold ASCII table row."""

    def __init__(self) -> None:
        """Initialize ASCII table row structure."""
        self.cells: list[ASCIITableCell] = []


class ASCIITable:
    """Structure to hold ASCII table."""

    def __init__(self) -> None:
        """Initialize ASCII table structure."""
        self.spaced = False
        self.rows: list[ASCIITableRow] = []

    def num_columns(self) -> int:
        """Return number of columns in table."""
        try:
            return len(self.rows[0].cells)
        except IndexError:
            return 0

    def square_off(self) -> None:
        """Ensure all rows have correct number of cells; no leading empty fragments;
        no unnecessary trailing fragments; each cell has correct number of fragments."""
        max_col_widths = self.get_max_column_widths()
        max_cols = max(len(row.cells) for row in self.rows)
        for row in self.rows:
            # Add cells to get correct number of cells on this row
            row.cells.extend(
                [ASCIITableCell() for _ in range(len(row.cells), max_cols)]
            )
            # If not spaced, don't want to mess with leading/trailing fragments
            if self.spaced:
                # Delete any leading empty/whitespace fragments
                for col, cell in enumerate(row.cells):
                    while cell.fragments and not cell.fragments[0].strip():
                        del cell.fragments[0]
                # Delete any trailing empty/whitespace fragments
                for col, cell in enumerate(row.cells):
                    while cell.fragments and not cell.fragments[-1].strip():
                        del cell.fragments[-1]
            # Recalculate max number of fragments & add trailing whitespace fragments
            # so all cells on row have same number
            max_frags = max(len(cell.fragments) for cell in row.cells)
            for col, cell in enumerate(row.cells):
                cell.fragments.extend(
                    max_col_widths[col] * " "
                    for _ in range(len(cell.fragments), max_frags)
                )

    def add_text(self, row_num: int, col_num: int, frag_num: int, text: str) -> None:
        """Add text to cell at given row, column & fragment, padding with
        empty cells & fragments as necessary.

        Args:
            row_num: Zero-based row number of cell to add text to.
            col_num: Zero-based column number of cell to add text to.
            frag_num: Zero-based fragment number to add
            text: Text to be added to cell.
        """
        while len(self.rows) <= row_num:
            self.rows.append(ASCIITableRow())
        for row in self.rows:
            while len(row.cells) <= col_num:
                row.cells.append(ASCIITableCell())
        while len(self.rows[row_num].cells[col_num].fragments) < frag_num:
            self.rows[row_num].cells[col_num].fragments.append("")
        self.rows[row_num].cells[col_num].fragments.append(text)

    def get_max_column_widths(self) -> list[int]:
        """Get the max cell widths for each column in given table.

        Args:
            table: ASCIITable structure.

        Returns:
            List of max cell widths.
        """
        cols: list[int] = []
        for row in self.rows:
            for col_num, cell in enumerate(row.cells):
                size = (
                    max(len(line) for line in cell.fragments) if cell.fragments else 0
                )
                if col_num >= len(cols):
                    cols.append(size)
                elif size > cols[col_num]:
                    cols[col_num] = size
        return cols


class ASCIITableDialog(ToplevelDialog):
    """Dialog for ASCII special tables effects."""

    manual_page = "Text_Menu#ASCII_Table_Effects"

    def __init__(self) -> None:
        """Initialize ASCII Table dialog."""
        super().__init__("ASCII Table Special Effects", resize_x=False, resize_y=False)

        self.start_mark_name = ASCIITableDialog.get_dlg_name() + "Start"
        self.end_mark_name = ASCIITableDialog.get_dlg_name() + "End"

        self.selected_column = -1

        center_frame = ttk.Frame(
            self.top_frame, borderwidth=1, relief=tk.GROOVE, padding=5
        )
        center_frame.grid(row=0, column=0, columnspan=4, sticky="NSEW")

        for row in range(0, 4):
            center_frame.rowconfigure(row, pad=2)
        for col in range(0, 4):
            center_frame.columnconfigure(col, pad=2)

        # First row of buttons.
        sel_btn = ttk.Button(
            center_frame,
            text="Table Select",
            command=self.table_select,
        )
        sel_btn.grid(row=0, column=0, sticky="NSEW")
        ToolTip(sel_btn, "Highlight selected region as table to be worked on")
        desel_btn = ttk.Button(
            center_frame,
            text="Table Deselect",
            command=self.table_deselect,
        )
        desel_btn.grid(row=0, column=1, sticky="NSEW")
        ToolTip(desel_btn, "Unhighlight table region")
        ins_btn = ttk.Button(
            center_frame,
            text="Insert Vertical Line",
            command=lambda: self.insert_vert_line("i"),
        )
        ins_btn.grid(row=0, column=2, sticky="NSEW")
        ToolTip(ins_btn, "Insert column of vertical lines to right of cursor position")
        add_btn = ttk.Button(
            center_frame,
            text="Add Vertical Line",
            command=lambda: self.insert_vert_line("a"),
        )
        add_btn.grid(row=0, column=3, sticky="NSEW")
        ToolTip(
            add_btn,
            "Replace column of spaces with vertical lines to right of cursor position",
        )

        # Second row of buttons.
        space_btn = ttk.Button(
            center_frame,
            text="Space Out Table",
            command=self.space_out_table,
        )
        space_btn.grid(row=1, column=0, sticky="NSEW")
        ToolTip(space_btn, "Add blank lines between text lines to mark table rows")
        compress_btn = ttk.Button(
            center_frame,
            text="Compress Table",
            command=self.compress_table,
        )
        compress_btn.grid(row=1, column=1, sticky="NSEW")
        ToolTip(compress_btn, "Remove blank lines between table rows")
        del_btn = ttk.Button(
            center_frame,
            text="Delete Sel. Line",
            command=self.delete_selected_line,
        )
        del_btn.grid(row=1, column=2, sticky="NSEW")
        ToolTip(del_btn, "Delete current highlighted column of vertical lines")
        rem_btn = ttk.Button(
            center_frame,
            text="Remove Sel. Line",
            command=self.remove_selected_line,
        )
        rem_btn.grid(row=1, column=3, sticky="NSEW")
        ToolTip(
            rem_btn, "Replace current highlighted column of vertical lines with spaces"
        )

        # Third row of buttons.
        prev_btn = ttk.Button(
            center_frame,
            text="Select Prev. Line",
            command=self.select_prev_line,
        )
        prev_btn.grid(row=2, column=0, sticky="NSEW")
        ToolTip(
            prev_btn,
            "Select previous column, highlighting the vertical lines to the right of it",
        )
        next_btn = ttk.Button(
            center_frame,
            text="Select Next Line",
            command=self.select_next_line,
        )
        next_btn.grid(row=2, column=1, sticky="NSEW")
        ToolTip(
            next_btn,
            "Select next column, highlighting the vertical lines to the right of it",
        )
        desel_btn = ttk.Button(
            center_frame,
            text="Line Deselect",
            command=self.line_deselect,
        )
        desel_btn.grid(row=2, column=2, sticky="NSEW")
        ToolTip(desel_btn, "Unhighlight selected column of vertical lines")
        auto_btn = ttk.Button(
            center_frame,
            text="Auto Columns",
            command=self.auto_columns,
        )
        auto_btn.grid(row=2, column=3, sticky="NSEW")
        ToolTip(
            auto_btn,
            "Add vertical lines where cells are separated by at least 2 spaces",
        )

        # "Adjust Column" LabelFrame.
        self.adjust_col_frame = ttk.LabelFrame(
            self.top_frame, text="Adjust Column", padding=5
        )
        self.adjust_col_frame.grid(row=3, column=0, sticky="NSEW")
        self.adjust_col_frame.columnconfigure(0, weight=1)

        adjust_col_row1_frame = ttk.Frame(self.adjust_col_frame)
        adjust_col_row1_frame.grid(row=0, column=0, pady=2)
        adjust_col_row2_frame = ttk.Frame(self.adjust_col_frame)
        adjust_col_row2_frame.grid(row=1, column=0, pady=2)

        # Populate the first row.
        rewrap_cols_checkbox = ttk.Checkbutton(
            adjust_col_row1_frame,
            text="Rewrap Cols",
            variable=PersistentBoolean(PrefKey.ASCII_TABLE_REWRAP),
            command=self.justify_update,
        )
        rewrap_cols_checkbox.grid(row=0, column=0, padx=(0, 10), pady=2, sticky="NSEW")
        ToolTip(
            rewrap_cols_checkbox,
            "If checked, text within cells will rewrap & justify when vertical lines are moved",
        )

        self.label_justify = ttk.Label(adjust_col_row1_frame, text="Justify")
        self.label_justify.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="NSEW")

        justify_style = PersistentString(PrefKey.ASCII_TABLE_JUSTIFY)
        self.justify_left = ttk.Radiobutton(
            adjust_col_row1_frame,
            text="L",
            variable=justify_style,
            value=JustifyStyle.LEFT,
        )
        self.justify_left.grid(row=0, column=2, pady=2, sticky="NSEW")

        self.justify_center = ttk.Radiobutton(
            adjust_col_row1_frame,
            text="C",
            variable=justify_style,
            value=JustifyStyle.CENTER,
        )
        self.justify_center.grid(row=0, column=3, pady=2, sticky="NSEW")

        self.justify_right = ttk.Radiobutton(
            adjust_col_row1_frame,
            text="R",
            variable=justify_style,
            value=JustifyStyle.RIGHT,
        )
        self.justify_right.grid(row=0, column=4, padx=(0, 15), pady=2, sticky="NSEW")

        self.label_indent = ttk.Label(adjust_col_row1_frame, text="Indent")
        self.label_indent.grid(row=0, column=5, padx=5, pady=2, sticky="NSEW")
        self.indent_value_entry = tk.Entry(
            adjust_col_row1_frame,
            width=5,
            textvariable=PersistentInt(PrefKey.ASCII_TABLE_INDENT),
        )
        self.indent_value_entry.grid(row=0, column=6, padx=0, pady=2, sticky="NSEW")
        ToolTip(
            self.indent_value_entry,
            "Number of spaces to indent first line when rewrapping",
        )

        self.hanging_checkbox = ttk.Checkbutton(
            adjust_col_row1_frame,
            text="Hanging",
            variable=PersistentBoolean(PrefKey.ASCII_TABLE_HANGING),
        )
        self.hanging_checkbox.grid(row=0, column=7, padx=10, pady=2, sticky="NSEW")
        ToolTip(
            self.hanging_checkbox,
            "If checked, use hanging indent instead of standard indent when rewrapping",
        )
        self.justify_update()

        # Populate the second row.
        move_left_button = ttk.Button(
            adjust_col_row2_frame,
            text="Move Left",
            command=lambda: self.column_adjust(-1),
        )
        move_left_button.grid(row=0, column=1, sticky="NSEW", padx=5)
        ToolTip(
            move_left_button,
            "Move highlighted vertical line left, reducing column width, and rewrapping if enabled",
        )

        move_right_button = ttk.Button(
            adjust_col_row2_frame,
            text="Move Right",
            command=lambda: self.column_adjust(1),
        )
        move_right_button.grid(row=0, column=3, sticky="NSEW", padx=5)
        ToolTip(
            move_right_button,
            "Move highlighted vertical line right, increasing column width, and rewrapping if enabled",
        )

        # "Leading/Trailing Spaces" LabelFrame
        spaces_frame = ttk.LabelFrame(
            self.top_frame, text="Leading/Trailing Spaces", padding=5
        )
        spaces_frame.grid(row=4, column=0, sticky="NSEW")
        spaces_frame.columnconfigure(0, weight=1)
        center_frame = ttk.Frame(spaces_frame)
        center_frame.grid(row=0, column=0, pady=2)

        fill_btn = ttk.Button(
            center_frame,
            text="Fill With",
            command=self.fill_spaces,
        )
        fill_btn.grid(row=0, column=0, sticky="NSEW")
        ToolTip(
            fill_btn,
            "Replace leading and trailing spaces in column with following character",
        )

        fill_entry = tk.Entry(
            center_frame,
            width=2,
            justify=tk.CENTER,
            textvariable=PersistentInt(PrefKey.ASCII_TABLE_FILL_CHAR),
            validate=tk.ALL,
            validatecommand=(self.register(lambda val: len(val) <= 1), "%P"),
        )
        fill_entry.grid(row=0, column=1, padx=(5, 20), sticky="NSEW")
        ToolTip(fill_entry, "Character to use when filling leading and trailing spaces")

        unfill_btn = ttk.Button(
            center_frame,
            text="Restore Spaces",
            command=self.restore_spaces,
        )
        unfill_btn.grid(row=0, column=2, sticky="NSEW")
        ToolTip(unfill_btn, "Replace fill character with spaces")

        # "Grid <==> Step" LabelFrame
        restructure_frame = ttk.LabelFrame(
            self.top_frame, text="Restructure", padding=5
        )
        restructure_frame.grid(row=5, column=0, sticky="NSEW")
        restructure_frame.columnconfigure(0, weight=1)
        center_frame = ttk.Frame(restructure_frame)
        center_frame.grid(row=0, column=0, pady=2)
        ttk.Label(center_frame, text="Table Right Column").grid(
            row=0, column=0, pady=2, sticky="NSEW"
        )
        right_entry = tk.Entry(
            center_frame,
            width=3,
            justify=tk.CENTER,
            textvariable=PersistentInt(PrefKey.ASCII_TABLE_RIGHT_COL),
            validate=tk.ALL,
            validatecommand=(self.register(lambda val: val.isdigit() or not val), "%P"),
        )
        right_entry.grid(row=0, column=1, padx=(5, 20), sticky="NSEW")
        ToolTip(right_entry, "Right margin to use when converting grid ⇔ step format")
        g2s_btn = ttk.Button(
            center_frame,
            text="Convert Grid to Step",
            command=self.grid_to_step,
        )
        g2s_btn.grid(row=0, column=2, sticky="NSEW", padx=5)
        ToolTip(g2s_btn, "Convert table from grid to step format")
        s2g_btn = ttk.Button(
            center_frame,
            text="Convert Step to Grid",
            command=self.step_to_grid,
        )
        s2g_btn.grid(row=0, column=3, sticky="NSEW", padx=5)
        ToolTip(s2g_btn, "Convert table from step to grid format")
        cpl2g_btn = ttk.Button(
            restructure_frame,
            text="Convert Cell-per-line to Grid",
            command=self.cell_per_line_to_grid,
        )
        cpl2g_btn.grid(row=1, column=0, pady=(5, 0))
        ToolTip(cpl2g_btn, "Convert table from one-cell-per-line to grid format")

        # Since focus remains in dialog when buttons are pressed, bind undo/redo
        # keys to dialog so they work when the user wants to undo the previous operation
        self.key_bind("Cmd/Ctrl+Z", lambda: maintext().event_generate("<<Undo>>"))
        self.key_bind(
            "Cmd+Shift+Z" if is_mac() else "Ctrl+Y",
            lambda: maintext().event_generate("<<Redo>>"),
        )
        # Also, if user does undo/redo, we want to refresh the table display
        maintext().add_undo_redo_callback(
            self.get_dlg_name(), self.refresh_table_display
        )

        self.selected_col_width_label = ttk.Label(adjust_col_row2_frame)
        self.selected_col_width_label.grid(row=0, column=4, sticky="NSEW")
        self.table_select()
        self.refresh_table_display()

    def on_destroy(self) -> None:
        """Override method that tidies up when the dialog is destroyed.

        Needs to remove the undo_redo callback.
        """
        super().on_destroy()
        if not maintext().winfo_exists():
            return
        self.table_deselect()
        self.refresh_table_display()
        maintext().remove_undo_redo_callback(self.get_dlg_name())

    def justify_update(self) -> None:
        """Update controls to be active/disabled depending on whether justify is on."""
        state = "normal" if preferences.get(PrefKey.ASCII_TABLE_REWRAP) else "disable"
        for widget in (
            self.label_justify,
            self.justify_left,
            self.justify_center,
            self.justify_right,
            self.label_indent,
            self.indent_value_entry,
            self.hanging_checkbox,
        ):
            widget["state"] = state

    def column_adjust(self, direction: int) -> None:
        """Move a column dividing line left or right.

        If 'Rewrap Cols' ticked, text in the selected column is rewrapped to fit the change
        in width. It is always justified left at this point. Each line of text in the column
        will have padding added later so that it can be centered or right-justified as required
        by the 'Justify' radio button choice.

        Args:
            direction: -1 to move left one column, 1 to move right one column
        """
        tbl = self.get_table_grid()
        if (
            len(tbl.rows) == 0
            or self.selected_column < 0
            or self.selected_column >= len(tbl.rows[0].cells)
        ):
            return
        # Don't attempt to shrink if any fragment has no spaces
        if direction < 0:
            for row in tbl.rows:
                for frag in row.cells[self.selected_column].fragments:
                    if " " not in frag:
                        return

        col_width = tbl.get_max_column_widths()[self.selected_column] + direction
        if preferences.get(PrefKey.ASCII_TABLE_JUSTIFY) == JustifyStyle.LEFT:
            justify_func = str.ljust
        elif preferences.get(PrefKey.ASCII_TABLE_JUSTIFY) == JustifyStyle.RIGHT:
            justify_func = str.rjust
        else:
            justify_func = str.center
        # Set up wrapper class in case it's needed
        ini_ind = sub_ind = preferences.get(PrefKey.ASCII_TABLE_INDENT) * " "
        if preferences.get(PrefKey.ASCII_TABLE_HANGING):
            ini_ind = ""
        else:
            sub_ind = ""
        wrapper = TextWrapper(
            width=col_width,
            initial_indent=ini_ind,
            subsequent_indent=sub_ind,
            break_long_words=False,
        )
        # Don't wrap if whole column is just whitespace
        all_spaces = True
        for row in tbl.rows:
            test_cell = "".join(row.cells[self.selected_column].fragments)
            if re.search("[^ ]", test_cell):
                all_spaces = False
                break
        if preferences.get(PrefKey.ASCII_TABLE_REWRAP) and not all_spaces:
            for row in tbl.rows:
                cell_fragments = row.cells[self.selected_column].fragments
                cell_text = re.sub("  +", " ", " ".join(cell_fragments)).strip()
                # Wrap the cell text & store as fragments
                row.cells[self.selected_column].fragments = wrapper.wrap(cell_text)
            # Recalculate max width required and justify accordingly
            col_width = max(
                col_width, tbl.get_max_column_widths()[self.selected_column]
            )
            for row in tbl.rows:
                cell_fragments = row.cells[self.selected_column].fragments
                for nfrag, _ in enumerate(cell_fragments):
                    cell_fragments[nfrag] = justify_func(
                        cell_fragments[nfrag], col_width
                    )
        else:
            for row in tbl.rows:
                cell_fragments = row.cells[self.selected_column].fragments
                # Can't move left if any fragment would lose non-space characters
                max_fraglen = (
                    max(len(frag.rstrip()) for frag in cell_fragments)
                    if cell_fragments
                    else 0
                )
                if direction < 0 and col_width < max_fraglen:
                    col_width = max_fraglen
                for nfrag, _ in enumerate(cell_fragments):
                    cell_fragments[nfrag] = (
                        cell_fragments[nfrag].rstrip().ljust(col_width)
                    )
        maintext().undo_block_begin()
        tbl.square_off()
        self.put_table_grid(tbl)
        self.refresh_table_display()

    def fill_spaces(self) -> None:
        """Replace leading/trailing spaces in current column with fill character."""
        fill_char = preferences.get(PrefKey.ASCII_TABLE_FILL_CHAR)
        tbl = self.get_table_grid()
        if (
            len(tbl.rows) == 0
            or self.selected_column < 0
            or self.selected_column >= len(tbl.rows[0].cells)
            or not fill_char
        ):
            return
        for row in tbl.rows:
            cell_fragments = row.cells[self.selected_column].fragments
            for nfrag, frag in enumerate(cell_fragments):
                ns = len(frag) - len(frag.lstrip())
                frag = "@" * ns + frag[ns:]  # Replace leading
                ns = len(frag) - len(frag.rstrip())
                cell_fragments[nfrag] = (
                    frag[: len(frag) - ns] + "@" * ns
                )  # Replace trailing
        maintext().undo_block_begin()
        tbl.square_off()
        self.put_table_grid(tbl)
        self.refresh_table_display()

    def restore_spaces(self) -> None:
        """Replace all occurrences of fill character with spaces."""
        fill_char = preferences.get(PrefKey.ASCII_TABLE_FILL_CHAR)
        tbl = self.get_table_grid()
        if (
            len(tbl.rows) == 0
            or self.selected_column < 0
            or self.selected_column >= len(tbl.rows[0].cells)
            or not fill_char
        ):
            return
        for row in tbl.rows:
            cell_fragments = row.cells[self.selected_column].fragments
            for nfrag, _ in enumerate(cell_fragments):
                cell_fragments[nfrag] = cell_fragments[nfrag].replace(fill_char, " ")
        maintext().undo_block_begin()
        tbl.square_off()
        self.put_table_grid(tbl)
        self.refresh_table_display()

    def grid_to_step(self) -> None:
        """Convert table from grid format to step format."""
        right_col = preferences.get(PrefKey.ASCII_TABLE_RIGHT_COL)
        tbl = self.get_table_grid()
        if len(tbl.rows) == 0 or right_col <= 0:
            return
        maintext().undo_block_begin()
        tbl.square_off()
        self.put_table_step(tbl)
        self.refresh_table_display()

    def step_to_grid(self) -> None:
        """Convert table from step format to grid format."""
        right_col = preferences.get(PrefKey.ASCII_TABLE_RIGHT_COL)
        tbl = self.get_table_step()
        if len(tbl.rows) == 0 or right_col <= 0:
            return
        maintext().undo_block_begin()
        tbl.square_off()
        self.put_table_grid(tbl)
        self.refresh_table_display()

    def cell_per_line_to_grid(self) -> None:
        """Convert format from one cell per line to grid."""
        ranges = maintext().tag_ranges(HighlightTag.TABLE_BODY)
        if len(ranges) == 0:
            return
        maintext().undo_block_begin()
        line_num = maintext().rowcol(self.start_mark_name).row + 1
        while line_num < maintext().rowcol(self.end_mark_name).row:
            if line := maintext().get(f"{line_num}.0", f"{line_num}.end").strip():
                # Check if first cell on line
                if maintext().rowcol(f"{line_num - 1}.end").col == 0:
                    maintext().replace(f"{line_num}.0", f"{line_num}.end", line)
                else:
                    # Because we're removing a newline char, skip incrementing line_num
                    maintext().replace(
                        f"{line_num - 1}.end", f"{line_num}.end", f"  {line}"
                    )
                    continue
            line_num += 1
        self.refresh_table_display()

    def column_width_refresh(self) -> None:
        """Calculate the width of selected column and display it.

        Args:
            row: Row to use to calculate column width on. Negative to clear width.
        """
        width_text = ""
        try:
            start_row = maintext().rowcol(self.start_mark_name).row
        except tk.TclError:
            start_row = -1
        if start_row > 0 and self.selected_column >= 0:
            column_width_text = maintext().get(f"{start_row}.0", f"{start_row}.end")
            cells = column_width_text.split("|")
            if self.selected_column < len(cells):
                width_text = f" {self.selected_column + 1} (width {len(cells[self.selected_column])})"
        if self.adjust_col_frame.winfo_exists():
            self.adjust_col_frame["text"] = f"Adjust Column{width_text}"

    def table_select(self) -> None:
        """Mark and tag the selected text as a table to be worked on.
        If column selection, table is whole of each line in the column selection."""
        ranges = maintext().selected_ranges()
        if len(ranges) == 0:
            return

        maintext().undo_block_begin()
        # Always start at beginning of first line of the selection.
        tblstart = maintext().rowcol(f"{ranges[0].start.index()} linestart")
        # Always end at start of line following the selection end (unless already there).
        if ranges[-1].end.col == 0:
            tblend = maintext().rowcol(f"{ranges[-1].end.index()}")
        else:
            tblend = maintext().rowcol(f"{ranges[-1].end.index()} +1l linestart")
        # Mark the beginning and end of the selected table.
        maintext().set_mark_position(
            self.start_mark_name,
            tblstart,
            gravity=tk.LEFT,
        )
        maintext().set_mark_position(
            self.end_mark_name,
            tblend,
            gravity=tk.RIGHT,
        )
        # The 'sel' tag has priority so its highlighting remains even if we add the
        # table body tag highlighting. To have our table body tag highlight the whole
        # of the selection (i.e. our table), clear selection first.
        maintext().clear_selection()
        self.selected_column = -1
        self.refresh_table_display()

    def table_deselect(self) -> None:
        """Remove tags and marks added by do_table_select()."""
        maintext().undo_block_begin()
        mark = "1.0"
        # Delete all marks we set.
        while mark_next := maintext().mark_next(mark):
            if mark_next.startswith((self.start_mark_name, self.end_mark_name)):
                mark = maintext().index(mark_next)
                maintext().mark_unset(mark_next)
            else:
                mark = mark_next
        self.selected_column = -1
        self.refresh_table_display()

    def insert_vert_line(self, mode: str) -> None:
        """Add a column dividing line according to mode.

        Arg:
            mode: 'i' when called by Insert Vertical Line button
                  'a' when called by Add Vertical Line button
        """
        # Has user selected a table?
        if not self.table_is_marked():
            sound_bell()
            return
        maintext().undo_block_begin()
        made_a_dividing_line = False
        # Get column position of insert cursor.
        cursor_pos = maintext().get_insert_index()
        cursor_column = cursor_pos.col
        # Set start and end row/col of table from marks for "|" insert loop.
        start_row = maintext().rowcol(self.start_mark_name).row
        end_row = maintext().rowcol(self.end_mark_name).row
        end_col = maintext().rowcol(self.end_mark_name).col
        # Back up a row if last row of table is blank.
        if end_col == 0:
            end_row -= 1
        # 'insert' (mode == 'i') a vertical line or 'add' (mode == 'a') a vertical line.
        if mode == "i":
            # 'Insert Vertical Line' button. This is the easy one. Unconditionally
            # insert a "|" character to the right of the cursor position for each
            # file line in the table. Pushes rest of each line to the right.
            for table_row in range(start_row, end_row + 1):
                row_end_column = maintext().rowcol(f"{table_row}.0 lineend").col
                row_end_index = maintext().rowcol(f"{table_row}.0 lineend").index()
                # If necessary, fill row with spaces to the cursor column position.
                if row_end_column < cursor_column:
                    maintext().insert(
                        row_end_index, (" " * (cursor_column - row_end_column))
                    )
                # Insert a "|" character on this line at cursor position.
                maintext().insert(f"{table_row}.{cursor_column}", "|")
            made_a_dividing_line = True
        else:
            # Assume mode == 'a'.
            # 'Add Vertical Line' button. A little more tricky as we should first
            # check there is a column of space characters immediately to the right
            # of the cursor position. That column is then replaced by a column of
            # '|' characters. If there is no column of space characters we
            # may still have altered the table by padding lines with space characters
            # so repaint table background colour, etc., as if we had added stiles.
            found_column_of_spaces = True
            for table_row in range(start_row, end_row + 1):
                row_end_column = maintext().rowcol(f"{table_row}.0 lineend").col
                row_end_index = maintext().rowcol(f"{table_row}.0 lineend").index()
                # If necessary, fill row with spaces to the cursor column position.
                if row_end_column < cursor_column:
                    maintext().insert(
                        row_end_index, (" " * (cursor_column - row_end_column))
                    )
                next_char = maintext().get(
                    f"{table_row}.{cursor_column}", f"{table_row}.{cursor_column} +1c"
                )
                if next_char != " ":
                    found_column_of_spaces = False
            # We've run down the table to see if we have a column of spaces to the
            # right of the cursor position. If we have then replace that column with
            # "|" characters.
            if found_column_of_spaces:
                for table_row in range(start_row, end_row + 1):
                    # Replace a space character with a "|" character at cursor position
                    # on this file line.
                    maintext().replace(
                        f"{table_row}.{cursor_column}",
                        f"{table_row}.{cursor_column} +1c",
                        "|",
                    )
                    made_a_dividing_line = True
        # All inserts/replacements done and/or table lines padded with spaces.
        # If we have inserted/added a divider then select it then refresh table.
        if made_a_dividing_line:
            self.selected_column = self.get_selected_column_from_rowcol(
                IndexRowCol(table_row, cursor_column)
            )
        maintext().set_insert_index(cursor_pos)  # Restore cursor position
        self.refresh_table_display()

    def space_out_table(self) -> None:
        """Add empty lines between table rows."""
        ranges = maintext().tag_ranges(HighlightTag.TABLE_BODY)
        # Has user selected a table?
        if len(ranges) == 0:
            sound_bell()
            return
        maintext().undo_block_begin()
        # Get start and end row/col of table from marks.
        start_row = maintext().rowcol(self.start_mark_name).row
        start_col = maintext().rowcol(self.start_mark_name).col
        end_row = maintext().rowcol(self.end_mark_name).row
        end_col = maintext().rowcol(self.end_mark_name).col
        self.refresh_table_display()
        # Back up a row if last row of table is blank.
        if end_col == 0:
            end_row -= 1
        # Get copy of first row of table. If table has any column dividers they
        # will be present in the copy.
        blank_row_text = maintext().get(
            f"{start_row}.{start_col} linestart", f"{start_row}.end"
        )
        # Replace in this copy all characters, other than '|', with a space.
        blank_row_text = re.sub(r"[^|]", " ", blank_row_text)
        # Back up to the penultimate row of the table.
        end_row -= 1
        # Insert 'blank_row_text' lines between each row of the table. If a
        # blank row already exists in the table don't add a new one. Instead
        # replace it with 'blank_row_text'. Work from bottom of table toward
        # the top.
        prev_row_is_blank = False
        while end_row >= start_row:
            if (
                maintext().get(f"{end_row}.0", f"{end_row}.end") != ""
                and not prev_row_is_blank
            ):
                prefixed_blank_row_text = "\n" + blank_row_text
                maintext().insert(f"{end_row}.end", f"{prefixed_blank_row_text}")
            elif (
                maintext().get(f"{end_row}.0", f"{end_row}.end") != ""
                and prev_row_is_blank
            ):
                prev_row_is_blank = False
            elif maintext().get(f"{end_row}.0", f"{end_row}.end") == "":
                # Have encountered a blank line in the table. Replace this
                # with 'blank_row_text' in order to display continuation
                # of any column dividers in the table. This situation will
                # occur when the user has added a blank line to the table
                # and has omitted to continue a column divider that is on
                # the rows above and below the blank line.
                maintext().delete(f"{end_row}.0", f"{end_row}.end")
                maintext().insert(f"{end_row}.end", f"{blank_row_text}")
                prev_row_is_blank = True
            end_row -= 1
        self.refresh_table_display()

    def compress_table(self) -> None:
        """Remove the 'blank' spacing lines between table rows."""
        ranges = maintext().tag_ranges(HighlightTag.TABLE_BODY)
        # Has user selected a table?
        if len(ranges) == 0:
            sound_bell()
            return
        maintext().undo_block_begin()
        # Get start and end row/col of table from marks.
        start_row = maintext().rowcol(self.start_mark_name).row
        end_row = maintext().rowcol(self.end_mark_name).row
        end_col = maintext().rowcol(self.end_mark_name).col
        self.refresh_table_display()
        # Back up a row if last row of table is blank.
        if end_col == 0:
            end_row -= 1
        while end_row >= start_row:
            row_text = maintext().get(f"{end_row}.0", f"{end_row}.end")
            if re.match(r"^[ |]*$", row_text):
                maintext().delete(f"{end_row}.0 -1c", f"{end_row}.end")
            end_row -= 1
        self.refresh_table_display()

    def delete_selected_line(self) -> None:
        """Handle click on 'Delete Sel. Line' button."""
        maintext().undo_block_begin()
        self.delete_remove_selected_line("d")

    def remove_selected_line(self) -> None:
        """Handle click on 'Remove Sel. Line' button."""
        maintext().undo_block_begin()
        self.delete_remove_selected_line("r")

    def delete_remove_selected_line(self, mode: str) -> None:
        """Delete selected column divider from each table row in which it appears.

        Args:
            mode: 'd' - delete column divider; 'r' - replace column divider with space
        """
        # NB 'ranges' is a tuple that contains zero or more pairs of indexes as strings.
        #    e.g. ("1.2", "1.3", "2.2", "2.3", "3.2", "3.3", ...)
        # If a there is a selected column divider then there will be as many pairs of
        # indexes in the tuple as there are rows in the table. If no column divider is
        # selected then the tuple is empty.
        ranges_tuple = maintext().tag_ranges(HighlightTag.TABLE_COLUMN)
        # Is there a selected column divider in the table?
        if len(ranges_tuple) == 0:
            return
        # Convert tuple to a list as it's easier to manipulate.
        ranges = list(ranges_tuple)
        # Now delete (or replace with a space) the selected column divider from each table row in which it appears.
        replacement = " " if mode == "r" else ""
        while ranges:
            index2 = ranges.pop()
            index1 = ranges.pop()
            if maintext().get(index1, index2) == "|":
                maintext().replace(index1, index2, replacement)
        self.selected_column %= self.get_table_grid().num_columns()
        self.refresh_table_display()

    def select_prev_line(self) -> None:
        """Select the previous column divider."""
        maintext().undo_block_begin()
        self.select_next_prev_line(-1)

    def select_next_line(self) -> None:
        """Select the next column divider."""
        maintext().undo_block_begin()
        self.select_next_prev_line(1)

    def select_next_prev_line(self, idir: int) -> None:
        """Select the next/previous column divider.

        Args:
            dir: +1 to select next, -1 to select previous.
        """
        if not self.table_is_marked():
            return
        # If a column is already selected, select the next/previous
        if self.selected_column >= 0:
            self.selected_column = self.selected_column + idir
        # If no column selected, base on cursor position: the next/prev
        # from the cursor, or the first column if cursor not in table at all
        else:
            insert_rowcol = maintext().get_insert_index()
            if maintext().compare(
                insert_rowcol.index(), "<", self.start_mark_name
            ) or maintext().compare(insert_rowcol.index(), ">=", self.end_mark_name):
                self.selected_column = 0
            else:
                self.selected_column = self.get_selected_column_from_rowcol(
                    insert_rowcol
                ) - (1 if idir < 0 else 0)
        # Ensure selected column is between 0 & number of columns
        self.selected_column %= self.get_table_grid().num_columns()
        self.refresh_table_display()

    def line_deselect(self) -> None:
        """Deselect the currently highlighted column divider."""
        # Is there a table selected?
        if not self.table_is_marked():
            return
        maintext().undo_block_begin()
        self.selected_column = -1
        self.refresh_table_display()

    def auto_columns(self) -> None:
        """Automatically split text into table columns at multi-space points
        using vertical column dividers at those points."""
        ranges = maintext().tag_ranges(HighlightTag.TABLE_BODY)
        if len(ranges) == 0:
            return

        maintext().undo_block_begin()
        tbl = self.get_table_grid()
        col_widths = tbl.get_max_column_widths()
        for row in tbl.rows:
            for col_num, col in enumerate(row.cells):
                for line_num, _ in enumerate(col.fragments):
                    assert col_widths[col_num] >= len(col.fragments[line_num])
                    col.fragments[line_num] += " " * (
                        col_widths[col_num] - len(col.fragments[line_num]) + 1
                    )
        self.put_table_grid(tbl)
        self.selected_column = -1
        self.refresh_table_display()

    def get_table_grid(self) -> ASCIITable:
        """Get grid-format table from file and return as an ASCIITable.

        Returns:
            Table with each cell in one element of 2D array, i.e.
            all sublists have the same number of elements(=table columns).
        """
        table = ASCIITable()
        ranges = maintext().tag_ranges(HighlightTag.TABLE_BODY)
        if len(ranges) == 0:
            return table
        table_text = maintext().get(self.start_mark_name, self.end_mark_name)
        split_regex = r"\|" if "|" in table_text else r"  +"
        text_rows: list[str] = re.split(r"\n[| ]*\n", table_text)
        if len(text_rows) > 1:
            table.spaced = True
        # For each row of the table
        for row, text_row in enumerate(text_rows):
            # For each text line in that row
            text_lines = text_row.split("\n")
            if text_lines[-1] == "":  # Trailing empty line.
                del text_lines[-1]
            for frag_num, text_line in enumerate(text_lines):
                text_line = re.sub(r"|\|$", "", text_line.rstrip())
                # For each cell line in that text line
                for col, cell_line in enumerate(re.split(split_regex, text_line)):
                    table.add_text(row, col, frag_num, cell_line)
        # "Square off" table, making all rows have max_cols columns
        table.square_off()
        return table

    def put_table_grid(self, table: ASCIITable) -> None:
        """Put ASCIITable back into file in grid format.

        Args:
            table: ASCIITable structure to be inserted back into file.
        """
        text_rows: list[str] = []
        col_widths = table.get_max_column_widths()
        for row_num, row in enumerate(table.rows):
            # If necessary, space table with space-replaced previous line
            if table.spaced and row_num > 0:
                text_rows.append(re.sub("[^|]", " ", text_rows[row_num - 1]))
            # Need to output same number of lines for each cell on row
            max_lines = max(len(cell.fragments) for cell in row.cells)
            for line_num in range(max_lines):
                line_parts = []
                for col_num, cell in enumerate(row.cells):
                    if line_num < len(cell.fragments):
                        line_parts.append(cell.fragments[line_num])
                    else:
                        line_parts.append(" " * col_widths[col_num])
                text_rows.append("|".join(line_parts))
        text_table = "|\n".join(text_rows) + "|\n"
        maintext().replace(self.start_mark_name, self.end_mark_name, text_table)

    def get_table_step(self) -> ASCIITable:
        """Get step-format table from file and return as an ASCIITable.

        Returns:
            Table with each cell in one element of 2D array, i.e.
            all sublists have the same number of elements(=table columns).
        """
        table = ASCIITable()
        table.spaced = True
        ranges = maintext().tag_ranges(HighlightTag.TABLE_BODY)
        if len(ranges) == 0:
            return table
        table_text = maintext().get(self.start_mark_name, self.end_mark_name)
        text_lines: list[str] = table_text.split("\n")
        # Get max number of columns
        max_cols = max(len(re.findall(r"(    \|)", line)) + 1 for line in text_lines)
        # Space columns evenly (allow for max_cols dividers)
        col_width = max(
            (preferences.get(PrefKey.ASCII_TABLE_RIGHT_COL) - max_cols) // max_cols, 1
        )
        wrapper = TextWrapper(
            width=col_width,
            break_long_words=False,
        )

        # For each line of text, check if we've moved to a new cell by counting "    |" prefixes
        # Once cell is complete, wrap it & store in fragments
        col_num = -1
        fragments: list[str] = []

        def store_fragments() -> None:
            """Store collected fragments in new table cell."""
            table.rows[-1].cells.append(ASCIITableCell())
            join_text = re.sub("  +", " ", " ".join(fragments)).strip()
            table.rows[-1].cells[-1].fragments = wrapper.wrap(join_text)

        table.rows.append(ASCIITableRow())
        for line in text_lines:
            # Check for end of row - store collected fragments & start new row
            if re.fullmatch(r"(    \|)+ *", line):
                store_fragments()
                table.rows.append(ASCIITableRow())
                col_num = -1
                fragments = []
                continue
            ncol = len(re.findall(r"(    \|)", line))
            frag_text = re.sub(r"^(    \|)+ *", "", line)
            if ncol == col_num:  # Same cell as previously
                fragments.append(frag_text)
            else:
                # Store collected fragments and start new cell
                if fragments:
                    store_fragments()
                col_num = ncol
                fragments = [frag_text]
        # "Square off" table, making all rows have max_cols columns
        table.square_off()
        # Pad fragments with space to fit column widths
        col_widths = table.get_max_column_widths()
        for row in table.rows:
            for col_num, cell in enumerate(row.cells):
                cell_fragments = cell.fragments
                for nfrag, _ in enumerate(cell_fragments):
                    cell_fragments[nfrag] = cell_fragments[nfrag].ljust(
                        col_widths[col_num]
                    )
        return table

    def put_table_step(self, table: ASCIITable) -> None:
        """Put ASCIITable back into file in step format.

        Args:
            table: ASCIITable structure to be inserted back into file.
        """

        wrapper = TextWrapper(
            width=preferences.get(PrefKey.ASCII_TABLE_RIGHT_COL),
            break_long_words=False,
        )
        text_rows: list[str] = []
        leading_vertical_line = True
        for row in table.rows:
            for frag in row.cells[0].fragments:
                if len(frag.strip()) > 0:
                    leading_vertical_line = False
                    break
            else:
                # No non-empty frag on this row - check next row
                continue
            # Non-empty frag found, break outer loop
            break
        for row in table.rows:
            col_num = 0
            for idx, cell in enumerate(row.cells):
                if leading_vertical_line and idx == 0:
                    continue
                wrapper.initial_indent = "    |" * col_num + " " if col_num > 0 else ""
                wrapper.subsequent_indent = wrapper.initial_indent
                cell_text = re.sub("  +", " ", " ".join(cell.fragments)).strip()
                text_rows.extend(wrapper.wrap(cell_text))
                col_num += 1
            text_rows.append(
                "    |" * (col_num - 1 if leading_vertical_line else col_num)
            )
        text_table = "\n".join(text_rows) + "\n"
        maintext().replace(self.start_mark_name, self.end_mark_name, text_table)

    def refresh_table_display(self) -> None:
        """Refresh the table highlighting after an edit. Remove tag from
        whole file and attempt to add it to table. It's OK if the table
        isn't marked at the moment. This refreshing avoids parts of table
        not being highlighted after editing.

        Also highlight current column if any and display current column width.
        """
        maintext().tag_remove(HighlightTag.TABLE_BODY, "1.0", tk.END)
        try:
            maintext().tag_add(
                HighlightTag.TABLE_BODY, self.start_mark_name, self.end_mark_name
            )
        except tk.TclError:
            pass  # OK if no start/end tags
        self.remove_column_highlighting()
        self.highlight_column_divider()
        self.column_width_refresh()

    def remove_column_highlighting(self) -> None:
        """Remove column highlighting from whole file (to be safe)."""
        maintext().tag_remove(HighlightTag.TABLE_COLUMN, "1.0", tk.END)

    def get_selected_column_from_rowcol(self, rowcol: IndexRowCol) -> int:
        """Return which column is currently selected, given a rowcol.

        Returns:
            Number of "|" characters on line before given col.
            Returns -1 if line has no "|" characters.
        """
        line = maintext().get(f"{rowcol.row}.0", f"{rowcol.row}.end")
        if "|" not in line:
            return -1
        # Ensure result is between 0 & number of cols
        return line.count("|", 0, rowcol.col) % self.get_table_grid().num_columns()

    def table_is_marked(self) -> bool:
        """Returns 'False' if no table has been selected and marked."""
        table_start_mark_present = False
        table_end_mark_present = False
        for mark in maintext().mark_names():
            if mark.startswith(self.start_mark_name):
                table_start_mark_present = True
            elif mark.startswith(self.end_mark_name):
                table_end_mark_present = True
        return table_start_mark_present and table_end_mark_present

    def highlight_column_divider(self) -> None:
        """Highlight currently selected column divider."""
        if self.selected_column < 0:
            return
        try:
            start = maintext().rowcol(self.start_mark_name)
            end = maintext().rowcol(self.end_mark_name)
        except tk.TclError:
            return  # No table marked
        # Back up a row if last row of table is blank.
        if end.col == 0:
            end.row -= 1
        for table_row in range(start.row, end.row + 1):
            pipe_index = f"{table_row}.0"
            for _ in range(self.selected_column + 1):
                pipe_index = maintext().search("|", f"{pipe_index}", f"{table_row}.end")
                if not pipe_index:
                    break
                pipe_index = f"{pipe_index}+1c"
            if pipe_index:
                maintext().tag_add(HighlightTag.TABLE_COLUMN, f"{pipe_index}-1c")
