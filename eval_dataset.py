import argparse
import ast
import logging
import re
from pathlib import Path

import numpy as np
from PIL import Image

from agent_studio.llm import setup_model
from agent_studio.utils.json_utils import add_jsonl, read_jsonl

logger = logging.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=[
            "gemini-pro-vision",
            "gpt-4-vision-preview",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
        ],
    )
    parser.add_argument("--data_path", type=str, default=None)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)

    return parser


def construct_prompt(
    instruction: str, screenshot: np.ndarray, resolution: tuple[int, int]
) -> list:
    messages: list[dict[str, str | np.ndarray]] = []
    messages.append(
        {
            "role": "user",
            "content": f"""You must use `mouse.click(x: int, y: int, click_type: str, is_double_click: bool)` to click at the specified coordinate. You can choose "left_click", "right_click" or "middle_click" as the click_type. "is_double_click" (True or False) indicates whether the click is a double click.
For example, output `mouse.click(x, y, click_type, is_double_click)` to click at the coordinate (x, y).
The image resolution is {resolution[0]}x{resolution[1]} pixels.
The task instruction: {instruction}.
Output:""",  # noqa: E501
        }
    )
    messages.append({"role": "user", "content": screenshot})

    return messages


def get_args_as_kwargs(s):
    # Define the order of parameters for the mouse.click function
    param_order = ["x", "y", "click_type", "is_double_click"]

    # Initialize a dictionary to hold all kwargs
    all_kwargs = {}

    # Parse the string to an AST
    tree = ast.parse(s, mode="eval")

    if isinstance(tree.body, ast.Call):
        # Handle positional arguments
        for i, arg in enumerate(tree.body.args):
            # Attempt to evaluate the argument value
            try:
                # This assumes that all positional arguments can be safely evaluated
                value = ast.literal_eval(arg)
            except ValueError:
                value = None  # Placeholder for non-evaluable arguments
            all_kwargs[param_order[i]] = value

        # Handle keyword arguments
        for kw in tree.body.keywords:
            all_kwargs[kw.arg] = ast.literal_eval(kw.value)

    return all_kwargs


def parse_action(response: str) -> tuple[dict, int, int] | None:
    logger.info(f"Extracted action: from response: {response}")
    pattern = r"(mouse\.click\([^)]+\))"
    matches = re.findall(pattern, response)
    logger.info(f"Extracted action: {matches}")
    if len(matches) == 0:
        return None
    else:
        click_type_dict = {
            "left_click": False,
            "right_click": False,
            "middle_click": False,
            "double_click": False,
        }
        try:
            kwargs = get_args_as_kwargs(matches[0])
            if not (
                isinstance(kwargs["x"], int)
                and isinstance(kwargs["y"], int)
                and isinstance(kwargs["click_type"], str)
                and isinstance(kwargs["is_double_click"], bool)
            ):
                raise ValueError("Invalid action")
            click_type_dict[kwargs["click_type"]] = True
            if kwargs["is_double_click"]:
                click_type_dict["double_click"] = True
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to extract action: {e}")
            return None
    return click_type_dict, kwargs["x"], kwargs["y"]


def main():
    parser = create_parser()
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")

    task_configs = read_jsonl(args.data_path, args.start_idx, args.end_idx)

    model = setup_model(args.provider)

    total_scores = {}
    for task_config in task_configs:
        # read task configs
        task_id = task_config["task_id"]
        instruction = task_config["instruction"]
        logger.info(f"Task instruction: {instruction}")
        trajectory = task_config["trajectory"]

        img = Image.open(trajectory[0]["obs"])
        screenshot = np.array(img)
        height, width = screenshot.shape[:2]
        resolution = (width, height)

        annotation = trajectory[0]["annotation"]
        mouse_action = annotation["mouse_action"]
        click_type = mouse_action["click_type"]
        left_x = mouse_action["x"]
        right_x = mouse_action["x"] + mouse_action["width"]
        top_y = mouse_action["y"]
        bottom_y = mouse_action["y"] + mouse_action["height"]

        # query LLMs
        click_type_match = False
        location_match = False
        score = 0.0
        message = construct_prompt(instruction, screenshot, resolution)
        response, info = model.generate_response(message, model=args.provider)
        predicted_action = parse_action(response)
        if predicted_action is not None:
            predicted_click_type, predicted_x, predicted_y = predicted_action
            click_type_match = predicted_click_type == click_type
            location_match = (
                predicted_x >= left_x
                and predicted_x <= right_x
                and predicted_y >= top_y
                and predicted_y <= bottom_y
            )

            # calculate metrics
            if click_type_match and location_match:
                score = 1.0
                logger.info("PASS")
            else:
                logger.info("FAIL")
        else:
            logger.info("FAIL")
        total_scores[task_id] = score

        # save conversations
        save_path = Path(
            args.data_path.replace(
                "grounding", f"grounding_results/{args.provider}"
            ).replace("actions", "results")
        )
        save_path.parent.mkdir(parents=True, exist_ok=True)
        add_jsonl(
            [
                {
                    "task_id": task_id,
                    "response": response,
                    "total_tokens": info["total_tokens"],
                    "score": score,
                    "click_type_match": click_type_match,
                    "location_match": location_match,
                }
            ],
            save_path,
        )

    logger.info(
        f"Average score: {sum(total_scores.values()) / max(len(total_scores), 1)}"
    )


if __name__ == "__main__":
    main()
