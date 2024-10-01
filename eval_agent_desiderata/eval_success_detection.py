import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
from common import map_with_progress
from eval_base import BaseEval

from agent_studio.utils.json_utils import add_jsonl
from agent_studio.utils.types import Message, MessageList

logger = logging.getLogger("agent_studio")

QUERY_TEMPLATE = """
Analyze the sequence of images provided. These images are snapshots taken from a video screen recording. Your task is to evaluate whether the given instruction has been successfully completed based on the provided trajectory. This trajectory is depicted through a series of actions and the corresponding observations before and after each action.
Instruction: {instruction}
Action space: {action_space}
Carefully examine the sequence of actions and their results. Determine if the final state successfully fulfills the given instruction.
Conclude your analysis with one of these two responses:
If the trajectory successfully completes the instruction:
Answer: True
If the trajectory fails to complete the instruction:
Answer: False
""".strip()  # noqa: E501

ACTIONLESS_QUERY_TEMPLATE = """
Analyze the sequence of images provided. These images are snapshots taken from a video screen recording. Your task is to evaluate whether the given instruction has been successfully completed based on the provided images.
Instruction: {instruction}
Carefully examine the sequence of images. Determine if the final state successfully fulfills the given instruction.
Conclude your analysis with one of these two responses:
If the trajectory successfully completes the instruction:
Answer: True
If the trajectory fails to complete the instruction:
Answer: False
""".strip()  # noqa: E501


def format_success_detection_prompt(
    instruction: str,
    actions: list[dict],
    action_space: list[str] | None,
) -> list:
    messages: MessageList = []
    messages_str = []
    for action in actions:
        messages.append(
            Message(
                role="user",
                content=action["obs_before"],
            )
        )
        if action_space is not None:
            messages.append(
                Message(
                    role="user",
                    content=action["metadata"]["repr"],
                )
            )
        messages_str.append(
            {
                "role": "user",
                "content": action["obs_before_path"],
            }
        )
        if action_space is not None:
            messages_str.append(
                {
                    "role": "user",
                    "content": action["metadata"]["repr"],
                }
            )
    if actions[-1]["obs_after"] is not None:
        messages.append(
            Message(
                role="user",
                content=actions[-1]["obs_after"],
            )
        )
        messages_str.append(
            {
                "role": "user",
                "content": actions[-1]["obs_after_path"],
            }
        )
    if action_space is not None:
        messages.append(
            Message(
                role="user",
                content=QUERY_TEMPLATE.format(
                    instruction=instruction,
                    action_space=", ".join(action_space),
                ),
            ),
        )
        messages_str.append(
            {
                "role": "user",
                "content": QUERY_TEMPLATE.format(
                    instruction=instruction,
                    action_space=", ".join(action_space),
                ),
            },
        )
    else:
        messages.append(
            Message(
                role="user",
                content=ACTIONLESS_QUERY_TEMPLATE.format(
                    instruction=instruction,
                ),
            ),
        )
        messages_str.append(
            {
                "role": "user",
                "content": ACTIONLESS_QUERY_TEMPLATE.format(
                    instruction=instruction,
                ),
            },
        )

    return messages, messages_str


class SuccessDetectionEval(BaseEval):
    def __init__(self, actionless: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.actionless = actionless

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
            is_success = row["is_success"]

            # Only use the last 5 actions at most
            actions = actions[-5:] if len(actions) > 5 else actions

            for action in actions:
                if self.data_dir is not None:
                    action["obs_before_path"] = action["obs_before"]
                    action["obs_before"] = Path(
                        os.path.join(self.data_dir, action["obs_before"])
                    )
                    if action["obs_after"] is not None:
                        action["obs_after_path"] = action["obs_after"]
                        action["obs_after"] = Path(
                            os.path.join(self.data_dir, action["obs_after"])
                        )
                    else:
                        action["obs_after"] = None
                        action["obs_after_path"] = None
                else:
                    action["obs_before"] = np.array(action["obs_before"].convert("RGB"))
                    if action["obs_after"] is not None:
                        action["obs_after"] = np.array(
                            action["obs_after"].convert("RGB")
                        )
                    else:
                        action["obs_after"] = None
                    action["obs_before_path"] = action["obs_before_path"]
                    action["obs_after_path"] = action["obs_after_path"]

            # Query the model and evaluate the response
            if self.actionless:
                prompt, prompt_str = format_success_detection_prompt(
                    instruction, actions, None
                )
            else:
                prompt, prompt_str = format_success_detection_prompt(
                    instruction, actions, row["action_space"]
                )
            response, info = self.model.generate_response(
                prompt,
                model=model_name,
                tokenizer=tokenizer_name,
                do_sample=False,
                max_new_tokens=32,
                num_return_sequences=1,
            )
            logger.info(f"response: {response}")

            if (
                is_success
                and "True" in response
                or not is_success
                and "False" in response
            ):
                score = 1.0
            else:
                score = 0.0

            result = {
                "prompt": prompt_str,
                "instruction": instruction,
                "score": score,
                "source": row["source"],
                "platform": row["platform"],
                "ref_answer": is_success,
                "response": response,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }

            add_jsonl([result], self.result_filename)
            logger.info(
                f"Writing results {row['annotation_id']} to {self.result_filename}"
            )

        map_with_progress(fn, self.data, self.num_workers)
