import json
from pathlib import Path

import cv2

from playground.agent.base_agent import Agent


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
    agent: Agent,
    task_config: dict,
    trajectory: list,
    record_path: str,
    score: float,
    feedback: str,
) -> None:
    """Exports the trajectory data to a .jsonl file."""
    if task_config["visual"]:
        media_path = Path(record_path) / task_config["task_id"]
        video_path = (media_path / "video.mp4").as_posix()
    else:
        media_path = None
        video_path = None
    results = {
        "video": video_path,
        "task_id": task_config["task_id"],
        "instruction": task_config["instruction"],
        "trajectory": [],
        "self_eval": agent.eval(),
        "score": score,
        "feedback": feedback,
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
        file_path=(Path(record_path) / "results.jsonl").as_posix(),
    )
