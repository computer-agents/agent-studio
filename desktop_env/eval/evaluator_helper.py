from desktop_env.eval.evaluator import Evaluator
from desktop_env.eval.google_evaluators.calendar_evaluator import (
    GoogleCalendarEvaluator,
)
from desktop_env.eval.os_evaluators.filesystem_evaluator import FilesystemEvaluator


class EvaluatorComb:
    def __init__(self, evaluators: list[Evaluator]) -> None:
        self.evaluators = evaluators

    def reset(self) -> None:
        for evaluator in self.evaluators:
            evaluator.reset()

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
    env_configs: dict,
) -> EvaluatorComb:
    """Router to get the evaluator class"""

    evaluators: list[Evaluator] = []
    for eval in task_configs["evals"]:
        eval_type = eval["eval_type"]
        reset_actions_dict: dict = task_configs.get("reset_actions", {})
        match eval_type:
            case "google_calendar":
                evaluators.append(
                    GoogleCalendarEvaluator(
                        reference_answer=eval["reference_answers"],
                        env_config=env_configs["google_calendar"],
                        reset_actions=reset_actions_dict.get("google_calendar", []),
                    )
                )
            case "filesystem":
                evaluators.append(
                    FilesystemEvaluator(
                        reference_answer=eval["reference_answers"],
                        env_config=env_configs["filesystem"],
                        reset_actions=reset_actions_dict.get("filesystem", []),
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
    env_configs: dict,
) -> float:
    total_score = 0.0
    gained_score = 0.0
    for task_config in task_configs["tasks"]:
        comb = evaluator_router(task_config, env_configs)
        comb.reset()
        task_score = comb()
        gained_score += task_score * task_config["score"]
        total_score += task_config["score"]
    return (gained_score / total_score) * task_configs["score_weight"]
