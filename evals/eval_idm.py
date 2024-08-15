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

logger = logging.getLogger("agent_studio")

QUERY_TEMPLATE = """
Analyze the two sequential images provided. These images represent observations before and after an action was taken. Your task is to identify which type of action was executed between these two observations.
Available actions:
{choices_str}
After your analysis, conclude your response with the answer in this format:
Answer: X
Where X is the letter corresponding to the action you believe was taken, chosen from the options provided above.
For example, if the options were:
A: Type
B: Click
C: Scroll
And you determined the action was "Click", your response would end with:
Answer: B
""".strip()  # noqa: E501

ANSWER_PATTERN = r"(?i)Answer\s*:\s*([A-Z])"


def format_idm_prompt(
    obs_before: np.ndarray | Path,
    obs_after: np.ndarray | Path,
    obs_before_path: str,
    obs_after_path: str,
    action_space: list[str],
) -> list:
    choicestr = "\n".join(
        [f"{chr(65 + i)}. {action}" for i, action in enumerate(list(action_space))]
    )

    messages: MessageList = [
        Message(role="user", content=obs_before),
        Message(role="user", content=obs_after),
        Message(
            role="user",
            content=QUERY_TEMPLATE.format(choices_str=choicestr),
        ),
    ]

    messages_str = [
        {
            "role": "user",
            "content": obs_before_path,
        },
        {
            "role": "user",
            "content": obs_after_path,
        },
        {
            "role": "user",
            "content": QUERY_TEMPLATE.format(choices_str=choicestr),
        },
    ]

    return messages, messages_str


def parse_idm_response(response: str) -> str:
    try:
        match = re.findall(ANSWER_PATTERN, response)[-1]
    except Exception:
        match = None
    return match


def eval_idm_response(response: str, reference: str) -> float:
    return 1.0 if response == reference else 0.0


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
            action_space = row["action_space"]
            operation = row["operation"]

            # Query the model and evaluate the response
            prompt, prompt_str = format_idm_prompt(
                obs_before,
                obs_after,
                obs_before_path,
                obs_after_path,
                action_space,
            )
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
            answer = parse_idm_response(response)
            score = eval_idm_response(answer, ref_answer)

            result = {
                "prompt": prompt_str,
                "score": score,
                "source": row["source"],
                "platform": row["platform"],
                "instruction": row["instruction"],
                "response": response,
                "parsed_answer": answer,
                "ref_answer": operation,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            add_jsonl([result], self.result_filename)
            logger.info(f"Writing results {row['action_id']} to {self.result_filename}")

        map_with_progress(fn, self.data, self.num_workers)
