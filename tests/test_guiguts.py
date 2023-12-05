"""Test functions"""

from file import File
from mainwindow import _process_label, _process_accel
from preferences import preferences
from utilities import is_mac, is_windows, is_x11, _is_system


def test_which_os():
    """Test the OS checking functions"""
    assert is_mac() or is_windows() or is_x11()
    assert not _is_system("Android")


def test_file():
    """Test the File class"""
    ff = File(lambda: None)
    ff.filename = "dummy.txt"
    assert ff.filename == "dummy.txt"


def test_preferences():
    """Test the Preferences class"""
    assert preferences.get_default("pkey1") is None
    preferences.set_default("pkey1", "pdefault1")
    assert preferences.get_default("pkey1") == "pdefault1"
    preferences.set("pkey1", "pvalue1")
    assert preferences.get("pkey1") == "pvalue1"
    assert preferences.get_default("pkey1") == "pdefault1"
    keys = preferences.keys()
    assert len(keys) == 2
    assert "pkey1" in keys


def test_mainwindow():
    """Test mainwindow functions"""
    (tilde, text) = _process_label("~Save...")
    assert tilde == 0
    assert text == "Save..."
    (tilde, text) = _process_label("Save ~As...")
    assert tilde == 5
    assert text == "Save As..."
    (accel, event) = _process_accel("Ctrl+X")
    assert accel == "Ctrl+X"
    assert event == "<Control-X>"
    (accel, event) = _process_accel("Cmd/Ctrl+y")
    assert accel == "Ctrl+y"
    assert event == "<Control-y>"
    (accel, event) = _process_accel("Shift+Ctrl+Z")
    assert accel == "Shift+Ctrl+Z"
    assert event == "<Shift-Control-Z>"
    (accel, event) = _process_accel("Cmd+?")
    assert accel == "Cmd+?"
    assert event == "<Meta-?>"
