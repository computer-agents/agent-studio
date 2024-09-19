import logging
import os
import time

from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    evaluation_handler,
    reset_handler,
)

logger = logging.getLogger(__name__)


class SystemEvaluator(Evaluator):
    name: str = "system"

    @reset_handler("sleep")
    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    @evaluation_handler("sleep")
    def sleep_eval(self, seconds: float) -> None:
        time.sleep(seconds)

    @reset_handler("exec")
    @evaluation_handler("exec")
    def exec_rst(self, command: str) -> None:
        os.system(command)
