import argparse
import numpy as np

from common import (
    HTML_JINJA,
    jinja_env,
    make_report,
)
from gui_grounding_eval import format_gui_grounding_prompt

from agent_studio.utils.json_utils import read_jsonl


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_path", type=str)

    return parser


def compute_stat(values: list, stat: str):
    if stat == "mean":
        return np.mean(values)
    elif stat == "std":
        return np.std(values)
    elif stat == "min":
        return np.min(values)
    elif stat == "max":
        return np.max(values)
    else:
        raise ValueError(f"Unknown {stat =}")


def main():
    parser = create_parser()
    args = parser.parse_args()

    results = read_jsonl(args.result_path)
    metrics = {
        "score": [],
        "input_tokens": [],
        "output_tokens": [],
    }
    htmls = []
    for result in results:
        for k in metrics:
            metrics[k].append(result[k])
        prompt = format_gui_grounding_prompt(result["instruction"], result["image_path"])
        print(result)
        html = jinja_env.from_string(HTML_JINJA).render(
            prompt_messages=prompt,
            next_message=result["response"],
            score=result["score"],
            correct_bbox=result["bbox"],
            pred_coord=result["parsed_action"],
        )
        htmls.append(html)

    final_metrics = {}
    for k, v in metrics.items():
        stats = ("mean",)
        for stat in stats:
            key = k if stat == "mean" else f"{k}:{stat}"
            final_metrics[key] = float(compute_stat(v, stat))

    report_filename = args.result_path.replace(".jsonl", ".html")
    print(f"Writing report to {report_filename}")
    with open(report_filename, "w") as fh:
        fh.write(make_report(
            score=final_metrics.pop("score", None),
            metrics=final_metrics,
            htmls=htmls[:10],  # Only show the first 10 examples
        ))


if __name__ == "__main__":
    main()
