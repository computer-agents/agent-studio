"""base class for evaluation"""


class Evaluator(object):
    def __init__(
        self,
        reference_answer: dict,
        env_configs: dict | None = None,
        extra_info: dict | None = None,
        eval_tag: str = "",
    ) -> None:
        self.reference_answer = reference_answer
        self.env_configs = env_configs
        self.extra_info = extra_info
        self.eval_tag = eval_tag

    @staticmethod
    def evaluator_name() -> str:
        raise NotImplementedError

    def __call__(self) -> float:
        raise NotImplementedError
