"""Test functions for Checker tools."""

import pytest

from guiguts.application import Guiguts
from guiguts.file import the_file
from guiguts.spell import spell_check, SpellCheckerDialog
from guiguts.tools.jeebies import jeebies_check, JeebiesCheckerDialog
from guiguts.tools.pphtml import PPhtmlChecker, PPhtmlCheckerDialog
from guiguts.tools.pptxt import pptxt, PPtxtCheckerDialog
from .test_support import run_test


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
    run_test(
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
    run_test(
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
    run_test(
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
    run_test(
        base_in,
        base_exp,
        lambda: PPhtmlChecker().run(),
        PPhtmlCheckerDialog,
    )
