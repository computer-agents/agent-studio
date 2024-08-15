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
Analyze the sequence of images provided. These images are snapshots taken from a video screen recording. Your task is to identify the types of actions executed in order throughout this recording.
Available actions:
{choices_str}
After your analysis, conclude your response with the answer in this format:
Answer:
X
Y
Z
...
Where X, Y, Z, etc. are letters corresponding to the actions you believe were taken, chosen from the options provided above.
For example, if the options were:
A: Type
B: Click
C: Scroll
And you determined the actions were "Type", then "Scroll", your response would end with:
Answer:
A
C
""".strip()  # noqa: E501

ANSWER_PATTERN = r"(?i)Answer:\s*([A-Z](?:\n[A-Z])*)"


def format_idm_prompt(
    actions: list[dict],
    action_space: list[str],
) -> tuple[list, list, list]:
    choicestr = "\n".join(
        [
            f"{chr(65 + i)}. {selected_actions}"
            for i, selected_actions in enumerate(list(action_space))
        ]
    )

    messages: MessageList = [
        Message(
            role="user",
            content=action["obs_before"],
        )
        for action in actions
    ]
    messages.append(
        Message(
            role="user",
            content=actions[-1]["obs_after"],
        )
    )
    messages.append(
        Message(
            role="user",
            content=QUERY_TEMPLATE.format(choices_str=choicestr),
        )
    )

    messages_str = [
        {
            "role": "user",
            "content": action["obs_before_path"],
        }
        for action in actions
    ]
    messages_str.append(
        {
            "role": "user",
            "content": actions[-1]["obs_after_path"],
        }
    )
    messages_str.append(
        {
            "role": "user",
            "content": QUERY_TEMPLATE.format(choices_str=choicestr),
        }
    )

    return messages, messages_str


def parse_idm_response(response: str) -> str:
    try:
        match = re.findall(ANSWER_PATTERN, response)[-1].split("\n")
    except Exception:
        match = []
    return match


def get_edit_distance(response: list[str], reference: list[str]) -> int:
    len1 = len(response)
    len2 = len(reference)

    # Create a 2D array, where dp[i][j] represents the edit distance between the first i characters of response and the first j characters of reference  # noqa: E501
    dp = [[0 for _ in range(len2 + 1)] for _ in range(len1 + 1)]

    # Initialize dp array
    for i in range(len1 + 1):
        dp[i][
            0
        ] = i  # The cost of converting the first i characters of response to an empty list (all deletions)  # noqa: E501
    for j in range(len2 + 1):
        dp[0][
            j
        ] = j  # The cost of converting an empty list to the first j characters of reference (all insertions)  # noqa: E501

    # Fill the dp array
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if response[i - 1] == reference[j - 1]:
                dp[i][j] = dp[i - 1][
                    j - 1
                ]  # No extra cost if the current characters are the same
            else:
                # Take the minimum of three operations: delete, insert, or replace, and add 1  # noqa: E501
                dp[i][j] = (
                    min(
                        dp[i - 1][j],  # Deletion
                        dp[i][j - 1],  # Insertion
                        dp[i - 1][j - 1],  # Replacement
                    )
                    + 1
                )

    # Return the final edit distance
    return dp[len1][len2]


def eval_idm_response(response: list[str], reference: list[str]) -> tuple[int, float]:
    edit_distance = get_edit_distance(response, reference)
    if edit_distance == 0:
        score = 1.0
    else:
        score = 0.0
    return edit_distance, score


class IDMMultipleEval(BaseEval):
    def __call__(
        self,
        model_name: str,
        tokenizer_name: str,
    ) -> list[dict[str, Any]]:
        def fn(row: dict):
            if self.data_dir is not None:
                actions = row["actions"]
            else:
                actions = [
                    dict(zip(row["actions"].keys(), values))
                    for values in zip(*row["actions"].values())
                ]
            action_space = row["action_space"]

            # Only use the last 5 actions at most
            if actions[-1]["obs_after"] is not None:
                actions = actions[-5:] if len(actions) > 5 else actions
            else:
                # If the last action has no obs_after, use the last 6 actions
                actions = actions[-6:-1] if len(actions) > 6 else actions[:-1]

            ref_answer = []
            for action in actions:
                if self.data_dir is not None:
                    action["obs_before_path"] = action["obs_before"]
                    action["obs_after_path"] = action["obs_after"]
                    action["obs_before"] = Path(
                        os.path.join(self.data_dir, action["obs_before"])
                    )
                    action["obs_after"] = Path(
                        os.path.join(self.data_dir, action["obs_after"])
                    )
                else:
                    action["obs_before"] = np.array(action["obs_before"].convert("RGB"))
                    action["obs_after"] = np.array(action["obs_after"].convert("RGB"))
                    action["obs_before_path"] = action["obs_before_path"]
                    action["obs_after_path"] = action["obs_after_path"]
                ref_answer.append(chr(65 + action_space.index(action["operation"])))

            # Query the model and evaluate the response
            prompt, prompt_str = format_idm_prompt(
                actions,
                action_space,
            )
            response, info = self.model.generate_response(
                prompt,
                model=model_name,
                tokenizer=tokenizer_name,
                do_sample=False,
                max_length=32,
                num_return_sequences=1,
            )
            answer = parse_idm_response(response)
            edit_distance, score = eval_idm_response(answer, ref_answer)

            result = {
                "prompt": prompt_str,
                "score": score,
                "edit_distance": edit_distance,
                "source": row["source"],
                "platform": row["platform"],
                "instruction": row["instruction"],
                "response": response,
                "parsed_answer": answer,
                "ref_answer": ref_answer,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            add_jsonl([result], self.result_filename)
            logger.info(
                f"Writing results {row['annotation_id']} to {self.result_filename}"
            )

        map_with_progress(fn, self.data, self.num_workers)
