from pathlib import Path
import os
import matplotlib
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO

matplotlib.use("Agg")  # Use the 'Agg' backend for non-GUI environments

from agent_studio.llm import setup_model
from agent_studio.utils.json_utils import read_jsonl


# naive_data_path = "raw_data/screenspot/metadata.jsonl"

# naive_data = read_jsonl(naive_data_path)

# row = naive_data[0]
# data_dir = Path(naive_data_path).parent

# image_path = os.path.join(data_dir, row["image"])
# original_instruction = row["instruction"]
# left, top, right, bottom = row["bbox"]

# image = Image.open(image_path)
# img_width, img_height = image.size
# dpi = 40
# figsize = img_width / float(dpi), img_height / float(dpi)

# # Plot image
# fig, ax = plt.subplots(1, figsize=figsize)
# ax.imshow(image)

# # Plot bounding box
# rect = patches.Rectangle(
#     (left, top),
#     right - left,
#     bottom - top,
#     linewidth=6,
#     edgecolor="r",
#     facecolor="none",
# )
# ax.add_patch(rect)
# plt.axis("off")

# # Save the new image to a BytesIO object
# buf = BytesIO()
# plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=dpi)
# plt.close(fig)

# image = Image.open(buf).convert('RGB')

image_path = Path("tmp.png")
image = Image.open(image_path)

query = """
Caption the content within the red bounding box with an 'Click on' instruction. Make sure your description can be uniquely mapped into the content.
Example instructions:
- "Click on the 'Safari' browser icon in the bottom."
- "Click on the green 'Messages' icon."
""".strip()

messages = [
    {"role": "user", "content": query},
    {"role": "user", "content": image},
]

model = setup_model("huggingface")

# response = model.generate_response(messages=messages, model="/mnt/data/public/ckpt/cogvlm2-llama3-chat-19B")
response = model.generate_response(messages=messages, model="/mnt/data/public/ckpt/cogagent-chat-hf", tokenizer="/mnt/data/public/ckpt/vicuna-7b-v1.5")
# response = model.generate_response(messages=messages, model="/mnt/data/public/ckpt/paligemma-3b-mix-448")

messages = [
    {"role": "user", "content": query},
    {"role": "user", "content": image_path},
]

# response = model.generate_response(messages=messages, model="/mnt/data/public/ckpt/Qwen--Qwen-VL-Chat")
# response = model.generate_response(messages=messages, model="/mnt/data/public/ckpt/SeeClick", tokenizer="/mnt/data/public/ckpt/Qwen--Qwen-VL-Chat")
