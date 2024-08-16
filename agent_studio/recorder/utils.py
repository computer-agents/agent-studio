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
    duration: float = 0.0

    def __gt__(self, other) -> bool:
        return self.time > other.time

    def __lt__(self, other) -> bool:
        return self.time < other.time

    def __str__(self) -> str:
        # use ns for time, 9 digits
        template = "{:.9f} | {}"
        return template.format(self.time, self.event_type)

    def format(self) -> str:
        # format time as mm:ss:ms
        template = "{:02d}:{:02d}:{:03d} | {:<10}"
        minutes, seconds = divmod(int(self.time), 60)
        milliseconds = self.time - int(self.time)
        return template.format(minutes, seconds, int(milliseconds * 1000), self.event_type)

    def __repr__(self) -> str:
        return str(self)


class KeyboardAction(Enum):
    KEY_DOWN = auto()  # key down
    KEY_UP = auto()    # key up


class KeyboardActionAdvanced(Enum):
    KEY_TYPE = auto()  # key type
    KEY_SHORTCUT = auto()  # key combination


class KeyboardEvent(Event, BaseModel):
    action: KeyboardAction
    # virtual key code of the key or key name of the key
    key_code: int | None = None
    # ascii code of the key, modifier keys have no ascii code
    ascii: int | None = None
    note: str | None = None

    def format(self) -> str:
        # {time} | {event_type} | {Key} {Action} |
        template = "{} | {} {} |"
        key = self.note
        return template.format(super().format(), key, self.action.name)


class KeyboardEventAdvanced(Event, BaseModel):
    action: KeyboardActionAdvanced
    key_code: list[str | int | None] = []
    note: str | None = None

    def format(self) -> str:
        # {time} | {event_type} | {ACTION} {str} |
        if self.action == KeyboardActionAdvanced.KEY_TYPE:
            template = "{} | {} \"{}\" |"
            return template.format(super().format(), self.action.name, self.note)
        elif self.action == KeyboardActionAdvanced.KEY_SHORTCUT:
            template = "{} | {} {} |"
            return template.format(super().format(), self.action.name, "+".join(
                [str(key) for key in self.key_code]))
        else:
            return super().format()


class MouseAction(Enum):
    MOUSE_POS = auto()     # position of the mouse
    MOUSE_BUTTON = auto()  # click or release of a button
    MOUSE_SCROLL = auto()  # scroll of the mouse wheel


class MouseEvent(Event, BaseModel):
    action: MouseAction
    x: int
    y: int
    button: str | None = None
    pressed: bool | None = None
    dx: int | None = None
    dy: int | None = None

    def format(self) -> str:
        if self.action == MouseAction.MOUSE_POS:
            # {time} | {event_type} | POS {X} {Y} |
            template = "{} | {} {} {} |"
            return template.format(super().format(), self.action.name, self.x, self.y)
        elif self.action == MouseAction.MOUSE_BUTTON:
            # {time} | {event_type} | {Button} {Action} {Pressed} |
            template = "{} | {} {} {} |"
            return template.format(super().format(), self.button, self.action.name,
                                   "Pressed" if self.pressed else "Released")
        elif self.action == MouseAction.MOUSE_SCROLL:
            assert self.dy is not None and self.dx is not None
            # {time} | {event_type} | SCROLL {Direction} |
            template = "{} | {} {} |"
            return template.format(super().format(), self.action.name, "DOWN" if self.dy < 0 else "UP")
        else:
            return super().format()


class VideoInfo(BaseModel):
    region: dict[str, int]
    fps: int
    path: str


class Record(BaseModel):
    instruction: str
    annotation_id: str
    start_time: float
    stop_time: float
    events: list[MouseEvent | KeyboardEvent | KeyboardEventAdvanced]
    video: VideoInfo


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
