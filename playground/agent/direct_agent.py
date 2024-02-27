import logging
from typing import Any

from playground.agent.base_agent import Agent
from playground.config import Config
from playground.llm.utils import extract_from_response

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
            self.step(init_code)

    def run(self) -> list:
        """The main logic of the agent."""
        # Loop until the task is done or the max step is reached.
        obs = None
        for _ in range(config.max_step):
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
            result = self.step(code)
            self.trajectory.append(
                {"obs": obs, "act": raw_code, "res": result, "done": done}
            )
            if done:
                break

        return self.trajectory

    def construct_prompt(self):
        messages: list[dict[str, Any]] = []
        if self.system_prompt is not None:
            messages.append({"role": "system", "content": self.system_prompt})
        for step in self.trajectory:
            if step["obs"] is not None:
                messages.append(
                    {"role": "user", "content": f"Observation: {step['obs']}"}
                )
            messages.append({"role": "assistant", "content": f"Action: {step['act']}"})
            messages.append({"role": "user", "content": f"Result: {step['res']}"})
