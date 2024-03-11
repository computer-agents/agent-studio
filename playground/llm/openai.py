import logging
from typing import Any

import backoff
import numpy as np
from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from playground.config.config import Config
from playground.llm.base_model import BaseModel
from playground.llm.utils import encode_image

config = Config()
logger = logging.getLogger(__name__)


class OpenAIProvider(BaseModel):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.client = OpenAI(api_key=config.openai_api_key)

    def compose_messages(
        self,
        intermedia_msg: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Composes the messages to be sent to the model.
        """
        model_message: list[dict[str, Any]] = []
        past_role = None
        for msg in intermedia_msg:
            if isinstance(msg["content"], np.ndarray):
                content: dict = {
                    "type": "image_url",
                    "image_url": {"url": encode_image(msg["content"])},
                }
            elif isinstance(msg["content"], str):
                content = {"type": "text", "text": msg["content"]}
            current_role = msg["role"]
            if past_role != current_role:
                model_message.append(
                    {
                        "role": current_role,
                        "content": [content],
                    }
                )
            else:
                model_message[-1]["content"].append(content)
        return model_message

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Creates a chat completion using the OpenAI API."""

        model = kwargs.get("model", config.exec_model)
        temperature = kwargs.get("temperature", config.temperature)
        max_tokens = kwargs.get("max_tokens", config.max_tokens)
        model_message = self.compose_messages(intermedia_msg=messages)
        logger.info(
            f"Creating chat completion with model {model}. "
            f"Message:\n{model_message}"
        )

        @backoff.on_exception(
            backoff.constant,
            (APIError, RateLimitError, APITimeoutError),
            max_tries=config.max_retries,
            interval=10,
        )
        def _generate_response_with_retry() -> tuple[str, dict[str, int]]:
            response = self.client.chat.completions.create(
                model=model,
                messages=model_message,
                temperature=temperature,
                seed=config.seed,
                max_tokens=max_tokens,
            )

            if response is None:
                logger.error("Failed to get a response from OpenAI. Try again.")

            response_message = response.choices[0].message.content
            if response.usage is None:
                info = {}
                logger.warn("Failed to get usage information from OpenAI.")
            else:
                info = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "system_fingerprint": response.system_fingerprint,
                }

            logger.info(f"\nReceived response:\n{response_message}\nInfo:\n{info}")

            return response_message, info

        return _generate_response_with_retry()
