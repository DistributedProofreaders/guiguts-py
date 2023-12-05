"""Configure pytest"""

import utilities


def pytest_configure(config):
    """Set flag so application code can detect if within a pytest run

    See: https://pytest.org/en/7.4.x/example/simple.html#detect-if-running-from-within-a-pytest-run
    """
    utilities._called_from_test = True
