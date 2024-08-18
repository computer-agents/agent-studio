import numpy as np
from bs4 import BeautifulSoup


def parse_html_file(file_path):
    """Parse the HTML file and extract metrics as a dictionary."""
    with open(file_path, "r") as file:
        soup = BeautifulSoup(file, "html.parser")

    metrics = {}
    table = soup.find("table")
    rows = table.find_all("tr")[1:]  # Skip the header row

    for row in rows:
        cells = row.find_all("td")
        metric_name = cells[0].text.strip()
        value = cells[1].text.strip()
        metrics[metric_name] = float(value) if value != "nan" else np.nan

    return metrics


def format_value(value, max_value):
    """Format value for LaTeX, bolding the maximum values."""
    if np.isnan(value):
        return ""
    if value == max_value:
        return r"\textbf{" + f"{value:.1f}" + "}"
    return f"{value:.1f}"


def generate_latex_table(models_data):
    """Generate LaTeX table from the collected data."""
    latex = r"\begin{tabular}{c|cccc|cccc}" + "\n"
    latex += r"\hline" + "\n"
    latex += (
        r"\multirow{2}{*}{\textbf{Model}} & \multicolumn{4}{c|}{\textbf{Observation-Action Pairs}} & \multicolumn{4}{c}{\textbf{Only Observations}} \\"  # noqa: E501
        + "\n"
    )
    latex += (
        r"& \textbf{Web} & \textbf{Desktop} & \textbf{Mobile} & \textbf{Total} & \textbf{Web} & \textbf{Desktop} & \textbf{Mobile} & \textbf{Total} \\"  # noqa: E501
        + "\n"
    )
    latex += r"\hline" + "\n"

    for category in ["Accuracy", "F1 Score", "Precision", "Recall"]:
        latex += r"\multicolumn{9}{c}{\textbf{" + category + r"}} \\" + "\n"
        latex += r"\hline" + "\n"
        if category == "F1 Score":
            category = "f1"

        # Find the maximum values for each metric across all models
        max_values_obs_act = {
            f"web_{category.lower()}": -np.inf,
            f"desktop_{category.lower()}": -np.inf,
            f"mobile_{category.lower()}": -np.inf,
            f"total_{category.lower()}": -np.inf,
        }
        max_values_obs_only = {
            f"web_{category.lower()}": -np.inf,
            f"desktop_{category.lower()}": -np.inf,
            f"mobile_{category.lower()}": -np.inf,
            f"total_{category.lower()}": -np.inf,
        }

        for model in models_data:
            for metric in max_values_obs_act.keys():
                if (
                    not np.isnan(model["obs_act"][metric])
                    and model["obs_act"][metric] > max_values_obs_act[metric]
                ):
                    max_values_obs_act[metric] = model["obs_act"][metric]
                if (
                    not np.isnan(model["obs_only"][metric])
                    and model["obs_only"][metric] > max_values_obs_only[metric]
                ):
                    max_values_obs_only[metric] = model["obs_only"][metric]

        # Sort models based on the total scores in Observation-Action Pairs
        sorted_models = sorted(
            models_data,
            key=lambda x: x["obs_act"][f"total_{category.lower()}"],
            reverse=True,
        )

        for model_data in sorted_models:
            name = model_data["name"]
            obs_act_data = model_data["obs_act"]
            obs_only_data = model_data["obs_only"]

            latex += f"{name} & "
            latex += " & ".join(
                format_value(obs_act_data[metric], max_values_obs_act[metric])
                for metric in [
                    f"web_{category.lower()}",
                    f"desktop_{category.lower()}",
                    f"mobile_{category.lower()}",
                    f"total_{category.lower()}",
                ]
            )
            latex += " & "
            latex += " & ".join(
                format_value(obs_only_data[metric], max_values_obs_only[metric])
                for metric in [
                    f"web_{category.lower()}",
                    f"desktop_{category.lower()}",
                    f"mobile_{category.lower()}",
                    f"total_{category.lower()}",
                ]
            )
            latex += r"\\" + "\n"

        latex += r"\hline" + "\n"

    latex += r"\end{tabular}" + "\n"
    return latex


def process_model(file_paths, name):
    """Process the HTML files and return the relevant data."""
    obs_act_metrics = parse_html_file(file_paths["obs_act"])
    obs_only_metrics = parse_html_file(file_paths["obs_only"])

    return {
        "name": name,
        "obs_act": {
            "web_accuracy": obs_act_metrics.get("web_accuracy", 0.0) * 100,
            "desktop_accuracy": obs_act_metrics.get("desktop_accuracy", 0.0) * 100,
            "mobile_accuracy": obs_act_metrics.get("mobile_accuracy", 0.0) * 100,
            "total_accuracy": obs_act_metrics.get("accuracy", 0.0) * 100,
            "web_f1": obs_act_metrics.get("web_f1", 0.0) * 100,
            "desktop_f1": obs_act_metrics.get("desktop_f1", 0.0) * 100,
            "mobile_f1": obs_act_metrics.get("mobile_f1", 0.0) * 100,
            "total_f1": obs_act_metrics.get("f1", 0.0) * 100,
            "web_precision": obs_act_metrics.get("web_precision", 0.0) * 100,
            "desktop_precision": obs_act_metrics.get("desktop_precision", 0.0) * 100,
            "mobile_precision": obs_act_metrics.get("mobile_precision", 0.0) * 100,
            "total_precision": obs_act_metrics.get("precision", 0.0) * 100,
            "web_recall": obs_act_metrics.get("web_recall", 0.0) * 100,
            "desktop_recall": obs_act_metrics.get("desktop_recall", 0.0) * 100,
            "mobile_recall": obs_act_metrics.get("mobile_recall", 0.0) * 100,
            "total_recall": obs_act_metrics.get("recall", 0.0) * 100,
        },
        "obs_only": {
            "web_accuracy": obs_only_metrics.get("web_accuracy", 0.0) * 100,
            "desktop_accuracy": obs_only_metrics.get("desktop_accuracy", 0.0) * 100,
            "mobile_accuracy": obs_only_metrics.get("mobile_accuracy", 0.0) * 100,
            "total_accuracy": obs_only_metrics.get("accuracy", 0.0) * 100,
            "web_f1": obs_only_metrics.get("web_f1", 0.0) * 100,
            "desktop_f1": obs_only_metrics.get("desktop_f1", 0.0) * 100,
            "mobile_f1": obs_only_metrics.get("mobile_f1", 0.0) * 100,
            "total_f1": obs_only_metrics.get("f1", 0.0) * 100,
            "web_precision": obs_only_metrics.get("web_precision", 0.0) * 100,
            "desktop_precision": obs_only_metrics.get("desktop_precision", 0.0) * 100,
            "mobile_precision": obs_only_metrics.get("mobile_precision", 0.0) * 100,
            "total_precision": obs_only_metrics.get("precision", 0.0) * 100,
            "web_recall": obs_only_metrics.get("web_recall", 0.0) * 100,
            "desktop_recall": obs_only_metrics.get("desktop_recall", 0.0) * 100,
            "mobile_recall": obs_only_metrics.get("mobile_recall", 0.0) * 100,
            "total_recall": obs_only_metrics.get("recall", 0.0) * 100,
        },
    }


def main():
    # Define the HTML file paths for each model
    models = {
        "Gemini 1.5 Flash": {
            "obs_act": "results/success_detection/gemini-1.5-flash-001.html",
            "obs_only": "results/success_detection_actionless/gemini-1.5-flash-001.html",  # noqa: E501
        },
        "Gemini 1.5 Pro": {
            "obs_act": "results/success_detection/gemini-1.5-pro-001.html",
            "obs_only": "results/success_detection_actionless/gemini-1.5-pro-001.html",  # noqa: E501
        },
        "Claude 3.5 Sonnet": {
            "obs_act": "results/success_detection/claude-3-5-sonnet-20240620.html",
            "obs_only": "results/success_detection_actionless/claude-3-5-sonnet-20240620.html",  # noqa: E501
        },
        "GPT-4o (0513)": {
            "obs_act": "results/success_detection/gpt-4o-2024-05-13.html",
            "obs_only": "results/success_detection_actionless/gpt-4o-2024-05-13.html",  # noqa: E501
        },
        "Qwen-VL-Chat": {
            "obs_act": "results/success_detection/Qwen-VL-Chat.html",
            "obs_only": "results/success_detection_actionless/Qwen-VL-Chat.html",
        },
    }

    models_data = [
        process_model(file_paths, model_name)
        for model_name, file_paths in models.items()
    ]

    # Generate LaTeX table
    latex_table = generate_latex_table(models_data)
    print(latex_table)


if __name__ == "__main__":
    main()
