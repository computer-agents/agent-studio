import os
import re
from pathlib import Path

import numpy as np

from common import map_with_progress, aggregate_results, Eval, EvalResult, SingleEvalResult, HTML_JINJA, jinja_env

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import read_jsonl


QUERY_TEMPLATE = """
Please output the coordinates based on the given single-step instruction and screenshot. The last line of your response should be of the following format: 'Answer: (X, Y)' (without quotes) where X, Y is the coordinates ranging from 0 to 1. Think step by step before answering.

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
        model: BaseModel,
        data_path: str,
        start_idx: int = 0,
        end_idx: int | None = None,
    ):
        self.model = model
        self.data = read_jsonl(data_path, start_idx, end_idx)
        self.data_dir = Path(data_path).parent

    def __call__(self, model_name: str, tokenizer_name: str, num_workers: int = 1) -> EvalResult:
        def fn(row: dict):
            screenshot = os.path.join(self.data_dir, row["image"])
            instruction = row["instruction"]
            left, top, right, bottom = row["bbox"]
            img_width, img_height = row["resolution"]

            # Query the model and evaluate the response
            prompt = format_gui_grounding_prompt(instruction, screenshot)
            response, info = self.model.generate_response(prompt, model=model_name, tokenizer=tokenizer_name)
            action = parse_gui_grounding_response(response)
            if action is None:
                score = 0.0
            else:
                pred_x, pred_y = action
                pred_x *= img_width
                pred_y *= img_height
                if pred_x > left and pred_x < right and pred_y > top and pred_y < bottom:
                    score = 1.0
                else:
                    score = 0.0

            # Log results
            html = jinja_env.from_string(HTML_JINJA).render(
                prompt_messages=prompt,
                next_message=dict(content=response, role="assistant"),
                score=score,
                correct_bbox=(left, top, right, bottom),
                pred_coord=action,
            )
            log = {
                "image": row["image"],
                "score": score,
                "source": row["source"],
                "platform": row["platform"],
                "resolution": row["resolution"],
            }
            metrics = {
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            return SingleEvalResult(
                html=html, score=score, metrics=metrics, log=log
            )

        results = map_with_progress(fn, self.data, num_workers)
        return aggregate_results(results)
