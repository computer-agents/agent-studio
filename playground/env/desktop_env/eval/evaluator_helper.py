import ast
import importlib
import logging
import os
from pathlib import Path

from playground.config import Config
from playground.env.desktop_env.eval.evaluator import Evaluator

config = Config()
logger = logging.getLogger(__name__)


class EvaluatorComb:
    def __init__(self, evaluators: list[Evaluator]) -> None:
        self.evaluators = evaluators

    def reset(self) -> None:
        for evaluator in self.evaluators:
            evaluator.reset()

    def __call__(self, **kwargs) -> tuple[float, str]:
        score = 1.0
        feedback = ""
        for evaluator in self.evaluators:
            cur_score, cur_feedback = evaluator(**kwargs)
            score *= cur_score
            feedback += cur_feedback
        return score, feedback


def register_evaluators(
    base_path: str | Path = "playground/desktop_env/eval",
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
                    logger.error(f"Error parsing {file_path} skipping...")
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
                                    logger.error(
                                        f"Error importing {module_name} {node.name}"
                                    )
                                break
    return registered_classes


def evaluator_router(
    task_configs: dict,
) -> EvaluatorComb:
    """Router to get the evaluator class"""

    registered_evaluators: dict[str, type[Evaluator]] = register_evaluators()
    evaluators: list[Evaluator] = []

    for eval in task_configs["evals"]:
        eval_type: str = eval["eval_type"]
        if eval_type in registered_evaluators:
            if eval_type == "model":
                from playground.llm import setup_model

                model = setup_model(config.eval_model)
                evaluators.append(
                    registered_evaluators[eval_type](
                        eval_procedure=[],
                        reset_procedure=[],
                        model=model,
                        instruction=task_configs["instruction"],
                    )
                )
            else:
                evaluators.append(
                    registered_evaluators[eval_type](
                        eval_procedure=eval.get("eval_procedure", []),
                        reset_procedure=eval.get("reset_procedure", []),
                    )
                )
        else:
            raise ValueError(f"eval_type {eval_type} is not supported")

    return EvaluatorComb(evaluators)
