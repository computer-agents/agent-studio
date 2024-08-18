import argparse
import os
import shutil
from pathlib import Path

from agent_studio.utils.types import Episode

parser = argparse.ArgumentParser()
parser.add_argument("-i", type=str)
parser.add_argument("--image_folder", type=str)
parser.add_argument("--jsonl_folder", type=str)

args = parser.parse_args()

if args.i:
    input_folder = args.i
else:
    raise Exception("Please specify the input folder")

if args.image_folder:
    image_folder = Path(args.image_folder)
else:
    raise Exception("Please specify the image path")

if args.jsonl_folder:
    jsonl_folder = Path(args.jsonl_folder)
else:
    raise Exception("Please specify the jsonl path")

try:
    image_folder.relative_to(jsonl_folder)
except ValueError:
    raise Exception("The image folder must be a subfolder of the jsonl path")

jsonl_path = jsonl_folder / "output.jsonl"

for dir in os.listdir(input_folder):
    if dir == ".DS_Store":
        continue
    if not os.path.exists(f"{input_folder}/{dir}/trajectory.jsonl"):
        print("skip", dir)
        continue
    print(dir)
    with open(f"{input_folder}/{dir}/trajectory.jsonl", "r") as f:
        for line in f:
            epi = Episode.model_validate_json(line)
            image_folder_epi = image_folder / epi.annotation_id

            # create image folder
            image_folder_epi.mkdir(parents=True, exist_ok=True)

            for action in epi.actions:
                # copy image to image folder
                # and change the path for obs_before and obs_after
                if action.obs_before:
                    src = f"{input_folder}/{dir}/{action.obs_before}"
                    shutil.copy(src, image_folder_epi)
                    action.obs_before = (
                        (image_folder_epi / Path(src).name)
                        .relative_to(jsonl_folder)
                        .as_posix()
                    )
                if action.obs_after:
                    src = f"{input_folder}/{dir}/{action.obs_after}"
                    shutil.copy(src, image_folder_epi)
                    action.obs_after = (
                        (image_folder_epi / Path(src).name)
                        .relative_to(jsonl_folder)
                        .as_posix()
                    )

            # write a line to output.jsonl, write line by line
            with open(jsonl_path, "a") as out_f:
                out_f.write(epi.model_dump_json() + "\n")
