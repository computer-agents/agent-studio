from agent.base_agent import Agent
from desktop_env.computer.env import ComputerEnv


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
        self.trajectory = kwargs.get("oracle_trajectory", [])

    def run(self):
        for action in self.trajectory:
            print(action)
            # response = input(
            #     "Would you like to run this code? (y/n)\n"
            # )
            # if response.strip().lower() == "y":
            for chunk in self.env.run("python", action):
                print(chunk)
