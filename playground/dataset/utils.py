import platform
from abc import ABC
from enum import Flag, Enum, auto

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

class MODE(Enum):
    INIT = auto()
    CODING = auto()
    TYPING = auto()

class Event:
    def __init__(self, time: float, event_type: str, data: dict | None):
        self.time : float = time
        self.event_type : str = event_type
        self.data : dict | None = data

    def __gt__(self, other) -> bool:
        return self.time > other.time

    def __lt__(self, other) -> bool:
        return self.time < other.time

    def __str__(self) -> str:
        template = "{0:<20}|{1:<20}|{2}"
        return template.format(self.time, self.event_type, self.data)

    def __repr__(self) -> str:
        return str(self)

class Recorder(ABC):
    def __init__(self):
        self.mode : MODE = MODE.INIT
        self.start_time : float = 0
        self.stop_time : float = float('inf')

    def set_mode(self, mode: MODE) -> None:
        self.mode = mode

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def wait_exit(self) -> None:
        raise NotImplementedError
