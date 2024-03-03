import json
from pathlib import Path

import cv2


def read_jsonl(file_path: str, start_idx: int = 0, end_idx: int | None = None) -> list:
    """Reads lines from a .jsonl file between start_idx and end_idx.

    Args:
        file_path (str): Path to the .jsonl file
        start_idx (int, optional): The starting index of lines to read
        end_idx (int | None, optional): The ending index of lines to read

    Returns:
        list[dict]: A list of dictionaries, each dictionary is a line from
            the .jsonl file
    """
    if end_idx is not None and start_idx > end_idx:
        raise ValueError("start_idx must be less or equal to end_idx")

    data = []
    with open(file_path, "r") as file:
        for i, line in enumerate(file):
            if end_idx is not None and i >= end_idx:
                break
            if i >= start_idx:
                data.append(json.loads(line))

    return data


def add_jsonl(data: list, file_path: str, mode="a"):
    """Adds a list of dictionaries to a .jsonl file.

    Args:
        data (list[dict]): A list of json objects to add to the file
        file_path (str): Path to the .jsonl file
    """
    with open(file_path, mode) as file:
        for item in data:
            json_str = json.dumps(item)
            file.write(json_str + "\n")


def format_json(data: dict):
    """Prints a dictionary in a formatted way.

    Args:
        data (dict): The dictionary to print
    """
    return json.dumps(data, indent=4, sort_keys=True)


def export_trajectories(
    self_eval_results: dict | None,
    task_config: dict,
    trajectory: list,
    record_path: str,
    score: float | None,
    feedback: str | None,
    video_path: str | None = None,
    jsonl_name: str = "results.jsonl",
) -> None:
    """Exports the trajectory data to a .jsonl file."""
    if task_config["visual"]:
        media_path = Path(record_path) / task_config["task_id"]
        media_path.mkdir(parents=True, exist_ok=True)
        if video_path is not None:
            video_path = (media_path / "video.mp4").as_posix()
        else:
            video_path = None
    else:
        media_path = None
        video_path = None
    results = {
        "video": video_path,
        "task_id": task_config["task_id"],
        "instruction": task_config["instruction"],
        "trajectory": [],
    }
    if score is not None:
        results["score"] = score
    if feedback is not None:
        results["feedback"] = feedback
    if self_eval_results is not None:
        results["self_eval"] = {
            "score": self_eval_results["score"],
            "response": self_eval_results["response"],
        }
    if task_config["visual"]:
        assert media_path is not None
        for traj in trajectory:
            image_path = (media_path / f"{traj['timestamp']}.png").as_posix()
            cv2.imwrite(image_path, traj["obs"])
            results["trajectory"].append(
                {
                    "obs": image_path,
                    "prompt": traj["prompt"],
                    "response": traj["response"],
                    "info": traj["info"],
                    "act": traj["act"],
                    "res": traj["res"],
                    "timestamp": traj["timestamp"],
                }
            )
    else:
        results["trajectory"] = trajectory
    add_jsonl(
        data=[results],
        file_path=(Path(record_path) / jsonl_name).as_posix(),
    )
