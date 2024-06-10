import os
import re
from pathlib import Path
from typing import Tuple, Any

import numpy as np
from common import map_with_progress
from pydantic_core import from_json

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import read_jsonl, add_jsonl
from hzy.schema import Action, Episode

QUERY_TEMPLATE = """
You are a human annotator, your task is to judge whether the instruction is correctly executed based on the above human trajectory. The trajectory is represented by a sequence of actions and the observations before and after each action. Your response is either "succ" if the trajectory finished the instruction or "fail" if not. 
The action space: {action_space}
Instruction: {instruction}
""".strip()  # noqa: E501

ANSWER_PATTERN = r"(succ|fail)"


def format_success_detection_prompt(
    data_dir: str,
    episode: Episode,
) -> list:
    messages = [
    ]
    for action in episode.actions:
        if action.obs_before is not None:
            messages.append({"role": "user", "content": Path(os.path.join(data_dir, action.obs_before))})
        messages.append({"role": "user", "content": f'{action.metadata["repr"]}'})
    if action.obs_after is not None:
        messages.append({"role": "user", "content": Path(os.path.join(data_dir, action.obs_after))})
    messages.append(
        {"role": "user", "content": QUERY_TEMPLATE.format(instruction=episode.instruction, action_space=", ".join(episode.action_space))},
    )

    return messages


def parse_success_detection_response(response: str) -> float:
    try:
        match = re.search(ANSWER_PATTERN, response.splitlines()[-1])
    except:
        match = None
    return 1.0 if (match and match.group(1) == "succ") else 0.0


class SuccessDetectionEval:
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
        def fn(row: dict):
            episode: Episode = Episode.model_validate(row)

            # Query the model and evaluate the response
            prompt = format_success_detection_prompt(self.data_dir, episode)
            response, info = self.model.generate_response(
                prompt, model=model_name, tokenizer=tokenizer_name,
                do_sample=False, max_length=32, num_return_sequences=1,
            )
            print("response:", response)
            score = parse_success_detection_response(response)

            result = {
                "trajectory_images": [action.obs_before for action in episode.actions] + ([episode.actions[-1].obs_after] if episode.actions[-1].obs_after else []),
                "trajectory_actions": [action.metadata["repr"] for action in episode.actions],
                "instruction": episode.instruction,
                # "image": row["image"],
                "score": score,
                "source": episode.source,
                "annotation_id": episode.annotation_id,
                # "platform": row["platform"],
                # "resolution": row["resolution"],
                "instruction": episode.instruction,
                "response": response,
                # "parsed_action": action,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            # breakpoint()

            add_jsonl([result], self.result_filename)
            print(f"Writing results to {self.result_filename}")

        map_with_progress(fn, self.data, self.num_workers)
