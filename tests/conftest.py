"""Configure pytest."""

import pytest

import guiguts.utilities


def pytest_configure(config: pytest.Config) -> None:  # pylint: disable=unused-argument
    """Set flag so application code can detect if within a pytest run

    See: https://pytest.org/en/7.4.x/example/simple.html#detect-if-running-from-within-a-pytest-run
    """
    guiguts.utilities.CALLED_FROM_TEST = True
