"""Common code/classes relating to dialogs."""

import tkinter as tk
from tkinter import simpledialog, ttk


class OkCancelDialog(simpledialog.Dialog):
    """A Tk simpledialog with OK and Cancel buttons and some overridden
    methods to avoid duplicated application code.
    """

    def __init__(self, parent: tk.Tk, title: str) -> None:
        """Initialize the dialog."""
        super().__init__(parent, title)

    def buttonbox(self) -> None:
        """Override default to set up OK and Cancel buttons."""
        frame = ttk.Frame(self, padding=5)
        frame.pack()
        ok_button = ttk.Button(
            frame, text="OK", default="active", command=self.ok_pressed
        )
        ok_button.grid(column=1, row=1)
        cancel_button = ttk.Button(
            frame, text="Cancel", default="normal", command=self.cancel_pressed
        )
        cancel_button.grid(column=2, row=1)
        self.bind("<Return>", lambda event: self.ok_pressed())
        self.bind("<Escape>", lambda event: self.cancel_pressed())

    def ok_press_complete(self) -> bool:
        """Complete processing needed when OK is pressed, e.g. storing
        dialog values in persistent variables.

        Will usually be overridden.

            Returns:
                True if OK to close dialog, False if not
        """
        return True

    def ok_pressed(self) -> None:
        """Update page label settings from the dialog."""
        if self.ok_press_complete():
            self.destroy()

    def cancel_pressed(self) -> None:
        """Destroy dialog."""
        self.destroy()
