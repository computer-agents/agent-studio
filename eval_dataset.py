# python eval_dataset.py --end_idx 1 --data_path data/grounding/calculator/calculator.jsonl --provider gemini-pro-vision --save_path  # noqa: E501
import argparse
import logging
from pathlib import Path

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
            "content": f"""You can complete any instruction by writing Python code. You can use the mouse to interact with the environment. `mouse.click(x, y)` can be used to click the mouse at the specified position. You should only return `mouse.click(x, y)` as the action.
The task instruction: {instruction}""",  # noqa: E501
        }
    )
    # TODO: add few-shot
    messages.append({"role": "user", "content": screenshot})

    return messages


def extract_action(response: str) -> tuple[str, int, int]:
    # TODO: extract action from response by regex (but need to consider four click types)  # noqa: E501
    return "left", 0, 0


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
        click_type = None
        for k, v in mouse_action["click_type"].items():
            if v:
                click_type = k
        assert click_type is not None
        left_x = mouse_action["x"]
        right_x = mouse_action["x"] + mouse_action["width"]
        top_y = mouse_action["y"]
        bottom_y = mouse_action["y"] + mouse_action["height"]

        # query LLMs
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
            predicted_click_type, predicted_x, predicted_y = extract_action(response)

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
            {
                "conversations": conversations,
                "score": score,
                "click_type_match": click_type_match,
                "location_match": location_match,
            },
            args.save_path,
        )

    logger.info(
        f"Average score: {sum(total_scores.values()) / max(len(total_scores), 1)}"
    )


if __name__ == "__main__":
    main()
