import os

from datasets import Dataset, Features, Image, Sequence, Value

from agent_studio.utils.json_utils import read_jsonl


def push_ground_ui_1k():
    dataset_dict = {
        "image_path": [],
        "image": [],
        "instruction": [],
        "raw_instruction": [],
        "bbox": [],
        "resolution": [],
        "source": [],
        "platform": [],
    }

    data_jsonl = "evals/datasets/gui_grounding/metadata_1k.jsonl"
    data = read_jsonl(data_jsonl)

    image_dir = "evals/datasets/gui_grounding/images"

    for d in data:
        dataset_dict["image_path"].append(d["image"])
        dataset_dict["image"].append(os.path.join(image_dir, d["image"]))
        dataset_dict["instruction"].append(d["instruction"])
        dataset_dict["raw_instruction"].append(d["raw_instruction"])
        dataset_dict["bbox"].append(d["bbox"])
        dataset_dict["resolution"].append(d["resolution"])
        dataset_dict["source"].append(d["source"])
        dataset_dict["platform"].append(d["platform"])

    dataset = Dataset.from_dict(dataset_dict)
    dataset = dataset.cast_column("image", Image())
    print(f"column: {dataset.column_names}")
    print(f"length: {len(dataset)}")
    print(f"dataset[0]: {dataset[0]}")

    dataset.push_to_hub("agent-studio/GroundUI-1K")


def push_ground_ui_18k():
    dataset_dict = {
        "image_path": [],
        "image": [],
        "instruction": [],
        "bbox": [],
        "resolution": [],
        "source": [],
        "platform": [],
    }

    data_jsonl = "evals/datasets/gui_grounding/metadata.jsonl"
    data = read_jsonl(data_jsonl)

    image_dir = "evals/datasets/gui_grounding/images"

    for d in data:
        dataset_dict["image_path"].append(d["image"])
        dataset_dict["image"].append(os.path.join(image_dir, d["image"]))
        dataset_dict["instruction"].append(d["instruction"])
        dataset_dict["bbox"].append(d["bbox"])
        dataset_dict["resolution"].append(d["resolution"])
        dataset_dict["source"].append(d["source"])
        dataset_dict["platform"].append(d["platform"])

    dataset = Dataset.from_dict(dataset_dict)
    dataset = dataset.cast_column("image", Image())
    print(f"column: {dataset.column_names}")
    print(f"length: {len(dataset)}")
    print(f"dataset[0]: {dataset[0]}")

    dataset.push_to_hub("agent-studio/GroundUI-18K")


def push_idm_single():
    dataset_dict = {
        "action_id": [],
        "obs_before_path": [],
        "obs_after_path": [],
        "obs_before": [],
        "obs_after": [],
        "operation": [],
        "bbox": [],
        "metadata": [],
        "instruction": [],
        "source": [],
        "platform": [],
        "action_space": [],
    }

    data_jsonl = "evals/datasets/trajectory_lite/metadata_idm.jsonl"
    data = read_jsonl(data_jsonl)

    image_dir = "evals/datasets/trajectory_lite/images"

    for d in data:
        dataset_dict["action_id"].append(d["action_id"])
        dataset_dict["obs_before_path"].append(d["obs_before"])
        dataset_dict["obs_after_path"].append(d["obs_after"])
        dataset_dict["obs_before"].append(os.path.join(image_dir, d["obs_before"]))
        dataset_dict["obs_after"].append(os.path.join(image_dir, d["obs_after"]))
        dataset_dict["operation"].append(d["operation"])
        dataset_dict["bbox"].append(d["bbox"])
        dataset_dict["metadata"].append(d["metadata"])
        dataset_dict["instruction"].append(d["instruction"])
        dataset_dict["source"].append(d["source"])
        dataset_dict["platform"].append(d["platform"])
        dataset_dict["action_space"].append(d["action_space"])

    dataset = Dataset.from_dict(dataset_dict)
    dataset = dataset.cast_column("obs_before", Image())
    dataset = dataset.cast_column("obs_after", Image())
    print(f"column: {dataset.column_names}")
    print(f"length: {len(dataset)}")
    print(f"dataset[0]: {dataset[0]}")

    dataset.push_to_hub("agent-studio/IDM-Single")


def push_idm_multiple():
    features = Features(
        {
            "instruction": Value("string"),
            "annotation_id": Value("string"),
            "actions": Sequence(
                {
                    "action_id": Value("string"),
                    "obs_before_path": Value("string"),
                    "obs_after_path": Value("string"),
                    "obs_before": Image(),
                    "obs_after": Image(),
                    "operation": Value("string"),
                    "bbox": {
                        "x": Value("float32"),
                        "y": Value("float32"),
                        "width": Value("float32"),
                        "height": Value("float32"),
                    },
                    "metadata": {
                        "repr": Value("string"),
                        "text": Value("string"),
                    },
                }
            ),
            "source": Value("string"),
            "platform": Value("string"),
            "metadata": {
                "repr": Value("string"),
                "text": Value("string"),
            },
            "action_space": Sequence(Value("string")),
            "is_success": Value("bool"),
        }
    )

    dataset_dict = {
        "instruction": [],
        "annotation_id": [],
        "actions": [],
        "source": [],
        "platform": [],
        "metadata": [],
        "action_space": [],
        "is_success": [],
    }

    data_jsonl = "evals/datasets/trajectory_lite/metadata_idmn2n.jsonl"
    data = read_jsonl(data_jsonl)

    image_dir = "evals/datasets/trajectory_lite/images"

    for d in data:
        dataset_dict["instruction"].append(d["instruction"])
        dataset_dict["annotation_id"].append(d["annotation_id"])
        for action in d["actions"]:
            action["obs_before"] = os.path.join(image_dir, action["obs_before"])
            action["obs_before_path"] = action["obs_before"]
            if action["obs_after"] is not None:
                action["obs_after"] = os.path.join(image_dir, action["obs_after"])
                action["obs_after_path"] = action["obs_after"]
            else:
                action["obs_after"] = None
                action["obs_after_path"] = None
        dataset_dict["actions"].append(d["actions"])
        dataset_dict["source"].append(d["source"])
        dataset_dict["platform"].append(d["platform"])
        dataset_dict["metadata"].append(d["metadata"])
        dataset_dict["action_space"].append(d["action_space"])
        dataset_dict["is_success"].append(d["is_success"])

    dataset = Dataset.from_dict(dataset_dict, features=features)
    print(f"column: {dataset.column_names}")
    print(f"length: {len(dataset)}")
    print(f"dataset[0]: {dataset[0]}")

    dataset.push_to_hub("agent-studio/IDM-Multiple")


def push_success_detection():
    features = Features(
        {
            "instruction": Value("string"),
            "annotation_id": Value("string"),
            "actions": Sequence(
                {
                    "action_id": Value("string"),
                    "obs_before_path": Value("string"),
                    "obs_after_path": Value("string"),
                    "obs_before": Image(),
                    "obs_after": Image(),
                    "operation": Value("string"),
                    "bbox": {
                        "x": Value("float32"),
                        "y": Value("float32"),
                        "width": Value("float32"),
                        "height": Value("float32"),
                    },
                    "metadata": {
                        "repr": Value("string"),
                        "text": Value("string"),
                    },
                }
            ),
            "source": Value("string"),
            "platform": Value("string"),
            "metadata": {
                "repr": Value("string"),
                "text": Value("string"),
            },
            "action_space": Sequence(Value("string")),
            "is_success": Value("bool"),
        }
    )

    dataset_dict = {
        "instruction": [],
        "annotation_id": [],
        "actions": [],
        "source": [],
        "platform": [],
        "metadata": [],
        "action_space": [],
        "is_success": [],
    }

    data_jsonl = "evals/datasets/trajectory_lite/metadata_success_detection.jsonl"
    data = read_jsonl(data_jsonl)

    image_dir = "evals/datasets/trajectory_lite/images"

    for d in data:
        dataset_dict["instruction"].append(d["instruction"])
        dataset_dict["annotation_id"].append(d["annotation_id"])
        for action in d["actions"]:
            action["obs_before"] = os.path.join(image_dir, action["obs_before"])
            action["obs_before_path"] = action["obs_before"]
            if action["obs_after"] is not None:
                action["obs_after"] = os.path.join(image_dir, action["obs_after"])
                action["obs_after_path"] = action["obs_after"]
            else:
                action["obs_after"] = None
                action["obs_after_path"] = None
        dataset_dict["actions"].append(d["actions"])
        dataset_dict["source"].append(d["source"])
        dataset_dict["platform"].append(d["platform"])
        dataset_dict["metadata"].append(d["metadata"])
        dataset_dict["action_space"].append(d["action_space"])
        dataset_dict["is_success"].append(d["is_success"])

    dataset = Dataset.from_dict(dataset_dict, features=features)
    print(f"column: {dataset.column_names}")
    print(f"length: {len(dataset)}")
    print(f"dataset[0]: {dataset[0]}")

    dataset.push_to_hub("agent-studio/SuccessDetection")


if __name__ == "__main__":
    push_ground_ui_1k()
    push_ground_ui_18k()
    push_idm_single()
    push_idm_multiple()
    push_success_detection()
