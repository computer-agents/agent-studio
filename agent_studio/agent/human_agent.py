import logging
import time
from typing import Any

import numpy as np
import requests

from agent_studio.agent.base_agent import BaseAgent, TrajectorySeg
from agent_studio.config import Config
from agent_studio.llm.base_model import BaseModel


config = Config()
logger = logging.getLogger(__name__)


class HumanAgent(BaseAgent):
    """Human agents for Human-recorder"""

    name = "human"

    def __init__(self) -> None:
        super().__init__(model=BaseModel())

    def reset(self, task_config: dict[str, Any], registered_evaluators: dict[str, Any]) -> None:
        super().reset(task_config=task_config, registered_evaluators={})
        with open(config.init_code_path, "r") as f:
            init_code = f.read()
            assert self.runtime is not None
            self.runtime(init_code)

    def step_action(self, confirmed: bool, **kwargs) -> tuple[dict, bool]:
        """Executes the code and record the result.

        Args:
            confirmed (bool): Whether the action is confirmed by the human.
            obs (np.ndarray | None): The observation of the environment. \
                For example, the screenshot.
            code (str): The code to execute.
            annotation (dict): The annotation of the action. For bounding box, etc.

        Returns:
            tuple[dict, bool]: The result of the execution and whether the task is done.
        """
        obs = kwargs.get("obs", None)
        code = kwargs.get("code", "")
        annotation = kwargs.get("annotation", {})
        self.cur_obs = obs
        self.cur_raw_code = code
        cur_time = time.time()
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

        assert self.cur_prompt is not None, "Invalid prompt"
        self.trajectory.append(
            TrajectorySeg(
                obs=self.cur_obs,
                prompt=self.cur_prompt,
                response=self.cur_response,
                info=self.cur_info,
                act=self.cur_raw_code,
                annotation=annotation,
                res=result,
                timestamp=cur_time,
            )
        )
        logger.info(f"Output: {result}")

        return result, True

    def generate_action(self, obs: np.ndarray | None) -> tuple[str, str]:
        """This function shouldn't be called by human agents."""
        raise NotImplementedError

    def trajectory2intermediate_msg(self) -> list[dict[str, Any]]:
        """This function shouldn't be called by human agents."""
        raise NotImplementedError

    def eval(self, final_obs: np.ndarray | None = None) -> dict[str, Any]:
        """This function shouldn't be called by human agents."""
        raise NotImplementedError
