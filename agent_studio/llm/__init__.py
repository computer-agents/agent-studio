import logging

from agent_studio.llm.base_model import BaseModel

logger = logging.getLogger(__name__)


def setup_model(provider_name: str) -> BaseModel:
    if provider_name in [
        "gpt-4o-2024-05-13",
        "gpt-4-turbo-2024-04-09",
        "gpt-3.5-turbo-0125",
    ]:
        from agent_studio.llm.openai import OpenAIProvider
        
        model = OpenAIProvider()

    elif provider_name in [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro-vision",
        "gemini-1.0-pro",
    ]:
        from agent_studio.llm.gemini import GeminiProvider

        model = GeminiProvider()

    elif provider_name in [
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229",
    ]:
        from agent_studio.llm.claude import AnthropicProvider

        model = AnthropicProvider()

    else:
        from agent_studio.llm.huggingface import HuggingFaceProvider

        model = HuggingFaceProvider()

    return model


__all__ = [
    "setup_model",
]
