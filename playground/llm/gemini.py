import logging
from typing import Any

import backoff
import google.generativeai as genai
from vertexai.preview.generative_models import (  # GenerativeModel,; Image,; Part,
    GenerationConfig,
)

from playground.config.config import Config
from playground.llm.base_model import BaseModel

config = Config()
logger = logging.getLogger(__name__)


class GeminiProvider(BaseModel):
    def __init__(self, **kwargs: Any) -> None:
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = kwargs.get("model", config.model)
        self.model = genai.GenerativeModel(model)

    def generate_response(self, messages: list, **kwargs) -> tuple[str, dict[str, int]]:
        """Creates a chat completion using the Gemini API."""

        model = kwargs.get("model", None)
        if model is not None:
            self.model = genai.GenerativeModel(model)
        generation_config = GenerationConfig(
            temperature=kwargs.get("temperature", config.temperature),
            # top_p=kwargs.get("top_p", config.max_tokens),
            # top_k=kwargs.get("top_k", config.max_tokens),
            candidate_count=1,
            max_output_tokens=kwargs.get("max_tokens", config.max_tokens),
        )
        logger.info(f"Creating chat completion with model {model}...")

        @backoff.on_exception(
            backoff.constant,
            max_tries=config.max_retries,
            interval=10,
        )
        def _generate_response_with_retry() -> tuple[str, dict[str, int]]:
            response = model.generate_content(
                messages, generation_config=generation_config
            )
            message = response.text
            info: dict[str, int] = {}

            logger.info(f"Response received from {model}")

            return message, info

        return _generate_response_with_retry()
