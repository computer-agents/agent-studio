import logging
import time

from pynput import mouse

from playground.env.desktop_env.recorder.base_recorder import (
    Event,
    MouseOptions,
    Recorder,
)

logger = logging.getLogger(__name__)


class MouseRecorder(Recorder):
    def __init__(
        self,
        fps: int,
        options: MouseOptions = MouseOptions.LOG_ALL,
    ) -> None:
        super().__init__()
        self.events: list[Event] = []
        self.options: MouseOptions = options
        self.fps: int = fps
        self.last_capture_time: float = 0

    def reset(self, **kwargs) -> None:
        self.events = []
        self.last_capture_time = 0

    def start(self):
        self.listener = mouse.Listener(
            on_move=self._on_move if MouseOptions.LOG_MOVE in self.options else None,
            on_click=self._on_click if MouseOptions.LOG_CLICK in self.options else None,
            on_scroll=self._on_scroll
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

    def filter_recorded_events(
        self, start_time: float, stop_time: float
    ) -> list[Event]:
        # Removes events outside the time range
        self.events = [e for e in self.events if start_time <= e.time <= stop_time]

        # Removes mouse events with only 'up' event or 'down' event
        in_func = lambda e: (
            e.data["button"] if e.data["action"] == "button" else None,
            e.data["pressed"] == 1 if e.data["action"] == "button" else False,
        )
        out_func = lambda e: (
            e.data["button"] if e.data["action"] == "button" else None,
            e.data["pressed"] == 0 if e.data["action"] == "button" else False,
        )
        self.events = self.remove_incomplete_events(in_func, out_func, self.events)
        self.events = list(reversed(self.events))
        in_func = lambda e: (
            e.data["button"] if e.data["action"] == "button" else None,
            e.data["pressed"] == 0 if e.data["action"] == "button" else False,
        )
        out_func = lambda e: (
            e.data["button"] if e.data["action"] == "button" else None,
            e.data["pressed"] == 1 if e.data["action"] == "button" else False,
        )
        self.events = self.remove_incomplete_events(in_func, out_func, self.events)
        self.events = list(reversed(self.events))

        return self.events

    def _on_move(self, x: int, y: int) -> None:
        """The callback function when mouse is moved."""
        cur_time = time.time()
        if cur_time - self.last_capture_time > 1 / self.fps:
            self.events.append(
                Event(time.time(), "mouse", {"action": "pos", "x": x, "y": y})
            )
            self.last_capture_time = cur_time

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """The callback function when mouse button is clicked."""
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

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """The callback function when mouse wheel is scrolled."""
        self.events.append(
            Event(
                time.time(),
                "mouse",
                {"action": "mouse_scroll", "x": x, "y": y, "dx": dx, "dy": dy},
            )
        )
