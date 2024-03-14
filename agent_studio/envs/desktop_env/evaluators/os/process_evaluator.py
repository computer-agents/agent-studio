import logging
import os
import re
import subprocess
import time

import psutil

from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from agent_studio.utils.human_utils import confirm_action

logger = logging.getLogger(__name__)


def find_procs_by_name(name: str) -> list[psutil.Process]:
    ls = []
    template = re.compile(name)
    for p in psutil.process_iter():
        name_, exe = "", ""
        try:
            name_ = p.name()
            exe = p.exe()
        except (psutil.AccessDenied, psutil.ZombieProcess, psutil.NoSuchProcess):
            continue
        if template.match(name_) or template.match(os.path.basename(exe)):
            ls.append(p)
    return ls


class ProcessEvaluator(Evaluator):
    name: str = "process"

    @evaluation_handler("match_process")
    def match_process(self, name: str) -> None:
        """
        Check if a process with the given name is running. \
                Can be a regex pattern.

        Args:
            name (str): Name of the process to check.

        Raises:
            FeedbackException: If the process is not found.
        """
        procs = find_procs_by_name(name)
        if len(procs) == 0:
            raise FeedbackException(f"Process with name {name} not found.")

    @reset_handler("create_process")
    def create_process(self, cmd: list[str], wait_for: str | None) -> None:
        """
        Create a process with the given command.

        Args:
            cmd (list[str]): Command to create the process.
            wait_for (str | None): Name of the process to wait for. \
                Can be a regex pattern. \
                If None, the function will not wait for any process.

        Raises:
            FeedbackException: If the process creation fails.
        """
        subprocess.Popen(cmd)
        if wait_for is not None:
            while len(find_procs_by_name(wait_for)) == 0:
                time.sleep(0.5)

    @reset_handler("pkill_by_name")
    def pkill_by_name(self, name: str) -> None:
        """
        Kill all processes with the given name.

        Args:
            name (str): Name pattern of the process to kill. \
                Can be a regex pattern.
        """

        def _kill_processes(procs: list[psutil.Process]) -> None:
            for proc in procs:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass

        proc_list = find_procs_by_name(name)
        message: str = f"Killing processes: \n"
        for proc in proc_list:
            message += f"{proc}\n"
        if len(proc_list) > 0:
            confirm_action(message)(_kill_processes)(proc_list)
