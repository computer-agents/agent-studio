from llm.huggingface import HFProvider
from llm.lm_config import LMConfig
from llm.openai import OpenAIProvider
from llm.vllm import VLLMProvider


def setup_llm(lm_config: LMConfig):
    if lm_config.provider == "openai":
        model_provider = OpenAIProvider(lm_config)
    elif lm_config.provider == "vllm":
        print("Loading model and tokenizer...")
        model_provider = VLLMProvider(lm_config)
    elif lm_config.provider == "huggingface":
        print("Loading model and tokenizer...")
        model_provider = HFProvider(lm_config)
    else:
        raise NotImplementedError(f"Provider {lm_config.provider} not implemented")

    return model_provider
