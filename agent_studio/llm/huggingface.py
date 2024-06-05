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
        kwargs.pop("model")
        kwargs.pop("tokenizer")

        assert self.model is not None, "Model is not loaded."

        logger.info(
            f"Creating chat completion with model {self.model_name}. "
            f"Message:\n{model_message}"
        )

        if "cogvlm" in self.model_name:
            assert len(model_message) == 2 and "text" in model_message[1] and "image" in model_message[0], "Expected only 1 image and 1 text for cogvlm."
            query = model_message[1]["text"]
            image = Image.open(model_message[0]["image"]).convert("RGB")
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
                "max_new_tokens": 32,
                "pad_token_id": 128002,
            }
            with torch.no_grad():
                outputs = self.model.generate(**inputs, **gen_kwargs)
                outputs = outputs[:, inputs["input_ids"].shape[1]:]
                response = self.tokenizer.decode(outputs[0])
                response = response.split("<|end_of_text|>")[0]
        
        elif "cogagent" in self.model_name:
            assert len(model_message) == 2 and "text" in model_message[1] and "image" in model_message[0], "Expected only 1 image and 1 text for cogagent."
            query = model_message[1]["text"]
            image = Image.open(model_message[0]["image"]).convert("RGB")
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
                "max_new_tokens": 32,
                "do_sample": False,
            }
            with torch.no_grad():
                outputs = self.model.generate(**inputs, **gen_kwargs)
                outputs = outputs[:, inputs["input_ids"].shape[1]:]
                response = self.tokenizer.decode(outputs[0])
                response = response.split("</s>")[0]

        elif "paligemma" in self.model_name:
            assert len(model_message) == 2 and "text" in model_message[1] and "image" in model_message[0], "Expected only 1 image and 1 text for paligemma."
            query = model_message[1]["text"]
            image = Image.open(model_message[0]["image"]).convert("RGB")
            inputs = self.processor(query, image, return_tensors="pt").to("cuda")
            gen_kwargs = {
                "max_new_tokens": 32,
                "do_sample": False,
            }
            output = self.model.generate(**inputs, **gen_kwargs)
            response = self.processor.decode(
                output[0], skip_special_tokens=True
            )[len(query):]

        elif "Qwen" in self.model_name or "SeeClick" in self.model_name:
            system = "You are a helpful assistant."

            # format input
            text = ''
            num_images = 0
            for ele in model_message:
                if 'image' in ele:
                    num_images += 1
                    text += f'Picture {num_images}: '
                    text += '<img>' + ele['image'] + '</img>'
                    text += '\n'
                elif 'text' in ele:
                    text += ele['text']
                elif 'box' in ele:
                    if 'ref' in ele:
                        text += '<ref>' + ele['ref'] + '</ref>'
                    for box in ele['box']:
                        text += '<box>' + '(%d,%d),(%d,%d)' % (box[0], box[1], box[2], box[3]) + '</box>'
                else:
                    raise ValueError("Unsupport element: " + str(ele))
            query = text

            # tokenize input
            im_start, im_end = "<|im_start|>", "<|im_end|>"
            im_start_tokens = [self.tokenizer.im_start_id]
            im_end_tokens = [self.tokenizer.im_end_id]
            nl_tokens = self.tokenizer.encode("\n")

            def _tokenize_str(role, content):
                return f"{role}\n{content}", self.tokenizer.encode(
                    role, allowed_special=set(self.tokenizer.IMAGE_ST)
                ) + nl_tokens + self.tokenizer.encode(content, allowed_special=set(self.tokenizer.IMAGE_ST))

            system_text, system_tokens_part = _tokenize_str("system", system)
            context_tokens = im_start_tokens + system_tokens_part + im_end_tokens
            raw_text = f"{im_start}{system_text}{im_end}"
            context_tokens += (
                nl_tokens
                + im_start_tokens
                + _tokenize_str("user", query)[1]
                + im_end_tokens
                + nl_tokens
                + im_start_tokens
                + self.tokenizer.encode("assistant")
                + nl_tokens
            )
            raw_text += f"\n{im_start}user\n{query}{im_end}\n{im_start}assistant\n"

            # generate response
            stop_words_ids = [[self.tokenizer.im_end_id], [self.tokenizer.im_start_id]]
            input_ids = torch.tensor([context_tokens]).to("cuda")
            outputs = self.model.generate(
                input_ids,
                stop_words_ids=stop_words_ids,
                return_dict_in_generate=False,
                **kwargs,
            )

            # decode tokens
            tokens = outputs[0]
            if torch.is_tensor(tokens):
                tokens = tokens.cpu().numpy().tolist()
            eod_token_ids = [self.tokenizer.im_start_id, self.tokenizer.im_end_id]
            context_length = len(context_tokens)
            eod_token_idx = context_length
            for eod_token_idx in range(context_length, len(tokens)):
                if tokens[eod_token_idx] in eod_token_ids:
                    break
            trim_decode_tokens = self.tokenizer.decode(tokens[:eod_token_idx], errors='replace')[len(raw_text):].strip()
            response = trim_decode_tokens

        elif "MiniCPM" in self.model_name:
            assert len(model_message) == 2 and "text" in model_message[1] and "image" in model_message[0], "Expected only 1 image and 1 text for paligemma."
            image = Image.open(model_message[0]["image"]).convert("RGB")
            response = self.model.chat(
                image=image,
                msgs=[{'role': 'user', 'content': model_message[1]['text']}],
                tokenizer=self.tokenizer,
                max_new_tokens=32,
                sampling=False,  # if sampling=False, beam_search will be used by default
                # temperature=0.7,
                # system_prompt='' # pass system_prompt if needed
            )

        else:
            raise ValueError(f"Model {self.model_name} is not supported.")

        logger.info(f"\nReceived response:\n{response}")

        return response, {"total_tokens": None}
