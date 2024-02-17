import logging
import time
from typing import Any

from numpy.typing import NDArray

from playground.agent.runtime import PythonRuntime
from playground.config import Config
from playground.llm.base_model import BaseModel
from playground.utils.human_utils import confirm_action

config = Config()
logger = logging.getLogger(__name__)


class Agent:
    """Base class for agents."""

    def __init__(self, env: str, model: BaseModel, record_path: str) -> None:
        self.env = env
        self.model = model
        self.runtime: PythonRuntime | None = None
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
        if self.runtime is not None:
            self.runtime.close()
        self.runtime = PythonRuntime()

        if self.record_screen:
            self.recorder.reset(
                task_id=task_id, instruction=instruction, record_screen=record_screen
            )
            self.recorder.start()

    def step(self, code: str) -> dict:
        """Executes and records the given code in the environment."""

        @confirm_action
        def _step_helper(code: str) -> dict:
            if self.record_screen:
                self.recorder.resume()
                time.sleep(0.5)
            assert self.runtime is not None, "The agent is not reset."
            return self.runtime.exec(code)

        if self.record_screen:
            self.recorder.pause()
        logger.info(f"Executing code:\n{code}\n")
        result = _step_helper(code)
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

    def close(self) -> None:
        if self.runtime is not None:
            self.runtime.close()
