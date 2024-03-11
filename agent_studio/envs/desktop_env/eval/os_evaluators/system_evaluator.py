import logging
import time

from agent_studio.envs.desktop_env.eval.evaluator import Evaluator, reset_handler

logger = logging.getLogger(__name__)


class SystemEvaluator(Evaluator):
    name: str = "system"

    @reset_handler("sleep")
    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)
