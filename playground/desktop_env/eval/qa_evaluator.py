import logging
from typing import Any

from playground.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class QAEvaluator(Evaluator):
    name: str = "qa"

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        score = 1.0
        for step in steps:
            for action, params in step.items():
                match action:
                    case "string_match":
                        score *= float(params == response)
                    case _:
                        raise Exception(
                            f"Action {action} not supported by Google Drive"
                        )

        return score
