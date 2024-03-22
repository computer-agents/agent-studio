from typing import Any
import logging
import backoff

from agent_studio.config.config import Config
from agent_studio.llm.base_model import BaseModel

from anthropic import Anthropic, APIError, RateLimitError, APITimeoutError

config = Config()
logger = logging.getLogger(__name__)


class AnthropicProvider(BaseModel):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.client = Anthropic(api_key=config.anthropic_api_key)
        self.system_prompt = None

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
            if msg["role"] == "system":
                self.system_prompt = msg["content"]
                continue
            if isinstance(msg["content"], list):
                content: dict = {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": msg["content"][0],
                    },
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
        """Creates a chat completion using the Anthropic API."""

        model = kwargs.get("model", None)
        if model is None:
            raise ValueError("Model name is not set")
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
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            logger.info(f"\nReceived response:\n{response_message}\nInfo:\n{info}")

            return response_message, info

        return _generate_response_with_retry()
