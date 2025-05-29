"""Test functions for tools that modify main text."""

import pytest

from guiguts.application import Guiguts
from guiguts.html_convert import do_html_autogenerate, HTMLGeneratorDialog
from .test_support import run_test


@pytest.mark.parametrize(
    "base_in, base_exp",
    [
        ("raw_ctf.txt", "htmlconvert1.txt"),
        ("pre_htmlgen.txt", "htmlconvert2.txt"),
    ],
)
def test_htmlconvert_output(
    guiguts_app: Guiguts, base_in: str, base_exp: str  # pylint: disable=unused-argument
) -> None:
    """Test the HTML conversion tool."""

    def do_test_htmlconvert() -> None:
        """Execute necessary commands to do HTML conversion."""
        HTMLGeneratorDialog.show_dialog()
        do_html_autogenerate()
        if dlg := HTMLGeneratorDialog.get_dialog():
            dlg.destroy()

    run_test(
        base_in,
        base_exp,
        do_test_htmlconvert,
    )
