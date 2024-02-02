import logging

from playground.env.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class HumanEvaluator(Evaluator):
    name: str = "human"

    def __init__(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def __call__(self, response: str | None = None) -> float:
        feedback = input("Is the task successful? (y/n): ")
        # TODO: semantic feedback for verbal RL
        return 1.0 if feedback == "y" else 0.0
