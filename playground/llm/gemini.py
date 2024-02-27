import base64
import json
import logging
import pickle
from typing import Any

import backoff
import google.generativeai as genai
import numpy as np

# Magic import, add following import to fix bug
# https://github.com/google/generative-ai-python/issues/178
import PIL.PngImagePlugin
import requests
from google.generativeai.types import GenerationConfig
from numpy.typing import NDArray
from PIL import Image

from playground.config.config import Config
from playground.llm.base_model import BaseModel
from playground.utils.communication import bytes2str, str2bytes

# Run this to pass mypy checker
PIL.PngImagePlugin


config = Config()
logger = logging.getLogger(__name__)


class GeminiProvider(BaseModel):
    def __init__(self, **kwargs) -> None:
        with open(config.api_key_path, "r") as f:
            api_keys = json.load(f)
        genai.configure(api_key=api_keys["gemini"])
        self.model_server: str | None = getattr(config, "model_server", None)

    def compose_messages(
        self,
        obs: NDArray | None,
        trajectory: list[dict[str, Any]],
        system_prompt: str | None,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if system_prompt is not None:
            messages.append({"role": "user", "parts": [system_prompt]})
        for step in trajectory:
            if not all(key in step for key in ["obs", "act", "res"]):
                raise ValueError(
                    "Each step in the trajectory must contain 'obs', 'act' and 'res'"
                    f" keys. Got {step} instead."
                )
            img = Image.fromarray(np.uint8(step["obs"])).convert("RGB")
            user_content: list[Image.Image | str] = ["[Observation]", img]
            user_content.append(f"[Action]: \n{step['act']}")
            user_content.append(f"[Result]: \n{step['res']}")
            if messages[-1]["role"] == "user":
                messages[-1]["parts"].extend(user_content)
            else:
                messages.append(
                    {
                        "role": "user",
                        "parts": user_content,
                    }
                )
        img = Image.fromarray(np.uint8(obs)).convert("RGB")
        user_content = [img]
        if messages[-1]["role"] == "user":
            messages[-1]["parts"].append(*user_content)
        else:
            messages.append(
                {
                    "role": "user",
                    "parts": user_content,
                }
            )
        return messages

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Creates a chat completion using the Gemini API."""
        messages: str = "\n".join([m["content"] for m in messages])

        if not self.model_server:
            model = kwargs.get("model", None)
            if model is not None:
                self.model = genai.GenerativeModel(model)
            logger.info(f"Creating chat completion with model {model}...")

        generation_config = GenerationConfig(
            temperature=kwargs.get("temperature", config.temperature),
            # top_p=kwargs.get("top_p", config.max_tokens),
            # top_k=kwargs.get("top_k", config.max_tokens),
            candidate_count=1,
            # max_output_tokens=kwargs.get("max_tokens", config.max_tokens),
        )

        @backoff.on_exception(
            backoff.constant,
            genai.types.IncompleteIterationError,
            max_tries=config.max_retries,
            interval=10,
        )
        def _generate_response_with_retry() -> tuple[str, dict[str, int]]:
            if self.model_server:
                body = {
                    "messages": bytes2str(messages),
                    "config": bytes2str(generation_config),
                }
                response_raw = requests.post(self.model_server, json=body)
                response: genai.types.GenerateContentResponse = str2bytes(
                    response_raw.text
                )
            else:
                response = self.model.generate_content(
                    contents=messages, generation_config=generation_config
                )
            try:
                message = response.text
            except ValueError:
                print(response.__dict__)
                # TODO: Remove this after debugging
                for candidate in response.candidates:
                    print("Finish Reason: ", candidate.finish_reason)
                    message = [part.text for part in candidate.content.parts]
                    print("Message: ", message)
                raise genai.types.IncompleteIterationError

            info: dict[str, int] = {}
            logger.info(f"Received response: {message}")
            return message, info

        return _generate_response_with_retry()
