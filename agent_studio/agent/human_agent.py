import logging
import time
from typing import Any

import numpy as np

from agent_studio.agent.base_agent import BaseAgent, StepInfo
from agent_studio.config import Config
from agent_studio.agent.runtime import PythonRuntime, RemotePythonRuntime
from agent_studio.utils.types import TaskConfig
from agent_studio.agent.base_agent import RUNTIME_INIT_CODE


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

    def generate_action(self, obs: np.ndarray | None, model_name: str) -> str:
        return "Confirm when you finish"

    def step_action(self, confirmed: bool) -> tuple[dict, bool]:
        return {}, True
