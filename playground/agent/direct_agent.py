from playground.agent.base_agent import Agent
from playground.desktop_env import ComputerEnv
from playground.llm import setup_llm
from playground.llm.lm_config import LMConfig


class DirectAgent(Agent):
    """LLM agents."""

    def __init__(
        self,
        env: ComputerEnv,
        lm_config: LMConfig,
    ) -> None:
        super().__init__(env=env)
        self.lm_config = lm_config
        self.llm = setup_llm(lm_config)

    def reset(
        self,
        instruction: str,
        **kwargs,
    ) -> None:
        super().reset(instruction=instruction)

    def run(self):
        pass
        # prompt = self.construct_prompt(obs)
        # response = self.llm.generate_response(prompt)
        # action = self.parse_response(response)

        # self.history.append({"obs": obs, "action": action})

        # return action

    def construct_prompt(self, obs):
        messages = []
        messages.append({"role": "system", "text": self.system_prompt})
        for step in self.history:
            messages.append({"role": "user", "text": step["obs"]})
            messages.append({"role": "assistant", "text": step["action"]})
        messages.append({"role": "user", "text": obs})

        return messages

    def parse_response(self, response):
        return response
