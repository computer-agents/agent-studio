from typing import Generator

import pytest

from desktop_env.computer.env import ComputerEnv


@pytest.fixture(scope="function")
def computer_env() -> Generator[ComputerEnv, None, None]:
    """Create a ComputerEnv instance for testing.
    It is automatically closed after the test session.
    """
    env = ComputerEnv()
    yield env
    env.close()
