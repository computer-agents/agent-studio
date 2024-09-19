import logging
import os
import subprocess
import time

from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)

logger = logging.getLogger(__name__)


class SystemEvaluator(Evaluator):
    name: str = "system"

    @reset_handler("sleep")
    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    @reset_handler("exec")
    def exec(self, command: str) -> None:
        os.system(command)

    @evaluation_handler("sleep")
    def sleep_eval(self, seconds: float) -> None:
        time.sleep(seconds)

    @reset_handler("exec")
    def exec_rst(self, command: str) -> None:
        os.system(command)

    @evaluation_handler("diff")
    def diff_rst(self, file1: str, file2: str) -> None:
        result = subprocess.run(
            ["diff", file1, file2], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.returncode == 1:
            raise FeedbackException(f"Files {file1} and {file2} are different")
