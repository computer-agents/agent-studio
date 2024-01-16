from typing import Generator

import pytest

from playground.desktop_env.computer.env import ComputerEnv
from playground.utils.logger import Logger


@pytest.fixture(scope="function")
def computer_env() -> Generator[ComputerEnv, None, None]:
    """Create a ComputerEnv instance for testing.
    It is automatically closed after the test session.
    """
    env = ComputerEnv()
    yield env
    # env.close()


def pytest_configure():
    """Add logger to pytest."""
    pytest.logger = Logger()
