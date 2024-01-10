from desktop_env.eval.bridges.bridge import Environment
from desktop_env.eval.bridges.bridge_helper import EnvironmentComb
from desktop_env.eval.evaluator import Evaluator
from desktop_env.eval.google_evaluators.calendar_evaluator import (
    GoogleCalendarEvaluator,
)
from desktop_env.eval.os_evaluators.filesystem_evaluator import FilesystemEvaluator


class EvaluatorComb:
    def __init__(self, evaluators: list[Evaluator]) -> None:
        self.evaluators = evaluators

    def __call__(self) -> float:
        score = 1.0
        # TODO: add score weight, see JSON format
        for evaluator in self.evaluators:
            cur_score = evaluator()
            score *= cur_score
        return score


# TODO: register evaluators


def evaluator_router(
    task_configs: dict,
    environments: dict[str, Environment],
) -> EvaluatorComb:
    """Router to get the evaluator class"""

    evaluators: list[Evaluator] = []
    for eval in task_configs["evals"]:
        eval_type = eval["eval_type"]
        match eval_type:
            case "google_calendar":
                evaluators.append(
                    GoogleCalendarEvaluator(
                        reference_answer=eval["reference_answers"],
                        env=environments["google_calendar"],
                        env_settings=environments["google_calendar"].get_env_settings(),
                    )
                )
            case "filesystem":
                evaluators.append(
                    FilesystemEvaluator(
                        reference_answer=eval["reference_answers"],
                        env=environments["filesystem"],
                        env_settings=environments["filesystem"].get_env_settings(),
                    )
                )
            # case "string_match":
            #     evaluators.append(StringEvaluator())
            # case "url_match":
            #     evaluators.append(URLEvaluator())
            # case "program_html":
            #     evaluators.append(HTMLContentEvaluator())
            case _:
                raise ValueError(f"eval_type {eval_type} is not supported")

    return EvaluatorComb(evaluators)


# TODO: this function only for testing!!!
def eval_tasks(
    task_configs: dict,
    env_comb: EnvironmentComb,
) -> float:
    total_score = 0.0
    gained_score = 0.0
    for task_config in task_configs["tasks"]:
        comb = evaluator_router(task_config, env_comb.environments)
        task_score = comb()
        gained_score += task_score * task_config["score"]
        total_score += task_config["score"]
    return (gained_score / total_score) * task_configs["score_weight"]
