"""Config for language models."""
import argparse
import dataclasses
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LMConfig:
    """A config for a language model.

    Attributes:
        provider: The name of the API provider.
        model_name_or_path: The name or path of the model.
        temperature: The temperature for sampling.
    """

    provider: str
    model_name_or_path: str
    temperature: float = 0.1
    max_tokens: int = 1024
    gen_config: dict[str, Any] = dataclasses.field(default_factory=dict)


def construct_llm_config(args: argparse.Namespace) -> LMConfig:
    llm_config = LMConfig(
        provider=args.provider,
        model_name_or_path=args.model_name_or_path,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    if args.provider == "openai":
        # TODO: add reproducible seed
        pass
    elif args.provider == "vllm":
        llm_config.gen_config["tokenizer_name_or_path"] = args.tokenizer_name_or_path
        llm_config.gen_config[
            "use_slow_tokenizer"
        ] = args.use_slow_tokenizer  # default False
    elif args.provider == "huggingface":
        llm_config.gen_config["tokenizer_name_or_path"] = args.tokenizer_name_or_path
        llm_config.gen_config["use_fast_tokenizer"] = not args.use_slow_tokenizer
        llm_config.gen_config["padding_side"] = args.padding_side  # default left
        llm_config.gen_config["torch_dtype"] = args.torch_dtype
        llm_config.gen_config[
            "add_special_tokens"
        ] = args.add_special_tokens  # default True
        llm_config.gen_config["batch_size"] = args.batch_size  # dafeult 1
        llm_config.gen_config["num_return_sequences"] = args.num_return_sequences
    else:
        raise NotImplementedError(f"provider {args.provider} not implemented")
    return llm_config
