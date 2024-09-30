import fire
from agent_studio.utils.json_utils import make_report, make_report2, load_result
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


class Stat:
    def basic_stat(self, model: str, task_dir: str = "eval_online_benchmarks/tasks", agent: str = "direct"):
        make_report2(Path(task_dir), Path(f"logs/{model}/{agent}"))

    def full_stat(self, model: str, task_dir: str = "eval_online_benchmarks/tasks", agent: str = "direct"):
        report = make_report(Path(task_dir), Path(f"logs/{model}/{agent}"))
        for k, v in report.items():
            print(f"{k}: {v}")

    def failure_stat(self, model: str, task_dir: str = "eval_online_benchmarks/tasks", agent: str = "direct"):
        report = make_report(Path(task_dir), Path(f"logs/{model}/{agent}"))

        reason_count = {}
        for task_id in report["fail_task_ids"]:
            result_dir = Path(f"logs/{model}/{agent}/{task_id}")
            result = load_result(result_dir)
            if "content" in result.trajectory[-1].result:
                reason_count.setdefault(result.trajectory[-1].result["content"], 0)
                reason_count[result.trajectory[-1].result["content"]] += 1
            else:
                reason_count.setdefault("Wrong Answer", 0)
                reason_count["Wrong Answer"] += 1
        reason_count = sorted(reason_count.items(), key=lambda x: x[1], reverse=True)

        for reason, count in reason_count:
            print(f"{reason}: {count}")

    def traj_length_stat(self, model: str, visual: bool = True, task_dir: str = "eval_online_benchmarks/tasks", agent: str = "direct"):
        report = make_report(Path(task_dir), Path(f"logs/{model}/{agent}"))

        length_list = []
        for task_id in report["total_task_ids"]:
            result_dir = Path(f"logs/{model}/{agent}/{task_id}")
            result = load_result(result_dir)
            length_list.append(len(result.trajectory))

        print(f"Mean: {np.mean(length_list)}")
        print(f"Median: {np.median(length_list)}")
        print(f"Max: {np.max(length_list)}")
        print(f"Min: {np.min(length_list)}")
        print(f"std: {np.std(length_list)}")
        if visual:
            plt.hist(length_list, bins=range(
                1, max(max(length_list), 10)), edgecolor="black")
            plt.show()


if __name__ == "__main__":
    fire.Fire(Stat)
