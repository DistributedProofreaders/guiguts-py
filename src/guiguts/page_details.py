"""Store and manipulate page labels."""

import tkinter as tk
from tkinter import simpledialog, ttk

import roman  # type: ignore[import-untyped]

from guiguts.maintext import maintext
from guiguts.widgets import OkCancelDialog

STYLE_COLUMN = "#2"
STYLE_ARABIC = "Arabic"
STYLE_ROMAN = "Roman"
STYLE_DITTO = '"'
NUMBER_COLUMN = "#3"
NUMBER_PAGENUM = "Number"
NUMBER_INCREMENT = "+1"
NUMBER_NONE = "No Count"
COL_HEAD_IMG = "Img"
COL_HEAD_STYLE = "Style"
COL_HEAD_NUMBER = "Number"
COL_HEAD_LABEL = "Label"
PAGE_LABEL_PREFIX = "Pg "

STYLE_NEXT = {
    STYLE_ARABIC: STYLE_ROMAN,
    STYLE_ROMAN: STYLE_DITTO,
    STYLE_DITTO: STYLE_ARABIC,
}
NUMBER_NEXT = {
    NUMBER_PAGENUM: NUMBER_INCREMENT,
    NUMBER_INCREMENT: NUMBER_NONE,
    NUMBER_NONE: NUMBER_PAGENUM,
}


class PageDetail(dict):
    """Page detail information for one page.

    Attributes:
        index: Index of start of page in file.
        style: Page number style: "Arabic" or "Roman"
        number:
    """

    def __init__(
        self, index: str, style: str = '"', number: str = NUMBER_INCREMENT
    ) -> None:
        """Initialize a PageDetail object to hold page information."""
        self["index"] = index
        self["style"] = style
        self["number"] = number
        self["label"] = ""


class PageDetails(dict[str, PageDetail]):
    """Dictionary of Page Detail objects: key is png name."""

    def __init__(self) -> None:
        """Initialize dictionary."""
        super().__init__()

    def recalculate(self) -> None:
        """Recalculate labels from details."""
        number = 0
        style = STYLE_ARABIC
        for _, detail in sorted(self.items()):
            if detail["style"] != STYLE_DITTO:
                style = detail["style"]
            if detail["number"] == NUMBER_NONE:
                detail["label"] = ""
            else:
                if detail["number"] == NUMBER_INCREMENT:
                    number += 1
                else:
                    number = int(detail["number"])
                if style == STYLE_ROMAN:
                    try:
                        label = roman.toRoman(number).lower()
                    except roman.OutOfRangeError:
                        label = "Roman error"
                else:
                    label = str(number)
                detail["label"] = PAGE_LABEL_PREFIX + label

    def png_from_label(self, label: str) -> str:
        """Find the png corresponding to the page with the given label.

        Args:
            label: The label to match against.

        Returns:
            The png number corresponding to the given label, or empty string.
        """
        for png, detail in self.items():
            if detail["label"] == label:
                return png
        return ""

    def copy_details_from(self, details: "PageDetails") -> None:
        """Copy the style and number details from given PageDetails

        Args:
            details: Details to copy from.
        """
        for img, detail in details.items():
            self[img] = PageDetail("", detail["style"], detail["number"])
        self.recalculate()


class PageDetailsDialog(OkCancelDialog):
    """A dialog that allows the user to view/edit page details.

    Attributes:
        master_details: Dictionary of page details as used by text file.
        details: Temporary dictionary to hold values as changed in dialog.
        changed: True if any changes have been made in dialog.
    """

    def __init__(self, parent: tk.Tk, page_details: PageDetails) -> None:
        """Initialize ``labels`` and ``entries`` to empty dictionaries."""
        self.master_details = page_details
        self.details = PageDetails()
        self.details.copy_details_from(self.master_details)
        self.changed = False
        super().__init__(parent, "Configure Page Labels")

    def body(self, frame: tk.Frame) -> tk.Frame:
        """Override default to construct widgets needed to show page labels"""
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.pack(expand=True, fill=tk.BOTH)

        columns = (COL_HEAD_IMG, COL_HEAD_STYLE, COL_HEAD_NUMBER, COL_HEAD_LABEL)
        widths = (50, 80, 80, 120)
        self.list = ttk.Treeview(
            frame, columns=columns, show="headings", height=10, selectmode=tk.BROWSE
        )
        for col in range(len(columns)):
            self.list.column(
                f"#{col + 1}",
                minwidth=10,
                width=widths[col],
                stretch=False,
                anchor=tk.CENTER,
            )
            self.list.heading(f"#{col + 1}", text=columns[col])

        self.list.bind("<ButtonRelease-1>", self.item_clicked)
        self.list.grid(row=0, column=0, sticky=tk.NSEW)

        self.scrollbar = ttk.Scrollbar(
            frame, orient=tk.VERTICAL, command=self.list.yview
        )
        self.list.configure(yscroll=self.scrollbar.set)  # type: ignore[call-overload]
        self.scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.populate_list(self.details)
        return frame

    def populate_list(self, details: PageDetails, see_index: int = 0) -> None:
        """Populate the page details list from the given details.

        Args:
            details: PageDetails to be displayed in dialog.
            see_index: Index of item in list that should be made visible.
        """
        children = self.list.get_children()
        for child in children:
            self.list.delete(child)

        for png, detail in sorted(details.items()):
            entry = (png, detail["style"], detail["number"], detail["label"])
            self.list.insert("", tk.END, values=entry)

        children = self.list.get_children()
        if children:
            self.list.see(children[see_index])
            self.list.selection_set(children[see_index])

    def item_clicked(self, event: tk.Event) -> None:
        """Called when page detail item is clicked.

        If click is in style or number column, then advance style/number
        setting to the next value. Refresh the list to show new labels.
        """
        col_id = self.list.identify_column(event.x)
        if col_id not in (STYLE_COLUMN, NUMBER_COLUMN):
            return

        row_id = self.list.identify_row(event.y)
        row = self.list.set(row_id)

        if col_id == STYLE_COLUMN:
            if COL_HEAD_STYLE not in row:
                return
            # Click in style column advances style
            new_value = STYLE_NEXT[row[COL_HEAD_STYLE]]
            self.details[row[COL_HEAD_IMG]]["style"] = new_value
        elif col_id == NUMBER_COLUMN:
            if COL_HEAD_NUMBER not in row:
                return
            # Click in number column advances number type.
            # May need to prompt user for page number.
            value = row[COL_HEAD_NUMBER]
            if value.isdecimal():
                value = NUMBER_PAGENUM
            new_value = NUMBER_NEXT[value]
            if new_value == NUMBER_PAGENUM:
                pagenum = simpledialog.askinteger(
                    "Set Number", "Enter page number", parent=self
                )
                new_value = pagenum if pagenum else value
            self.details[row[COL_HEAD_IMG]]["number"] = new_value

        # Refresh the list
        self.details.recalculate()
        self.populate_list(self.details, self.list.index(row_id))
        self.changed = True

    def ok_press_complete(self) -> bool:
        """Overridden to update page label settings from the dialog."""
        if self.changed:
            self.master_details.copy_details_from(self.details)
            maintext().set_modified(True)
        return True
