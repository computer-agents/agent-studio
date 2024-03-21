import logging
from typing import Any

import numpy as np

from agent_studio.agent.base_agent import Agent
from agent_studio.config import Config

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
            assert self.runtime is not None
            self.runtime(init_code)

    def trajectory2intermediate_msg(self) -> list[dict[str, Any]]:
        """Converts the trajectory to intermediate messages.

        Returns:
            list[dict[str, Any]]: The intermediate messages.
                + role:
                    - system
                    - user
                    - assistant
                + content: The content of the message.\
                    content can either be a string or a np.array.\
                    If it is a np.array, it should be in RGB format.
        """
        messages: list[dict[str, Any]] = []
        if self.system_prompt is not None:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append(
            {"role": "user", "content": f"The task instruction: {self.instruction}"}
        )
        for step in self.trajectory:
            messages.append(
                {
                    "role": "assistant",
                    "content": f"[Action]: ```python\n{step['act']}\n```",
                }
            )

        if self.cur_obs is not None:
            messages.append({"role": "user", "content": self.cur_obs})

        return messages

    def eval(self, final_obs: np.ndarray | None = None) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        messages.append(
            {"role": "user", "content": f"The task instruction: {self.instruction}"}
        )
        for step in self.trajectory:
            if step["obs"] is not None:
                messages.append({"role": "user", "content": "[Observation]: \n"})
                messages.append({"role": "user", "content": step["obs"]})
            messages.append(
                {
                    "role": "assistant",
                    "content": f"[Action]: \n```python\n{step['act']}\n```",
                }
            )
            messages.append({"role": "user", "content": f"[Result]: \n{step['res']}"})

        if final_obs is not None:
            messages.append({"role": "user", "content": "[Observation]: \n"})
            messages.append({"role": "user", "content": final_obs})

        messages.append(
            {
                "role": "user",
                "content": (
                    "The content in [Result:] is the output of the code execution. "
                    "If it is empty, it means the code execution is successful, "
                    "but you still need to check whether the code is correct. "
                    "Answer 'True' if the above trajectory successfully complete "
                    "the task instruction, otherwise answer 'False' and provide "
                    "a explanation in one sentence. The explanation should not "
                    "contain the word 'True'."
                ),
            }
        )

        response, _ = self.model.generate_response(
            messages=messages, model=config.eval_model
        )

        if "True" in response:
            return {
                "score": 1.0,
                "feedback": "",
                "prompt": messages,
                "response": response,
            }
        else:
            return {
                "score": 0.0,
                "feedback": response,
                "prompt": messages,
                "response": response,
            }
