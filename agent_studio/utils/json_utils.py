import dataclasses
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from agent_studio.llm.utils import decode_image
from agent_studio.utils.types import TaskConfig, TaskResult, TrajectoryInfo, VideoMeta


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


def read_json(
    file_path: str, start_idx: int = 0, end_idx: int | None = None
) -> dict | list:
    """Reads a dictionary from a .json file.

    Args:
        file_path (str): Path to the .json file
    """
    with open(file_path, "r") as file:
        if end_idx is None:
            data = json.load(file)[start_idx:]
        else:
            data = json.load(file)[start_idx:end_idx]
    return data


def apply_env_vars(task_config: TaskConfig, env_vars: dict) -> TaskConfig:
    def replace_placeholders(text, env_vars):
        # Regex to find patterns like ${VAR_NAME}
        pattern = re.compile(r"\$\{(\w+)\}")

        def replacer(match):
            var_name = match.group(1)
            if var_name in env_vars:
                return env_vars[var_name]
            else:
                raise ValueError(
                    f"Variable {var_name} not found in environment variables"
                )

        return pattern.sub(replacer, text)

    def traverse_and_replace(obj, env_vars):
        if isinstance(obj, dict):
            return {
                traverse_and_replace(k, env_vars): traverse_and_replace(v, env_vars)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [traverse_and_replace(item, env_vars) for item in obj]
        elif isinstance(obj, str):
            return replace_placeholders(obj, env_vars)
        else:
            return obj

    json_dict = task_config.model_dump()
    replaced_json = traverse_and_replace(json_dict, env_vars)
    return TaskConfig.model_validate(replaced_json)


def read_task_jsons(path: Path) -> list[TaskConfig]:
    """
    Read task configs from folder or file
    """
    task_configs: list[TaskConfig] = []
    if path.is_dir():
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".json"):
                    with open(os.path.join(root, file), "r") as f:
                        task_configs.append(TaskConfig.model_validate(json.load(f)))
    else:
        with open(path, "r") as f:
            task_configs.append(TaskConfig.model_validate(json.load(f)))
    return task_configs


def read_unfinished_tasks(
    task_configs_path: Path, results_dir: Path
) -> list[TaskConfig]:
    """
    Read task configs from folder or file and read finished task logs from
    `results_dir`. Remaining unfinished tasks are returned.
    """
    task_configs: list[TaskConfig] = []
    if task_configs_path.is_dir():
        for root, _, files in os.walk(task_configs_path):
            for file in files:
                if file.endswith(".json"):
                    with open(os.path.join(root, file), "r") as f:
                        task_configs.append(TaskConfig.model_validate(json.load(f)))
    else:
        with open(task_configs_path, "r") as f:
            task_configs.append(TaskConfig.model_validate(json.load(f)))

    finished_tasks = load_results(results_dir)
    finished_task_ids = [task.task_id for task in finished_tasks]
    unfinished_tasks = []
    for task_config in task_configs:
        if task_config.task_id not in finished_task_ids:
            unfinished_tasks.append(task_config)
    return unfinished_tasks


def add_json(data: dict, file_path: str, mode="a"):
    """Adds a dictionary to a .json file.

    Args:
        data (dict): The dictionary to add to the file
        file_path (str): Path to the .json file
    """
    with open(file_path, mode) as file:
        json.dump(data, file)
        file.write("\n")


def format_json(data: dict, indent=4, sort_keys=False):
    """Prints a dictionary in a formatted way.

    Args:
        data (dict): The dictionary to print
    """
    return json.dumps(data, indent=indent, sort_keys=sort_keys)


def export_trajectory(
    task_config: TaskConfig,
    trajectory: TrajectoryInfo,
    path: Path,
    score: float,
    feedback: str,
    token_count: int | None,
    time_cost: float,
    video_meta: VideoMeta | None = None,
) -> None:
    """Exports the trajectory data to a .jsonl file."""
    result_dict = {
        "video": video_meta,
        "task_id": task_config.task_id,
        "instruction": task_config.instruction,
        "trajectory": trajectory,
        "token_count": token_count,
        "score": score,
        "feedback": feedback,
        "time_cost": time_cost,
    }
    parse_and_save_objects(obj=result_dict, folder_path=path)
    # model check
    result = TaskResult.model_validate(result_dict)
    add_jsonl(
        data=[result.model_dump()],
        file_path=(path / "result.jsonl").as_posix(),
        mode="w",
    )


def make_report(task_config_dir: Path, result_dir: Path) -> dict:
    """Make a report from the results"""
    task_configs = read_task_jsons(task_config_dir)
    unfinished_tasks = read_unfinished_tasks(task_config_dir, result_dir)
    results_all = load_results(result_dir)
    task_config_ids = [task.task_id for task in task_configs]
    results = [result for result in results_all if result.task_id in task_config_ids]
    scores = [result.score for result in results]
    average_score = 100 * sum(scores) / len(scores) if len(scores) > 0 else 0
    return {
        "average_score": average_score,
        "total_task_count": len(task_configs),
        "finished_task_count": len(results),
        "unfinished_task_count": len(unfinished_tasks),
        "succ_task_count": len([result for result in results if result.score > 0]),
        "fail_task_count": len([result for result in results if result.score == 0]),
        "total_task_ids": [task.task_id for task in task_configs],
        "finished_task_ids": [result.task_id for result in results],
        "unfinished_task_ids": [task.task_id for task in unfinished_tasks],
        "succ_task_ids": [result.task_id for result in results if result.score > 0],
        "fail_task_ids": [result.task_id for result in results if result.score == 0],
    }


def make_report2(task_config_dir: Path, result_dir: Path, depth: int = 0) -> dict:
    """Make a report from the results"""
    results_all = load_results(result_dir)
    result = {
        "average_score": 0.0,
        "total_task_count": 0,
        "finished_task_count": 0,
        "unfinished_task_count": 0,
        "succ_task_count": 0,
        "fail_task_count": 0,
    }
    for dir in task_config_dir.iterdir():
        if dir.is_dir():
            report = make_report2(dir, result_dir, depth + 1)
            result["total_task_count"] += report["total_task_count"]
            result["finished_task_count"] += report["finished_task_count"]
            result["unfinished_task_count"] += report["unfinished_task_count"]
            result["succ_task_count"] += report["succ_task_count"]
            result["fail_task_count"] += report["fail_task_count"]
        else:
            task_configs = read_task_jsons(dir)
            assert (
                len(task_configs) == 1
            ), "Task config dir should contain only one file"
            task_config = task_configs[0]
            task_id = task_config.task_id
            results = [result for result in results_all if result.task_id == task_id]
            result["total_task_count"] += 1
            if len(results) == 0:
                result["unfinished_task_count"] += 1
            else:
                result["finished_task_count"] += 1
                if results[0].score > 0:
                    result["succ_task_count"] += 1
                else:
                    result["fail_task_count"] += 1
    result["average_score"] = (
        100 * result["succ_task_count"] / result["finished_task_count"]
        if result["finished_task_count"] > 0
        else 0
    )
    indent = "    " * depth
    print(
        f"{indent}{task_config_dir.name: <20}: "
        f"score: {result['average_score']: <10.2f}, "
        f"succ: {result['succ_task_count']: <10}, "
        f"finished: {result['finished_task_count']: <10}, "
        f"total: {result['total_task_count']: <10}"
    )
    return result


def load_result(result_dir: Path) -> TaskResult:
    """Load result from result_dir
    result_dir: directory containing the result
    result_dir/result.jsonl: the result file
    result_dir/video.mp4: the video file
    result_dir/{uuid}.png: the images
    """
    result_raw = read_jsonl((result_dir / "result.jsonl").as_posix())
    saved_trajectory = TaskResult.model_validate(result_raw[0])
    return saved_trajectory


def load_results(results_dir: Path) -> list[TaskResult]:
    """Load results from result_dir
    results_dir: directory containing the results
    results_dir/{task_id}: the result directory of the task
    results_dir/{task_id}/result.jsonl: the result file
    results_dir/{task_id}/video.mp4: the video file
    results_dir/{task_id}/{uuid}.png: the images
    """
    if not results_dir.exists():
        return []
    results: list[TaskResult] = []
    for dir in results_dir.iterdir():
        try:
            result = load_result(dir)
            results.append(result)
        except Exception as e:
            print(f"Error loading result from {dir}: {e}")
            pass
    return results


def save_image(obj: Any, folder_path: Path) -> str:
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)

    # A unique identifier for the filename.
    unique_filename = f"{str(uuid.uuid4())}.png"
    file_path = folder_path / unique_filename
    if isinstance(obj, Image.Image):
        obj.save(file_path)
    elif isinstance(obj, np.ndarray):
        cv2.imwrite(file_path.as_posix(), obj)
    else:
        raise ValueError("Unsupported object type for saving.")
    return f"file://{unique_filename}"


def parse_and_save_objects(obj: Any, folder_path: Path) -> Any:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (Image.Image, np.ndarray)):
                obj[key] = save_image(value, folder_path)
            elif isinstance(value, (dict, list)):
                obj[key] = parse_and_save_objects(value, folder_path)
            elif (
                isinstance(value, str)
                and key == "url"
                and value.startswith("data:image")
            ):
                obj[key] = save_image(decode_image(value), folder_path)
            elif dataclasses.is_dataclass(value) and not isinstance(value, type):
                obj[key] = parse_and_save_objects(
                    dataclasses.asdict(value), folder_path
                )
    elif isinstance(obj, list):
        for i in range(len(obj)):
            if isinstance(obj[i], (Image.Image, np.ndarray)):
                obj[i] = save_image(obj[i], folder_path)
            elif isinstance(obj[i], (dict, list)):
                obj[i] = parse_and_save_objects(obj[i], folder_path)
            elif dataclasses.is_dataclass(obj[i]):
                obj[i] = parse_and_save_objects(dataclasses.asdict(obj[i]), folder_path)
    return obj
