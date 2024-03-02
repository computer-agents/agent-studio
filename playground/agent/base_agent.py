import logging
import time
from typing import Any

import numpy as np
import requests

from playground.agent.runtime import PythonRuntime, RemotePythonRuntime
from playground.config import Config
from playground.llm.base_model import BaseModel
from playground.llm.utils import extract_from_response

config = Config()
logger = logging.getLogger(__name__)


class Agent:
    """Base class for agents."""

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.instruction: str = ""
        self.trajectory: list[dict[str, Any]] = []
        self.runtime: PythonRuntime | RemotePythonRuntime | None = None

        self.cur_prompt: list[dict[str, Any]] | None = None
        self.cur_response: str | None = None
        self.cur_info: dict[str, Any] = {}
        self.cur_raw_code: str = ""

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

        if self.runtime is not None:
            self.runtime.close()
        if config.remote:
            self.runtime = RemotePythonRuntime()
        else:
            self.runtime = PythonRuntime()

    def generate_action(self, obs: np.ndarray | None) -> tuple[str, str]:
        self.cur_obs = obs
        cur_messages = self.trajectory2intermediate_msg()
        self.cur_response, self.cur_info = self.model.generate_response(
            messages=cur_messages, model=config.exec_model
        )
        self.cur_raw_code = extract_from_response(self.cur_response)

        return self.cur_response, self.cur_raw_code

    def step_action(self, confirmed: bool) -> tuple[dict, bool]:
        """Executes the code and record the result."""
        result = {}
        if confirmed:
            done = self.cur_raw_code.endswith(config.stop_code)
            if done:
                code = self.cur_raw_code[: -len(config.stop_code)]
            else:
                code = self.cur_raw_code

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
                "timestamp": time.time(),
            }
        )
        logger.info(f"Output: {result}")

        return result, done

    def eval(self) -> dict[str, Any]:
        raise NotImplementedError

    def close(self) -> None:
        if self.runtime is not None:
            self.runtime.close()

    def trajectory2intermediate_msg(self) -> list[dict[str, Any]]:
        raise NotImplementedError
