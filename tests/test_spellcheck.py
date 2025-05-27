"""Test functions"""

from pathlib import Path
import tkinter as tk
from typing import Callable

from guiguts.application import Guiguts
from guiguts.checkers import CheckerDialog
from guiguts.file import the_file
from guiguts.spell import spell_check, SpellCheckerDialog


def test_spellcheck_output(
    guiguts_app: Guiguts,  # pylint: disable=unused-argument
) -> None:
    """Test the spellchecker."""
    run_tool_test(
        "spell1.txt",
        lambda: spell_check(
            the_file().project_dict,
            the_file().add_good_word_to_project_dictionary,
            the_file().add_good_word_to_global_dictionary,
        ),
        SpellCheckerDialog,
    )


def run_tool_test(
    basename: str, run_func: Callable, dialog: type[CheckerDialog]
) -> None:
    """Test a checker tool.

    Args:
        basename: Name of file to load, e.g. "spell1.txt".
        run_func: Function to run to test the tool.
        dialog: Class of dialog that will contain results.
    """
    test_dir = Path(__file__).parent
    input_file = test_dir / "input" / basename
    expected_file = test_dir / "expected" / basename
    failed_output_file = test_dir / "actual" / basename

    the_file().open_file(str(input_file))
    run_func()
    dlg = dialog.get_dialog()
    assert dlg is not None
    actual_output = dlg.text.get("1.0", tk.END)

    expected_output = expected_file.read_text(encoding="utf-8")

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
