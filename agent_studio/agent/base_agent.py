import logging
import time
from typing import Any

import numpy as np
import requests

from agent_studio.agent.runtime import PythonRuntime, RemotePythonRuntime
from agent_studio.config import Config
from agent_studio.llm.base_model import BaseModel
from agent_studio.llm.utils import extract_from_response

config = Config()
logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for agents."""

    name: str = "base"

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.instruction: str = ""
        self.trajectory: list[dict[str, Any]] = []
        self.runtime: PythonRuntime | RemotePythonRuntime | None = None

        self.cur_prompt: list[dict[str, Any]] | None = None
        self.cur_response: str | None = None
        self.cur_info: dict[str, Any] = {}
        self.cur_raw_code: str = ""
        self.total_tokens: int = 0

    def reset(
        self,
        instruction: str,
    ) -> None:
        self.instruction = instruction
        self.trajectory = []
        self.cur_prompt = None
        self.cur_response = None
        self.cur_info = {}
        self.cur_raw_code = ""
        self.total_tokens = 0

        if self.runtime is not None:
            self.runtime.close()
        if config.remote:
            self.runtime = RemotePythonRuntime()
        else:
            self.runtime = PythonRuntime()

    def get_token_count(self) -> int:
        return self.total_tokens

    def generate_action(self, obs: np.ndarray | None) -> tuple[str, str]:
        self.cur_obs = obs
        self.cur_prompt = self.trajectory2intermediate_msg()
        logger.debug(f"Prompt: {self.cur_prompt}")
        self.cur_response, self.cur_info = self.model.generate_response(
            messages=self.cur_prompt, model=config.exec_model
        )
        logger.debug(f"Response: {self.cur_response}")
        assert self.cur_response is not None, "Failed to generate response."
        self.total_tokens += self.cur_info.get("total_tokens", 0)
        self.cur_raw_code = extract_from_response(self.cur_response)

        return self.cur_response, self.cur_raw_code

    def step_action(self, confirmed: bool, **kwargs) -> tuple[dict, bool]:
        """Executes the code and record the result."""
        result = {}
        cur_time = time.time()
        if confirmed:
            code_clean = self.cur_raw_code.strip()
            done = code_clean.endswith(config.stop_code)
            if done:
                code = code_clean[: -len(config.stop_code)].strip()
            else:
                code = code_clean

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
        else:
            result["content"] = "Cancelled by user."
            done = True

        self.trajectory.append(
            {
                "obs": self.cur_obs,
                "prompt": self.cur_prompt,
                "response": self.cur_response,
                "info": self.cur_info,
                "act": self.cur_raw_code,
                "res": result,
                "timestamp": cur_time,
            }
        )
        logger.info(f"Output: {result}")

        return result, done

    def eval(self, final_obs: np.ndarray | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def close(self) -> None:
        if self.runtime is not None:
            self.runtime.close()

    def trajectory2intermediate_msg(self) -> list[dict[str, Any]]:
        raise NotImplementedError
