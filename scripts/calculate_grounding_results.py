import json
import os

import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt

from agent_studio.utils.json_utils import read_jsonl


def calculate_results(result_dict, task_configs):
    total_tasks = len(result_dict)
    success = 0
    click_type_match = 0
    location_match = 0
    total_tokens = 0

    box_size = {}
    for task_config in task_configs:
        task_id = task_config["task_id"]
        trajectory = task_config["trajectory"]
        annotation = trajectory[0]["annotation"]
        mouse_action = annotation["mouse_action"]
        box_size[task_id] = mouse_action["width"] * mouse_action["height"]

    box_success_pairs = []
    for result in result_dict:
        if result["score"] == 1.0:
            success += 1
        if result["click_type_match"]:
            click_type_match += 1
        if result["location_match"]:
            location_match += 1
        if result["total_tokens"] is not None:
            total_tokens += result["total_tokens"]
        box_success_pairs.append((box_size[result["task_id"]], result["score"]))

    return {
        "total_tasks": total_tasks,
        "success": f"{success} / {total_tasks} = "
        f"{round(success / total_tasks * 100, 1)}",
        "click_type_match": f"{click_type_match} / {total_tasks} = "
        f"{round(click_type_match / total_tasks * 100, 1)}",
        "location_match": f"{location_match} / {total_tasks} = "
        f"{round(location_match / total_tasks * 100, 1)}",
        "total_tokens": total_tokens,
        "box_success_pairs": box_success_pairs,
    }


def main():
    folder_path = "data/grounding_results"
    results = {}
    box_success_pairs = []

    # iterate over the folders
    total_tokens = 0
    for model_folder in os.listdir(folder_path):
        total_tasks = 0
        model_results = {}
        for os_folder in os.listdir(os.path.join(folder_path, model_folder)):
            os_results = {}
            for app_folder in os.listdir(
                os.path.join(folder_path, model_folder, os_folder)
            ):
                result_path = os.path.join(
                    folder_path, model_folder, os_folder, app_folder, "results.jsonl"
                )
                action_path = (
                    result_path.replace("results.jsonl", "actions.jsonl")
                    .replace("grounding_results", "grounding")
                    .replace(f"{model_folder}/", "")
                )
                app_results = calculate_results(
                    read_jsonl(result_path), read_jsonl(action_path)
                )
                os_results[app_folder] = {
                    "total_tasks": app_results["total_tasks"],
                    "success": app_results["success"],
                    "click_type_match": app_results["click_type_match"],
                    "location_match": app_results["location_match"],
                }
                total_tasks += app_results["total_tasks"]
                total_tokens += app_results["total_tokens"]
                box_success_pairs += app_results["box_success_pairs"]

            model_results[os_folder] = os_results
            model_results["total_tasks"] = total_tasks
        results[model_folder] = model_results

    print(json.dumps(results, indent=4))
    print("Total tokens:", total_tokens)

    # # Applying logarithm to x values, avoiding log(0) by adding a small
    # # constant to x values before applying log
    # x = [pair[0] for pair in box_success_pairs]
    # y = [pair[1] for pair in box_success_pairs]
    # log_x = np.log(np.array(x) + 1)

    # # Creating the violin plot with log-transformed x values
    # plt.figure(figsize=(8, 6))
    # sns.violinplot(x=np.array(y), y=log_x)
    # plt.title('Violin Plot of Binary Y Value vs. Log-transformed X Value')
    # plt.xlabel('Binary Y Value')
    # plt.ylabel('Log-transformed X Value')
    # plt.xticks([0, 1], ['0', '1'])
    # plt.tight_layout()
    # plt.show()

    # Splitting the data based on score
    x1 = [size for size, score in box_success_pairs if score == 0]
    x2 = [size for size, score in box_success_pairs if score == 1]
    x1 = np.log(np.array(x1) + 1)
    x2 = np.log(np.array(x2) + 1)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 8))

    sns.histplot(x1, color="blue", label="Score = 0", kde=False, stat="density")
    sns.histplot(x2, color="red", label="Score = 1", kde=False, stat="density")

    ax.set_title("Distribution of Size by Score", fontsize=33, pad=20)
    ax.set_xlabel("Box Size", fontsize=31)
    ax.set_ylabel("Distribution", fontsize=31)
    # ax.set_xscale('log')
    ax.tick_params(axis="x", length=10, color="grey")
    ax.tick_params(axis="y", length=10, color="grey")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
