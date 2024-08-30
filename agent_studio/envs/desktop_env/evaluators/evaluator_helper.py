import ast
import importlib
import logging
import os
from pathlib import Path

from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator import Evaluator

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
        # TODO: use bool instead of float
        return score, feedback


def register_evaluators(
    base_path: str | Path = "agent_studio/envs/desktop_env/evaluators",
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
                    logger.error(f"Error parsing {file_path}. Skipping...")
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
                                except Exception as e:
                                    logger.error(
                                        f"Error importing {module_name} {node.name}. "
                                        f"Due to {e}. Skipping..."
                                    )
                                break
    return registered_classes


def evaluator_router(
    task_configs: dict,
) -> EvaluatorComb:
    """Router to get the evaluator class"""

    registered_evaluators: dict[str, type[Evaluator]] = register_evaluators()
    evaluators: list[Evaluator] = []
    logger.info(f"Registered evaluators: {registered_evaluators.keys()}")

    for eval in task_configs["evals"]:
        eval_type: str = eval["eval_type"]
        if eval_type in registered_evaluators:
            evaluators.append(
                registered_evaluators[eval_type](
                    eval_procedure=eval.get("eval_procedure", []),
                    reset_procedure=eval.get("reset_procedure", []),
                )
            )
        else:
            raise ValueError(
                f"The eval_type '{eval_type}' is not registered. "
                f"This probably indicates a bug in the code."
            )

    return EvaluatorComb(evaluators)


def extract_evaluator_meta(file_path) -> tuple[str, list[dict]]:
    """Extracts the reset_handler and evaluate_handler \
        and their metadata from the evaluator."""
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    # Initialize a list to hold the extracted information
    extracted_info = []
    evaluator_name = None

    for node in ast.walk(tree):
        # Check for class definitions that are derived from "Evaluator"
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Evaluator":
                    # Iterate through the body of the class to find methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Check for decorators
                            for decorator in item.decorator_list:
                                if (
                                    isinstance(decorator, ast.Call)
                                    and hasattr(decorator.func, "id")
                                    and decorator.func.id
                                    in [
                                        "evaluation_handler",
                                        "reset_handler",
                                    ]
                                ):
                                    # Extract decorator name and arguments
                                    decorator_name = decorator.func.id
                                    decorator_args = [
                                        ast.literal_eval(arg) for arg in decorator.args
                                    ]

                                    # Extract function name, arguments, and docstring
                                    function_name = item.name
                                    function_args = {
                                        arg.arg: ast.unparse(arg.annotation)
                                        for arg in item.args.args
                                        if arg.annotation is not None
                                    }
                                    docstring = ast.get_docstring(item)

                                    # Add extracted information to the list
                                    extracted_info.append(
                                        {
                                            "decorator": decorator_name,
                                            "decorator_args": decorator_args,
                                            "function_name": function_name,
                                            "function_args": function_args,
                                            "docstring": docstring,
                                        }
                                    )
                        elif isinstance(item, ast.AnnAssign):
                            target = item.target
                            if isinstance(target, ast.Name) and target.id == "name":
                                if item.value is not None and hasattr(item.value, "n"):
                                    if evaluator_name is None:
                                        evaluator_name = item.value.n
                                    else:
                                        raise ValueError(
                                            "Multiple evaluator names found in "
                                            f"{file_path}"
                                        )
                        elif isinstance(item, ast.Assign):
                            for assign in item.targets:
                                if isinstance(assign, ast.Name) and assign.id == "name":
                                    if item.value is not None and hasattr(
                                        item.value, "n"
                                    ):
                                        if evaluator_name is None:
                                            evaluator_name = item.value.n
                                        else:
                                            raise ValueError(
                                                "Multiple evaluator names found in "
                                                f"{file_path}"
                                            )
    if evaluator_name is None:
        raise ValueError(f"No evaluator name found in {file_path}")
    return evaluator_name, extracted_info


def load_evaluator_meta(
    base_path: str = "agent_studio/envs/desktop_env/evaluators",
) -> dict[str, list[dict]]:
    """Loads the evaluator arguments."""
    evaluator_args = {}
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    evaluator_name, evaluator_info = extract_evaluator_meta(file_path)
                    evaluator_args[evaluator_name] = evaluator_info
                except Exception:
                    # logger.warn(f"Fail to parse {file_path}: {e}")
                    pass
    return evaluator_args


def verify_task_config(
    task_config: dict,
    evaluator_args: dict[str, list[dict]],
) -> None:
    """Verifies the task configuration."""
    for eval in task_config["evals"]:
        eval_type = eval["eval_type"]
        if eval_type not in evaluator_args:
            raise ValueError(f"Wrong evaluator type '{eval_type}' in task config.")
        for eval_procedure in eval.get("eval_procedure", []):
            for fun_name, fun_params in eval_procedure.items():
                for fun_param in fun_params:
                    fun_meta = [
                        meta
                        for meta in evaluator_args[eval_type]
                        if meta["function_name"] == fun_name
                    ]
                    if len(fun_meta) == 0:
                        raise ValueError(
                            f"Wrong eval_procedure '{fun_name}' in task config."
                        )
                    fun_meta = fun_meta[0]
                    if fun_meta["decorator"] != "evaluation_handler":
                        raise ValueError(
                            f"Wrong eval_procedure '{fun_name}' in task config."
                        )
                    if fun_param not in fun_meta["function_args"]:
                        raise ValueError(
                            f"Wrong eval_procedure '{fun_name}' in task config."
                        )
                    # TODO: check parameter type
        for reset_procedure in eval.get("reset_procedure", []):
            for fun_name, fun_params in reset_procedure.items():
                for fun_param in fun_params:
                    fun_meta = [
                        meta
                        for meta in evaluator_args[eval_type]
                        if meta["function_name"] == fun_name
                    ]
                    if len(fun_meta) == 0:
                        raise ValueError(
                            f"Wrong reset_procedure '{fun_name}' in task config."
                        )
                    fun_meta = fun_meta[0]
                    if fun_meta["decorator"] != "reset_handler":
                        raise ValueError(
                            f"Wrong reset_procedure '{fun_name}' in task config."
                        )
                    if fun_param not in fun_meta["function_args"]:
                        raise ValueError(
                            f"Wrong reset_procedure '{fun_name}' in task config."
                        )
                    # TODO: check parameter type
