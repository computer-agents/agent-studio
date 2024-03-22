import logging
from pathlib import Path
from typing import Any

from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation import GenerationConfig

from agent_studio.config.config import Config
from agent_studio.llm.base_model import BaseModel

config = Config()
logger = logging.getLogger(__name__)


class HuggingFaceProvider(BaseModel):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.tokenizer = None
        self.model = None

    def compose_messages(
        self,
        intermedia_msg: list[dict[str, Any]],
    ) -> Any:
        model_message: list[dict[str, Any]] = []
        for msg in intermedia_msg:
            if isinstance(msg["content"], str):
                model_message.append({"text": msg["content"]})
            elif isinstance(msg["content"], Path):
                model_message.append({"image": msg["content"].as_posix()})
            else:
                assert False, f"Unknown message type: {msg['content']}"

        return model_message

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Creates a chat completion using the Gemini API."""
        model_message = self.compose_messages(intermedia_msg=messages)

        if self.model is None:
            self.model_name = kwargs.get("model", None)
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, device_map="cuda", trust_remote_code=True, bf16=True
            ).eval()
            assert self.model is not None, "Model is not loaded."
            self.model.generation_config = GenerationConfig.from_pretrained(
                self.model_name, do_sample=False, trust_remote_code=True
            )
        assert self.model is not None, "Model is not loaded."

        logger.info(
            f"Creating chat completion with model {self.model_name}. "
            f"Message:\n{model_message}"
        )

        query = self.tokenizer.from_list_format(model_message)
        response, _ = self.model.chat(self.tokenizer, query=query, history=None)

        logger.info(f"\nReceived response:\n{response}")

        return response, {"total_tokens": None}
