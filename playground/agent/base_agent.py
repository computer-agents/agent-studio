import logging
from typing import Any

import requests

from playground.agent.runtime import PythonRuntime
from playground.config import Config
from playground.llm.base_model import BaseModel
from playground.utils.human_utils import confirm_action

config = Config()
logger = logging.getLogger(__name__)


class Agent:
    """Base class for agents."""

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.instruction: str = ""
        self.trajectory: list[dict[str, Any]] = []

        if not config.remote:
            self.runtime: PythonRuntime | None = None

    def reset(
        self,
        instruction: str,
    ) -> None:
        self.instruction = instruction
        self.trajectory = []

        if not config.remote:
            if self.runtime is not None:
                self.runtime.close()
            self.runtime = PythonRuntime()

    def step(self, code: str) -> dict:
        """Executes and records the given code in the environment."""
        logger.debug(f"Executing code:\n{code}\n")

        confirmed, _ = confirm_action(f"Executing code:\n{code}")(lambda: True)()
        result = {}
        if confirmed:
            if config.remote:
                response = requests.post(
                    f"http://{config.env_server_addr}:{config.env_server_port}/execute",
                    json={"message": code},
                )
                print(response.json())
                result = response.json()
            else:
                assert self.runtime is not None, "The agent needs to reset first."
                result = self.runtime.exec(code)
        else:
            result["content"] = "Cancelled by user."
        logger.info(f"Output: {result}\n")

        return result

    def run(self) -> list:
        """The main logic of the agent.

        Returns: The trajectory of the agent.
        """
        raise NotImplementedError

    def close(self) -> None:
        if self.runtime is not None:
            self.runtime.close()
