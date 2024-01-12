from desktop_env.eval.evaluator import Evaluator
from desktop_env.eval.google_evaluators.calendar_evaluator import (
    GoogleCalendarEvaluator,
)
from desktop_env.eval.google_evaluators.gmail_evaluator import GmailEvaluator
from desktop_env.eval.os_evaluators.filesystem_evaluator import FilesystemEvaluator


class EvaluatorComb:
    def __init__(self, evaluators: list[Evaluator]) -> None:
        self.evaluators = evaluators

    def reset(self) -> None:
        for evaluator in self.evaluators:
            evaluator.reset()

    def __call__(self) -> float:
        score = 1.0
        for evaluator in self.evaluators:
            cur_score = evaluator()
            score *= cur_score
        return score

    def get_oracle_trajectory(self) -> list[str]:
        oracle_trajectory = []
        for evaluator in self.evaluators:
            oracle_trajectory.extend(evaluator.get_oracle_trajectory())
        return oracle_trajectory


# TODO: register evaluators


def evaluator_router(
    task_configs: dict,
    env_configs: dict,
) -> EvaluatorComb:
    """Router to get the evaluator class"""

    evaluators: list[Evaluator] = []
    for eval in task_configs["evals"]:
        eval_type = eval["eval_type"]
        reference_action_sequence: dict = task_configs.get(
            "reference_action_sequence", {}
        )
        match eval_type:
            case "gmail":
                evaluators.append(
                    GmailEvaluator(
                        reference_answer=eval.get("eval_procedure", {}),
                        env_config=env_configs["gmail"],
                        reset_actions=eval.get("reset_actions", []),
                        reference_action_sequence=reference_action_sequence.get(
                            "gmail", {}
                        ),
                    )
                )
            case "google_calendar":
                evaluators.append(
                    GoogleCalendarEvaluator(
                        reference_answer=eval.get("eval_procedure", {}),
                        env_config=env_configs["google_calendar"],
                        reset_actions=eval.get("reset_actions", []),
                        reference_action_sequence=reference_action_sequence.get(
                            "google_calendar", {}
                        ),
                    )
                )
            case "filesystem":
                evaluators.append(
                    FilesystemEvaluator(
                        reference_answer=eval.get("eval_procedure", {}),
                        env_config=env_configs["filesystem"],
                        reset_actions=eval.get("reset_actions", []),
                        reference_action_sequence=reference_action_sequence.get(
                            "filesystem", {}
                        ),
                    )
                )
            case _:
                raise ValueError(f"eval_type {eval_type} is not supported")

    return EvaluatorComb(evaluators)
