import logging
from typing import Any

import backoff
from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from playground.config.config import Config
from playground.llm.base_model import BaseModel

config = Config()
logger = logging.getLogger(__name__)


class OpenAIProvider(BaseModel):
    def __init__(self, **kwargs: Any) -> None:
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Creates a chat completion using the OpenAI API."""

        model = kwargs.get("model", config.model)
        temperature = kwargs.get("temperature", config.temperature)
        max_tokens = kwargs.get("max_tokens", config.max_tokens)
        logger.info(f"Creating chat completion with model {model}...")

        @backoff.on_exception(
            backoff.constant,
            (APIError, RateLimitError, APITimeoutError),
            max_tries=config.max_retries,
            interval=10,
        )
        def _generate_response_with_retry() -> tuple[str, dict[str, int]]:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                seed=config.seed,
                max_tokens=max_tokens,
            )

            if response is None:
                logger.error("Failed to get a response from OpenAI. Try again.")

            message = response.choices[0].message.content

            info = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "system_fingerprint": response.system_fingerprint,
            }

            logger.info(f"Response received from {model}")

            return message, info

        return _generate_response_with_retry()
