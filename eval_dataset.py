# python eval_dataset.py --end_idx 1 --data_path data/grounding/calculator/calculator.jsonl --provider gemini-pro-vision --save_path  # noqa: E501
import argparse
import logging
from pathlib import Path
import ast
import re

import numpy as np
from PIL import Image

from agent_studio.llm import setup_model
from agent_studio.utils.json_utils import add_jsonl, read_jsonl

logger = logging.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider", type=str, default=None, choices=["gemini-pro-vision"]
    )
    parser.add_argument("--data_path", type=str, default=None)
    parser.add_argument("--save_path", type=str, default=None)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)
    parser.add_argument("--max_retry", type=int, default=1)

    return parser


def construct_prompt(instruction: str, screenshot: np.ndarray) -> list:
    messages = []
    messages.append(
        {
            "role": "user",
            "content": f"""You can complete any instruction by writing Python code. You can use the mouse to interact with the environment. `mouse.click(x: int, y: int, click_type: str, is_double_click: bool)` can be used to interact with the mouse at the specified position. You can choose "left_click", "right_click" or "middle_click" as the click_type. "is_double_click" indicates whether the click is a double click. You should only return `mouse.click(x, y, click_type, is_double_click)` as the action.
The task instruction: {instruction}""",  # noqa: E501
        }
    )
    # TODO: add few-shot
    messages.append({"role": "user", "content": screenshot})

    return messages


def extract_action(response: str) -> tuple[dict, int, int] | None:
    # TODO: extract action from response by regex (but need to consider four click types)  # noqa: E501
    logger.info(f"Extracted action: from response: {response}")
    pattern = r'(mouse\.click\([^)]+\))'
    matches = re.findall(pattern, response)
    logger.info(f"Extracted action: {matches}")
    if len(matches) == 0:
        return None
    else:
        click_type_dict = {
            "left_click": False,
            "right_click": False,
            "middle_click": False,
            "double_click": False
        }
        try:
            def get_args(expr):
                tree = ast.parse(expr)
                if not isinstance(tree.body[0], ast.Expr):
                    raise ValueError("Invalid action")
                if not isinstance(tree.body[0].value, ast.Call):
                    raise ValueError("Invalid action")
                args = tree.body[0].value.args
                return [arg.value for arg in args]
            x, y, click_type, is_double_click = get_args(matches[0])
            if not (isinstance(x, int) and isinstance(y, int) and \
                isinstance(click_type, str) and isinstance(is_double_click, bool)):
                raise ValueError("Invalid action")
            click_type_dict[click_type] = True
            if is_double_click:
                click_type_dict["double_click"] = True
        except (ValueError, IndexError) as e:
            logger.warn(f"Failed to extract action: {e}")
            return None
    return click_type_dict, x, y


def main():
    parser = create_parser()
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")

    task_configs = read_jsonl(args.data_path, args.start_idx, args.end_idx)

    if args.provider in ["gemini-pro-vision"]:
        model = setup_model("gemini")

    total_scores = {}
    for task_config in task_configs:
        # read task configs
        task_id = task_config["task_id"]
        instruction = task_config["instruction"]
        logger.info(f"Task instruction: {instruction}")
        trajectory = task_config["trajectory"]

        img = Image.open(trajectory[0]["obs"])
        screenshot = np.array(img)

        annotation = trajectory[0]["annotation"]
        mouse_action = annotation["mouse_action"]
        click_type = mouse_action["click_type"]
        assert click_type is not None
        left_x = mouse_action["x"]
        right_x = mouse_action["x"] + mouse_action["width"]
        top_y = mouse_action["y"]
        bottom_y = mouse_action["y"] + mouse_action["height"]

        # query LLMs
        score = 0.0
        conversations = []
        assert args.max_retry == 1, "We don't have reflection prompt yet."
        for t in range(args.max_retry):
            message = construct_prompt(instruction, screenshot)
            response, info = model.generate_response(message, model=args.provider)
            conversations.append(
                {
                    "prompt": message,
                    "response": response,
                    "total_tokens": info["total_tokens"],
                }
            )
            predicted_action = extract_action(response)
            if predicted_action is None:
                continue
            else:
                predicted_click_type, predicted_x, predicted_y = predicted_action

            click_type_match = predicted_click_type == click_type
            location_match = (
                predicted_x >= left_x
                and predicted_x <= right_x
                and predicted_y >= top_y
                and predicted_y <= bottom_y
            )

            if click_type_match and location_match:
                score = 1.0

        # calculate metrics
        total_scores[task_id] = score
        if score == 1.0:
            logger.info("PASS")
        else:
            logger.info("FAIL")

        # save conversations
        save_path = Path(args.save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        add_jsonl(
            [{
                "conversations": conversations,
                "score": score,
                "click_type_match": click_type_match,
                "location_match": location_match,
            }],
            args.save_path,
        )

    logger.info(
        f"Average score: {sum(total_scores.values()) / max(len(total_scores), 1)}"
    )


if __name__ == "__main__":
    main()
