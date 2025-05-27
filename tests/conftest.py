"""Configure pytest."""

from typing import Generator

import pytest

from guiguts.application import Guiguts
from guiguts.root import root


@pytest.fixture
def guiguts_app() -> Generator[Guiguts, None, None]:
    """Start GG in "test" mode"""
    app = Guiguts(args=["--nohome"])  # Force command line args
    yield app  # Don't enter event loop
    root().destroy()  # Cleanup after test
