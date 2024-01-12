from typing import Any

from langchain_openai.chat_models import ChatOpenAI

from llm.base_llm import BaseLLM


class OpenAIProvider(BaseLLM):
    """OpenAI provider."""

    def __init__(self, lm_config):
        super().__init__(lm_config)
        self.model = ChatOpenAI(
            model_name=lm_config.model_name_or_path,
            max_tokens=self.lm_config.max_tokens,
        )

    def generate_response(self, prompt: list[dict[str, str]], stop: list[str]) -> Any:
        """Generate a response given a prompt."""
        return self.model.generate(
            messages=prompt,
            stop=stop,
            temperature=self.lm_config.temperature,
        )
