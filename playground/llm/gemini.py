import logging
from typing import Any
import pickle
import base64

import backoff
import google.generativeai as genai
import numpy as np
import requests
# Magic import, add following import to fix bug
# https://github.com/google/generative-ai-python/issues/178
import PIL.PngImagePlugin
from google.generativeai.types import GenerationConfig

from numpy.typing import NDArray
from PIL import Image

from playground.config.config import Config
from playground.llm.base_model import BaseModel

# Run this to pass mypy checker
PIL.PngImagePlugin


config = Config()
logger = logging.getLogger(__name__)


class GeminiProvider(BaseModel):
    def __init__(self) -> None:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = config.model
        self.proxy = config.model_proxy
        self.model = genai.GenerativeModel(model)

    def _compose_messages(
        self,
        obs: NDArray | None,
        trajectory: list[dict[str, Any]],
        system_prompt: str | None,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if system_prompt is not None:
            messages.append({"role": "user", "parts": [system_prompt]})
        for step in trajectory:
            img = Image.fromarray(np.uint8(step["obs"])).convert("RGB")
            user_content: list[Image.Image|str] = [img]
            if "act" in step:
                user_content.append(
                    f"[Action]: \n{step['act']}"
                )
            if "res" in step:
                user_content.append(
                    f"[Result]: \n{step['res']}"
                )
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

        model = kwargs.get("model", None)
        if model is not None:
            self.model = genai.GenerativeModel(model)
        generation_config = GenerationConfig(
            temperature=kwargs.get("temperature", config.temperature),
            # top_p=kwargs.get("top_p", config.max_tokens),
            # top_k=kwargs.get("top_k", config.max_tokens),
            candidate_count=1,
            # max_output_tokens=kwargs.get("max_tokens", config.max_tokens),
        )
        logger.info(f"Creating chat completion with model {model}...")

        @backoff.on_exception(
            backoff.constant,
            genai.types.IncompleteIterationError,
            max_tries=config.max_retries,
            interval=10,
        )
        def _generate_response_with_retry() -> tuple[str, dict[str, int]]:
            if self.proxy:
                body = {
                    "messages": [
                        base64.b64encode(
                            pickle.dumps(messages)
                        ).decode('utf-8'),
                        base64.b64encode(
                            pickle.dumps(generation_config)
                        ).decode('utf-8')
                    ]
                }
                response = requests.post(
                    self.proxy,
                    json=body
                )
                try:
                    message = pickle.loads(base64.b64decode(response.text.encode('utf-8'))).text
                except Exception as e:
                    print(e)
                    print(response.text)
                    print(pickle.loads(base64.b64decode(response.text.encode('utf-8'))))
                    print(pickle.loads(base64.b64decode(response.text.encode('utf-8'))).parts)
                    raise e
            else:
                response = self.model.generate_content(
                    contents=messages, generation_config=generation_config
                )
                message = response.text
            info: dict[str, int] = {}

            logger.info(f"Response received from {model}")

            return message, info

        return _generate_response_with_retry()
