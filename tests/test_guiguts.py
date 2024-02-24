"""Test functions"""

from guiguts.file import File
from guiguts.mainwindow import process_label, process_accel
from guiguts.preferences import preferences
from guiguts.utilities import is_mac, is_windows, is_x11, _is_system


def test_which_os() -> None:
    """Test the OS checking functions"""
    assert is_mac() or is_windows() or is_x11()
    assert not _is_system("Android")


def test_file() -> None:
    """Test the File class"""
    ff = File(lambda: None, lambda: None)
    ff.filename = "dummy.txt"
    assert ff.filename == "dummy.txt"


def test_preferences() -> None:
    """Test the Preferences class"""
    assert preferences.get_default("pkey1") is None
    preferences.set_default("pkey1", "pdefault1")
    assert preferences.get_default("pkey1") == "pdefault1"
    preferences.set("pkey1", "pvalue1")
    assert preferences.get("pkey1") == "pvalue1"
    assert preferences.get_default("pkey1") == "pdefault1"
    keys = preferences.keys()
    assert len(keys) == 1
    assert "pkey1" in keys
    preferences.set_default("pkey2", "pdefault2")
    keys = preferences.keys()
    assert len(keys) == 2
    assert "pkey1" in keys
    assert "pkey2" in keys


def test_mainwindow() -> None:
    """Test mainwindow functions"""
    (tilde, text) = process_label("~Save...")
    assert tilde == 0
    assert text == "Save..."
    (tilde, text) = process_label("Save ~As...")
    assert tilde == 5
    assert text == "Save As..."
    (accel, event) = process_accel("Ctrl+X")
    assert accel == "Ctrl+X"
    assert event == "<Control-X>"
    (accel, event) = process_accel("Cmd/Ctrl+y")
    if is_mac():
        assert accel == "Cmd+y"
        assert event == "<Meta-y>"
    else:
        assert accel == "Ctrl+y"
        assert event == "<Control-y>"
    (accel, event) = process_accel("Shift+Ctrl+Z")
    assert accel == "Shift+Ctrl+Z"
    assert event == "<Shift-Control-Z>"
    (accel, event) = process_accel("Cmd+?")
    assert accel == "Cmd+?"
    assert event == "<Command-?>"
