import logging
from typing import Any

import numpy as np

from agent_studio.agent.base_agent import BaseAgent
from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator_helper import Evaluator
from agent_studio.utils.prompt import PromptSeg, SysPromptComposer

config = Config()
logger = logging.getLogger(__name__)


class DirectAgent(BaseAgent):
    """Zero-shot LLM agents."""

    name: str = "direct"

    def reset(
        self,
        task_config: dict[str, Any],
        registered_evaluators: dict[str, type[Evaluator]],
    ) -> None:
        super().reset(
            task_config=task_config, registered_evaluators=registered_evaluators
        )
        composer = SysPromptComposer(config.prompt_folder)
        for eval in task_config["evals"]:
            if "eval_procedure" in eval and len(eval["eval_procedure"]) > 0:
                evaluator = registered_evaluators[eval["eval_type"]]
                if evaluator.prompt is not None:
                    composer.add(evaluator.prompt)
                    logger.info(f"Add evaluator prompt: {evaluator.prompt}")

        self.system_prompt = composer.compose()

        with open(config.init_code_path, "r") as f:
            init_code = f.read()
            assert self.runtime is not None
            self.runtime(init_code)

    def trajectory2intermediate_msg(self) -> list[PromptSeg]:
        """Converts the trajectory to intermediate messages.

        Returns:
            list[PromptSeg]: The intermediate messages.
                + role:
                    - system
                    - user
                    - assistant
                + content: The content of the message.\
                    content can either be a string or a np.array.\
                    If it is a np.array, it should be in RGB format.
        """
        messages: list[PromptSeg] = []
        if self.system_prompt is not None:
            messages.append(PromptSeg(role="system", content=self.system_prompt))
        messages.append(
            PromptSeg(role="user", content=f"The task instruction: {self.instruction}")
        )
        for step in self.trajectory:
            messages.append(
                PromptSeg(
                    role="assistant", content=f"[Action]: ```python\n{step.act}\n```"
                )
            )

        if self.cur_obs is not None:
            messages.append(PromptSeg(role="user", content=self.cur_obs))

        return messages

    def eval(self, final_obs: np.ndarray | None = None) -> dict[str, Any]:
        messages: list[PromptSeg] = []
        messages.append(
            PromptSeg(role="user", content=f"The task instruction: {self.instruction}")
        )
        for step in self.trajectory:
            if step.obs is not None:
                messages.append(PromptSeg(role="user", content="[Observation]: \n"))
                messages.append(PromptSeg(role="user", content=step.obs))
            messages.append(
                PromptSeg(
                    role="assistant", content=f"[Action]: \n```python\n{step.act}\n```"
                )
            )
            messages.append(PromptSeg(role="user", content=f"[Result]: \n{step.res}"))

        if final_obs is not None:
            messages.append(PromptSeg(role="user", content="[Observation]: \n"))
            messages.append(PromptSeg(role="user", content=final_obs))

        messages.append(
            PromptSeg(
                role="user",
                content=(
                    "The content in [Result:] is the output of the code execution. "
                    "If it is empty, it means the code execution is successful, "
                    "but you still need to check whether the code is correct. "
                    "Answer 'True' if the above trajectory successfully complete "
                    "the task instruction, otherwise answer 'False' and provide "
                    "a explanation in one sentence. The explanation should not "
                    "contain the word 'True'."
                ),
            )
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
