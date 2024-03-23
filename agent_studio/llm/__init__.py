import logging

from agent_studio.llm.base_model import BaseModel

logger = logging.getLogger(__name__)


def setup_model(provider_name: str) -> BaseModel:
    model: BaseModel
    if provider_name in [
        "gpt-3.5-turbo-0125",
        "gpt-4-vision-preview",
        "gpt-4-0125-preview",
    ]:
        from agent_studio.llm.openai import OpenAIProvider

        model = OpenAIProvider()
    elif provider_name in ["gemini-pro", "gemini-pro-vision"]:
        from agent_studio.llm.gemini import GeminiProvider

        model = GeminiProvider()
    elif provider_name in ["claude-3-sonnet-20240229", "claude-3-opus-20240229"]:
        from agent_studio.llm.claude import AnthropicProvider

        model = AnthropicProvider()
    elif provider_name in ["Qwen/Qwen-VL-Chat", "cckevinn/SeeClick"]:
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
