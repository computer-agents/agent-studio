import json
import os

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
                # box_success_pairs = app_results["box_success_pairs"]

            model_results[os_folder] = os_results
            model_results["total_tasks"] = total_tasks
        results[model_folder] = model_results

    print(json.dumps(results, indent=4))
    print("Total tokens:", total_tokens)


if __name__ == "__main__":
    main()
