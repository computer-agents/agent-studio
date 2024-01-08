from typing import Any, List

from desktop_env.eval.task_config import TaskConfig


class Agent:
    """Base class for agents."""

    def __init__(self, *args: Any) -> None:
        self.instruction: str | None = None
        self.history: List = []

    def reset(
        self,
        task_config: TaskConfig,
    ) -> None:
        self.instruction = task_config.instruction
        # read system prompt from the file path
        with open(task_config.system_prompt) as f:
            self.system_prompt = f.read()

    def step(self, obs):
        """Perform the next action given the observation."""
        raise NotImplementedError

    def construct_prompt(self, obs):
        """Construct the prompt given the observation."""
        raise NotImplementedError

    def parse_response(self, response):
        """Parse the response from the LLM."""
        raise NotImplementedError
