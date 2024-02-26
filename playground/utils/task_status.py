from typing import Any
import threading
import time
from enum import Enum, auto

from playground.utils.singleton import ThreadSafeSingleton

class StateEnum(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    WAIT_FOR_INPUT = auto()
    FINISHED = auto()


class StateInfo:
    def __init__(self, state: StateEnum, info: Any=None):
        self.state = state
        self.info = info


class TaskStatus(metaclass=ThreadSafeSingleton):
    def __init__(self):
        self.state_info: StateInfo = StateInfo(StateEnum.PENDING)
        self.lock: threading.Lock = threading.Lock()
        self.active_thread: threading.Thread | None = None

    def set_task_state(self, state_info: StateInfo) -> None:
        with self.lock:
            self.state_info = state_info

    def get_task_state(self) -> StateInfo:
        with self.lock:
            return self.state_info

    def reset_state(self):
        with self.lock:
            self.state_info = StateInfo(StateEnum.PENDING)

    def wait_for_state(self, state: StateEnum) -> StateInfo:
        while True:
            with self.lock:
                if self.state_info.state == state:
                    return self.state_info
            time.sleep(0.1)

    def wait_not_state(self, state: StateEnum) -> StateInfo:
        while True:
            with self.lock:
                if self.state_info.state != state:
                    return self.state_info
            time.sleep(0.1)
