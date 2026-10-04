"""Handle Tk root window"""

import ctypes
import ctypes.util
from enum import StrEnum, auto
import logging
import traceback
import tkinter as tk
from tkinter import ttk

from types import TracebackType
from typing import Any
from ttkthemes import ThemedTk

from guiguts.preferences import preferences, PrefKey
from guiguts.utilities import is_mac, is_x11

logger = logging.getLogger(__package__)

_the_root = None


class RootWindowState(StrEnum):
    """Enum class to store root window states."""

    NORMAL = auto()
    ZOOMED = auto()
    FULLSCREEN = auto()


class Root(ThemedTk):
    """Inherits from Tk root window"""

    def __init__(self, **kwargs: Any) -> None:
        global _the_root
        assert _the_root is None
        _the_root = self

        super().__init__(**kwargs)
        self.geometry(preferences.get(PrefKey.ROOT_GEOMETRY))

        preferences.set(
            PrefKey.ROOT_GEOMETRY_FULL_SCREEN,
            preferences.get(PrefKey.ROOT_GEOMETRY_STATE) == RootWindowState.FULLSCREEN,
        )
        self.allow_config_saves = False

        self.option_add(
            "*tearOff", preferences.get(PrefKey.TEAROFF_MENU_TYPE) == "builtin"
        )
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.set_tcl_word_characters()
        self.save_config = False
        self.bind("<Configure>", self._handle_config)

        # Make Ctrl-A select all in Entries/Comboboxes on Linux only
        # Works by default on Windows/macOS (Cmd-A)
        if is_x11():

            def select_all(event: tk.Event) -> str:
                assert isinstance(event.widget, (ttk.Entry, ttk.Combobox))
                event.widget.selection_range(0, tk.END)
                return "break"

            self.bind_class("TEntry", "<Control-a>", select_all)
            self.bind_class("TEntry", "<Control-A>", select_all)
            self.bind_class("TCombobox", "<Control-a>", select_all)
            self.bind_class("TCombobox", "<Control-A>", select_all)

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
        if is_mac():
            # Native fullscreen is disabled on macOS, so zoom instead.
            if state == RootWindowState.FULLSCREEN:
                state = RootWindowState.ZOOMED
            disable_macos_native_fullscreen(self)
        if state == RootWindowState.ZOOMED:
            if is_x11():
                root().wm_attributes("-zoomed", True)
            else:
                self.state("zoomed")
        elif state == RootWindowState.FULLSCREEN:
            # Fullscreen doesn't work quite right on macOS without withdraw
            # and deiconify. Doesn't seem to hurt other platforms to do this.
            # This is also needed to avoid the problem of dialogs on Mac
            # becoming fullscreen tabs (see widgets.py:ToplevelDialog)
            self.wm_withdraw()
            self.wm_attributes("-fullscreen", True)
            self.wm_deiconify()
        self.allow_config_saves = True


def disable_macos_native_fullscreen(window: tk.Misc) -> None:
    """Make the macOS green title-bar button zoom the window rather than
    putting it into native fullscreen mode, which Guiguts doesn't handle well.

    Applied now (if window is currently a toplevel) and whenever the window is mapped
    in future, because Tk resets the behavior in an idle callback whenever a window
    is (re)mapped, e.g. restored from Dock, or a frame becomes a toplevel via wm_manage.

    Args:
        window: Root, Toplevel, or frame that will become a toplevel via wm_manage.
    """
    if not is_mac():
        return
    # Toplevel bindtag means children's Map events arrive here too - ignore them.
    window.bind(
        "<Map>",
        lambda event: (
            window.after(10, _set_ns_window_fullscreen_none, window)
            if event.widget is window
            else None
        ),
        add=True,
    )
    _set_ns_window_fullscreen_none(window)


def _set_ns_window_fullscreen_none(window: tk.Misc) -> None:
    """Change the NSWindow for the given toplevel so it can't go native fullscreen.

    Tk gives no control over this, so the NSWindow's collectionBehavior is
    changed via the Objective-C runtime. Any failure is logged and ignored.
    """
    if not window.winfo_exists() or window.tk.call("winfo", "toplevel", window) != str(
        window
    ):
        return  # E.g. image viewer frame when docked
    full_screen_primary = 1 << 7  # NSWindowCollectionBehaviorFullScreenPrimary
    full_screen_none = 1 << 9  # NSWindowCollectionBehaviorFullScreenNone
    title = window.tk.call("wm", "title", window)
    try:
        libobjc_path = ctypes.util.find_library("objc")
        assert libobjc_path is not None
        objc = ctypes.cdll.LoadLibrary(libobjc_path)
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        msg_send_addr = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
        assert msg_send_addr is not None

        def send(restype: Any, obj: Any, selector: str, *args: Any) -> Any:
            """Send Objective-C message. Needs exact prototype (not variadic) on arm64.
            Only NSUInteger arguments are needed here."""
            prototype = ctypes.CFUNCTYPE(
                restype, ctypes.c_void_p, ctypes.c_void_p, *[ctypes.c_ulong] * len(args)
            )
            func = prototype(msg_send_addr)
            return func(obj, objc.sel_registerName(selector.encode()), *args)

        # Tk doesn't expose the NSWindow, so temporarily give the window a unique
        # title, and find the NSWindow with that title.
        unique_title = f"guiguts-fullscreen-none-{id(window)}"
        window.tk.call("wm", "title", window, unique_title)
        window.update_idletasks()
        app = send(
            ctypes.c_void_p, objc.objc_getClass(b"NSApplication"), "sharedApplication"
        )
        ns_windows = send(ctypes.c_void_p, app, "windows")
        for idx in range(send(ctypes.c_ulong, ns_windows, "count")):
            ns_window = send(ctypes.c_void_p, ns_windows, "objectAtIndex:", idx)
            ns_title = send(ctypes.c_void_p, ns_window, "title")
            if send(ctypes.c_char_p, ns_title, "UTF8String") != unique_title.encode():
                continue
            behavior = send(ctypes.c_ulong, ns_window, "collectionBehavior")
            behavior = (behavior & ~full_screen_primary) | full_screen_none
            send(None, ns_window, "setCollectionBehavior:", behavior)
            break
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug(f"Unable to disable macOS native fullscreen: {exc}")
    finally:
        window.tk.call("wm", "title", window, title)


def root() -> Root:
    """Return the single instance of Root"""
    assert _the_root is not None
    return _the_root
