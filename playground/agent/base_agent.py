import logging
from typing import Any
import time

import requests
import PIL.Image

from playground.agent.runtime import PythonRuntime, RemotePythonRuntime
from playground.config import Config
from playground.llm.base_model import BaseModel
from playground.llm.utils import extract_from_response
from playground.utils.human_utils import confirm_action

config = Config()
logger = logging.getLogger(__name__)


class Action:
    """A class for the action of the agent."""

    def __init__(
            self,
            raw_code: str,
            code: str,
            done: bool,
            obs: PIL.Image.Image | None = None
        ) -> None:
        self.obs = obs
        self.raw_code = raw_code
        self.code = code
        self.done = done


class Agent:
    """Base class for agents."""

    def __init__(self, model: BaseModel) -> None:
        self.model = model
        self.instruction: str = ""
        self.trajectory: list[dict[str, Any]] = []
        self.current_action: Action | None = None

        if config.remote:
            self.runtime = RemotePythonRuntime()
        else:
            self.runtime = PythonRuntime()

    def reset(
        self,
        instruction: str,
    ) -> None:
        self.instruction = instruction
        self.trajectory = []
        self.current_action = None

        if config.remote:
            if self.runtime is not None:
                self.runtime.close()
            self.runtime = RemotePythonRuntime()
        else:
            if self.runtime is not None:
                self.runtime.close()
            self.runtime = PythonRuntime()

    def get_trajectory(self) -> list[dict[str, Any]]:
        return self.trajectory

    def generate_action(self) -> tuple[str, str, bool]:
        prompt = self.construct_prompt()
        response, info = self.model.generate_response(
            messages=prompt, model=config.model
        )
        raw_code = extract_from_response(response)

        # Execute the code and record the result.
        done = raw_code.endswith(config.stop_code)
        if done:
            code = raw_code[: -len(config.stop_code)]
        else:
            code = raw_code

        logger.debug(f"Executing code:\n{code}\n")
        self.current_action = Action(raw_code=raw_code, code=code, done=done)
        return raw_code, code, done

    def step_action(self, confirmed: bool) -> tuple[dict, bool]:
        """"""
        assert self.current_action is not None, "No action to execute."
        code = self.current_action.code
        done = self.current_action.done
        raw_code = self.current_action.raw_code
        obs = self.current_action.obs
        result = {}
        if confirmed:
            if config.remote:
                response = requests.post(
                    f"http://{config.env_server_addr}:{config.env_server_port}/execute",
                    json={"message": code},
                )
                result = response.json()
            else:
                assert self.runtime is not None, "The agent needs to reset first."
                result = self.runtime.exec(code)
        else:
            result["content"] = "Cancelled by user."
        logger.info(f"Output: {result}\nDone: {done}\n")

        self.trajectory.append(
            {"obs": obs, "act": raw_code, "res": result, "done": done, "timestamp": time.time()}
        )

        return result, done

    def step(self) -> tuple[dict, bool]:
        """Executes and records the given code by LLM in the environment."""
        _, code, _ = self.generate_action()
        confirmed, _ = confirm_action(f"Executing code:\n{code}")(lambda: True)()
        result, done = self.step_action(confirmed)

        return result, done

    def run(self) -> list:
        """The main logic of the agent.

        Returns: The trajectory of the agent.
        """
        raise NotImplementedError

    def close(self) -> None:
        if self.runtime is not None:
            self.runtime.close()

    def construct_prompt(self):
        raise NotImplementedError
