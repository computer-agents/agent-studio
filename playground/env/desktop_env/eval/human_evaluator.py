import logging

from playground.env.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class HumanEvaluator(Evaluator):
    name: str = "human"

    def __call__(self, **kwargs) -> tuple[float, str]:
        score = float(input("Is the task successful? (y/n): ") == "y")
        feedback = input("Type any feedback and press Enter (or press Enter to skip): ")
        return score, feedback
