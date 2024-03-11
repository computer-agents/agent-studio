from typing import Callable

from agent_studio.config.config import Config
from agent_studio.utils.task_status import StateEnum, StateInfo, TaskStatus

config = Config()
task_status = TaskStatus()


def confirm_action(prompt: str = "") -> Callable:
    assert isinstance(prompt, str)

    def decorator(func) -> Callable:
        assert callable(func)

        def wrapper(*args, **kwargs):
            if config.need_human_confirmation:
                if config.headless:
                    user_input = (
                        input(f"{prompt}\nConfirm action (y/n): ").strip().lower()
                    )
                else:
                    task_status.set_task_state(
                        StateInfo(
                            state=StateEnum.WAIT_FOR_INPUT,
                            message=f"{prompt}\nConfirm action (y/n): ",
                        )
                    )
                    current_status = task_status.wait_for_state_change(
                        StateEnum.WAIT_FOR_INPUT
                    )
                    assert current_status.state == StateEnum.IN_PROGRESS, current_status
                    user_input = current_status.message.strip().lower()
                if user_input == "y":
                    return True, func(*args, **kwargs)
                else:
                    return False, None
            else:
                return True, func(*args, **kwargs)

        return wrapper

    return decorator
