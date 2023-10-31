# Handy functions related to tk
#
# Attempt to avoid passing root & maintext widgets everywhere for the
# few places they are needed - to be reviewed/reconsidered
# Maybe use singleton classes for root, maintext, mainimage
# - only appropriate if certain there will only be one instance

import re
import tkinter as tk


#
# Functions to check which OS/windowing system is being used
def isMac():
    return _isWindowingSystem("aqua")


def isWindows():
    return _isWindowingSystem("win32")


def isX11():
    return _isWindowingSystem("x11")


def _isWindowingSystem(system):
    try:
        _isWindowingSystem.windowsystem
    except AttributeError:
        _isWindowingSystem.windowsystem = ggRoot().tk.call("tk", "windowingsystem")
        if _isWindowingSystem.windowsystem not in ["aqua", "win32", "x11"]:
            raise Exception("Unknown windowing system")
    return _isWindowingSystem.windowsystem == system


#
# Set/return root widget
def ggRoot(root=None):
    if root:
        ggRoot.root = root
    return ggRoot.root


#
# Set/return main text widget
def ggMainText(maintext=None):
    if maintext:
        ggMainText.maintext = maintext
    return ggMainText.maintext


#
# Set/return main image widget
def ggMainImage(mainimage=None):
    if mainimage:
        ggMainImage.mainimage = mainimage
    return ggMainImage.mainimage


#
# Bind lower & uppercase versions of keyevent to handler
# in main text window
def keyBind(keyevent, handler):
    lk = re.sub("[A-Z]>$", lambda m: m.group(0).lower(), keyevent)
    uk = re.sub("[A-Z]>$", lambda m: m.group(0).upper(), keyevent)
    ggMainText().bind(lk, handler)
    ggMainText().bind(uk, handler)


#
# Return widget that currently has focus
def focusGet():
    return ggRoot().focus_get()
