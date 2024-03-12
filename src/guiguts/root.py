"""Handle Tk root window"""


import logging
import traceback
import tkinter as tk

from types import TracebackType
from typing import Any

from guiguts.maintext import maintext
from guiguts.preferences import preferences
from guiguts.widgets import grab_focus

logger = logging.getLogger(__package__)

_the_root = None


class Root(tk.Tk):
    """Inherits from Tk root window"""

    def __init__(self, **kwargs: Any) -> None:
        global _the_root
        assert _the_root is None
        _the_root = self

        super().__init__(**kwargs)
        self.geometry(preferences.get("RootGeometry"))
        self.option_add("*tearOff", False)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.after_idle(lambda: grab_focus(self, maintext(), True))
        self.set_tcl_word_characters()
        self.save_config = False
        self.bind("<Configure>", self._handle_config)

    def report_callback_exception(
        self, exc: type[BaseException], val: BaseException, tb: TracebackType | None
    ) -> None:
        """Override tkinter exception reporting rather just
        writing it to stderr.
        """
        err = "Tkinter Exception\n" + "".join(traceback.format_exception(exc, val, tb))
        logger.error(err)

    def set_tcl_word_characters(self) -> None:
        """Configure which characters are considered word/non-word characters by tcl.

        Alphanumerics & stright/curly apostrophe will be considered word characters.
        These affect operations such as double-click to select word, Cmd/Ctrl left/right
        to move forward/backward a word at a time, etc.
        See https://wiki.tcl-lang.org/page/tcl%5Fwordchars for more info.
        """
        # Trigger tcl to autoload library that defines variables we want to override.
        self.tk.call("tcl_wordBreakAfter", "", 0)
        # Set word and non-word characters
        self.tk.call("set", "tcl_wordchars", r"[[:alnum:]'’]")
        self.tk.call("set", "tcl_nonwordchars", r"[^[:alnum:]'’]")

    def _handle_config(self, _event: tk.Event) -> None:
        """Callback from root dialog <Configure> event.

        By setting flag now, and queuing calls to _save_config,
        we ensure the flag will be true for the first call to
        _save_config when process becomes idle."""
        self.save_config = True
        self.after_idle(self._save_config)

    def _save_config(self) -> None:
        """Only save geometry when process becomes idle.

        Several calls to this may be queued by config changes during
        root dialog creation and resizing. Only the first will actually
        do a save, because the flag will only be true on the first call."""
        if self.save_config:
            preferences.set("RootGeometry", self.geometry())


def root() -> Root:
    """Return the single instance of Root"""
    assert _the_root is not None
    return _the_root
