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
from playground.utils.human_utils import confirm_action

logger = logging.getLogger(__name__)


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

class ProcessEvaluator(Evaluator):
    name: str = "process"

    @evaluation_handler("match_process")
    def match_process(self, name: str) -> None:
        """
        Check if a process with the given name is running.

        Args:
            name (str): Name of the process to check.

        Raises:
            FeedbackException: If the process is not found.
        """
        procs = find_procs_by_name(name)
        if len(procs) == 0:
            raise FeedbackException(f"Process with name {name} not found.")

    @reset_handler("create_process")
    def create_process(self, cmd: list[str]) -> None:
        """
        Create a process with the given command.

        Args:
            cmd (list[str]): Command to create the process.

        Raises:
            FeedbackException: If the process creation fails.
        """
        psutil.Popen(cmd)

    @reset_handler("pkill_by_name")
    def pkill_by_name(self, name: str) -> None:
        """
        Kill all processes with the given name.

        Args:
            name (str): Name pattern of the process to kill.\
                Can be a regex pattern.

        Raises:
            FeedbackException: If the process is not found.
        """
        @confirm_action
        def _kill_process(proc: psutil.Process) -> None:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass

        for proc in find_procs_by_name(name):
            print("Killing process: ", proc)
            _kill_process(proc)