import threading
from enum import Enum

from playground.utils.singleton import ThreadSafeSingleton


class StateEnum(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAIT_FOR_INPUT = "wait_for_input"
    FINISHED = "finished"


class StateInfo:
    def __init__(self, state: StateEnum, message: str | dict = "", result: str = ""):
        self.state: StateEnum = state
        self.message = message
        self.result = result


class TaskStatus(metaclass=ThreadSafeSingleton):
    def __init__(self):
        self.state_info: StateInfo = StateInfo(StateEnum.PENDING)
        self.condition: threading.Condition = threading.Condition()
        self.active_thread: threading.Thread | None = None

    def set_task_state(self, state_info: StateInfo) -> None:
        with self.condition:
            self.state_info = state_info
            self.condition.notify_all()

    def get_task_state(self) -> StateInfo:
        with self.condition:
            return self.state_info

    def reset_state(self):
        with self.condition:
            self.state_info = StateInfo(StateEnum.PENDING)

    def wait_for_state_change(self) -> StateInfo:
        with self.condition:
            self.condition.wait()
        return self.state_info
