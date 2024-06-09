import argparse
import os
from io import BytesIO
from pathlib import Path
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from tqdm import tqdm

from agent_studio.llm import setup_model
from agent_studio.utils.json_utils import add_jsonl, read_jsonl

PROMPT = """
Caption the content within the red bounding box with an 'Click on' instruction. Make sure your description can be uniquely mapped into the content.
""".strip()  # noqa: E501


def draw_bbox(image_path, bbox):
    left, top, right, bottom = bbox

    image = Image.open(image_path)
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

    model = setup_model(args.provider)
    data = read_jsonl(args.data_path, args.start_idx, args.end_idx)
    if args.provider == "huggingface":
        kwargs = {"max_new_tokens": 64}

    image_dir = Path(args.data_path).parent / "images"
    save_path = args.data_path.replace("_raw", "")

    info_list = []
    for row in tqdm(data):
        image_path = os.path.join(image_dir, row["image"])
        messages = [
            {"role": "user", "content": draw_bbox(image_path, row["bbox"])},
            {"role": "user", "content": PROMPT},
        ]
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
