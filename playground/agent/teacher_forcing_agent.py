import logging

from playground.agent.base_agent import Agent
from playground.desktop_env import ComputerEnv

logger = logging.getLogger(__name__)


class TeacherForcingAgent(Agent):
    """Agent that follows a pre-defined action sequence"""

    def __init__(self, env: ComputerEnv, **kwargs) -> None:
        super().__init__(env=env)
        self.trajectory: str = ""

    def reset(
        self,
        instruction: str,
        **kwargs,
    ) -> None:
        super().reset(instruction=instruction)
        self.trajectory = kwargs.get("reference_action_sequence", "")

    def run(self):
        # response = input(
        #     "Would you like to run this code? (y/n)\n"
        # )
        # if response.strip().lower() == "y":
        logger.info(f"Running code:\n{self.trajectory}")
        for chunk in self.env.run("python", self.trajectory):
            logger.info(chunk)
