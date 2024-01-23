import logging
from typing import Any

logger = logging.getLogger(__name__)


class Evaluator(object):
    """Base class for evaluation."""

    name: str = "evaluator"

    def __init__(
        self,
        reference_answer: dict,
        reset_procedure: list[dict],
        eval_tag: str = "",
    ) -> None:
        self.reference_answer = reference_answer
        self.eval_tag = eval_tag
        self.reset_procedure = reset_procedure

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        raise NotImplementedError

    def reset(self) -> None:
        self.execute(self.reset_procedure)

    def __call__(self, response: str | None = None) -> float:
        """Evaluate the outcome of the task."""
        return self.execute([self.reference_answer], response)
