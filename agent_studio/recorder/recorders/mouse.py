from time import time
import logging

from pynput import mouse

from utils import MouseEvent, MouseAction, MouseOptions, Recorder

logger = logging.getLogger(__name__)


class MouseRecorder(Recorder):
    def __init__(
        self,
        options: MouseOptions,
        fps: int,
    ) -> None:
        super().__init__()
        self.events: list[MouseEvent] = []
        self.options: MouseOptions = options
        self.fps: int = fps
        self.last_capture_time: float = 0

    def __on_move(self, x: int, y: int) -> None:
        # print('Pointer moved to {0}'.format(
        #     (x, y)))
        cur_time = time()
        if cur_time - self.last_capture_time > 1 / self.fps:
            self.events.append(
                MouseEvent(
                    time=time(),
                    event_type="mouse",
                    action=MouseAction.MOVE,
                    x=x,
                    y=y
                )
            )
            self.last_capture_time = cur_time

    def __on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> bool | None:
        # print('{0} at {1}'.format(
        #     'Pressed' if pressed else 'Released',
        #     (x, y)))
        self.events.append(
            MouseEvent(
                time=time(),
                event_type="mouse",
                action=MouseAction.BUTTON,
                x=x,
                y=y,
                button=button.name,
                pressed=pressed
            )
        )

    def __on_scroll(self, x: int, y: int, dx: int, dy: int):
        # scroll_direction = 'down' if dy < 0 else 'up'
        # self.events.append(Event(time(), f'mouse_scroll_{scroll_direction}', {'x': x, 'y': y, 'dx': dx, 'dy': dy}))
        self.events.append(
            MouseEvent(
                time=time(),
                event_type="mouse",
                action=MouseAction.SCROLL,
                x=x,
                y=y,
                dx=dx,
                dy=dy
            )
        )

    def start(self):
        self.listener = mouse.Listener(
            on_move=self.__on_move if MouseOptions.LOG_MOVE in self.options else None,
            on_click=self.__on_click if MouseOptions.LOG_CLICK in self.options else None,
            on_scroll=self.__on_scroll if MouseOptions.LOG_SCROLL in self.options else None
        )
        self.listener.start()
        self.start_time = time()

    def stop(self):
        self.listener.stop()
        self.stop_time = time()
        logger.info(f"Mouse recorder stopped. Captured {len(self.events)} events")

    def wait_exit(self):
        self.listener.join()
