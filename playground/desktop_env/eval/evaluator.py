from typing import Any


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
        self.phase: str = "init"

    def reset(self) -> bool:
        assert self.phase == "init", "Evaluator is not in the init phase"
        self.phase = "reset"
        succ = self.execute(self.reset_procedure)
        self.phase = "eval"
        return succ

    def execute(self, steps: list[dict[str, dict[str, Any]]]) -> bool:
        raise NotImplementedError

    def __call__(self) -> float:
        raise NotImplementedError
