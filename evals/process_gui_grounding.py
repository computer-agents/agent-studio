import json
import os

from PIL import Image

from agent_studio.utils.json_utils import add_jsonl

screenspot_data_dir = "raw_data/screenspot"

mobile_data_path = f"{screenspot_data_dir}/screenspot_mobile.json"
with open(mobile_data_path, "r") as file:
    mobile_data = json.load(file)

desktop_data_path = f"{screenspot_data_dir}/screenspot_desktop.json"
with open(desktop_data_path, "r") as file:
    desktop_data = json.load(file)

web_data_path = f"{screenspot_data_dir}/screenspot_web.json"
with open(web_data_path, "r") as file:
    web_data = json.load(file)


def process_screenspot(raw_data: list, platform: str):
    processed_data = []
    for d in raw_data:
        img_filename = d["img_filename"]
        img_path = os.path.join(screenspot_data_dir, img_filename)
        image = Image.open(img_path)
        img_width, img_height = image.size

        left, top, width, height = d["bbox"]
        right = left + width
        bottom = top + height

        processed_data.append(
            {
                "image": img_filename,
                "instruction": d["instruction"],
                "bbox": [left, top, right, bottom],
                "source": "screenspot",
                "platform": platform,
                "resolution": [img_width, img_height],
            }
        )

    return processed_data


processed_mobile_data = process_screenspot(mobile_data, "mobile")
processed_desktop_data = process_screenspot(desktop_data, "desktop")
processed_web_data = process_screenspot(web_data, "web")

dataset = processed_mobile_data + processed_desktop_data + processed_web_data

add_jsonl(dataset, f"{screenspot_data_dir}/metadata.jsonl")
print("Processed data saved.")


# import os
# import json
# import PIL.Image
# from datasets import Dataset, Image


# dataset_dict = {
#     "image": [],
#     "instruction": [],
#     "bbox": [],
#     "resolution": [],
#     "source": [],
#     "platform": [],
# }

# screenspot_data_dir = "raw_data/screenspot"

# mobile_data_path = f"{screenspot_data_dir}/screenspot_mobile.json"
# with open(mobile_data_path, 'r') as file:
#     mobile_data = json.load(file)

# desktop_data_path = f"{screenspot_data_dir}/screenspot_desktop.json"
# with open(desktop_data_path, 'r') as file:
#     desktop_data = json.load(file)

# web_data_path = f"{screenspot_data_dir}/screenspot_web.json"
# with open(web_data_path, 'r') as file:
#     web_data = json.load(file)


# def process_screenspot(raw_data: list, platform: str):
#     images = []
#     instructions = []
#     bboxes = []
#     sources = []
#     platforms = []
#     resolutions = []

#     for d in raw_data:
#         img_filename = d["img_filename"]
#         img_path = os.path.join(screenspot_data_dir, img_filename)
#         image = PIL.Image.open(img_path)
#         img_width, img_height = image.size

#         left, top, width, height = d["bbox"]
#         right = left + width
#         bottom = top + height

#         images.append(img_path)
#         instructions.append(d["instruction"])
#         bboxes.append([left, top, right, bottom])
#         sources.append("screenspot")
#         platforms.append(platform)
#         resolutions.append([img_width, img_height])

#     return {
#         "image": images,
#         "instruction": instructions,
#         "bbox": bboxes,
#         "source": sources,
#         "platform": platforms,
#         "resolution": resolutions,
#     }


# processed_mobile_data = process_screenspot(mobile_data, "mobile")
# processed_desktop_data = process_screenspot(desktop_data, "desktop")
# processed_web_data = process_screenspot(web_data, "web")

# for k in dataset_dict.keys():
#     dataset_dict[k].extend(processed_mobile_data[k])
#     dataset_dict[k].extend(processed_desktop_data[k])
#     dataset_dict[k].extend(processed_web_data[k])


# save_dir = "evals/gui_grounding_dataset"

# dataset = Dataset.from_dict(dataset_dict)
# dataset.save_to_disk(save_dir)


# from datasets import load_from_disk

# dataset = load_from_disk(save_dir).cast_column("image", Image())
# print(f"column: {dataset.column_names}")
# print(f"length: {len(dataset)}")
# print(f"dataset[0]: {dataset[0]}")
