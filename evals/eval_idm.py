import logging
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
from common import map_with_progress
from eval_base import BaseEval

from agent_studio.utils.json_utils import add_jsonl
from agent_studio.utils.types import Message, MessageList

logger = logging.getLogger("eval_logger")

QUERY_TEMPLATE = """
Answer the following multiple choice question. The last line of your response should be of the following format: 'Answer: $LETTER' (without quotes) where LETTER is one of {choices}. Think step by step before answering. For example, if there'are three options "A: type\nB: click\nC: scroll", and you think the executed action is "click", then your response should be "Answer: B".

You are given two sequential images which denotes the observation before and after an action respectively, and the action is one of the steps to finish the insuruction. Your task is to determine the executed action type between the two observations.
Instruction: {instruction}

{choices_str}
""".strip()  # noqa: E501

# {''.join([chr(65 + i) for i in range(len(choices))])}
ANSWER_PATTERN = r"(?i)Answer\s*:\s*([A-Z])"


def format_idm_prompt(
    obs_before: np.ndarray | Path,
    obs_after: np.ndarray | Path,
    instruction: str,
    action_space: list[str],
) -> list:
    messages: MessageList = []
    messages.append(Message(role="user", content=obs_before))
    messages.append(Message(role="user", content=obs_after))
    choicestr = "\n".join(
        [f"{chr(65 + i)}. {action}" for i, action in enumerate(list(action_space))]
    )
    choices = "".join([chr(65 + i) for i in range(len(action_space))])
    messages.append(
        Message(
            role="user",
            content=QUERY_TEMPLATE.format(
                instruction=instruction, choices_str=choicestr, choices=choices
            ),
        )
    )

    return messages


def eval_idm_response(response: str, reference: str) -> float:
    try:
        match = re.search(ANSWER_PATTERN, response.splitlines()[-1])
    except Exception:
        match = None
    return 1.0 if (match and match.group(1).strip().startswith(reference)) else 0.0


class IDMSingleEval(BaseEval):
    def __call__(
        self,
        model_name: str,
        tokenizer_name: str,
    ) -> list[dict[str, Any]]:
        def fn(row: dict):
            if self.data_dir is not None:
                obs_before = Path(os.path.join(self.data_dir, row["obs_before"]))
                obs_after = Path(os.path.join(self.data_dir, row["obs_after"]))
                obs_before_path = row["obs_before"]
                obs_after_path = row["obs_after"]
            else:
                obs_before = np.array(row["obs_before"].convert("RGB"))
                obs_after = np.array(row["obs_after"].convert("RGB"))
                obs_before_path = row["obs_before_path"]
                obs_after_path = row["obs_after_path"]
            instruction = row["instruction"]
            action_space = row["action_space"]
            operation = row["operation"]

            # Query the model and evaluate the response
            prompt = format_idm_prompt(obs_before, obs_after, instruction, action_space)
            response, info = self.model.generate_response(
                prompt,
                model=model_name,
                tokenizer=tokenizer_name,
                do_sample=False,
                max_new_tokens=32,
                num_return_sequences=1,
            )
            # get the position in the set of action_space
            index = action_space.index(operation)
            ref_answer = chr(65 + index)

            score = eval_idm_response(response, ref_answer)

            result = {
                "obs_before": obs_before_path,
                "obs_after": obs_after_path,
                "action_space": action_space,
                "score": score,
                "source": row["source"],
                "platform": row["platform"],
                "annotation_id": row["action_id"],
                "instruction": instruction,
                "response": response,
                "ref_answer": operation,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            add_jsonl([result], self.result_filename)
            logger.info(f"Writing results {row['action_id']} to {self.result_filename}")

        map_with_progress(fn, self.data, self.num_workers)
