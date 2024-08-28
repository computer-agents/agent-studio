import logging
import time
from typing import Any

import numpy as np

from agent_studio.agent.base_agent import BaseAgent, StepInfo
from agent_studio.config import Config

config = Config()
logger = logging.getLogger(__name__)


class HumanAgent(BaseAgent):
    """Human agents for Human-recorder"""

    name = "human"

    def step_action(self, confirmed: bool) -> tuple[dict, bool]:
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
        if self.step_info is None:
            raise ValueError("step_info is None")
        code = self.step_info.action
        logger.debug(f"Code to execute:\n{code}\n")
        result = self.runtime(code)

        self.step_info.result = result
        self.step_info.timestamp = time.time()
        self.trajectory.append(self.step_info)
        self.step_info = StepInfo(
            obs=None,
            prompt=None,
            response=None,
            action="",
            info={},
            result={},
            timestamp=0.0,
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
