import sys
import threading
from enum import Enum

from agent_studio.utils.singleton import ThreadSafeSingleton


class StateEnum(Enum):
    IN_PROGRESS = "in_progress"
    WAIT_FOR_INPUT = "wait_for_input"
    FINISHED = "finished"
    TERMINATE = "terminate"


class StateInfo:
    def __init__(self, state: StateEnum, message: str | dict = "", result: str = ""):
        self.state: StateEnum = state
        self.message = message
        self.result = result


class TaskStatus(metaclass=ThreadSafeSingleton):
    def __init__(self) -> None:
        self.state_info: StateInfo = StateInfo(StateEnum.FINISHED)
        self.condition: threading.Condition = threading.Condition()
        self.active_thread: threading.Thread | None = None

    def set_task_state(self, state_info: StateInfo) -> None:
        with self.condition:
            self.state_info = state_info
            self.condition.notify_all()

    def get_task_state(self) -> StateInfo:
        with self.condition:
            return self.state_info

    def reset_state(self) -> None:
        with self.condition:
            self.state_info = StateInfo(StateEnum.FINISHED)

    def wait_for_state_change(self, cur_state: StateEnum) -> StateInfo:
        """Return when the state is different from the current state"""
        with self.condition:
            while cur_state == self.state_info.state:
                self.condition.wait()
        if self.state_info.state == StateEnum.TERMINATE:
            sys.exit(0)
        return self.state_info
