from agent.base_agent import Agent
from desktop_env.eval.task_config import TaskConfig
from llm import setup_llm
from llm.lm_config import LMConfig


class DirectAgent(Agent):
    """LLM agents."""

    def __init__(
        self,
        lm_config: LMConfig,
    ) -> None:
        super().__init__()
        self.lm_config = lm_config
        self.llm = setup_llm(lm_config)

    def reset(
        self,
        task_config: TaskConfig,
    ) -> None:
        super().reset(task_config)

    def step(self, obs):
        prompt = self.construct_prompt(obs)
        response = self.llm.generate_response(prompt)
        action = self.parse_response(response)

        self.history.append({"obs": obs, "action": action})

        return action

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
