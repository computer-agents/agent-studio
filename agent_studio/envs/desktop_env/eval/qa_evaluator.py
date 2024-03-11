import logging
from typing import Any

from agent_studio.envs.desktop_env.eval.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
)

logger = logging.getLogger(__name__)


class QAEvaluator(Evaluator):
    name: str = "qa"

    def __init__(
        self,
        eval_procedure: list[dict[str, dict[str, Any]]],
        reset_procedure: list[dict[str, dict[str, Any]]],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )

    @evaluation_handler("string_match")
    def string_match(self, response: str, answer: str) -> None:
        if response != answer:
            raise FeedbackException(f"The answer is incorrect: {response}.")
