import argparse
import os
from io import BytesIO
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from tqdm import tqdm

from agent_studio.llm import ModelManager
from agent_studio.utils.json_utils import add_jsonl, read_jsonl

GPT4O_PROMPT = """
Caption the content within the red bounding box with an 'Click on' instruction. Make sure your description can be uniquely mapped into the content.
""".strip()  # noqa: E501

COGVLM2_PROMPT = """
Refine the original instruction for the content within the red bounding box with a short instruction starting with 'Click on' with no more than 10 words. If the original instruction is not clear or NA, you can provide instruction based on the image.
Examples:
Original instruction: redirect_discounts
Cleaned instruction: Click on "Discounts".
Original instruction: view_IMAX_at_AMC
Cleaned instruction: Click on 'IMAX at AMC'.

Original instruction: {instruction}
Cleaned instruction:
""".strip()  # noqa: E501

model_manager = ModelManager()


def draw_bbox(image_path, bbox):
    left, top, right, bottom = bbox

    image = Image.open(image_path).convert("RGB")
    img_width, img_height = image.size
    dpi = 40
    figsize = img_width / float(dpi), img_height / float(dpi)

    # Plot image
    fig, ax = plt.subplots(1, figsize=figsize)
    ax.imshow(image)

    # Plot bounding box
    rect = patches.Rectangle(
        (left, top),
        right - left,
        bottom - top,
        linewidth=6,
        edgecolor="r",
        facecolor="none",
    )
    ax.add_patch(rect)
    plt.axis("off")

    # Save the new image to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=dpi)
    buf.seek(0)
    img = Image.open(buf).convert("RGB")

    # Convert image to numpy array
    img_arr = np.array(img)
    plt.close(fig)  # Close the figure to free memory

    return img_arr


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider", type=str, choices=["openai", "gemini", "claude", "huggingface"]
    )
    parser.add_argument("--model", type=str)
    parser.add_argument("--data_path", type=str)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    model = model_manager.get_model(args.provider)
    data = read_jsonl(args.data_path, args.start_idx, args.end_idx)

    image_dir = Path(args.data_path).parent / "images"
    save_path = args.data_path.replace("_raw", "")

    info_list = []
    for row in tqdm(data):
        image_path = os.path.join(image_dir, row["image"])
        messages = [
            {"role": "user", "content": draw_bbox(image_path, row["bbox"])},
        ]
        if args.provider == "huggingface":
            kwargs = {"max_new_tokens": 64}
            messages.append(
                {
                    "role": "user",
                    "content": COGVLM2_PROMPT.format(instruction=row["instruction"]),
                }
            )
        else:
            messages.append({"role": "user", "content": GPT4O_PROMPT})

        response, info = model.generate_response(messages, model=args.model, **kwargs)
        row["raw_instruction"] = row["instruction"]
        row["instruction"] = response

        add_jsonl([row], save_path)
        print(f"Writing results to {save_path}")

        info_list.append(info)

    input_tokens = sum([info.get("prompt_tokens", 0) for info in info_list])
    output_tokens = sum([info.get("completion_tokens", 0) for info in info_list])
    print(f"Total input tokens: {input_tokens}")
    print(f"Total output tokens: {output_tokens}")


if __name__ == "__main__":
    main()
