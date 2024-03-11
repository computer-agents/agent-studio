from agent_studio.llm.base_model import BaseModel
from agent_studio.llm.gemini import GeminiProvider
from agent_studio.llm.openai import OpenAIProvider


def setup_model(provider_name: str) -> BaseModel:
    model = BaseModel()
    match provider_name:
        case "openai":
            model = OpenAIProvider()
        case "gemini":
            model = GeminiProvider()
        case _:
            raise NotImplementedError(f"Provider {provider_name} not implemented")

    return model


__all__ = [
    "OpenAIProvider",
    "setup_model",
]
