"""Handle Tk root window"""


from enum import StrEnum, auto
import logging
import traceback
import tkinter as tk

from types import TracebackType
from typing import Any

from guiguts.maintext import maintext
from guiguts.preferences import preferences, PrefKey
from guiguts.utilities import is_x11
from guiguts.widgets import grab_focus

logger = logging.getLogger(__package__)

_the_root = None  # pylint: disable=invalid-name


class RootWindowState(StrEnum):
    """Enum class to store root window states."""

    NORMAL = auto()
    ZOOMED = auto()
    FULLSCREEN = auto()


class Root(tk.Tk):
    """Inherits from Tk root window"""

    def __init__(self, **kwargs: Any) -> None:
        global _the_root
        assert _the_root is None
        _the_root = self

        super().__init__(**kwargs)
        self.geometry(preferences.get(PrefKey.ROOT_GEOMETRY))

        self.full_screen_var = tk.BooleanVar(
            value=preferences.get(PrefKey.ROOT_GEOMETRY_STATE)
            == RootWindowState.FULLSCREEN
        )
        self.allow_config_saves = False

        self.option_add("*tearOff", preferences.get(PrefKey.TEAROFF_MENUS))
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
        do a save, because the flag will only be true on the first call.

        Will do nothing until enabled via a call to set_zoom_fullscreen."""
        if self.allow_config_saves and self.save_config:
            zoomed = (
                root().wm_attributes("-zoomed")
                if is_x11()
                else (self.state() == "zoomed")
            )
            state = RootWindowState.ZOOMED if zoomed else RootWindowState.NORMAL
            fullscreen = root().wm_attributes("-fullscreen")
            self.full_screen_var.set(fullscreen)
            if fullscreen:
                state = RootWindowState.FULLSCREEN
            # Only save geometry if "normal". Then de-maximize should restore correct size and top-left.
            if state == RootWindowState.NORMAL:
                preferences.set(PrefKey.ROOT_GEOMETRY, self.geometry())
            preferences.set(PrefKey.ROOT_GEOMETRY_STATE, state)

    def set_zoom_fullscreen(self) -> None:
        """Set zoomed/fullscreen state appropriately for platform.

        Also enable saving of config after this point, to avoid confusion as the window gets created.
        """
        state = preferences.get(PrefKey.ROOT_GEOMETRY_STATE)
        if state == RootWindowState.ZOOMED:
            if is_x11():
                root().wm_attributes("-zoomed", True)
            else:
                self.state("zoomed")
        elif state == RootWindowState.FULLSCREEN:
            self.wm_attributes("-fullscreen", True)
        self.allow_config_saves = True


def root() -> Root:
    """Return the single instance of Root"""
    assert _the_root is not None
    return _the_root
