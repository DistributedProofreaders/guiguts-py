# Handy functions related to tk
#

import platform


#
# Functions to check which OS/windowing system is being used
def isMac():
    return _isWindowingSystem("Darwin")


def isWindows():
    return _isWindowingSystem("Windows")


def isX11():
    return _isWindowingSystem("Linux")


def _isWindowingSystem(system):
    try:
        _isWindowingSystem.windowsystem
    except AttributeError:
        _isWindowingSystem.windowsystem = platform.system()
        if _isWindowingSystem.windowsystem not in ["Darwin", "Linux", "Windows"]:
            raise Exception("Unknown windowing system")
    return _isWindowingSystem.windowsystem == system
