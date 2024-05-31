import logging
from pathlib import Path
from typing import Any
from PIL import Image
import torch

from transformers import AutoModelForCausalLM, AutoTokenizer, AutoProcessor, PaliGemmaForConditionalGeneration
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
        self.processor = None

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
            elif isinstance(msg["content"], Image.Image):
                model_message.append({"image": msg["content"].convert('RGB')})
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
            tokenizer_name = kwargs.get("tokenizer", self.model_name)
            self.dtype = torch.bfloat16
            if "paligemma" in self.model_name:
                self.model = PaliGemmaForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=self.dtype,
                ).to("cuda").eval()
                self.processor = AutoProcessor.from_pretrained(self.model_name)
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    tokenizer_name, trust_remote_code=True
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=self.dtype,
                    trust_remote_code=True,
                ).to("cuda").eval()
                self.model.generation_config = GenerationConfig.from_pretrained(
                    self.model_name, do_sample=False, trust_remote_code=True
                )

        assert self.model is not None, "Model is not loaded."

        logger.info(
            f"Creating chat completion with model {self.model_name}. "
            f"Message:\n{model_message}"
        )

        if "cogvlm" in self.model_name:
            assert len(model_message) == 2 and "text" in model_message[0] and "image" in model_message[1], "Expected only 1 text and 1 image for cogvlm."
            query = model_message[0]["text"]
            image = model_message[1]["image"]
            assert isinstance(image, Image.Image), "Expected image to be of type PIL.Image."
            input_by_model = self.model.build_conversation_input_ids(
                self.tokenizer,
                query=query,
                history=[],
                images=[image],
                template_version="chat",
            )
            inputs = {
                "input_ids": input_by_model["input_ids"].unsqueeze(0).to("cuda"),
                "token_type_ids": input_by_model["token_type_ids"].unsqueeze(0).to("cuda"),
                "attention_mask": input_by_model["attention_mask"].unsqueeze(0).to("cuda"),
                "images": [[input_by_model["images"][0].to("cuda").to(self.dtype)]]
                if image is not None
                else None,
            }
            gen_kwargs = {
                "max_new_tokens": 2048,
                "pad_token_id": 128002,
            }
            with torch.no_grad():
                outputs = self.model.generate(**inputs, **gen_kwargs)
                outputs = outputs[:, inputs["input_ids"].shape[1]:]
                response = self.tokenizer.decode(outputs[0])
                response = response.split("<|end_of_text|>")[0]
        
        elif "cogagent" in self.model_name:
            assert len(model_message) == 2 and "text" in model_message[0] and "image" in model_message[1], "Expected only 1 text and 1 image for cogagent."
            query = model_message[0]["text"]
            image = model_message[1]["image"]
            assert isinstance(image, Image.Image), "Expected image to be of type PIL.Image."
            input_by_model = self.model.build_conversation_input_ids(
                self.tokenizer,
                query=query,
                history=[],
                images=[image],
                # template_version="chat",
            )
            inputs = {
                "input_ids": input_by_model["input_ids"].unsqueeze(0).to("cuda"),
                "token_type_ids": input_by_model["token_type_ids"].unsqueeze(0).to("cuda"),
                "attention_mask": input_by_model["attention_mask"].unsqueeze(0).to("cuda"),
                "images": [[input_by_model["images"][0].to("cuda").to(self.dtype)]]
                if image is not None
                else None,
            }
            if 'cross_images' in input_by_model and input_by_model['cross_images']:
                inputs['cross_images'] = [[input_by_model['cross_images'][0].to("cuda").to(self.dtype)]]
            gen_kwargs = {
                "max_new_tokens": 2048,
                "do_sample": False,
            }
            with torch.no_grad():
                outputs = self.model.generate(**inputs, **gen_kwargs)
                outputs = outputs[:, inputs["input_ids"].shape[1]:]
                response = self.tokenizer.decode(outputs[0])
                response = response.split("</s>")[0]

        elif "paligemma" in self.model_name:
            assert len(model_message) == 2 and "text" in model_message[0] and "image" in model_message[1], "Expected only 1 text and 1 image for paligemma."
            query = model_message[0]["text"]
            image = model_message[1]["image"]
            assert isinstance(image, Image.Image), "Expected image to be of type PIL.Image."
            inputs = self.processor(query, image, return_tensors="pt").to("cuda")
            gen_kwargs = {
                "max_new_tokens": 2048,
                "do_sample": False,
            }
            output = self.model.generate(**inputs, **gen_kwargs)
            response = self.processor.decode(
                output[0], skip_special_tokens=True
            )[len(query):]

        elif "Qwen" in self.model_name or "SeeClick" in self.model_name:
            query = self.tokenizer.from_list_format(model_message)
            response, _ = self.model.chat(self.tokenizer, query=query, history=None)

        else:
            raise ValueError(f"Model {self.model_name} is not supported.")

        logger.info(f"\nReceived response:\n{response}")

        return response, {"total_tokens": None}
