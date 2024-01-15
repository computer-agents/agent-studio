from typing import Any

from playground.llm.lm_config import LMConfig


class BaseLLM:
    """Base class for LLMs."""

    def __init__(self, lm_config: LMConfig) -> None:
        self.lm_config = lm_config

    def generate_response(self, prompt: list[dict[str, str]], stop: list[str]) -> Any:
        """Generate a response given a prompt."""
        raise NotImplementedError
