import inspect
import logging
from typing import Callable

import requests

from agent_studio.utils.types import Procedure

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


class Handler:
    def __init__(self, name: str, fun: Callable) -> None:
        self.name: str = name
        self.fun: Callable = fun
        self.params: dict[str, inspect.Parameter] = dict(
            inspect.signature(fun).parameters
        )
        logging.info(f"[{self.name}] Params: {self.params}")

    def __call__(self, **kwargs) -> None:
        target_params = {}
        for name, param in self.params.items():
            if name not in kwargs and param.default == inspect.Parameter.empty:
                logger.error(f"Parameter {name} is missing in {name}.")
                raise ValueError(f"Parameter {name} is missing in {name}.")
            target_params[name] = kwargs[name] if name in kwargs else param.default
        self.fun(**target_params)


class Evaluator:
    """Base class for evaluation."""

    name: str = "evaluator"

    def __init__(
        self,
    ) -> None:
        self.evaluation_handlers: dict[str, Handler] = {}
        self.reset_handlers: dict[str, Handler] = {}
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
                    self.evaluation_handlers[name] = Handler(name, f)
                if getattr(f, "reset_handler", False) is True:
                    if name is None or name in self.reset_handlers:
                        raise ValueError(
                            f"Registration for handler {name} failed."
                            f"Current handlers: {self.evaluation_handlers}"
                        )
                    self.reset_handlers[name] = Handler(name, f)

    # def reset(self) -> None:
    #     """Reset the environment before task execution."""
    #     for step in self.reset_procedure:
    #         for action, params in step.items():
    #             if action in self.reset_handlers:
    #                 self.reset_handlers[action](**params)
    #             else:
    #                 raise ValueError(f"Action {action} is not supported for reset.")

    def reset(self, procedure: Procedure) -> None:
        """Reset the environment before task execution."""
        action = procedure.function
        params = procedure.params
        if action in self.reset_handlers:
            self.reset_handlers[action](**params)
        else:
            raise ValueError(f"Action {action} is not supported for reset.")

    def __call__(self, procedure: Procedure, **kwargs) -> tuple[float, str]:
        """Evaluate the outcome of the task."""
        score = 1.0
        feedback = ""
        action = procedure.function
        params = procedure.params
        assert self.name == procedure.evaluator
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


class LocalEvaluator:
    def __init__(self) -> None:
        pass

    def __call__(self, code: str) -> dict:
        return {"output": [code]}


class RemoteEvaluator:
    def __init__(self, env_server_addr: str, env_server_port: int):
        self.env_server_addr = env_server_addr
        self.env_server_port = env_server_port

    def __call__(self, code: str) -> dict:
        response = requests.post(
            f"http://{self.env_server_addr}:{self.env_server_port}/execute",
            json={"message": code},
        )
        return response.json()

    def close(self) -> bool:
        return True

    def reset(self) -> bool:
        if not self.close():
            return False
        response = requests.post(
            f"http://{self.env_server_addr}:{self.env_server_port}/runtime/reset"
        )
        return response.json()["status"] == "success"
