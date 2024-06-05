import os
from io import BytesIO

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from common import map_with_progress
from PIL import Image

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


def main():
    model = setup_model("openai")
    model_name = "gpt-4o-2024-05-13"
    num_workers = 1

    data_path = "evals/datasets/gui_grounding/metadata_raw_1k.jsonl"
    data = read_jsonl(data_path)

    image_dir = "evals/datasets/gui_grounding/images"
    save_path = data_path.replace("metadata_raw_1k.jsonl", "metadata_1k.jsonl")

    def fn(row: dict):
        image_path = os.path.join(image_dir, row["image"])
        messages = [
            {"role": "user", "content": draw_bbox(image_path, row["bbox"])},
            {"role": "user", "content": PROMPT},
        ]
        response, info = model.generate_response(messages, model=model_name)
        row["raw_instruction"] = row["instruction"]
        row["instruction"] = response

        add_jsonl([row], save_path)
        print(f"Writing results to {save_path}")

        return info

    info_list = map_with_progress(fn, data, num_workers)
    input_tokens = sum([info["prompt_tokens"] for info in info_list])
    output_tokens = sum([info["completion_tokens"] for info in info_list])
    print(f"Total input tokens: {input_tokens}")
    print(f"Total output tokens: {output_tokens}")


if __name__ == "__main__":
    main()
