from typing import Any, Dict, List

import torch
import tqdm
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    GPTNeoXForCausalLM,
    OPTForCausalLM,
    StoppingCriteria,
)

from llm.base_llm import BaseLLM


class KeyWordsCriteria(StoppingCriteria):
    def __init__(self, stop_id_sequences):
        assert isinstance(
            stop_id_sequences[0], list
        ), "stop_id_sequences should be a list of list of ids"
        self.stop_sequences = stop_id_sequences

    def __call__(
        self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs
    ) -> bool:
        sequences_should_be_stopped = []
        for i in range(input_ids.shape[0]):
            sequence_should_be_stopped = False
            for stop_sequence in self.stop_sequences:
                if input_ids[i][-len(stop_sequence) :].tolist() == stop_sequence:
                    sequence_should_be_stopped = True
                    break
            sequences_should_be_stopped.append(sequence_should_be_stopped)
        return all(sequences_should_be_stopped)


class HFProvider(BaseLLM):
    """HuggingFace provider."""

    def __init__(self, lm_config):
        super().__init__(lm_config)
        lm_config.device_map = (
            "balanced_low_0" if torch.cuda.device_count() > 1 else "auto"
        )
        if lm_config.device_map:
            self.model = AutoModelForCausalLM.from_pretrained(
                lm_config.model_name_or_path,
                device_map=lm_config.device_map,
                torch_dtype=lm_config.torch_dtype,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                lm_config.model_name_or_path, torch_dtype=lm_config.torch_dtype
            )
            if torch.cuda.is_available():
                self.model = self.model.cuda()
        self.model.eval()
        if not lm_config.tokenizer_name_or_path:
            lm_config.tokenizer_name_or_path = lm_config.model_name_or_path
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                lm_config.tokenizer_name_or_path, use_fast=lm_config.use_fast_tokenizer
            )
        except ValueError:
            # some tokenizers (e.g., GPTNeoXTokenizer) don't have the slow or fast
            # version, so we just roll back to the default one
            self.tokenizer = AutoTokenizer.from_pretrained(
                lm_config.tokenizer_name_or_path
            )

        # set padding side to left for batch generation
        self.tokenizer.padding_side = lm_config.padding_side
        # set pad token to eos token if pad token is not set (as is the case for llama)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        # for OPT and Pythia models, we need to set tokenizer.model_max_length to
        # model.config.max_position_embeddings
        # to avoid wrong embedding index.
        if isinstance(self.model, GPTNeoXForCausalLM) or isinstance(
            self.model, OPTForCausalLM
        ):
            self.tokenizer.model_max_length = self.model.config.max_position_embeddings
            print(
                "Set tokenizer.model_max_length to "
                "model.config.max_position_embeddings: {}".format(
                    self.model.config.max_position_embeddings
                )
            )

    def generate_response(self, prompt: List[Dict[str, str]], stop: List[str]) -> Any:
        """Generate a response given a prompt."""
        stop_id_sequences = (
            None  # For chat format, we will rely on the model knows when to stop.
        )
        generations = []
        progress = tqdm.tqdm(total=len(prompt), desc="Generating Completions")

        num_return_sequences = self.lm_config.gen_config.get("num_return_sequences", 1)
        for i in range(0, len(prompt), self.lm_config.gen_config.get("batch_size", 1)):
            batch_prompts = prompt[
                i : i + self.lm_config.gen_config.get("batch_size", 1)
            ]
            tokenized_prompts = self.tokenizer(
                batch_prompts,
                padding="longest",
                return_tensors="pt",
                add_special_tokens=self.lm_config.gen_config.get(
                    "add_special_tokens", True
                ),
            )
            batch_input_ids = tokenized_prompts.input_ids
            attention_mask = tokenized_prompts.attention_mask

            if self.model.device.type == "cuda":
                batch_input_ids = batch_input_ids.cuda()
                attention_mask = attention_mask.cuda()

            try:
                batch_outputs = self.model.generate(
                    input_ids=batch_input_ids,
                    attention_mask=attention_mask,
                    stopping_criteria=[KeyWordsCriteria(stop_id_sequences)]
                    if stop_id_sequences
                    else None,
                )

                # the stopping criteria is applied at batch level, so if other examples
                # are not stopped, the entire batch will continue to generate.
                # so some outputs still have the stop sequence to remove.
                if stop_id_sequences:
                    for output_idx in range(batch_outputs.shape[0]):
                        for token_idx in range(
                            batch_input_ids.shape[1], batch_outputs.shape[1]
                        ):
                            if any(
                                batch_outputs[
                                    output_idx,
                                    token_idx : token_idx + len(stop_sequence),
                                ].tolist()
                                == stop_sequence
                                for stop_sequence in stop_id_sequences
                            ):
                                batch_outputs[
                                    output_idx, token_idx:
                                ] = self.tokenizer.pad_token_id
                                break

                # remove the prompt from the output
                # we need to re-encode the prompt because we need to make sure the
                # special tokens are treated the same way as in the outputs.
                # we changed our previous way of truncating the output token ids
                # dicrectly because some tokenizer (e.g., llama) won't add space
                # token before the first token.
                # space is important for some tasks (e.g., code completion).
                batch_outputs = self.tokenizer.batch_decode(
                    batch_outputs, skip_special_tokens=True
                )
                batch_prompts = self.tokenizer.batch_decode(
                    batch_input_ids, skip_special_tokens=True
                )
                # duplicate the prompts to match the number of return sequences
                batch_prompts = [
                    prompt
                    for prompt in batch_prompts
                    for _ in range(num_return_sequences)
                ]
                batch_generations = [
                    output[len(prompt) :]
                    for prompt, output in zip(batch_prompts, batch_outputs)
                ]
            except Exception as e:
                print("Error when generating completions for batch:")
                print(batch_prompts)
                print("Error message:")
                print(e)
                print("Use empty string as the completion.")
                batch_generations = [""] * len(batch_prompts) * num_return_sequences

            generations += batch_generations

            progress.update(len(batch_prompts) // num_return_sequences)

        assert (
            len(generations) == len(prompt) * num_return_sequences
        ), "number of generations should be equal to number of "
        "prompts * num_return_sequences"

        return generations
