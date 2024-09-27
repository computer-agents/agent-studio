import io
import logging
from pathlib import Path
from typing import Any

import backoff
import numpy as np
import PIL
import vertexai
from anthropic import AnthropicVertex
from vertexai.generative_models import GenerationConfig, GenerativeModel, Image, Part

from agent_studio.config.config import Config
from agent_studio.llm.base_model import BaseModel
from agent_studio.llm.utils import anthropic_encode_image
from agent_studio.utils.types import MessageList

config = Config()
logger = logging.getLogger(__name__)


class VertexAIProvider(BaseModel):
    name = "vertexai"

    def __init__(self, **kwargs) -> None:
        super().__init__()
        vertexai.init(
            project=config.vertexai_project_id, location=config.vertexai_location
        )

    def _format_messages(
        self,
        raw_messages: MessageList,
    ) -> Any:
        model_message: list = []
        past_role = None
        for msg in raw_messages:
            current_role = msg.role if "role" != "system" else "user"
            if past_role != current_role:
                model_message.append(f"[{current_role.capitalize()}]: ")
                past_role = current_role

            if isinstance(msg.content, str):
                content = msg.content
            elif isinstance(msg.content, np.ndarray):
                # convert from RGB NDArray to bytes
                image = PIL.Image.fromarray(msg.content).convert("RGB")
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                content = Part.from_image(Image.from_bytes(buffered.getvalue()))
            elif isinstance(msg.content, Path):
                content = Part.from_image(Image.load_from_file(msg.content))
            else:
                assert (
                    False
                ), f"Unknown message type: {type(msg.content)}, {msg.content}"
            model_message.append(content)

        return model_message

    def generate_response(
        self, messages: MessageList, **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Creates a chat completion using the Gemini API."""
        model_message = self._format_messages(raw_messages=messages)

        model_name = kwargs.get("model", None)
        if model_name is not None:
            model = GenerativeModel(model_name)
        else:
            raise ValueError("Model name is required for GeminiProvider.")
        logger.info(f"Creating chat completion with model {model_name}.")

        generation_config = GenerationConfig(
            temperature=kwargs.get("temperature", config.temperature),
            # top_p=kwargs.get("top_p", config.max_tokens),
            top_k=kwargs.get("top_k", config.top_k),
            candidate_count=1,
            max_output_tokens=kwargs.get("max_tokens", config.max_tokens),
        )

        @backoff.on_exception(
            backoff.constant,
            ValueError,
            max_tries=config.max_retries,
            interval=10,
        )
        def _generate_response_with_retry() -> tuple[str, dict[str, int]]:
            try:
                response = model.generate_content(
                    contents=model_message, generation_config=generation_config
                )
            except Exception as e:
                raise ValueError(f"Failed to generate response: {e}")
            token_count = model.count_tokens(model_message)
            info = {
                "total_tokens": token_count.total_tokens,
            }
            try:
                message = response.text
            except ValueError as e:
                message = ""
                logger.error(f"Failed to generate response: {e}")

            logger.info(f"\nReceived response:\n{message}\nInfo:\n{info}")
            return message, info

        return _generate_response_with_retry()


class VertexAIAnthropicProvider(BaseModel):
    name = "vertexai-anthropic"

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.client = AnthropicVertex(
            project_id=config.vertexai_project_id, region=config.vertexai_location
        )
        self.system_prompt = None

    def _format_messages(
        self,
        raw_messages: MessageList,
    ) -> list[dict[str, Any]]:
        """
        Composes the messages to be sent to the model.
        """
        model_message: list[dict[str, Any]] = []
        past_role = None
        for msg in raw_messages:
            if msg.role == "system":
                self.system_prompt = msg.content
                continue
            if isinstance(msg.content, np.ndarray) or isinstance(msg.content, Path):
                content: dict = {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": anthropic_encode_image(msg.content),
                    },
                }
            elif isinstance(msg.content, str):
                content = {"type": "text", "text": msg.content}
            current_role = msg.role
            if past_role != current_role:
                model_message.append(
                    {
                        "role": current_role,
                        "content": [content],
                    }
                )
                past_role = current_role
            else:
                model_message[-1]["content"].append(content)
        return model_message

    def generate_response(
        self, messages: MessageList, **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Creates a chat completion using the Anthropic API."""

        model = kwargs.get("model", None)
        if model is None:
            raise ValueError("Model name is not set")
        temperature = kwargs.get("temperature", config.temperature)
        max_tokens = kwargs.get("max_tokens", config.max_tokens)
        model_message = self._format_messages(raw_messages=messages)
        logger.info(f"Creating chat completion with model {model}.")

        if self.system_prompt is not None:
            response = self.client.messages.create(
                model=model,
                messages=model_message,
                temperature=temperature,
                max_tokens=max_tokens,
                system=self.system_prompt,
            )
        else:
            response = self.client.messages.create(
                model=model,
                messages=model_message,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        if response is None:
            logger.error("Failed to get a response from Anthropic. Try again.")

        response_message = response.content[0].text
        if response.usage is None:
            info = {}
            logger.warn("Failed to get usage information from OpenAI.")
        else:
            info = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens
                + response.usage.output_tokens,
            }

        logger.info(f"\nReceived response:\n{response_message}\nInfo:\n{info}")

        return response_message, info
