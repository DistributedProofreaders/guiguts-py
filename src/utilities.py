"""Handy utility functions"""

import platform


#
# Functions to check which OS is being used
def isMac():
    """Return true if running on Mac"""
    return _is_system("Darwin")


def isWindows():
    """Return true if running on Windows"""
    return _is_system("Windows")


def isX11():
    """Return true if running on Linux"""
    return _is_system("Linux")


def _is_system(system):
    """Return true if running on given system"""
    try:
        return _is_system.system == system
    except AttributeError:
        _is_system.system = platform.system()
        if _is_system.system not in ["Darwin", "Linux", "Windows"]:
            raise Exception("Unknown windowing system")
        return _is_system.system == system
