import argparse
import os

import numpy as np
from common import HTML_JINJA, jinja_env, make_report
from eval_gui_grounding import format_gui_grounding_prompt
from tqdm import tqdm

from agent_studio.utils.json_utils import read_jsonl


def compute_stat(values: list, stat: str):
    if stat == "mean":
        return np.mean(values)
    elif stat == "std":
        return np.std(values)
    elif stat == "min":
        return np.min(values)
    elif stat == "max":
        return np.max(values)
    elif stat == "sum":
        return np.sum(values)
    else:
        raise ValueError(f"Unknown {stat =}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_path", type=str)
    parser.add_argument("--image_path", type=str)
    args = parser.parse_args()

    results = read_jsonl(args.result_path)
    metrics = {
        "score": [],
        "web_score": [],
        "desktop_score": [],
        "mobile_score": [],
        "input_tokens": [],
        "output_tokens": [],
    }
    htmls = []
    for result in tqdm(results):
        for k in ["score", "input_tokens", "output_tokens"]:
            metrics[k].append(result[k])
        if result["platform"] == "web":
            metrics["web_score"].append(result["score"])
        elif result["platform"] == "desktop":
            metrics["desktop_score"].append(result["score"])
        elif result["platform"] == "mobile":
            metrics["mobile_score"].append(result["score"])

        if len(htmls) < 3:
            prompt = format_gui_grounding_prompt(
                result["instruction"], os.path.join(args.image_path, result["image"])
            )
            html = jinja_env.from_string(HTML_JINJA).render(
                prompt_messages=prompt,
                next_message=dict(content=result["response"], role="assistant"),
                score=result["score"],
                correct_bbox=result["bbox"],
                pred_coord=result["parsed_action"],
            )
            htmls.append(html)

    final_metrics = {}
    for k, v in metrics.items():
        stats = ("mean",) if "token" not in k else ("sum",)
        for stat in stats:
            key = k if stat == "mean" else f"{k}:{stat}"
            final_metrics[key] = float(compute_stat(v, stat))

    report_filename = args.result_path.replace(".jsonl", ".html")
    print(f"Writing report to {report_filename}")
    with open(report_filename, "w") as fh:
        fh.write(
            make_report(
                score=final_metrics.pop("score", None),
                metrics=final_metrics,
                htmls=htmls,
            )
        )


if __name__ == "__main__":
    main()
