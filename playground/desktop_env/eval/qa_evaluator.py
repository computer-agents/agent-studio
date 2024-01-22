import logging

from playground.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class QAEvaluator(Evaluator):
    name: str = "qa"

    def __call__(self, **kwargs) -> float:
        score = 1.0
        for approach, value in self.reference_answer.items():
            match approach:
                case "string_match":
                    score *= float(kwargs["output"] == value)

        return score
