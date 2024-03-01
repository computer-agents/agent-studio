from enum import Enum, Flag, auto
from typing import Callable


class MouseOptions(Flag):
    """
    Mouse options for the recorder. Log move, click and scroll, respectively.
    """

    LOG_MOVE = 1 << 0
    LOG_CLICK = 1 << 1
    LOG_SCROLL = 1 << 2
    LOG_ALL = LOG_MOVE | LOG_CLICK | LOG_SCROLL


class MODE(Enum):
    """
    The mode of the recorder. Switched by hotkeys.
    """

    INIT = auto()
    CODING = auto()
    TYPING = auto()


class Event:
    def __init__(self, time: float, event_type: str, data: dict | str | None):
        self.time: float = time
        self.event_type: str = event_type
        self.data: dict | str | None = data

    def __gt__(self, other) -> bool:
        return self.time > other.time

    def __lt__(self, other) -> bool:
        return self.time < other.time

    def __str__(self) -> str:
        template = "{0:<20}|{1:<20}|{2}"
        return template.format(self.time, self.event_type, self.data)

    def __repr__(self) -> str:
        return str(self)


class Recorder:
    def __init__(self) -> None:
        self.start_time: float = 0
        self.stop_time: float = float("inf")

    def reset(self, **kwargs) -> None:
        raise NotImplementedError

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def wait_exit(self) -> None:
        raise NotImplementedError

    @staticmethod
    def remove_incomplete_events(
        in_func: Callable, out_func: Callable, events: list[Event]
    ):
        clean_events = []
        occur_set = set()
        for event in events:
            name, is_in = in_func(event)
            if is_in and name not in occur_set:
                occur_set.add(name)
                clean_events.append(event)
            name, is_out = out_func(event)
            if is_out and name in occur_set:
                occur_set.remove(name)
                clean_events.append(event)
        return clean_events
