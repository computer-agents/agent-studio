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
Answer the following multiple selection question. The last line of your response should be of the following format: 'Answer: [LETTER] -> [LETTER] -> ...' (without quotes) where each letter is one of "{choices}".

In this question, you are given the goal(instruction) of the trajectory and a sequence of images during the trajectory, which denote the observations before and after each action. You should not assume whether the trajectory is finished or not. Your task is to determine the executed action types between the observations.
For example, the instruction is "Open the browser", the action space is ["type", "click", "scroll"], and the trajectory is ["obs1_image", "obs2_image", "obs3_image"], the choices are "A: type\nB: click\nC: scroll", and you think the executed action between obs1_image and obs2_image is "type", and the executed action between obs2_image and obs3_image is "scroll", then your response should be "Answer: [A] -> [C]". Think step by step before answering.

Instruction: {instruction}

{choices_str}
""".strip()  # noqa: E501


def format_idm_prompt(
    instruction: str,
    actions: list[dict],
    action_space: list[str],
) -> tuple[list, list, list]:
    messages: MessageList = []
    for action in actions:
        messages.append(
            Message(
                role="user",
                content=action["obs_before"],
            )
        )
    messages.append(
        Message(
            role="user",
            content=actions[-1]["obs_after"],
        )
    )

    choicestr = "\n".join(
        [
            f"{chr(65 + i)}. {selected_actions}"
            for i, selected_actions in enumerate(list(action_space))
        ]
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


def eval_idm_response(response: str, reference: list) -> float:
    try:
        section_match: re.Match[str] | None = re.search(
            r"Answer\s*:\s*(.*)", response.splitlines()[-1]
        )
        matched_section = section_match.group(1)
        letter_pattern = r"([A-Za-z])"
        match = re.findall(letter_pattern, matched_section)
    except Exception:
        match = []
    score = 0.0
    for i in range(min(len(match), len(reference))):
        if match[i] == reference[i]:
            score += 1
    return score


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
            instruction = row["instruction"]
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
                    action["obs_before"] = Path(
                        os.path.join(self.data_dir, action["obs_before"])
                    )
                    action["obs_after"] = Path(
                        os.path.join(self.data_dir, action["obs_after"])
                    )
                    action["obs_before_path"] = action["obs_before"]
                    action["obs_after_path"] = action["obs_after"]
                else:
                    action["obs_before"] = np.array(action["obs_before"].convert("RGB"))
                    action["obs_after"] = np.array(action["obs_after"].convert("RGB"))
                    action["obs_before_path"] = action["obs_before_path"]
                    action["obs_after_path"] = action["obs_after_path"]
                ref_answer.append(chr(65 + action_space.index(action["operation"])))

            # Query the model and evaluate the response
            prompt = format_idm_prompt(
                instruction,
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

            score = eval_idm_response(response, ref_answer)

            trajectory = [
                {
                    "obs_before": action["obs_before_path"],
                    "action": action["operation"],
                    "obs_after": action["obs_after_path"],
                }
                for action in actions
            ]
            result = {
                "trajectory": trajectory,
                "action_space": action_space,
                "score": score,
                "source": row["source"],
                "platform": row["platform"],
                "annotation_id": row["annotation_id"],
                "instruction": instruction,
                "response": response,
                "ref_answer": ref_answer,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            add_jsonl([result], self.result_filename)
            logger.info(
                f"Writing results {row['annotation_id']} to {self.result_filename}"
            )

        map_with_progress(fn, self.data, self.num_workers)
