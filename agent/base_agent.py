from desktop_env.computer.env import ComputerEnv


class Agent:
    """Base class for agents."""

    def __init__(self, env: ComputerEnv, **kwargs) -> None:
        self.env = env
        self.instruction: str = ""

    def reset(
        self,
        instruction: str,
        **kwargs,
    ) -> None:
        self.instruction = instruction

    def run(self):
        """Perform actions."""
        raise NotImplementedError

    def construct_prompt(self, obs):
        """Construct the prompt given the observation."""
        raise NotImplementedError

    def parse_response(self, response):
        """Parse the response from the LLM."""
        raise NotImplementedError
