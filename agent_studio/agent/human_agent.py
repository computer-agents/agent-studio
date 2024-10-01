import logging
import time  # noqa: F401
from typing import Any  # noqa: F401

import numpy as np

from agent_studio.agent.base_agent import RUNTIME_INIT_CODE, BaseAgent, StepInfo
from agent_studio.utils.runtime import PythonRuntime, RemotePythonRuntime
from agent_studio.config import Config
from agent_studio.utils.types import TaskConfig

config = Config()
logger = logging.getLogger(__name__)


class HumanAgent(BaseAgent):
    """Human agents for Human-recorder"""

    name = "human"

    def __init__(
        self,
        model: str,
        remote: bool,
        runtime_server_addr: str,
        runtime_server_port: int,
    ) -> None:
        """Initialize with model, prompt template, and initilization code."""
        self.remote = remote
        self.runtime_server_addr = runtime_server_addr
        self.runtime_server_port = runtime_server_port
        self.runtime: PythonRuntime | RemotePythonRuntime
        self.runtime_init_code: str = RUNTIME_INIT_CODE.strip()

        if self.remote:
            self.runtime = RemotePythonRuntime(
                env_server_addr=self.runtime_server_addr,
                env_server_port=self.runtime_server_port,
            )
        else:
            self.runtime = PythonRuntime()

        self.task_config: TaskConfig
        self.instruction: str
        self.trajectory: list[StepInfo]
        self.obs: np.ndarray | None = None
        self.step_info: StepInfo | None
        self.total_tokens: int

    def generate_action(self, obs: np.ndarray | None, model_name: str) -> StepInfo:
        return StepInfo(
            obs=None,
            prompt=None,
            response=None,
            action="Confirm when you finish",
            info={},
            result={},
            timestamp=0,
        )

    def step_action(self, failure_msg: str | None, step_info: StepInfo) -> tuple[dict, bool]:
        step_info.action = "Executed by human"
        step_info.timestamp = time.time()
        if failure_msg:
            step_info.result["force_stop_reason"] = "Cancelled by human."

        self.trajectory.append(step_info)
        logger.info(f"Output: {step_info.result}")

        return {}, True
