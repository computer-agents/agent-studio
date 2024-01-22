import logging

from playground.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class QAEvaluator(Evaluator):
    name: str = "qa"

    def __call__(self, output: str) -> float:
        score = 1.0
        for approach, value in self.reference_answer.items():
            match approach:
                case "string_match":
                    score *= float(output == value)

        return score
