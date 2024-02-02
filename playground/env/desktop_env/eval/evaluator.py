import logging
from typing import Any

logger = logging.getLogger(__name__)


class Evaluator:
    """Base class for evaluation."""

    name: str = "evaluator"

    def __init__(
        self,
        eval_procedure: list[dict[str, dict[str, Any]]],
        reset_procedure: list[dict[str, dict[str, Any]]],
    ) -> None:
        self.eval_procedure = eval_procedure
        self.reset_procedure = reset_procedure
        self.evaluation_handlers: dict[str, Any] = {}
        self.reset_handlers: dict[str, Any] = {}
        self.feedback_handlers: dict[str, Any] = {}

    def reset(self) -> None:
        """Reset the environment before task execution."""
        for step in self.reset_procedure:
            for action, params in step.items():
                if action in self.reset_handlers:
                    self.reset_handlers[action](**params)
                else:
                    raise ValueError(f"Action {action} is not supported for reset.")

    def __call__(self, response: str | None = None) -> float:
        """Evaluate the outcome of the task."""
        score = 1.0
        feedbacks = []
        for step in self.eval_procedure:
            for action, params in step.items():
                if action in self.evaluation_handlers:
                    if response is not None:
                        params["response"] = response
                    if not self.evaluation_handlers[action](**params):
                        score = 0.0
                        feedbacks.append(self.feedback_handlers[action](**params))
                else:
                    raise ValueError(
                        f"Action {action} is not supported for {self.name} evaluation."
                    )
        if score == 0.0:
            logger.info(f"Evaluation failed due to {feedbacks}")

        return score
