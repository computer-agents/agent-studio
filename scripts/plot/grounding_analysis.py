import json
import os

import matplotlib
import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from agent_studio.utils.json_utils import read_jsonl

matplotlib.rcParams["font.family"] = "Helvetica"
matplotlib.rcParams["mathtext.fontset"] = "cm"


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
        # "click_type_match": f"{click_type_match} / {total_tasks} = "
        # f"{round(click_type_match / total_tasks * 100, 1)}",
        # "location_match": f"{location_match} / {total_tasks} = "
        # f"{round(location_match / total_tasks * 100, 1)}",
        "click_type_match": click_type_match,
        "location_match": location_match,
        "total_tokens": total_tokens,
        "box_success_pairs": box_success_pairs,
    }


def plot_box_success_pairs(box_success_pairs):
    pdf = PdfPages("figures/success_vs_size.pdf")
    sns_colors = sns.color_palette("Paired", 8)
    alpha = 0.5

    # Splitting the data based on score
    x1 = [size for size, score in box_success_pairs if score == 0]
    x2 = [size for size, score in box_success_pairs if score == 1]
    x1 = np.log10(np.array(x1))
    x2 = np.log10(np.array(x2))

    # Plot
    fig, ax = plt.subplots(figsize=(9, 6.5))

    sns.kdeplot(x1, color=sns_colors[1], label="Fail", fill=True, alpha=alpha)
    sns.kdeplot(x2, color=sns_colors[3], label="Success", fill=True, alpha=alpha)

    ax.set_xlabel("Element Area (pixels)", fontsize=28)
    ax.set_ylabel("Frequency", fontsize=28)
    ax.tick_params(axis="x", length=10, color="grey")
    ax.tick_params(axis="y", length=10, color="grey")
    ax.legend(loc="upper right", fontsize=28)

    locs = [0, 2, 4, 6, 8]
    plt.xticks(
        locs,
        [r"$10^{%d}$" % loc for loc in locs],
        ha="center",
        fontsize=30,
        fontweight="bold",
    )
    locs = [0.0, 0.2, 0.4, 0.6]
    plt.yticks(
        locs,
        [r"$%d$" % loc for loc in [0, 20, 40, 60]],
        fontsize=30,
        fontweight="bold",
    )

    plt.tight_layout()
    plt.show()
    pdf.savefig(fig)
    pdf.close()


def plot_match(data):
    pdf = PdfPages("figures/match.pdf")
    sns_colors = sns.color_palette("Paired", 8)
    alpha = 0.5

    # Extracting data for plotting
    names = []
    location_matches = []
    click_type_matches = []
    for k, v in data.items():
        if k == "gpt-4-vision-preview":
            names.append("GPT-4V")
        elif k == "claude-3-sonnet-20240229":
            names.append("Claude-3 Sonnet")
        elif k == "Qwen-VL-Chat":
            names.append("Qwen-VL")
        elif k == "gemini-pro-vision":
            names.append("Gemini-Pro")
        else:
            continue
        click_type_matches.append(v["click_type_match"])
        location_matches.append(v["location_match"])

    # sort three by click type match in descending order
    names = [x for _, x in sorted(zip(click_type_matches, names), reverse=True)]
    location_matches = [
        x for _, x in sorted(zip(click_type_matches, location_matches), reverse=True)
    ]
    click_type_matches = sorted(click_type_matches, reverse=True)

    # Creating the plot
    fig, ax = plt.subplots(figsize=(7.5, 5))

    index = np.arange(len(names))
    bar_width = 0.3

    ax.bar(
        index - bar_width / 2,
        location_matches,
        bar_width,
        label="Location Match",
        color=sns_colors[1],
        alpha=alpha,
    )
    ax.bar(
        index + bar_width / 2,
        click_type_matches,
        bar_width,
        label="Click Type Match",
        color=sns_colors[3],
        alpha=alpha,
    )

    # ax.set_xlabel("Model", fontsize=31)
    # ax.set_ylabel("Scores", fontsize=31)
    # ax.set_title("Location and Click Type Match Scores by Model", fontsize=33, pad=20)
    ax.set_xticks(index + bar_width / 2)
    ax.set_xticklabels(names, ha="right")
    ax.tick_params(axis="x", length=10, color="grey")
    ax.tick_params(axis="y", length=10, color="grey")
    # ax.legend(loc="upper right", fontsize=28, ncol=2)
    ax.legend(
        loc="upper center",  # Position the legend above the plot
        fontsize=20,
        ncol=2,  # Keep the legend horizontal with 2 columns
        bbox_to_anchor=(
            0.5,
            1.2,
        ),  # Center it horizontally (0.5), and move it upwards (1.15)
        frameon=False,  # Optional: Removes the legend frame for a cleaner look
    )

    locs = [0, 1, 2, 3]
    plt.xticks(
        locs,
        names,
        ha="center",
        fontsize=20,
        fontweight="bold",
        rotation=15,
    )
    locs = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    plt.yticks(
        locs,
        [r"$%d$" % loc for loc in [0, 20, 40, 60, 80, 100]],
        fontsize=30,
        fontweight="bold",
    )

    plt.tight_layout()
    plt.show()
    pdf.savefig(fig)
    pdf.close()


def main():
    folder_path = "grounding_results"
    results = {}
    box_success_pairs = []

    # iterate over the folders
    total_tokens = 0
    for model_folder in os.listdir(folder_path):
        total_tasks = 0
        location_match = 0
        click_type_match = 0
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
                location_match += app_results["location_match"]
                click_type_match += app_results["click_type_match"]
                if model_folder == "claude-3-sonnet-20240229":
                    box_success_pairs += app_results["box_success_pairs"]

            # model_results[os_folder] = os_results
            # model_results["total_tasks"] = total_tasks
            model_results["location_match"] = location_match / total_tasks
            model_results["click_type_match"] = click_type_match / total_tasks
        results[model_folder] = model_results

    print(json.dumps(results, indent=4))
    print("Total tokens:", total_tokens)
    # plot_box_success_pairs(box_success_pairs)
    plot_match(results)


if __name__ == "__main__":
    main()
