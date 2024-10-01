from pathlib import Path

import fire
import matplotlib.pyplot as plt
import numpy as np

from agent_studio.utils.json_utils import load_result, make_report, make_report2


class Stat:
    def basic_stat(
        self,
        model: str,
        task_dir: str = "eval_online_benchmarks/tasks",
        agent: str = "direct",
    ):
        """Get basic statistics of the given model results"""
        make_report2(Path(task_dir), Path(f"logs/{model}/{agent}"))

    def full_stat(
        self,
        model: str,
        task_dir: str = "eval_online_benchmarks/tasks",
        agent: str = "direct",
    ):
        """
        Get full statistics of the given model results,
        including success task ids, total task ids...
        """
        report = make_report(Path(task_dir), Path(f"logs/{model}/{agent}"))
        for k, v in report.items():
            print(f"{k}: {v}")

    def failure_stat(
        self,
        model: str,
        task_dir: str = "eval_online_benchmarks/tasks",
        agent: str = "direct",
    ):
        """Calculate failure reason"""
        report = make_report(Path(task_dir), Path(f"logs/{model}/{agent}"))

        reason_count = {}
        for task_id in report["fail_task_ids"]:
            result_dir = Path(f"logs/{model}/{agent}/{task_id}")
            result = load_result(result_dir)
            if "force_stop_reason" in result.trajectory[-1].result:
                reason_count.setdefault(
                    result.trajectory[-1].result["force_stop_reason"], 0
                )
                reason_count[result.trajectory[-1].result["force_stop_reason"]] += 1
            else:
                reason_count.setdefault("Wrong Answer", 0)
                reason_count["Wrong Answer"] += 1
        reason_count = sorted(reason_count.items(), key=lambda x: x[1], reverse=True)

        for reason, count in reason_count:
            print(f"{reason}: {count}")

    def time_stat(
        self,
        model: str,
        visual: bool = True,
        task_dir: str = "eval_online_benchmarks/tasks",
        agent: str = "direct",
    ):
        """Calculate time cost"""
        report = make_report(Path(task_dir), Path(f"logs/{model}/{agent}"))

        time_list = []
        for task_id in report["total_task_ids"]:
            result_dir = Path(f"logs/{model}/{agent}/{task_id}")
            try:
                result = load_result(result_dir)
                time_list.append(result.time_cost)
            except Exception:
                pass

        print(f"Mean: {np.mean(time_list)}")
        print(f"Median: {np.median(time_list)}")
        print(f"Max: {np.max(time_list)}")
        print(f"Min: {np.min(time_list)}")
        print(f"std: {np.std(time_list)}")
        if visual:
            plt.hist(time_list, bins=80, edgecolor="black")
            plt.show()

    def traj_length_stat(
        self,
        model: str,
        visual: bool = True,
        task_dir: str = "eval_online_benchmarks/tasks",
        agent: str = "direct",
    ):
        """Calculate trajectory length"""
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
            plt.hist(
                length_list, bins=range(1, max(max(length_list), 10)), edgecolor="black"
            )
            plt.show()

    def exit_stat(
        self,
        model: str,
        task_dir: str = "eval_online_benchmarks/tasks",
        agent: str = "direct",
    ):
        """Calculate active exit rate"""
        report = make_report(Path(task_dir), Path(f"logs/{model}/{agent}"))

        active_exit_count = 0
        total_exit_count = 0
        for task_id in report["total_task_ids"]:
            result_dir = Path(f"logs/{model}/{agent}/{task_id}")
            result = load_result(result_dir)
            total_exit_count += 1
            if "force_stop_reason" not in result.trajectory[-1].result:
                active_exit_count += 1
        print(f"Active Exit Rate: {active_exit_count / total_exit_count}")


if __name__ == "__main__":
    fire.Fire(Stat)
