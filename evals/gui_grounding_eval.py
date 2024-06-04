import os
import re
from pathlib import Path
from typing import Tuple, Any

import numpy as np
from common import map_with_progress

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import read_jsonl, add_jsonl

QUERY_TEMPLATE = """
Please output the coordinate for the next action based on the instruction and screenshot. The last line of your response should be of the following format: '(X, Y)' (without quotes) where X, Y is the coordinates ranging from 0 to 1. Think step by step before answering.

Instruction: {instruction}
""".strip()  # noqa: E501


ANSWER_PATTERN = r"\(\s*([-+]?\d*\.?\d+)\s*,\s*([-+]?\d*\.?\d+)\s*\)"


def format_gui_grounding_prompt(
    instruction: str,
    image_path: np.ndarray | Path,
) -> list:
    messages = [
        {"role": "user", "content": Path(image_path)},
        {"role": "user", "content": QUERY_TEMPLATE.format(instruction=instruction)},
    ]

    return messages


def parse_gui_grounding_response(response: str) -> Tuple[float, float] | None:
    match = re.search(ANSWER_PATTERN, response.splitlines()[-1])
    return (float(match.group(1)), float(match.group(2))) if match else None


class GUIGroundingEval:
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
        self.data_dir = os.path.join(Path(data_path).parent, "images")
        self.result_filename = result_filename
        self.num_workers = num_workers

    def __call__(
        self, model_name: str, tokenizer_name: str,
    ) -> list[dict[str, Any]]:
        def fn(row: dict):
            image_path = os.path.join(self.data_dir, row["image"])
            instruction = row["instruction"]
            left, top, right, bottom = row["bbox"]
            img_width, img_height = row["resolution"]

            # Query the model and evaluate the response
            prompt = format_gui_grounding_prompt(instruction, image_path)
            response, info = self.model.generate_response(
                prompt, model=model_name, tokenizer=tokenizer_name
            )
            action = parse_gui_grounding_response(response)
            if action is None:
                score = 0.0
            else:
                pred_x, pred_y = action
                pred_x *= img_width
                pred_y *= img_height
                action = (pred_x, pred_y)
                if (
                    pred_x > left
                    and pred_x < right
                    and pred_y > top
                    and pred_y < bottom
                ):
                    score = 1.0
                else:
                    score = 0.0

            result = {
                "image": row["image"],
                "score": score,
                "source": row["source"],
                "platform": row["platform"],
                "bbox": [left, top, right, bottom],
                "resolution": row["resolution"],
                "instruction": instruction,
                "image_path": image_path,
                "response": dict(content=response, role="assistant"),
                "parsed_action": action,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }

            add_jsonl([result], self.result_filename)
            print(f"Writing results to {self.result_filename}")

        map_with_progress(fn, self.data, self.num_workers)
