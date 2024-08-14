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
You are a human annotator, your task is to judge whether the instruction is correctly executed based on the above trajectory. The trajectory is represented by a sequence of actions and the observations before and after each action. Your response is either "Answer: succ" if the trajectory finished the instruction or "Answer: fail" if not.
The action space: {action_space}
Instruction: {instruction}
""".strip()  # noqa: E501

ANSWER_PATTERN = r"(?i)Answer\s*:\s*(succ|fail)"


def format_success_detection_prompt(
    instruction: str,
    actions: list[dict],
    action_space: list[str],
) -> list:
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
                content=action["metadata"]["repr"],
            )
        )
    if actions[-1]["obs_after"] is not None:
        messages.append(
            Message(
                role="user",
                content=actions[-1]["obs_after"],
            )
        )
    messages.append(
        Message(
            role="user",
            content=QUERY_TEMPLATE.format(
                instruction=instruction,
                action_space=", ".join(action_space),
            ),
        ),
    )

    return messages


def parse_success_detection_response(response: str, reference: bool) -> float:
    try:
        match = re.search(ANSWER_PATTERN, response.splitlines()[-1])
    except Exception:
        match = None
    return 1.0 if (match and ((match.group(1) == "succ")) == reference) else 0.0


class SuccessDetectionEval(BaseEval):
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
                    action["obs_before_path"] = action["obs_before"]
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
            prompt = format_success_detection_prompt(
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
            score = parse_success_detection_response(response, is_success)

            trajectory_images = [action["obs_before_path"] for action in actions]
            if actions[-1]["obs_after_path"] is not None:
                trajectory_images.append(actions[-1]["obs_after_path"])
            result = {
                "trajectory_images": trajectory_images,
                "trajectory_actions": [
                    action["metadata"]["repr"] for action in actions
                ],
                "instruction": instruction,
                "score": score,
                "source": row["source"],
                "platform": row["platform"],
                "annotation_id": row["annotation_id"],
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
