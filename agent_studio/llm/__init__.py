import logging

from agent_studio.llm.base_model import BaseModel
from agent_studio.llm.claude import AnthropicProvider
from agent_studio.llm.gemini import GeminiProvider
from agent_studio.llm.openai import OpenAIProvider
from agent_studio.llm.remote_model import RemoteProvider

logger = logging.getLogger(__name__)


def setup_model(provider_name: str) -> BaseModel:
    model = BaseModel()
    if provider_name in [
        "gpt-3.5-turbo-0125",
        "gpt-4-vision-preview",
        "gpt-4-0125-preview",
    ]:
        model = OpenAIProvider()
    elif provider_name in ["gemini-pro", "gemini-pro-vision"]:
        model = GeminiProvider()
    elif provider_name in ["claude-3-sonnet-20240229", "claude-3-opus-20240229"]:
        model = AnthropicProvider()
    else:
        logger.warning(f"Unknown provider {provider_name}, fallback to remote provider")
        model = RemoteProvider()

    return model


__all__ = [
    "OpenAIProvider",
    "GeminiProvider",
    "RemoteProvider",
    "setup_model",
]
