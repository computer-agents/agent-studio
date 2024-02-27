import logging
from typing import Any

import requests
from numpy.typing import NDArray

from playground.config import Config
from playground.llm.base_model import BaseModel

config = Config()
logger = logging.getLogger(__name__)


class Agent:
    """Base class for agents."""

    def __init__(self, env: str, model: BaseModel, record_path: str) -> None:
        self.env = env
        self.model = model
        match env:
            case "desktop":
                from playground.env.desktop_env.recorder.agent_recorder import (
                    AgentRecorder,
                )

                self.recorder = AgentRecorder(record_path=record_path)
            case _:
                raise ValueError(f"Invalid env: {env}.")
        self.instruction: str = ""
        self.trajectory: list[dict[str, Any]] = []
        self.record_screen: bool = False

    def reset(
        self,
        task_id: str,
        instruction: str,
        record_screen: bool = False,
    ) -> None:
        self.instruction = instruction
        self.trajectory = []
        self.record_screen = record_screen

        if self.record_screen:
            self.recorder.reset(
                task_id=task_id, instruction=instruction, record_screen=record_screen
            )
            self.recorder.start()

    def step(self, code: str) -> dict:
        """Executes and records the given code in the environment."""
        logger.debug(f"Executing code:\n{code}\n")
        user_input = (
            input(f"Executing code:\n{code}\nDo you want to continue? (y/n): ")
            .strip()
            .lower()
        )
        confirmed = user_input == "y"
        result = {}
        if confirmed:
            response = requests.post(
                f"http://{config.env_server_addr}:{config.env_server_port}/execute",
                json={"message": code},
            )
            print(response.json())
            result = response.json()
        else:
            result["content"] = "Cancelled by user."
        logger.info(f"Output: {result}\n")

        return result

    def run(self) -> list:
        """The main logic of the agent.

        Returns: The trajectory of the agent.
        """
        raise NotImplementedError

    def get_obs(self) -> NDArray | None:
        """Gets the observation from the environment."""
        assert not config.use_video, "Video-as-observation is not supported yet."
        if self.record_screen:
            obs = self.recorder.get_screenshot()
        else:
            obs = None

        return obs
