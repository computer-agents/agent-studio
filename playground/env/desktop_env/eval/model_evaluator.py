import logging
from typing import Any

from playground.config import Config
from playground.env.desktop_env.eval.evaluator import Evaluator
from playground.llm.base_model import BaseModel
from playground.llm.utils import encode_image

config = Config()
logger = logging.getLogger(__name__)


class ModelEvaluator(Evaluator):
    name: str = "model"

    def __init__(self, model: BaseModel, instruction: str, **kwargs) -> None:
        super().__init__(
            eval_procedure=[],
            reset_procedure=[],
        )
        self.model = model
        self.instruction = instruction
        self.system_prompt = (
            "Judging from the screenshots and executed code, "
            "if the instruction is completed successfully, respond with 'True'. "
            f"The instruction is: {self.instruction}."
        )

    def __call__(self, **kwargs) -> tuple[float, str]:
        trajectory = kwargs["trajectory"]
        messages: list[dict[str, Any]] = []
        messages.append({"role": "system", "content": self.system_prompt})
        for step in trajectory:
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {"url": encode_image(step["obs"])},
                }
            ]
            if "res" in step:
                user_content.append({"type": "text", "text": step["res"]})
            messages.append(
                {
                    "role": "user",
                    "content": user_content,
                }
            )
            messages.append({"role": "assistant", "content": step["act"]})
        response, info = self.model.generate_response(
            messages=messages, model=config.model
        )
        score = 1.0 if ("True" in response) else 0.0
        return score, response
