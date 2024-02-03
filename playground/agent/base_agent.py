import logging

from playground.agent.runtime import PythonRuntime
from playground.config import Config
from playground.utils.human_utils import confirm_action

config = Config()
logger = logging.getLogger(__name__)


class Agent:
    """Base class for agents."""

    def __init__(self, env: str, record_path: str, **kwargs) -> None:
        self.env = env
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
        self.trajectory: list = []
        self.record_screen: bool = False

    def reset(
        self,
        task_id: str,
        instruction: str,
        record_screen: bool = False,
        **kwargs,
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

    def step(self, raw_code: str) -> None:
        """Executes and records the given code in the environment."""
        self.recorder.add_event(raw_code)
        end_of_episode = raw_code.endswith(config.stop_code)
        if end_of_episode:
            code = raw_code[: -len(config.stop_code)]
        else:
            code = raw_code

        if self.record_screen:
            self.recorder.pause()
        logger.info(f"Executing code:\n{code}")
        result = self._step_helper(code)
        logger.info(f"Output: {result}")

        if end_of_episode:
            if self.record_screen:
                self.recorder.stop()
            self.recorder.save()

    @confirm_action
    def _step_helper(self, code: str) -> dict:
        if self.record_screen:
            self.recorder.resume()
        assert self.runtime is not None, "The agent is not reset."
        result = self.runtime.exec(code)

        return result

    def run(self) -> list:
        """The main logic of the agent."""
        match self.env:
            case "desktop":
                init_code = (
                    "from playground.env.desktop_env import Shell, Keyboard, Mouse\n\n"
                    "shell = Shell()\nkeyboard = Keyboard()\nmouse = Mouse()\n"
                )
                self.step(init_code)
            case _:
                raise ValueError(f"Invalid env: {self.env}.")

        return self.trajectory

    def close(self) -> None:
        if self.runtime is not None:
            self.runtime.close()

    def construct_prompt(self, obs):
        """Construct the prompt given the observation."""
        raise NotImplementedError

    def parse_response(self, response):
        """Parse the response from the LLM."""
        raise NotImplementedError
