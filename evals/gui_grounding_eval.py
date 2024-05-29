import os
import re
import json
from pathlib import Path

import numpy as np

from common import map_with_progress, aggregate_results, Eval, EvalResult, SingleEvalResult

from agent_studio.llm import BaseModel


QUERY_TEMPLATE = """
Please output the coordinates based on the given single-step instruction and screenshot. The last line of your response should be of the following format: 'Answer: ($X, $Y)' (without quotes) where X, Y is the relative coordinates ranging from 0 to 1. Think step by step before answering.

Instruction: {instruction}
""".strip()


ANSWER_PATTERN = r"(?i)Answer\s*:\s*\(\s*([-+]?\d*\.?\d+)\s*,\s*([-+]?\d*\.?\d+)\s*\)"


def format_gui_grounding_prompt(
    instruction: str,
    screenshot: np.ndarray | Path,
) -> list:
    messages = [
        {"role": "user", "content": screenshot},
        {"role": "user", "content": QUERY_TEMPLATE.format(instruction=instruction)},
    ]

    return messages


def parse_gui_grounding_response(response: str) -> str:
    match = re.search(ANSWER_PATTERN, response)
    return (float(match.group(1)), float(match.group(2))) if match else None


class GUIGroundingEval(Eval):
    def __init__(
        self,
        provider: str,
        data_path: str,
        start_idx: int = 0,
        end_idx: int | None = None,
    ):
        with open(data_path, 'r') as file:
            if end_idx is None:
                self.data = json.load(file)[start_idx:]
            else:
                self.data = json.load(file)[start_idx:end_idx]
        self.data_dir = Path(data_path).parent
        self.provider = provider

    def __call__(self, model: BaseModel, num_workers: int = 1) -> EvalResult:
        def fn(row: dict):
            screenshot = os.path.join(self.data_dir, row["img_filename"])
            instruction = row["instruction"]
            x, y, width, height = row["bbox"]

            # Query the model and evaluate the response
            prompt = format_gui_grounding_prompt(instruction, screenshot)
            response, info = model.generate_response(prompt, model=self.provider)
            action = parse_gui_grounding_response(response)
            if action is None:
                score = 0.0
            else:
                pred_x, pred_y = action
                if pred_x > x and pred_x < x + width and pred_y > y and pred_y < y + height:
                    score = 1.0
                else:
                    score = 0.0

            # Log results
            conversation = prompt + [dict(content=response, role="assistant")]
            metrics = {
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            return SingleEvalResult(
                score=score, conversation=conversation, metrics=metrics
            )

        results = map_with_progress(fn, self.data, num_workers)
        return aggregate_results(results)
