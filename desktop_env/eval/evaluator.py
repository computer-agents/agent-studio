"""base class for evaluation"""
class Evaluator(object):
    def __init__(
            self, 
            reference_answer: dict,
            env_configs: dict = {},
            extra_info: dict = {},
            eval_tag: str = "",
        ) -> None:
        self.reference_answer = reference_answer
        self.env_configs = env_configs
        self.extra_info = extra_info
        self.eval_tag = eval_tag

    def __call__(
        self
    ) -> float:
        raise NotImplementedError
