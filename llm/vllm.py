from typing import Any, Dict, List

import torch
import vllm

from llm.base_llm import BaseLLM


class VLLMProvider(BaseLLM):
    """VLLM provider."""

    def __init__(self, lm_config):
        super().__init__(lm_config)
        self.model = vllm.LLM(
            model=lm_config.model_name_or_path,
            tokenizer=lm_config.tokenizer_name_or_path
            if lm_config.tokenizer_name_or_path
            else lm_config.model_name_or_path,
            tokenizer_mode="slow" if lm_config.use_slow_tokenizer else "auto",
            tensor_parallel_size=torch.cuda.device_count(),
        )

    def generate_response(self, prompt: List[Dict[str, str]], stop: List[str]) -> Any:
        """Generate a response given a prompt."""
        # We need to remap the outputs to the prompts because vllm might not return
        # outputs for some prompts (e.g., if the prompt is too long)
        sampling_params = vllm.SamplingParams(
            temperature=self.lm_config.temperature,
            max_tokens=self.lm_config.max_tokens,
            stop=stop,
        )
        generations = self.model.generate(prompt, sampling_params)
        prompt_to_output = {g.prompt: g.outputs[0].text for g in generations}
        outputs = [prompt_to_output[p] if p in prompt_to_output else "" for p in prompt]

        return outputs
