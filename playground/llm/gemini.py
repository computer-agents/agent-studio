import json
import logging
from typing import Any

import backoff
import google.generativeai as genai
import numpy as np

# Magic import, add following import to fix bug
# https://github.com/google/generative-ai-python/issues/178
import PIL.PngImagePlugin
import requests
from google.generativeai.types import GenerationConfig
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
        super().__init__()
        with open(config.api_key_path, "r") as f:
            api_keys = json.load(f)
        genai.configure(api_key=api_keys["gemini"])
        self.model_server: str | None = getattr(config, "model_server", None)

    def compose_messages(
        self,
        intermedia_msg: list[dict[str, Any]],
    ) -> Any:
        model_message: dict[str, Any] = {
            "role": "user",
            "parts": [],
        }
        past_role = None
        for msg in intermedia_msg:
            current_role = msg["role"] if "role" != "system" else "user"
            if past_role != current_role:
                model_message["parts"].append(f"[{current_role.capitalize()}]: ")
                past_role = current_role

            if isinstance(msg["content"], str):
                pass
            elif isinstance(msg["content"], np.ndarray):
                # convert from BGR NDArray to PIL RGB Image
                msg["content"] = Image.fromarray(msg["content"][:, :, ::-1])
            else:
                assert False, f"Unknown message type: {msg['content']}"
            model_message["parts"].append(msg["content"])

        return model_message

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Creates a chat completion using the Gemini API."""
        model_message = self.compose_messages(intermedia_msg=messages)

        model_name = kwargs.get("model", None)
        if not self.model_server:
            if model_name is not None:
                model = genai.GenerativeModel(model_name)
            else:
                raise ValueError("Model name is required for GeminiProvider.")
            logger.info(
                f"Creating chat completion with model {model_name}. "
                f"Message:\n{model_message}"
            )

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
                    "model": model_name,
                    "messages": bytes2str(model_message),
                    "config": bytes2str(generation_config),
                }
                response_raw = requests.post(f"{self.model_server}/generate", json=body)
                response: genai.types.GenerateContentResponse = str2bytes(
                    response_raw.json()["content"]
                )
                self.token_count += response_raw.json()["token_count"]
            else:
                response = model.generate_content(
                    contents=model_message, generation_config=generation_config
                )
                token_count = model.count_tokens(model_message)
                self.token_count += token_count.total_tokens
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
            logger.info(f"\nReceived response:\n{message}")
            return message, info

        return _generate_response_with_retry()
