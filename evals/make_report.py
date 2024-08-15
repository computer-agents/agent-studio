import argparse
import os

import numpy as np
from common import GROUND_UI_HTML_JINJA, HTML_JINJA, jinja_env, make_report

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


def compute_f1(results):
    pos = 0
    neg = 0
    tp = 0
    fp = 0
    tn = 0
    fn = 0
    for result in results:
        if result["ref_answer"]:
            pos += 1
            if result["score"] == 1:
                tp += 1
            else:
                fn += 1
        else:
            neg += 1
            if result["score"] == 1:
                fp += 1
            else:
                tn += 1
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    # precision = tp / (tp + fp)
    # recall = tp / (tp + fn)
    # f1 = 2 * precision * recall / (precision + recall)

    return {
        "accuracy": accuracy,
        # "precision": precision,
        # "recall": recall,
        # "f1": f1,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result_path", type=str)
    parser.add_argument("--image_path", type=str)
    args = parser.parse_args()

    results = read_jsonl(args.result_path)
    htmls = []
    if "gui_grounding" in args.result_path:
        metrics = {}
        for prefix in ["", "web_", "desktop_", "mobile_"]:
            metrics[f"{prefix}score"] = []
        metrics["input_tokens"] = []
        metrics["output_tokens"] = []

        for result in results:
            for k in ["score", "input_tokens", "output_tokens"]:
                metrics[k].append(result[k])

            for platform in ["web", "desktop", "mobile"]:
                if result["platform"] == platform:
                    metrics[f"{platform}_score"].append(result["score"])

            if len(htmls) < 3:
                prompt = result["prompt"]
                for i, p in enumerate(prompt):
                    if isinstance(p["content"], str):
                        if p["content"].endswith((".png", ".jpg", ".jpeg")):
                            prompt[i]["content"] = os.path.join(
                                args.image_path, p["content"]
                            )
                html = jinja_env.from_string(GROUND_UI_HTML_JINJA).render(
                    prompt_messages=prompt,
                    next_message=dict(content=result["response"], role="assistant"),
                    score=result["score"],
                    correct_bbox=result["bbox"],
                    pred_coord=result["parsed_action"],
                )
                htmls.append(html)

    elif "success_detection" in args.result_path:
        metrics = {}
        for metric in ["accuracy", "precision", "recall", "f1"]:
            for prefix in [
                "",
                "web_",
                "desktop_",
                "mobile_",
                "mind2web_",
                "aitw_",
                "vwa_",
                "agent_studio_",
            ]:
                metrics[f"{prefix}{metric}"] = []
        metrics["input_tokens"] = []
        metrics["output_tokens"] = []

        web_results = []
        desktop_results = []
        mobile_results = []
        mind2web_results = []
        aitw_results = []
        vwa_results = []
        agent_studio_results = []
        for result in results:
            if result["platform"] == "web":
                web_results.append(result)
            elif result["platform"] == "desktop":
                desktop_results.append(result)
            elif result["platform"] == "mobile":
                mobile_results.append(result)

            if "mind2web" in result["source"]:
                mind2web_results.append(result)
            elif "aitw" in result["source"]:
                aitw_results.append(result)
            elif "vwa" in result["source"]:
                vwa_results.append(result)
            elif "agent-studio" in result["source"]:
                agent_studio_results.append(result)

        stats = compute_f1(results)
        for k, v in stats.items():
            metrics[k].append(v)

        for res in [web_results, desktop_results, mobile_results]:
            stats = compute_f1(res)
            for k, v in stats.items():
                metrics[f"{res[0]['platform']}_{k}"].append(v)

        for res in [mind2web_results, aitw_results, vwa_results, agent_studio_results]:
            stats = compute_f1(res)
            if "mind2web" in res[0]["source"]:
                source = "mind2web"
            elif "aitw" in res[0]["source"]:
                source = "aitw"
            elif "vwa" in res[0]["source"]:
                source = "vwa"
            elif "agent-studio" in res[0]["source"]:
                source = "agent_studio"
            for k, v in stats.items():
                metrics[f"{source}_{k}"].append(v)

    elif "idm" in args.result_path:
        metrics = {}
        for prefix in ["", "web_", "desktop_", "mobile_", "mind2web_", "aitw_", "vwa_"]:
            metrics[f"{prefix}score"] = []
        metrics["input_tokens"] = []
        metrics["output_tokens"] = []

        for result in results:
            if "n2n" in args.result_path:
                metrics["score"].append(result["score"] / len(result["ref_answer"]))
            else:
                metrics["score"].append(result["score"])

            for k in ["input_tokens", "output_tokens"]:
                metrics[k].append(result[k])

            for platform in ["web", "desktop", "mobile"]:
                if result["platform"] == platform:
                    if "n2n" in args.result_path:
                        metrics[f"{platform}_score"].append(
                            result["score"] / len(result["ref_answer"])
                        )
                    else:
                        metrics[f"{platform}_score"].append(result["score"])

            for source in ["mind2web", "aitw", "vwa"]:
                if source in result["source"]:
                    if "n2n" in args.result_path:
                        metrics[f"{source}_score"].append(
                            result["score"] / len(result["ref_answer"])
                        )
                    else:
                        metrics[f"{source}_score"].append(result["score"])

            if len(htmls) < 3:
                prompt = result["prompt"]
                for i, p in enumerate(prompt):
                    if isinstance(p["content"], str):
                        if p["content"].endswith((".png", ".jpg", ".jpeg")):
                            prompt[i]["content"] = os.path.join(
                                args.image_path, p["content"]
                            )

                kwargs = dict(
                    prompt_messages=prompt,
                    next_message=dict(content=result["response"], role="assistant"),
                    score=result["score"],
                    parsed_answer=result["parsed_answer"],
                    ref_answer=result["ref_answer"],
                )
                if "n2n" in args.result_path:
                    kwargs["score"] = {
                        "score": result["score"],
                        "edit_distance": result["edit_distance"],
                    }
                html = jinja_env.from_string(HTML_JINJA).render(**kwargs)
                htmls.append(html)

    final_metrics = {}
    for k, v in metrics.items():
        stats = ("mean",) if "token" not in k else ("sum",)
        for stat in stats:
            key = k if stat == "mean" else f"{k}:{stat}"
            final_metrics[key] = round(float(compute_stat(v, stat)), 3)
    print(f"Metrics: {final_metrics}")

    if len(htmls) > 0:
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
