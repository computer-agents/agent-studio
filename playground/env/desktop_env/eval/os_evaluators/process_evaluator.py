import os
import re
from typing import Any
import psutil
import logging

from playground.env.desktop_env.eval.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)

logger = logging.getLogger(__name__)


class ProcessEvaluator(Evaluator):
    name: str = "process"

    @staticmethod
    def find_procs_by_name(name: str) -> list[psutil.Process]:
        ls = []
        template = re.compile(name)
        for p in psutil.process_iter():
            name_, exe = "", ""
            try:
                name_ = p.name()
                exe = p.exe()
            except (
                psutil.AccessDenied,
                psutil.ZombieProcess,
                psutil.NoSuchProcess
            ):
                continue
            if template.match(name_) or template.match(os.path.basename(exe)):
                ls.append(p)
        return ls

    def execute(self, steps: list[dict[str, dict[str, Any]]]) -> bool:
        try:
            for step in steps:
                for action, params in step.items():
                    match action:
                        case "create_process":
                            cmd: list[str] = params["cmd"]
                            psutil.Popen(cmd)
                        case "pkill_by_name":
                            process_name: str = params["name"]
                            for proc in self.find_procs_by_name(process_name):
                                proc.kill()
                        case _:
                            raise Exception(f"Action {action} not found")
        except Exception as e:
            logger.error(f"Error executing process evaluator: {e}")
            return False
        return True

    def __call__(self) -> float:
        score = 1.0
        for approach, value in self.reference_answer.items():
            match approach:
                case "match_process":
                    process_name: str = value["name"]
                    procs = self.find_procs_by_name(process_name)
                    if len(procs) == 0:
                        score = 0.0
                        break
                case _:
                    raise Exception(f"Approach {approach} not found")

        return score
