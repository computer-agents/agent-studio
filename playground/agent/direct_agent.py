import logging
from typing import Any

from playground.agent.base_agent import Agent
from playground.config import Config

config = Config()
logger = logging.getLogger(__name__)


class DirectAgent(Agent):
    """Zero-shot LLM agents."""

    def reset(self, instruction: str) -> None:
        super().reset(instruction=instruction)
        with open(config.system_prompt_path, "r") as f:
            self.system_prompt = f.read()
        with open(config.init_code_path, "r") as f:
            init_code = f.read()
            self.runtime(init_code)

    def construct_prompt(self) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if self.system_prompt is not None:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append(
            {"role": "user", "content": f"The task instruction: {self.instruction}"}
        )
        for step in self.trajectory:
            if step["obs"] is not None:
                messages.append(
                    {"role": "user", "content": f"Observation: {step['obs']}"}
                )
            messages.append({"role": "assistant", "content": f"Action: {step['act']}"})
            messages.append({"role": "user", "content": f"Result: {step['res']}"})

        return messages
