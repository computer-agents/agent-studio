import platform
from abc import ABC
from enum import Flag, Enum, auto
from pydantic import BaseModel

OS = platform.platform()

if OS.startswith("Windows"):
    import ctypes
    PROCESS_PER_MONITOR_DPI_AWARE = 2
    ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)


class MouseOptions(Flag):
    LOG_MOVE = 1 << 0
    LOG_CLICK = 1 << 1
    LOG_SCROLL = 1 << 2
    LOG_ALL = LOG_MOVE | LOG_CLICK | LOG_SCROLL


class Event(BaseModel):
    time: float
    event_type: str

    def __gt__(self, other) -> bool:
        return self.time > other.time

    def __lt__(self, other) -> bool:
        return self.time < other.time

    def __str__(self) -> str:
        # use ns for time, 9 digits
        template = "{:.9f} | {}"
        return template.format(self.time, self.event_type)

    def __repr__(self) -> str:
        return str(self)


class KeyboardAction(Enum):
    DOWN = auto()  # key down
    UP = auto()    # key up


class KeyboardEvent(Event, BaseModel):
    action: KeyboardAction
    key: str | int | None = None
    note: str | None = None


class MouseAction(Enum):
    MOVE = auto()   # movement of the mouse
    BUTTON = auto()  # click or release of a button
    SCROLL = auto()  # scroll of the mouse wheel


class MouseEvent(Event, BaseModel):
    action: MouseAction
    x: int
    y: int
    button: str | None = None
    pressed: bool | None = None
    dx: int | None = None
    dy: int | None = None


class VideoInfo(BaseModel):
    region: dict[str, int]
    fps: int
    path: str

class Record(BaseModel):
    task_type: str
    start_time: float
    stop_time: float
    events: list[MouseEvent | KeyboardEvent]
    video: VideoInfo | None = None


class Recorder(ABC):
    def __init__(self):
        self.start_time: float = 0
        self.stop_time: float = float('inf')

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def wait_exit(self) -> None:
        raise NotImplementedError
