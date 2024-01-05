"""base class for evaluation"""
import json
from pathlib import Path


class Evaluator(object):
    def __init__(self, eval_tag: str = "") -> None:
        self.eval_tag = eval_tag

    def __call__(
        self,
        config_file: Path | str,
    ) -> float:
        raise NotImplementedError


class EvaluatorComb:
    def __init__(self, evaluators: list[Evaluator]) -> None:
        self.evaluators = evaluators

    def __call__(
        self,
        config_file: Path | str,
    ) -> float:
        score = 1.0
        for evaluator in self.evaluators:
            cur_score = evaluator(config_file)
            score *= cur_score
        return score


# TODO: register evaluators


def evaluator_router(config_file: Path | str) -> EvaluatorComb:
    """Router to get the evaluator class"""
    with open(config_file, "r") as f:
        configs = json.load(f)

    eval_types = configs["eval"]["eval_types"]
    evaluators: list[Evaluator] = []
    for eval_type in eval_types:
        match eval_type:
            # case "string_match":
            #     evaluators.append(StringEvaluator())
            # case "url_match":
            #     evaluators.append(URLEvaluator())
            # case "program_html":
            #     evaluators.append(HTMLContentEvaluator())
            case _:
                raise ValueError(f"eval_type {eval_type} is not supported")

    return EvaluatorComb(evaluators)
