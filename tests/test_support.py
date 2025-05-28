"""Support functions for testing."""

from pathlib import Path
import tkinter as tk
from typing import Callable, Optional

from guiguts.checkers import CheckerDialog
from guiguts.file import the_file
from guiguts.maintext import maintext


def run_test(
    base_in: str,
    base_exp: str,
    run_func: Callable,
    dialog_class: Optional[type[CheckerDialog]] = None,
) -> None:
    """Test a checker tool.

    Args:
        base_in: Name of file to load, e.g. "test1.txt".
        base_exp: Name of file containing expected results, e.g. "spell1.txt".
        run_func: Function to run to test the tool.
        dialog_class: Class of dialog that will contain results, or None to use main text.
    """
    test_dir = Path(__file__).parent
    input_file = test_dir / "input" / base_in
    expected_file = test_dir / "expected" / base_exp
    failed_output_file = test_dir / "actual" / base_exp

    the_file().open_file(str(input_file))
    run_func()
    if dialog_class is None:
        actual_output = maintext().get_text()
    else:
        dlg = dialog_class.get_dialog()
        assert dlg is not None
        actual_output = dlg.text.get("1.0", tk.END)

    try:
        expected_output = expected_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        expected_output = ""

    if actual_output == expected_output:
        failed_output_file.unlink(
            missing_ok=True
        )  # Don't leave old failures lying around
    else:
        failed_output_file.parent.mkdir(parents=True, exist_ok=True)
        failed_output_file.write_text(actual_output, encoding="utf-8")
        assert (
            actual_output == expected_output
        ), f"Output mismatch. See: {failed_output_file}"
