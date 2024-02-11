import logging
from typing import Any

from playground.env.desktop_env.eval.evaluator import Evaluator, FeedBackException

logger = logging.getLogger(__name__)


class QAEvaluator(Evaluator):
    name: str = "qa"

    def string_match(self, response: str, answer: str) -> None:
        if response != answer:
            raise FeedBackException(f"The answer is incorrect: {response}.")

    def __init__(
        self,
        eval_procedure: list[dict[str, dict[str, Any]]],
        reset_procedure: list[dict[str, dict[str, Any]]],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.evaluation_handlers = {
            "string_match": self.string_match,
        }
