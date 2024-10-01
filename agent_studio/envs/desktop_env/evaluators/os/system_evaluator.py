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

    @reset_handler("exec")
    @evaluation_handler("exec")
    def exec(self, command: str) -> None:
        os.system(command)

    @reset_handler("sleep")
    @evaluation_handler("sleep")
    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    @evaluation_handler("diff")
    def diff_rst(self, file1: str, file2: str) -> None:
        if not os.path.exists(file1):
            raise FeedbackException(f"File {file1} does not exist")
        if not os.path.exists(file2):
            raise FeedbackException(f"File {file2} does not exist")
        result = subprocess.run(
            ["diff", file1, file2], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if result.returncode == 1:
            raise FeedbackException(f"Files {file1} and {file2} are different")
