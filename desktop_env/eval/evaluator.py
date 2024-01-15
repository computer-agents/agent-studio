from typing import Any


class Evaluator(object):
    """Base class for evaluation."""

    name: str = "evaluator"

    def __init__(
        self,
        reference_answer: dict,
        reset_procedure: list[dict],
        env_config: dict,
        eval_tag: str = "",
    ) -> None:
        self.reference_answer = reference_answer
        self.eval_tag = eval_tag
        self.reset_procedure = reset_procedure
        self.enter_steps: list = env_config["enter"] if "enter" in env_config else []
        self.exit_steps: list = env_config["exit"] if "exit" in env_config else []
        self.env_settings: dict = (
            env_config["env_settings"] if "env_settings" in env_config else {}
        )
        self.phase: str = "init"
        # self.execute(self.enter_steps)

    def reset(self) -> bool:
        assert self.phase == "init", "Evaluator is not in the init phase"
        self.phase = "reset"
        succ = self.execute(self.reset_procedure)
        self.phase = "eval"
        return succ

    def execute(self, steps: list[dict[str, dict[str, Any]]]) -> bool:
        raise NotImplementedError

    def get_env_settings(self) -> dict:
        return self.env_settings

    def __call__(self) -> float:
        raise NotImplementedError
