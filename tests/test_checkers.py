"""Test functions"""

from pathlib import Path
import tkinter as tk
from typing import Callable

import pytest

from guiguts.application import Guiguts
from guiguts.checkers import CheckerDialog
from guiguts.file import the_file
from guiguts.spell import spell_check, SpellCheckerDialog
from guiguts.tools.jeebies import jeebies_check, JeebiesCheckerDialog
from guiguts.tools.pphtml import PPhtmlChecker, PPhtmlCheckerDialog
from guiguts.tools.pptxt import pptxt, PPtxtCheckerDialog


@pytest.mark.parametrize(
    "base_in, base_exp",
    [
        ("raw_ctf.txt", "spell1.txt"),
        ("pp_complete.txt", "spell2.txt"),
    ],
)
def test_spellcheck_output(
    guiguts_app: Guiguts, base_in: str, base_exp: str  # pylint: disable=unused-argument
) -> None:
    """Test the spellchecker."""
    run_checker_test(
        base_in,
        base_exp,
        lambda: spell_check(
            the_file().project_dict,
            the_file().add_good_word_to_project_dictionary,
            the_file().add_good_word_to_global_dictionary,
        ),
        SpellCheckerDialog,
    )


@pytest.mark.parametrize(
    "base_in, base_exp",
    [
        ("raw_ctf.txt", "jeebies1.txt"),
        ("pp_complete.txt", "jeebies2.txt"),
    ],
)
def test_jeebies_output(
    guiguts_app: Guiguts, base_in: str, base_exp: str  # pylint: disable=unused-argument
) -> None:
    """Test Jeebies."""
    run_checker_test(
        base_in,
        base_exp,
        jeebies_check,
        JeebiesCheckerDialog,
    )


@pytest.mark.parametrize(
    "base_in, base_exp",
    [
        ("raw_ctf.txt", "pptxt1.txt"),
        ("pp_complete.txt", "pptxt2.txt"),
    ],
)
def test_pptxt_output(
    guiguts_app: Guiguts, base_in: str, base_exp: str  # pylint: disable=unused-argument
) -> None:
    """Test PPtxt."""
    run_checker_test(
        base_in,
        base_exp,
        lambda: pptxt(the_file().project_dict),
        PPtxtCheckerDialog,
    )


@pytest.mark.parametrize(
    "base_in, base_exp",
    [
        ("raw_ctf.txt", "pphtml1.txt"),
        ("pp_complete.html", "pphtml2.txt"),
    ],
)
def test_pphtml_output(
    guiguts_app: Guiguts, base_in: str, base_exp: str  # pylint: disable=unused-argument
) -> None:
    """Test PPhtml."""
    run_checker_test(
        base_in,
        base_exp,
        lambda: PPhtmlChecker().run(),
        PPhtmlCheckerDialog,
    )


def run_checker_test(
    base_in: str, base_exp: str, run_func: Callable, dialog: type[CheckerDialog]
) -> None:
    """Test a checker tool.

    Args:
        base_in: Name of file to load, e.g. "test1.txt".
        base_exp: Name of file containing expected results, e.g. "spell1.txt".
        run_func: Function to run to test the tool.
        dialog: Class of dialog that will contain results.
    """
    test_dir = Path(__file__).parent
    input_file = test_dir / "input" / base_in
    expected_file = test_dir / "expected" / base_exp
    failed_output_file = test_dir / "actual" / base_exp

    the_file().open_file(str(input_file))
    run_func()
    dlg = dialog.get_dialog()
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
