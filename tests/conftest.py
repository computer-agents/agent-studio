import logging

import pytest


def pytest_configure():
    """Add logger to pytest."""
    pytest.logger = logging.getLogger(__name__)
