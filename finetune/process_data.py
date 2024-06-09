import json
from tqdm import tqdm
import os
import argparse
from pathlib import Path

from agent_studio.utils.json_utils import add_jsonl


# is instruction English
def is_english_simple(text):
    try:
        text.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True


def bbox_2_point(bbox):
    # bbox [left, top, right, bottom]
    point = [(bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2]
    point = [f"{item:.2f}" for item in point]
    point_str = "({},{})".format(point[0], point[1])
    return point_str


QUERY_TEMPLATE = """
Please output the coordinate for the next action based on the instruction and screenshot. Your answer should be of the following format: '(X, Y)' (without quotes) where X, Y is the coordinates ranging from 0 to 1.
Instruction: {instruction}
Answer:
""".strip()  # noqa: E501


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mobile_imgs", required=True, help="Path to the directory containing mobile images.")
    parser.add_argument("--web_imgs", required=True, help="Path to the directory containing web images.")
    parser.add_argument("--widgetcap_json", required=True, help="Path to the widget captioning JSON file.")
    parser.add_argument("--ricosca_json", required=True, help="Path to the RICOSCA JSON file.")
    parser.add_argument("--web_json", required=True, help="Path to the seeclick web JSON file.")
    parser.add_argument("--output_dir", required=True)

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mobile_imgs = args.mobile_imgs
    web_imgs = args.web_imgs
    widgetcap_json = args.widgetcap_json
    ricosca_json = args.ricosca_json
    web_json = args.web_json

    # widget captioning & RICOSCA grounding
    widgetcap_train = json.load(open(widgetcap_json, "r"))
    ricosca_train = json.load(open(ricosca_json, "r"))
    num_mobile_data = 0
    mobile_data_loca = {"widgetcap": widgetcap_train, "ricosca": ricosca_train}
    for data_name, data in mobile_data_loca.items():
        print("Processing " + str(data_name))
        for i, item in tqdm(enumerate(data)):
            img_filename = item["img_filename"]
            img_path = os.path.join(mobile_imgs, img_filename)

            goal = item["instruction"]
            click_point = bbox_2_point(item["bbox"])

            prompt = QUERY_TEMPLATE.format(instruction=goal)
            conv_user = {"from": "user", "value": f"Picture 1: <img>{img_path}</img>\n"}
            conv_user["value"] += prompt
            conv_ai = {"from": "assistant", "value": click_point}
            conversations = [conv_user, conv_ai]

            data = {"id": f"{data_name}_loca_point_{i}", "conversations": conversations, "source": data_name}

            num_mobile_data += 1
            add_jsonl([data], output_dir / "sft_train.jsonl")

    print(f"Num of mobile data: {num_mobile_data}")

    # web
    web_train = json.load(open(web_json, "r"))
    num_ele_valid = 0
    num_web_data = 0
    print("Processing web")
    for i, item in tqdm(enumerate(web_train)):
        img_filename = item["img_filename"]
        img_path = os.path.join(web_imgs, img_filename)

        eles_valid = []
        for ele in item["elements"]:
            if len([item for item in ele["bbox"] if item < 0]) != 0:
                continue
            if len(ele["instruction"]) > 60:
                continue
            if ('{' in ele["instruction"]) or ('}' in ele["instruction"]):
                continue
            if not is_english_simple(ele["instruction"]):
                continue
            eles_valid.append(ele)

        if len(eles_valid) == 0:
            continue
        num_ele_valid += len(eles_valid)

        for item in eles_valid:
            goal = item["instruction"]
            click_point = bbox_2_point(item["bbox"])

            prompt = QUERY_TEMPLATE.format(instruction=goal)
            conv_user = {"from": "user", "value": f"Picture 1: <img>{img_path}</img>\n"}
            conv_user["value"] += prompt
            conv_ai = {"from": "assistant", "value": click_point}
            conversations = [conv_user, conv_ai]

            data = {"id": f"seeclick_web_loca_point_{i}", "conversations": conversations, "source": "seeclick_web"}
            num_web_data += 1
            add_jsonl([data], output_dir / "sft_train.jsonl")

    print(f"Num of valid elements: {num_ele_valid}")
    print(f"Num of web data: {num_web_data}")
    print(f"Num of sft data: {num_mobile_data + num_web_data}")


if __name__ == "__main__":
    main()
