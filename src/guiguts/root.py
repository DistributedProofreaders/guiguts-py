"""Handle Tk root window"""

import ctypes
import ctypes.util
from enum import StrEnum, auto
from functools import cache
import logging
import traceback
import tkinter as tk
from tkinter import ttk

from types import TracebackType
from typing import Any, Optional
from ttkthemes import ThemedTk

from guiguts.preferences import preferences, PrefKey
from guiguts.utilities import is_mac, is_x11

logger = logging.getLogger(__package__)

_THE_ROOT = None


class RootWindowState(StrEnum):
    """Enum class to store root window states."""

    NORMAL = auto()
    ZOOMED = auto()
    FULLSCREEN = auto()


class Root(ThemedTk):
    """Inherits from Tk root window"""

    def __init__(self, **kwargs: Any) -> None:
        global _THE_ROOT
        assert _THE_ROOT is None
        _THE_ROOT = self

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


@cache
def _objc_runtime() -> ctypes.CDLL:
    """Return the Objective-C runtime library, set up for use via ctypes."""
    libobjc_path = ctypes.util.find_library("objc")
    assert libobjc_path is not None
    objc = ctypes.cdll.LoadLibrary(libobjc_path)
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    return objc


def _objc_send(restype: Any, obj: Any, selector: str, *args: Any) -> Any:
    """Send Objective-C message. Needs exact prototype (not variadic) on arm64.
    Only NSUInteger arguments, or equivalents passed as integers, are needed here."""
    objc = _objc_runtime()
    msg_send_addr = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
    assert msg_send_addr is not None
    prototype = ctypes.CFUNCTYPE(
        restype, ctypes.c_void_p, ctypes.c_void_p, *[ctypes.c_ulong] * len(args)
    )
    func = prototype(msg_send_addr)
    return func(obj, objc.sel_registerName(selector.encode()), *args)


def _objc_send_from_event_loop(obj: Any, selector: str) -> None:
    """Queue Objective-C message, with nil argument if it takes one, to be sent
    from the event loop, in the order queued.

    Needed for messages that change window state when called from a Tk callback.
    They can make Tk call back into Python, and tkinter aborts the process if that
    happens during a ctypes call made from a Python callback.
    """
    _objc_send(
        None,
        obj,
        "performSelectorOnMainThread:withObject:waitUntilDone:",
        _objc_runtime().sel_registerName(selector.encode()),
        0,
        0,
    )


def _ns_app() -> int:
    """Return the shared NSApplication instance."""
    return _objc_send(
        ctypes.c_void_p,
        _objc_runtime().objc_getClass(b"NSApplication"),
        "sharedApplication",
    )


def _ns_ordered_windows() -> list[int]:
    """Return the app's NSWindows, front to back."""
    ns_windows = _objc_send(ctypes.c_void_p, _ns_app(), "orderedWindows")
    return [
        _objc_send(ctypes.c_void_p, ns_windows, "objectAtIndex:", idx)
        for idx in range(_objc_send(ctypes.c_ulong, ns_windows, "count"))
    ]


def _ns_visible_parentless_windows() -> list[int]:
    """Return visible NSWindows that aren't child windows, front to back.

    Pinned dialogs are child windows, which are shown/hidden with their parent.
    Ordering one out directly would detach it from its parent.
    """
    return [
        ns_window
        for ns_window in _ns_ordered_windows()
        if _objc_send(ctypes.c_bool, ns_window, "isVisible")
        and not _objc_send(ctypes.c_void_p, ns_window, "parentWindow")
    ]


def install_macos_hide_workaround(window: tk.Misc) -> None:
    """Make the macOS Hide command (Cmd-H or app menu) hide all the app's windows.

    With Tk 9, macOS hides the app's windows except for one, usually the main window,
    which is left on screen behind other apps. On hide, order that window out.
    Using NSWindows directly avoids `wm withdraw`, which brings another window to the
    front when the key window is withdrawn, and which would detach pinned dialogs.

    By the time Tk reports the hide, the stacking order is lost, so it is recorded
    whenever the focus changes, and used to restore the stacking order on unhide.

    Args:
        window: Any widget, used to access Tk.
    """
    if not is_mac() or tk.TkVersion < 9.0:
        return
    stack: list[int] = []  # Front to back
    key_window: Optional[int] = None

    def record_stack() -> None:
        if not _objc_send(ctypes.c_bool, _ns_app(), "isHidden"):
            stack[:] = _ns_visible_parentless_windows()

    def on_hide() -> None:
        nonlocal key_window
        key_window = _objc_send(ctypes.c_void_p, _ns_app(), "keyWindow")
        existing = _ns_ordered_windows()
        left_on_screen = _ns_visible_parentless_windows()
        # Windows closed since the last record must not be messaged later
        stack[:] = [ns_window for ns_window in stack if ns_window in existing]
        stack.extend(w for w in left_on_screen if w not in stack)
        for ns_window in left_on_screen:
            # Ordering out the key window without this makes macOS unhide the app
            _objc_send_from_event_loop(ns_window, "resignKeyWindow")
            _objc_send_from_event_loop(ns_window, "orderOut:")

    def on_show() -> None:
        existing = _ns_ordered_windows()
        for ns_window in reversed(stack):
            if ns_window in existing:
                _objc_send_from_event_loop(ns_window, "orderFront:")
        if key_window in existing:
            _objc_send_from_event_loop(key_window, "makeKeyWindow")

    window.bind_all("<FocusIn>", lambda _: window.after_idle(record_stack), add=True)
    window.tk.createcommand("::tk::mac::OnHide", on_hide)
    window.tk.createcommand("::tk::mac::OnShow", on_show)


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
        # Tk doesn't expose the NSWindow, so temporarily give the window a unique
        # title, and find the NSWindow with that title.
        unique_title = f"guiguts-fullscreen-none-{id(window)}"
        window.tk.call("wm", "title", window, unique_title)
        window.update_idletasks()
        app = _ns_app()
        ns_windows = _objc_send(ctypes.c_void_p, app, "windows")
        for idx in range(_objc_send(ctypes.c_ulong, ns_windows, "count")):
            ns_window = _objc_send(ctypes.c_void_p, ns_windows, "objectAtIndex:", idx)
            ns_title = _objc_send(ctypes.c_void_p, ns_window, "title")
            if (
                _objc_send(ctypes.c_char_p, ns_title, "UTF8String")
                != unique_title.encode()
            ):
                continue
            behavior = _objc_send(ctypes.c_ulong, ns_window, "collectionBehavior")
            behavior = (behavior & ~full_screen_primary) | full_screen_none
            _objc_send(None, ns_window, "setCollectionBehavior:", behavior)
            break
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.debug(f"Unable to disable macOS native fullscreen: {exc}")
    finally:
        window.tk.call("wm", "title", window, title)


def root() -> Root:
    """Return the single instance of Root"""
    assert _THE_ROOT is not None
    return _THE_ROOT
