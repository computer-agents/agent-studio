import logging
from typing import Any

import backoff
import requests

from agent_studio.config.config import Config
from agent_studio.llm.base_model import BaseModel
from agent_studio.utils.communication import bytes2str, str2bytes


config = Config()
logger = logging.getLogger(__name__)


class RemoteProvider(BaseModel):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.model_server: str | None = getattr(config, "model_server", None)
        assert self.model_server, "Model server is not set"

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Creates a chat completion using the Gemini API."""

        model_name = kwargs.get("model", None)
        if model_name is None:
            raise ValueError("Model name is not set")

        @backoff.on_exception(
            backoff.constant,
            ConnectionError,
            max_tries=config.max_retries,
            interval=10,
        )
        def _generate_response_with_retry() -> tuple[str, dict[str, int]]:
            body = {
                "model": model_name,
                "messages": bytes2str(messages),
            }
            response_raw = requests.post(f"{self.model_server}/generate", json=body)
            if response_raw.status_code != 200:
                logger.error(
                    f"Failed to generate response: {response_raw.status_code}, "
                    f"{response_raw.text}"
                )
                raise ConnectionError
            message: str = str2bytes(response_raw.json()["message"])
            info: dict[str, Any] = str2bytes(response_raw.json()["info"])

            logger.info(f"\nReceived response:\n{message}\nInfo:\n{info}")
            return message, info

        return _generate_response_with_retry()
