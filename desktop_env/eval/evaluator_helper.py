import ast
import importlib
import os
from pathlib import Path

from desktop_env.eval.evaluator import Evaluator


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


def register_evaluators(
    base_path: str | Path = "desktop_env/eval",
) -> dict[str, type[Evaluator]]:
    registered_classes = {}
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)

                # Parse the Python file
                with open(file_path, "r") as f:
                    file_contents = f.read()
                try:
                    tree = ast.parse(file_contents)
                except SyntaxError:
                    print(f"Error parsing {file_path} skipping...")
                    continue
                # Check each class definition in the file
                for node in ast.walk(tree):
                    module_name = (
                        os.path.relpath(file_path, ".")
                        .replace(os.sep, ".")
                        .rstrip(".py")
                    )
                    if isinstance(node, ast.ClassDef):
                        for base in node.bases:
                            if isinstance(base, ast.Name) and base.id == "Evaluator":
                                try:
                                    module = importlib.import_module(module_name)
                                    new_class: type[Evaluator] | None = getattr(
                                        module, node.name, None
                                    )
                                    if (
                                        new_class is not None
                                        and new_class.name not in registered_classes
                                    ):
                                        registered_classes[new_class.name] = new_class
                                    else:
                                        raise AttributeError
                                except Exception:
                                    print(f"Error importing {module_name} {node.name}")
                                break
    return registered_classes


# TODO: need to redesign the evaluator_router
def evaluator_router(
    task_configs: dict,
    env_configs: dict,
) -> EvaluatorComb:
    """Router to get the evaluator class"""

    registered_evaluators: dict[str, type[Evaluator]] = register_evaluators()
    evaluators: list[Evaluator] = []
    for eval in task_configs["evals"]:
        eval_type: str = eval["eval_type"]
        reference_action_sequence: dict = task_configs.get(
            "reference_action_sequence", {}
        )
        if eval_type in registered_evaluators:
            evaluators.append(
                registered_evaluators[eval_type](
                    reference_answer=eval.get("eval_procedure", {}),
                    reset_actions=eval.get("reset_actions", []),
                    env_config=env_configs[eval_type],
                    reference_action_sequence=reference_action_sequence.get(
                        eval_type, {}
                    ),
                )
            )
        else:
            raise ValueError(f"eval_type {eval_type} is not supported")

    return EvaluatorComb(evaluators)
