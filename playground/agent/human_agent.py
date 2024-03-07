import logging
import time
from typing import Any

import numpy as np
import requests

from playground.agent.base_agent import Agent
from playground.agent.runtime import PythonRuntime, RemotePythonRuntime
from playground.config import Config
from playground.llm.base_model import BaseModel

config = Config()
logger = logging.getLogger(__name__)


class HumanAgent(Agent):
    """Human agents for Human-recorder"""

    def __init__(self) -> None:
        self.instruction: str = ""
        self.trajectory: list[dict[str, Any]] = []
        self.runtime: PythonRuntime | RemotePythonRuntime | None = None

        self.cur_prompt: list[dict[str, Any]] | None = None
        self.cur_response: str | None = None
        self.cur_info: dict[str, Any] = {}
        self.cur_raw_code: str = ""
        self.model = BaseModel()  # Dummy model

    def reset(self, instruction: str) -> None:
        super().reset(instruction=instruction)

    def step_action(self, confirmed: bool, **kwargs) -> tuple[dict, bool]:
        """Executes the code and record the result."""
        obs = kwargs.get("obs", None)
        code = kwargs.get("code", "")
        self.cur_obs = obs
        self.cur_raw_code = code
        result = {}

        logger.debug(f"Code to execute:\n{code}\n")
        if config.remote:
            response = requests.post(
                f"http://{config.env_server_addr}:{config.env_server_port}/execute",
                json={"message": code},
            )
            result = response.json()
        else:
            assert self.runtime is not None, "The agent needs to reset first."
            result = self.runtime(code)

        self.trajectory.append(
            {
                "obs": self.cur_obs,
                "prompt": self.cur_prompt,
                "response": self.cur_response,
                "info": self.cur_info,
                "act": self.cur_raw_code,
                "res": result,
                "timestamp": time.time(),
            }
        )
        logger.info(f"Output: {result}")

        return result, True

    def generate_action(self, obs: np.ndarray | None) -> tuple[str, str]:
        """This function shouldn't be called by human agents."""
        raise NotImplementedError

    def trajectory2intermediate_msg(self) -> list[dict[str, Any]]:
        """This function shouldn't be called by human agents."""
        raise NotImplementedError

    def eval(self) -> dict[str, Any]:
        """This function shouldn't be called by human agents."""
        raise NotImplementedError
