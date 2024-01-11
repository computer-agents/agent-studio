"""base class for evaluation"""


class Evaluator(object):
    def __init__(
        self,
        reference_answer: dict,
        reset_actions: list[dict],
        env_config: dict,
        eval_tag: str = "",
    ) -> None:
        self.reference_answer = reference_answer
        self.eval_tag = eval_tag
        self.reset_actions = reset_actions
        self.enter_steps: list = env_config["enter"] if "enter" in env_config else []
        self.exit_steps: list = env_config["exit"] if "exit" in env_config else []
        self.env_settings: dict = (
            env_config["env_settings"] if "env_settings" in env_config else {}
        )
        # self.execute(self.enter_steps)

    def reset(self) -> bool:
        return self.execute(self.reset_actions)

    def execute(self, steps: list[dict]) -> bool:
        raise NotImplementedError

    def get_env_settings(self) -> dict:
        return self.env_settings

    def __call__(self) -> float:
        raise NotImplementedError
