import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class FeedbackException(Exception):
    """Exception to be raised when evaluation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def evaluation_handler(name):
    if type(name) is not str:
        raise ValueError("Evaluation handler must have a name.")

    def decorator(func):
        setattr(func, "evaluation_handler", True)
        setattr(func, "name", name)
        return func

    return decorator


def reset_handler(name):
    if type(name) is not str:
        raise ValueError("Reset handler must have a name.")

    def decorator(func):
        setattr(func, "reset_handler", True)
        setattr(func, "name", name)
        return func

    return decorator


class EvaluatorHandler:
    def __init__(self, name: str, fun: Callable) -> None:
        self.name = name
        self.fun = fun
        self.params = fun.__code__.co_varnames
        print(f"Params: {self.params}")

    def __call__(self, **kwargs) -> None:
        target_params = {}
        for param in self.params:
            if param not in kwargs:
                logger.error(f"Parameter {param} is missing in {kwargs}.")
                raise ValueError(f"Parameter {param} is missing in {kwargs}.")
            target_params[param] = kwargs[param]
        self.fun(**target_params)


class Evaluator:
    """Base class for evaluation."""

    name: str = "evaluator"

    def __init__(
        self,
        eval_procedure: list[dict[str, dict[str, Any]]],
        reset_procedure: list[dict[str, dict[str, Any]]],
    ) -> None:
        self.eval_procedure = eval_procedure
        self.reset_procedure = reset_procedure
        self.evaluation_handlers: dict[str, EvaluatorHandler] = {}
        self.reset_handlers: dict[str, Any] = {}
        self.auto_register_handlers()

    def auto_register_handlers(self) -> None:
        """Register a handler for a specific action."""
        for func_name in dir(self):
            f = getattr(self, func_name)
            if callable(f):
                name = getattr(f, "name", None)
                if getattr(f, "evaluation_handler", False) is True:
                    if name is None or name in self.evaluation_handlers:
                        raise ValueError(
                            f"Registration for handler {name} failed."
                            f"Current handlers: {self.evaluation_handlers}"
                        )
                    self.evaluation_handlers[name] = f
                if getattr(f, "reset_handler", False) is True:
                    if name is None or name in self.reset_handlers:
                        raise ValueError(
                            f"Registration for handler {name} failed."
                            f"Current handlers: {self.evaluation_handlers}"
                        )
                    self.reset_handlers[name] = f

    def reset(self) -> None:
        """Reset the environment before task execution."""
        for step in self.reset_procedure:
            for action, params in step.items():
                if action in self.reset_handlers:
                    self.reset_handlers[action](**params)
                else:
                    raise ValueError(f"Action {action} is not supported for reset.")

    def __call__(self, **kwargs) -> tuple[float, str]:
        """Evaluate the outcome of the task."""
        score = 1.0
        feedback = ""
        for step in self.eval_procedure:
            for action, params in step.items():
                if action in self.evaluation_handlers:
                    try:
                        self.evaluation_handlers[action](**params, **kwargs)
                    except FeedbackException as e:
                        score = 0.0
                        feedback += e.message + "\n"
                    except Exception as e:
                        logger.error(f"Evaluation failed due to {e}")
                        raise e
                else:
                    raise ValueError(
                        f"Action {action} is not supported for {self.name} evaluation."
                    )

        return score, feedback
