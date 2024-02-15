from playground.llm.base_model import BaseModel
from playground.llm.openai import OpenAIProvider


def setup_model(provider_name) -> BaseModel:
    match provider_name:
        case "openai":
            model = OpenAIProvider()
        case _:
            raise NotImplementedError(f"Provider {provider_name} not implemented")

    return model


__all__ = [
    "OpenAIProvider",
    "setup_model",
]
