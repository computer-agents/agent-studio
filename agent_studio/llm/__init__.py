import logging

from agent_studio.llm.base_model import BaseModel

logger = logging.getLogger(__name__)


def setup_model(provider_name: str) -> BaseModel:
    model: BaseModel
    if provider_name == "openai":
        from agent_studio.llm.openai import OpenAIProvider

        model = OpenAIProvider()
    elif provider_name == "gemini":
        from agent_studio.llm.gemini import GeminiProvider

        model = GeminiProvider()
    elif provider_name == "claude":
        from agent_studio.llm.claude import AnthropicProvider

        model = AnthropicProvider()
    elif provider_name in "huggingface":
        from agent_studio.llm.huggingface import HuggingFaceProvider

        model = HuggingFaceProvider()
    else:
        logger.warning(f"Unknown provider {provider_name}, fallback to remote provider")
        from agent_studio.llm.remote_model import RemoteProvider

        model = RemoteProvider()

    return model


__all__ = [
    "OpenAIProvider",
    "GeminiProvider",
    "AnthropicProvider",
    "HuggingFaceProvider",
    "RemoteProvider",
    "setup_model",
]
