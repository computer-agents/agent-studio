import logging

from playground.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class QAEvaluator(Evaluator):
    name: str = "qa"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.evaluation_handlers = {
            "string_match": lambda response, answer: response == answer,
        }
        self.feedback_handlers = {
            "string_match": lambda response: f"The answer is incorrect: {response}."
        }
