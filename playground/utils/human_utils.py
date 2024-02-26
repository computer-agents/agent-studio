from typing import Callable

from playground.config.config import Config
from playground.utils.task_status import TaskStatus, StateEnum, StateInfo

config = Config()
task_status = TaskStatus()


def confirm_action(prompt: str) -> Callable:
    assert isinstance(prompt, str)

    def decorator(func) -> Callable:
        assert callable(func)

        def wrapper(*args, **kwargs):
            if config.need_human_confirmation:
                task_status.set_task_state(StateInfo(
                    state=StateEnum.WAIT_FOR_INPUT,
                    message=f"{prompt}\nDo you want to continue? (y/n): "
                ))
                current_status = task_status.wait_for_state(StateEnum.IN_PROGRESS)
                user_input = current_status.message.strip().lower()
                if user_input == "y":
                    return True, func(*args, **kwargs)
                else:
                    return False, None
            else:
                return True, func(*args, **kwargs)

        return wrapper

    return decorator
