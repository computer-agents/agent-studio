import logging
from pathlib import Path
from typing import Any

from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor
from transformers.generation import GenerationConfig

from agent_studio.config.config import Config
from agent_studio.llm.base_model import BaseModel

config = Config()
logger = logging.getLogger(__name__)


class HuggingFaceProvider(BaseModel):
    name = "huggingface"

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.tokenizer = None
        self.model = None
        # self.processor = None

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
            if self.model_name == "cckevinn/SeeClick":
                tokenizer_name = "Qwen/Qwen-VL-Chat"
            else:
                tokenizer_name = self.model_name
            self.tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_name, trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, device_map="cuda", trust_remote_code=True, bf16=True
            ).eval()
            assert self.model is not None, "Model is not loaded."
            self.model.generation_config = GenerationConfig.from_pretrained(
                self.model_name, do_sample=True, trust_remote_code=True
            )
            # self.processor = AutoProcessor.from_pretrained(self.model_name)

        assert self.model is not None, "Model is not loaded."

        logger.info(
            f"Creating chat completion with model {self.model_name}. "
            f"Message:\n{model_message}"
        )

        # if "paligemma" in self.model_name:
        #     inputs = self.processor(*list(model_message.values()), return_tensors="pt").to("cuda")
        #     output = self.model.generate(**inputs, max_new_tokens=20)
        #     print(self.processor.decode(output[0], skip_special_tokens=True)[len(prompt):])
        query = self.tokenizer.from_list_format(model_message)
        response, _ = self.model.chat(self.tokenizer, query=query, history=None)

        logger.info(f"\nReceived response:\n{response}")

        return response, {"total_tokens": None}
