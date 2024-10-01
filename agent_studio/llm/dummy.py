import logging
from typing import Any

from agent_studio.config.config import Config
from agent_studio.llm.base_model import BaseModel
from agent_studio.utils.types import MessageList

config = Config()
logger = logging.getLogger(__name__)


class DummyProvider(BaseModel):
    """
    Dummy provider for testing. Not provide any real LLM.
    To test if the interface is working.
    """

    name = "dummy"

    def generate_response(
        self, messages: MessageList, **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Creates a chat completion using the Gemini API."""

        model_name = kwargs.get("model", None)
        if model_name != "dummy":
            raise ValueError("Please use model name 'dummy'.")
        logger.info(f"Creating chat completion with model {model_name}.")

        return "", {}
