import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import requests

from agent_studio.agent.runtime import PythonRuntime
from agent_studio.llm import setup_model
from agent_studio.llm.utils import extract_from_response
from agent_studio.utils.types import MessageList

logger = logging.getLogger(__name__)


@dataclass
class StepInfo:
    obs: np.ndarray | None
    prompt: MessageList | None
    response: str | None
    action: str
    info: dict[str, Any]
    result: dict[str, Any]
    timestamp: float


TrajectoryInfo = list[StepInfo]


RUNTIME_INIT_CODE = """
from agent_studio.envs.desktop_env import Keyboard, Mouse


keyboard = Keyboard()
mouse = Mouse()
"""


class BaseAgent:
    """Base class for agents."""

    name: str = "base"

    def __init__(
        self,
        model: str,
        remote: bool,
        runtime_server_addr: str,
        runtime_server_port: int,
    ) -> None:
        """Initialize with model, prompt template, and initilization code."""
        self.model = setup_model(model)
        self.remote = remote
        self.runtime_server_addr = runtime_server_addr
        self.runtime_server_port = runtime_server_port
        self.runtime: PythonRuntime | None = None
        self.runtime_init_code: str = RUNTIME_INIT_CODE.strip()

        self.task_config = {}
        self.instruction: str = ""
        self.trajectory: TrajectoryInfo = []
        self.step_info = StepInfo(
            obs=None,
            prompt=None,
            response=None,
            action="",
            info={},
            result={},
            timestamp=0.0,
        )
        self.total_tokens: int = 0

    def reset(self, task_config: dict[str, Any]) -> None:
        """Reset the agent's state with a new task configuration."""
        self.task_config = task_config
        self.instruction = task_config["instruction"]
        self.trajectory = []
        self.step_info = StepInfo(
            obs=None,
            prompt=None,
            response=None,
            action="",
            info={},
            result={},
            timestamp=0.0,
        )
        self.total_tokens = 0

        if self.runtime is not None:
            self.runtime.close()
        if self.remote:
            if self.runtime_init_code is not None:
                requests.post(
                    f"http://{self.runtime_server_addr}:{self.runtime_server_port}/execute",  # noqa: E501
                    json={"message": self.runtime_init_code},
                )
        else:
            self.runtime = PythonRuntime(python_timeout=20)
            assert self.runtime is not None, "Failed to initialize runtime."
            if self.runtime_init_code is not None:
                self.runtime(self.runtime_init_code)

    def generate_action(self, obs: np.ndarray | None, model_name: str) -> str:
        """Generate an action based on the observation."""
        self.step_info.obs = obs
        prompt = self.action_prompt
        assert prompt is not None, "Invalid prompt"
        self.step_info.prompt = prompt
        logger.debug(f"Prompt: {prompt}")
        response, info = self.model.generate_response(messages=prompt, model=model_name)
        self.step_info.response = response
        self.step_info.info = info
        logger.debug(f"Response: {response}")
        assert response is not None, "Failed to generate response."
        self.total_tokens += info.get("total_tokens", 0)
        action = extract_from_response(response).strip()
        self.step_info.action = action

        return action

    def step_action(self, confirmed: bool) -> tuple[dict, bool]:
        """Execute the code if confirmed and record the result."""
        result = {}
        if confirmed:
            code_clean = self.step_info.action
            done = code_clean.endswith("exit()")
            if done:
                code = code_clean[: -len("exit()")].strip()
            else:
                code = code_clean

            logger.debug(f"Code to execute:\n{code}\n")
            if self.remote:
                response = requests.post(
                    f"http://{self.runtime_server_addr}:{self.runtime_server_port}/execute",  # noqa: E501
                    json={"message": code},
                )
                result = response.json()
            else:
                assert self.runtime is not None, "The agent needs to reset first."
                result = self.runtime(code)
        else:
            result["content"] = "Cancelled by user."
            done = True

        self.step_info.result = result
        self.step_info.timestamp = time.time()
        self.trajectory.append(self.step_info)
        logger.info(f"Output: {result}")
        self.step_info = StepInfo(
            obs=None,
            prompt=None,
            response=None,
            action="",
            info={},
            result={},
            timestamp=0.0,
        )

        return result, done

    @property
    def action_prompt(self) -> MessageList:
        """Construct the action prompt."""
        raise NotImplementedError

    def get_token_count(self) -> int:
        """Return the total number of tokens used."""
        return self.total_tokens

    def close(self) -> None:
        """Close the runtime if it is open."""
        if self.runtime is not None:
            self.runtime.close()
