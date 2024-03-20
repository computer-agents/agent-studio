import logging

from agent_studio.llm.base_model import BaseModel
from agent_studio.llm.gemini import GeminiProvider
from agent_studio.llm.openai import OpenAIProvider
from agent_studio.llm.remote_model import RemoteProvider


logger = logging.getLogger(__name__)


def setup_model(provider_name: str) -> BaseModel:
    model = BaseModel()
    match provider_name:
        case "openai":
            model = OpenAIProvider()
        case "gemini":
            model = GeminiProvider()
        case _:
            logger.warning(
                f"Unknown provider {provider_name}, fallback to remote provider"
            )
            model = RemoteProvider()

    return model


__all__ = [
    "OpenAIProvider",
    "GeminiProvider",
    "RemoteProvider",
    "setup_model",
]
