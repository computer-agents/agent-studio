import os
import re
from pathlib import Path
from typing import Any, Tuple

import numpy as np
from common import map_with_progress

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import add_jsonl, read_jsonl

QUERY_TEMPLATE = """
Please output the coordinate for the next action based on the instruction and screenshot. Your answer should be of the following format: '(X, Y)' (without quotes) where X, Y is the coordinates ranging from 0 to 1.
Instruction: {instruction}
Answer:
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
    try:
        match = re.search(ANSWER_PATTERN, response.splitlines()[-1])
    except Exception:
        match = None
    return [float(match.group(1)), float(match.group(2))] if match else None


def eval_coord_output(action, bbox, img_size, do_scale=True):
    if action is None:
        return 0.0, None

    pred_x, pred_y = action
    left, top, right, bottom = bbox
    img_width, img_height = img_size
    if do_scale:
        pred_x *= img_width
        pred_y *= img_height
    if pred_x > left and pred_x < right and pred_y > top and pred_y < bottom:
        score = 1.0
    else:
        score = 0.0

    return score, [pred_x, pred_y]


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
        self,
        model_name: str,
        tokenizer_name: str,
    ) -> list[dict[str, Any]]:
        def fn(row: dict):
            image_path = os.path.join(self.data_dir, row["image"])
            instruction = row["instruction"]

            # Query the model and evaluate the response
            prompt = format_gui_grounding_prompt(instruction, image_path)
            response, info = self.model.generate_response(
                prompt,
                model=model_name,
                tokenizer=tokenizer_name,
                do_sample=False,
                max_new_tokens=32,
                num_return_sequences=1,
            )
            action = parse_gui_grounding_response(response)
            score, action = eval_coord_output(
                action,
                row["bbox"],
                row["resolution"],
                do_scale=model_name != "gemini-1.5-flash",
            )

            result = {
                "image": row["image"],
                "score": score,
                "source": row["source"],
                "platform": row["platform"],
                "bbox": row["bbox"],
                "resolution": row["resolution"],
                "instruction": instruction,
                "response": response,
                "parsed_action": action,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }

            add_jsonl([result], self.result_filename)
            print(f"Writing results to {self.result_filename}")

        map_with_progress(fn, self.data, self.num_workers)
