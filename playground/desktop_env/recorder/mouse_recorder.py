import logging
import time

from pynput import mouse

from playground.desktop_env.recorder.base_recorder import (
    MODE,
    Event,
    MouseOptions,
    Recorder,
)

logger = logging.getLogger(__name__)


class MouseRecorder(Recorder):
    def __init__(
        self,
        options: MouseOptions,
        fps: int,
    ) -> None:
        super().__init__()
        self.events: list[Event] = []
        self.options: MouseOptions = options
        self.fps: int = fps
        self.last_capture_time: float = 0

    def __on_move(self, x: int, y: int) -> None:
        if self.mode == MODE.TYPING:
            cur_time = time.time()
            if cur_time - self.last_capture_time > 1 / self.fps:
                self.events.append(
                    Event(time.time(), "mouse", {"action": "pos", "x": x, "y": y})
                )
                self.last_capture_time = cur_time

    def __on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if self.mode == MODE.TYPING:
            self.events.append(
                Event(
                    time.time(),
                    "mouse",
                    {
                        "action": "button",
                        "pressed": pressed,
                        "button": button.name,
                        "x": x,
                        "y": y,
                    },
                )
            )

    def __on_scroll(self, x: int, y: int, dx: int, dy: int):
        if self.mode == MODE.TYPING:
            self.events.append(
                Event(
                    time.time(),
                    "mouse",
                    {"action": "mouse_scroll", "x": x, "y": y, "dx": dx, "dy": dy},
                )
            )

    def start(self):
        self.listener = mouse.Listener(
            on_move=self.__on_move if MouseOptions.LOG_MOVE in self.options else None,
            on_click=self.__on_click
            if MouseOptions.LOG_CLICK in self.options
            else None,
            on_scroll=self.__on_scroll
            if MouseOptions.LOG_SCROLL in self.options
            else None,
        )
        self.listener.start()
        self.start_time = time.time()
        logger.info("Mouse recorder started")

    def stop(self):
        self.listener.stop()
        self.stop_time = time.time()
        logger.info(f"Mouse recorder stopped. Captured {len(self.events)} events")

    def wait_exit(self):
        self.listener.join()
