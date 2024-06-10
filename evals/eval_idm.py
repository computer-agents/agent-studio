import os
import re
from pathlib import Path
from typing import Tuple, Any
import json
import logging

import numpy as np
from common import map_with_progress
from pydantic_core import from_json

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import read_jsonl, add_jsonl
from hzy.schema import Action, Episode

QUERY_TEMPLATE = """
Answer the following multiple choice question. The last line of your response should be of the following format: 'Answer: $LETTER' (without quotes) where LETTER is one of {choices}. Think step by step before answering.

You are given two sequential images which denotes the observation before and after an action respectively, and the action is one of the steps to finish the insuruction. Your task is to determine the executed action type between the two observations. 
Instruction: {instruction}

{choices_str}
""".strip()  # noqa: E501

# {''.join([chr(65 + i) for i in range(len(choices))])}
ANSWER_PATTERN = r"(?i)Answer\s*:\s*([A-Z])"


def format_idm_prompt(
    data_dir: str,
    instruction: str,
    action: Action,
    action_space: list[str],
) -> list:
    messages = [
        # {"role": "user", "content": QUERY_TEMPLATE.format(instruction=episode.instruction, action_space=", ".join(list(get_action_space())))},
    ]
    if action.obs_before is not None and action.obs_after is not None:
        messages.append({"role": "user", "content": Path(data_dir, action.obs_before)})
        messages.append({"role": "user", "content": Path(data_dir, action.obs_after)})
    choicestr = "\n".join([f"{chr(65 + i)}. {action}" for i, action in enumerate(list(action_space))])
    choices = ''.join([chr(65 + i) for i in range(len(action_space))])
    messages.append({"role": "user", "content": QUERY_TEMPLATE.format(instruction=instruction, choices_str=choicestr, choices=choices)})

    return messages


def eval_idm_response(response: str, reference: str) -> float:
    try:
        match = re.search(ANSWER_PATTERN, response.splitlines()[-1])
    except:
        match = None
    return 1.0 if (match and match.group(1).strip().startswith(reference)) else 0.0


class IDMEval:
    def __init__(
        self,
        model: BaseModel,
        data_path: str,
        result_filename: str,
        start_idx: int = 0,
        end_idx: int | None = None,
        num_workers: int = 1,
    ):
        self.model = model
        self.data = read_jsonl(data_path, start_idx, end_idx)
        self.data_dir = os.path.join(Path(data_path).parent.parent, "image100")
        self.result_filename = result_filename
        self.num_workers = num_workers

    def __call__(
        self, model_name: str, tokenizer_name: str,
    ) -> list[dict[str, Any]]:
        results = []
        def fn(row: dict):
            episode: Episode = Episode.model_validate(row)

            i = (len(episode.actions)-2)
            if i < 0 or episode.actions[i].obs_before is None or episode.actions[i].obs_after is None:
                logging.error(f"obs_before or obs_after is None")
                return
            # Query the model and evaluate the response
            prompt = format_idm_prompt(self.data_dir, episode.instruction, episode.actions[i], episode.action_space)
            response, info = self.model.generate_response(
                prompt, model=model_name, tokenizer=tokenizer_name,
                do_sample=False, max_length=32, num_return_sequences=1,
            )
            # get the position in the set of action_space
            ref_answer = None
            for j, a in enumerate(episode.action_space):
                if a == episode.actions[i].operation:
                    ref_answer = chr(65 + j)
                    break
            if ref_answer is None:
                logging.error(f"action not found {episode.actions[i].operation}")

            score = eval_idm_response(response, ref_answer)

            result = {
                "obs_before": episode.actions[i].obs_before,
                "obs_after": episode.actions[i].obs_after,
                "score": score,
                "source": episode.source,
                "annotation_id": episode.annotation_id,
                # "prompt": prompt,
                "instruction": episode.instruction,
                "response": response,
                "ref_answer": episode.actions[i].operation,
                # "parsed_action": action,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            results.append(result)

        map_with_progress(fn, self.data, self.num_workers)
        add_jsonl(results, self.result_filename)
