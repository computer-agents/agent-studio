"""
python task_statistics.py <config_root> -t <trajectory_root> -o <output_path>
Parse all jsonl files under <trajectory_root> and <config_root> folder and match the task_id
Output the statistics to <output_path> as csv, if output_path exists, update it.

Example:
    python ./scripts/task_statistics.py data/tasks -t data/trajectories/gemini/direct -o data.csv
"""


import argparse
import os
import logging

import pandas as pd

from agent_studio.utils.json_utils import read_jsonl


logger = logging.getLogger(__name__)


def extract_info_from_config(configs: dict[str, dict]):
    info = {}
    for task_id, config in configs.items():
        evaluators = set()
        for eval in config["evals"]:
            # System and human are not actual evaluators
            # System is the auxiliary evaluator
            if eval["eval_type"] not in ["system", "human"]:
                evaluators.add(eval["eval_type"])
        info[task_id] = {
            "task_id": task_id,
            "instruction": config["instruction"],
            "evaluators": list(evaluators),
            "visual": config["visual"],
        }
    return info


def extract_info_from_trajectory(trajectories: dict[str, dict]):
    info = {}
    for task_id, trajectory in trajectories.items():
        info[task_id] = {
            "task_id": task_id,
            "trajectory_length": len(trajectory["trajectory"]),
            "score": trajectory["score"],
            "self_eval_score": trajectory["self_eval"]["score"],
        }
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse all jsonl files and output the statistics to csv.")
    parser.add_argument("config_root", type=str, help="The root path of the config jsonl files.")
    parser.add_argument("-t", "--trajectory_root", type=str, help="The root path of the trajectory jsonl files.")
    parser.add_argument("-o", "--output_path", type=str, help="The output path of the statistics csv.")
    args = parser.parse_args()

    config_root = args.config_root
    trajectory_root = args.trajectory_root
    output_path = args.output_path

    configs = {}
    trajectories = {}

    for file in os.listdir(config_root):
        if file.endswith(".jsonl"):
            data = read_jsonl(os.path.join(config_root, file))
            for task in data:
                if task["task_id"] in configs:
                    logger.warn(f"Duplicate task_id {task['task_id']} in {file}.")
                    continue
                configs[task["task_id"]] = task

    config_info = extract_info_from_config(configs=configs)
    df_config = pd.DataFrame(config_info).T

    if trajectory_root:
        for file in os.listdir(trajectory_root):
            if file.endswith(".jsonl"):
                data = read_jsonl(os.path.join(trajectory_root, file))
                for task in data:
                    if task["task_id"] in trajectories:
                        logger.warn(f"Duplicate task_id {task['task_id']} in {file}.")
                        continue
                    trajectories[task["task_id"]] = task

        trajectory_info = extract_info_from_trajectory(trajectories=trajectories)
        df_trajectory = pd.DataFrame(trajectory_info).T

        df = pd.merge(df_config, df_trajectory, on="task_id", how="outer")

    df.to_csv(output_path, index=False)
    print(f"Output statistics to {output_path}.")
