import json
import os

from PIL import Image

from agent_studio.utils.json_utils import add_jsonl

screenspot_data_dir = "raw_data/screenspot"
mind2web_data_dir = "raw_data/mind2web"
aitw_data_dir = "raw_data/aitw"

# mobile_data_path = f"{screenspot_data_dir}/screenspot_mobile.json"
# with open(mobile_data_path, "r") as file:
#     mobile_data = json.load(file)

# desktop_data_path = f"{screenspot_data_dir}/screenspot_desktop.json"
# with open(desktop_data_path, "r") as file:
#     desktop_data = json.load(file)

# web_data_path = f"{screenspot_data_dir}/screenspot_web.json"
# with open(web_data_path, "r") as file:
#     web_data = json.load(file)


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


# processed_mobile_data = process_screenspot(mobile_data, "mobile")
# processed_desktop_data = process_screenspot(desktop_data, "desktop")
# processed_web_data = process_screenspot(web_data, "web")

# dataset = processed_mobile_data + processed_desktop_data + processed_web_data

# add_jsonl(dataset, f"{screenspot_data_dir}/metadata.jsonl")


# test_task_data_path = f"{mind2web_data_dir}/mind2web_data_test_task.json"
# with open(test_task_data_path, "r") as file:
#     test_task_data = json.load(file)

# test_website_data_path = f"{mind2web_data_dir}/mind2web_data_test_website.json"
# with open(test_website_data_path, "r") as file:
#     test_website_data = json.load(file)

# test_domain_data_path = f"{mind2web_data_dir}/mind2web_data_test_domain.json"
# with open(test_domain_data_path, "r") as file:
#     test_domain_data = json.load(file)

# print(f"Length before processing: {len(test_task_data) + len(test_website_data) + len(test_domain_data)}")

# mind2web_img_dir = os.path.join(mind2web_data_dir, "mind2web_images")


def process_mind2web(raw_data: list, split: str):
    processed_data = []
    for episode in raw_data:
        single_step_instructions = episode["action_reprs"]
        annotation_id = episode["annotation_id"]
        for step, instruction in zip(episode["actions"], single_step_instructions):
            if "bbox" not in step:
                continue

            img_filename = f"{annotation_id}-{step['action_uid']}.jpg"
            img_path = os.path.join(mind2web_img_dir, img_filename)
            image = Image.open(img_path)
            img_width, img_height = image.size

            bbox = step["bbox"]
            left = bbox["x"]
            top = bbox["y"]
            width = bbox["width"]
            height = bbox["height"]
            right = left + width
            bottom = top + height

            processed_data.append(
                {
                    "image": img_filename,
                    "instruction": instruction,
                    "bbox": [left, top, right, bottom],
                    "source": f"mind2web_{split}",
                    "platform": "web",
                    "resolution": [img_width, img_height],
                }
            )

    return processed_data

# processed_test_task_data = process_mind2web(test_task_data, "test_task")
# processed_test_website_data = process_mind2web(test_website_data, "test_website")
# processed_test_domain_data = process_mind2web(test_domain_data, "test_domain")

# dataset = processed_test_task_data + processed_test_website_data + processed_test_domain_data

# add_jsonl(dataset, f"{mind2web_img_dir}/metadata.jsonl")

# print(f"Processed data saved. Length={len(dataset)}")



# aitw_test_data_path = f"{aitw_data_dir}/aitw_data_test.json"
# with open(aitw_test_data_path, "r") as file:
#     aitw_test_data = json.load(file)

# print(f"Length before processing: {len(aitw_test_data)}")

# aitw_img_dir = os.path.join(aitw_data_dir, "aitw_images")


# def process_aitw(raw_data: list, split: str):
#     processed_data = []
#     for episode in raw_data:
#         annotation_id = episode["annotation_id"]
#         for step in episode:
#             if step["action_type_id"] == 4:  # click action
#                 # Following Seeclick, we calculate midpoint of touch and lift as the click point
#                 touch_point = step["touch"]
#                 lift_point = step["lift"]
#                 click_point = [(touch_point[0] + lift_point[0]) / 2, (touch_point[1] + lift_point[1]) / 2]
#                 click_point = [f"{item:.2f}" for item in click_point]
#             else:
#                 continue

#             img_filename = f"{step['img_filename']}.png"
#             img_path = os.path.join(aitw_img_dir, img_filename)
#             if not os.path.exists(img_path):
#                 print('image not found')
#                 continue
#             image = Image.open(img_path)
#             img_width, img_height = image.size

#             bbox = step["bbox"]
#             left = bbox["x"]
#             top = bbox["y"]
#             width = bbox["width"]
#             height = bbox["height"]
#             right = left + width
#             bottom = top + height

#             processed_data.append(
#                 {
#                     "image": img_filename,
#                     "instruction": step["goal"],
#                     "bbox": [left, top, right, bottom],
#                     "source": f"aitw_{split}",
#                     "platform": "mobile",
#                     "resolution": [img_width, img_height],
#                 }
#             )

#     return processed_data

# processed_aitw_general = process_aitw(aitw_test_data["general"], "general")
# processed_aitw_single = process_aitw(aitw_test_data["single"], "single")
# processed_aitw_webshopping = process_aitw(aitw_test_data["webshopping"], "webshopping")
# processed_aitw_install = process_aitw(aitw_test_data["install"], "install")
# processed_aitw_googleapps = process_aitw(aitw_test_data["googleapps"], "googleapps")

# dataset = processed_aitw_general + processed_aitw_single + processed_aitw_webshopping + processed_aitw_install + processed_aitw_googleapps

# add_jsonl(dataset, f"{aitw_data_dir}/metadata.jsonl")

# print(f"Processed data saved. Length={len(dataset)}")


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
