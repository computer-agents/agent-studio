import json
import os
import shutil

from PIL import Image
from tqdm import tqdm

from agent_studio.utils.json_utils import add_jsonl


def process_screenspot(screenspot_data_dir="raw_data/screenspot"):
    mobile_data_path = f"{screenspot_data_dir}/screenspot_mobile.json"
    with open(mobile_data_path, "r") as file:
        mobile_data = json.load(file)

    desktop_data_path = f"{screenspot_data_dir}/screenspot_desktop.json"
    with open(desktop_data_path, "r") as file:
        desktop_data = json.load(file)

    web_data_path = f"{screenspot_data_dir}/screenspot_web.json"
    with open(web_data_path, "r") as file:
        web_data = json.load(file)

    processed_data = []
    for data, platform in zip(
        [mobile_data, desktop_data, web_data], ["mobile", "desktop", "web"]
    ):
        for d in data:
            img_filename = d["img_filename"]
            img_path = os.path.join(screenspot_data_dir, img_filename)
            with Image.open(img_path) as img:
                img_width, img_height = img.size

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

    add_jsonl(processed_data, f"{screenspot_data_dir}/metadata.jsonl")
    print(f"Processed data saved. Length={len(processed_data)}")


def process_mind2web(mind2web_data_dir="raw_data/mind2web"):
    test_task_data_path = f"{mind2web_data_dir}/mind2web_data_test_task.json"
    with open(test_task_data_path, "r") as file:
        test_task_data = json.load(file)

    test_website_data_path = f"{mind2web_data_dir}/mind2web_data_test_website.json"
    with open(test_website_data_path, "r") as file:
        test_website_data = json.load(file)

    test_domain_data_path = f"{mind2web_data_dir}/mind2web_data_test_domain.json"
    with open(test_domain_data_path, "r") as file:
        test_domain_data = json.load(file)

    print(
        f"Length before processing: {len(test_task_data) + len(test_website_data) + len(test_domain_data)}"  # noqa: E501
    )

    mind2web_img_dir = os.path.join(mind2web_data_dir, "mind2web_images")

    processed_data = []
    for data, split in zip(
        [test_task_data, test_website_data, test_domain_data],
        ["test_task", "test_website", "test_domain"],
    ):
        for episode in data:
            single_step_instructions = episode["action_reprs"]
            annotation_id = episode["annotation_id"]
            for step, instruction in zip(episode["actions"], single_step_instructions):
                if "bbox" not in step:
                    continue

                img_filename = f"{annotation_id}-{step['action_uid']}.jpg"
                img_path = os.path.join(mind2web_img_dir, img_filename)
                with Image.open(img_path) as img:
                    img_width, img_height = img.size

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

    add_jsonl(processed_data, f"{mind2web_img_dir}/metadata.jsonl")
    print(f"Processed data saved. Length={len(processed_data)}")


def process_aitw(aitw_data_dir="raw_data/aitw"):
    aitw_test_data_path = f"{aitw_data_dir}/aitw_data_test.json"
    with open(aitw_test_data_path, "r") as file:
        aitw_test_data = json.load(file)

    print(f"Length before processing: {len(aitw_test_data)}")
    aitw_img_dir = os.path.join(aitw_data_dir, "aitw_images")

    processed_data = []
    for split in ["general", "single", "webshopping", "install", "googleapps"]:
        raw_data = aitw_test_data[split]
        for episode in raw_data:
            for step in episode:
                if step["action_type_id"] == 4:  # click action
                    # Following Seeclick, we calculate midpoint of touch and lift as the click point  # noqa: E501
                    touch_point = step["touch"]
                    lift_point = step["lift"]
                    click_point = [
                        (touch_point[0] + lift_point[0]) / 2,
                        (touch_point[1] + lift_point[1]) / 2,
                    ]
                    click_point = [f"{item:.2f}" for item in click_point]
                else:
                    continue

                img_filename = f"{step['img_filename']}.png"
                img_path = os.path.join(aitw_img_dir, img_filename)
                if not os.path.exists(img_path):
                    print("image not found")
                    continue
                with Image.open(img_path) as img:
                    img_width, img_height = img.size

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
                        "instruction": step["goal"],
                        "bbox": [left, top, right, bottom],
                        "source": f"aitw_{split}",
                        "platform": "mobile",
                        "resolution": [img_width, img_height],
                    }
                )

    add_jsonl(processed_data, f"{aitw_data_dir}/metadata.jsonl")
    print(f"Processed data saved. Length={len(processed_data)}")


def process_motif(
    motif_data_dir="raw_data/motif", motif_image_dir="motif_all_raw_data", split="test"
):
    test_set_list = []
    test_set_json_path_list = [
        f"{motif_data_dir}/eccv_motif_app_seen_task_unseen_all.json",
        f"{motif_data_dir}/eccv_motif_app_seen_task_unseen_curr.json",
        f"{motif_data_dir}/eccv_motif_app_unseen_task_seen.json",
        f"{motif_data_dir}/eccv_motif_app_unseen_task_unseen.json",
        f"{motif_data_dir}/eccv_motif_ricosca_app_seen_task_unseen_all.json",
        f"{motif_data_dir}/eccv_motif_ricosca_app_seen_task_unseen_curr.json",
        f"{motif_data_dir}/eccv_motif_ricosca_app_unseen_task_seen.json",
        f"{motif_data_dir}/eccv_motif_ricosca_app_unseen_task_unseen.json",
    ]
    for test_set_json_path in test_set_json_path_list:
        with open(test_set_json_path, "r") as file:
            test_set_list.extend(json.load(file)[split])

    print(len(test_set_list))
    test_set = list(set(test_set_list))
    print(len(test_set))

    motif_json_dir = f"{motif_data_dir}/processed_motif_deduped"

    processed_data = []
    for trace_id in tqdm(test_set):
        with open(os.path.join(motif_json_dir, trace_id + ".json"), "r") as file:
            data = json.load(file)

        app_name = data["app"]
        cur_image_dir = os.path.join(app_name, trace_id, "screens")
        image_ids = data["images"]
        instructions = data["obj_desc_str"]
        screen_bboxes = data["screen_bboxes"]

        for i in range(len(instructions)):
            image_id = image_ids[i]
            instruction = instructions[i]
            bbox = screen_bboxes[i]

            if bbox is None:
                continue

            new_image_filename = f"{app_name}_{trace_id}_{image_id}.jpg"
            filename = os.path.join(cur_image_dir, f"{image_id}.jpg")
            img_path = os.path.join(motif_image_dir, filename)
            assert os.path.exists(img_path)
            shutil.copyfile(
                img_path,
                os.path.join(
                    "/mnt/data/longtaozheng/agent-studio/evals/datasets/gui_grounding/images",  # noqa: E501
                    new_image_filename,
                ),
            )

            with Image.open(
                os.path.join(
                    "/mnt/data/longtaozheng/agent-studio/evals/datasets/gui_grounding/images",  # noqa: E501
                    new_image_filename,
                )
            ) as img:
                img_width, img_height = img.size

            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            left, top = x1, y1
            right = left + width
            bottom = top + height

            processed_data.append(
                {
                    "image": new_image_filename,
                    "instruction": instruction,
                    "bbox": [left, top, right, bottom],
                    "source": "motif",
                    "platform": "mobile",
                    "resolution": [img_width, img_height],
                }
            )

    add_jsonl(processed_data, f"{motif_data_dir}/metadata.jsonl")
    print(f"Processed data saved. Length={len(processed_data)}")


def process_agent_studio(root_path="raw_data/agent_studio"):
    processed_data = []
    os_dirs = os.listdir(root_path)
    for os_dir in os_dirs:
        os_dir = os.path.join(root_path, os_dir)
        if os.path.isdir(os_dir):
            app_dirs = os.listdir(os_dir)
            for app_dir in app_dirs:
                app_dir = os.path.join(root_path, os_dir, app_dir)
                if os.path.isdir(app_dir):
                    actions_jsonl = os.path.join(app_dir, "actions.jsonl")

                    with open(actions_jsonl, "r") as file:
                        lines = file.readlines()
                        for line in lines:
                            data = json.loads(line)
                            instruction = data["instruction"]
                            original_path = data["trajectory"][0]["obs"].replace(
                                "data/grounding", root_path
                            )

                            components = original_path.split("/")
                            new_image_filename = (
                                f"{components[-4]}_{components[-3]}_{components[-1]}"
                            )

                            assert os.path.exists(original_path), original_path
                            shutil.copyfile(
                                original_path,
                                os.path.join(
                                    "agent-studio/evals/datasets/gui_grounding/images",
                                    new_image_filename,
                                ),
                            )

                            with Image.open(original_path) as img:
                                img_width, img_height = img.size

                            mouse_action = data["trajectory"][0]["annotation"][
                                "mouse_action"
                            ]
                            x, y, width, height = (
                                mouse_action["x"],
                                mouse_action["y"],
                                mouse_action["width"],
                                mouse_action["height"],
                            )
                            left, top, right, bottom = x, y, x + width, y + height

                            processed_data.append(
                                {
                                    "image": new_image_filename,
                                    "instruction": instruction,
                                    "bbox": [left, top, right, bottom],
                                    "source": "agent_studio",
                                    "platform": "desktop",
                                    "resolution": [img_width, img_height],
                                }
                            )

    add_jsonl(
        processed_data,
        "agent-studio/evals/datasets/gui_grounding/metadata_agent_studio.jsonl",
    )
    print(f"Processed data saved. Length={len(processed_data)}")


def get_jsonl_length(jsonl_paths: str) -> int:
    image_list = []
    jsonl_paths = [
        "agent-studio/evals/datasets/gui_grounding/metadata_mind2web.jsonl",
        "agent-studio/evals/datasets/gui_grounding/metadata_omniact.jsonl",
        "agent-studio/evals/datasets/gui_grounding/metadata_motif.jsonl",
        "agent-studio/evals/datasets/gui_grounding/metadata_screenspot.jsonl",
        "agent-studio/evals/datasets/gui_grounding/metadata_agent_studio.jsonl",
        # "agent-studio/evals/datasets/gui_grounding/metadata.jsonl",
    ]

    for jsonl_path in jsonl_paths:
        with open(jsonl_path, "r") as file:
            lines = file.readlines()
            print(f"Length of {jsonl_path}: {len(lines)}")
            for line in lines:
                data = json.loads(line)
                image_list.append(data["image"])

    print(len(image_list))
    image_set = list(set(image_list))
    print(len(image_set))


def calculate_platforms():
    platforms = {
        "mobile": 0,
        "desktop": 0,
        "web": 0,
    }

    with open("agent-studio/evals/datasets/gui_grounding/metadata.jsonl", "r") as file:
        lines = file.readlines()
        for line in lines:
            data = json.loads(line)
            platforms[data["platform"]] += 1

    print(platforms, sum(list(platforms.values())))
