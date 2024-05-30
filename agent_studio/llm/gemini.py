import logging
from typing import Any

import backoff
import google.generativeai as genai
import numpy as np

# Magic import, add following import to fix bug
# https://github.com/google/generative-ai-python/issues/178
import PIL.PngImagePlugin
from google.generativeai.types import GenerationConfig
from PIL import Image

from agent_studio.config.config import Config
from agent_studio.llm.base_model import BaseModel, PromptSeg

# Run this to pass mypy checker
PIL.PngImagePlugin


config = Config()
logger = logging.getLogger(__name__)


class GeminiProvider(BaseModel):
    name = "gemini"

    def __init__(self, **kwargs) -> None:
        super().__init__()
        genai.configure(api_key=config.gemini_api_key)

    def compose_messages(
        self,
        intermedia_msg: list[PromptSeg],
    ) -> Any:
        model_message: dict[str, Any] = {
            "role": "user",
            "parts": [],
        }
        past_role = None
        for msg in intermedia_msg:
            current_role = msg.role if "role" != "system" else "user"
            if past_role != current_role:
                model_message["parts"].append(f"[{current_role.capitalize()}]: ")
                past_role = current_role

            content: str | Image.Image
            if isinstance(msg.content, str):
                content = msg.content
            elif isinstance(msg.content, np.ndarray):
                # convert from RGB NDArray to PIL RGB Image
                content = Image.fromarray(msg.content)
            else:
                assert (
                    False
                ), f"Unknown message type: {type(msg.content)}, {msg.content}"
            model_message["parts"].append(content)

        return model_message

    def generate_response(
        self, messages: list[PromptSeg], **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Creates a chat completion using the Gemini API."""
        model_message = self.compose_messages(intermedia_msg=messages)

        model_name = kwargs.get("model", None)
        if model_name is not None:
            model = genai.GenerativeModel(model_name)
        else:
            raise ValueError("Model name is required for GeminiProvider.")
        logger.info(f"Creating chat completion with model {model_name}.")

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
            response = model.generate_content(
                contents=model_message, generation_config=generation_config
            )
            token_count = model.count_tokens(model_message)
            info = {
                "total_tokens": token_count.total_tokens,
            }
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

            logger.info(f"\nReceived response:\n{message}\nInfo:\n{info}")
            return message, info

        return _generate_response_with_retry()
