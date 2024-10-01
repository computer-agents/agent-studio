import logging
import time

import numpy as np

from agent_studio.utils.runtime import PythonRuntime, RemotePythonRuntime
from agent_studio.llm import ModelManager
from agent_studio.llm.utils import extract_from_response
from agent_studio.utils.types import MessageList, TaskConfig, StepInfo

logger = logging.getLogger(__name__)


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
        model_manager = ModelManager()
        self.model = model_manager.get_model(model)
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

    def reset(self, task_config: TaskConfig) -> None:
        """Reset the agent's state with a new task configuration."""
        self.task_config = task_config
        self.instruction = task_config.instruction
        self.trajectory = []
        self.obs = None
        self.step_info: StepInfo | None = None
        self.total_tokens = 0

        self.runtime.reset()
        self.runtime(self.runtime_init_code)

    def generate_action(self, obs: np.ndarray | None, model_name: str) -> str:
        """Generate an action based on the observation."""
        self.obs = obs
        prompt = self.action_prompt
        assert prompt is not None, "Invalid prompt"
        logger.debug(f"Prompt: {prompt}")
        response, info = self.model.generate_response(messages=prompt, model=model_name)
        logger.debug(f"Response: {response}")
        assert response is not None, "Failed to generate response."
        self.total_tokens += info.get("total_tokens", 0)
        action = extract_from_response(response).strip()

        self.step_info = StepInfo(
            obs=obs,
            prompt=prompt,
            response=response,
            action=action,
            info=info,
            result={},
            timestamp=0.0,
        )

        return action

    def step_action(self, failure_msg: str | None) -> tuple[dict, bool]:
        """Execute the code if confirmed and record the result.
        If failure_msg is not None, the action is cancelled.
        """
        if self.step_info is None:
            raise ValueError("Invalid step_info")
        result = {}
        if not failure_msg:
            code_clean = self.step_info.action
            done = code_clean.endswith("exit()")
            if done:
                code = code_clean[: -len("exit()")].strip()
            else:
                code = code_clean

            logger.debug(f"Code to execute:\n{code}\n")
            result = self.runtime(code)
        else:
            result["force_stop_reason"] = failure_msg
            done = True

        self.step_info.result = result
        self.step_info.timestamp = time.time()
        self.trajectory.append(self.step_info)
        logger.info(f"Output: {result}")

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
