import json
import logging
import time
from typing import Any

from pynput import keyboard, mouse

from playground.desktop_env.recorder.base_recorder import MouseOptions

logger = logging.getLogger(__name__)


class Player:
    def __init__(self, event_time_zero: float, start_time: float) -> None:
        self.event_time_zero = event_time_zero
        self.start_time = start_time

    def run(self, event_time: float, data: dict) -> None:
        target_interval = event_time - self.event_time_zero
        current_interval = time.time() - self.start_time
        wait_time = target_interval - current_interval
        if wait_time > 0:
            time.sleep(wait_time)
        self._execute(data)

    def _execute(self, data: dict) -> None:
        raise NotImplementedError

    def stop(self):
        pass


class MousePlayer(Player):
    def __init__(
        self, event_time_zero: float, start_time: float, options: MouseOptions
    ) -> None:
        super().__init__(event_time_zero, start_time)
        self.controller = mouse.Controller()
        self.last_pos = self.controller.position
        self.options = options
        self.pressed_buttons: set[Any] = set()

    def _execute(self, data: dict) -> None:
        match data["action"]:
            case "pos":
                if MouseOptions.LOG_MOVE in self.options:
                    logger.debug(f"Mouse pos: {data['x']}, {data['y']}")
                    self.controller.move(
                        data["x"] - self.last_pos[0], data["y"] - self.last_pos[1]
                    )
                    self.last_pos = (data["x"], data["y"])
                    # self.controller.position = (data["x"], data["y"])
            case "button":
                logger.debug(
                    f"Mouse button: {data['button']}, {data['pressed']}"
                    f"at {data['x']}, {data['y']}"
                )
                if MouseOptions.LOG_CLICK in self.options:
                    self.controller.position = (data["x"], data["y"])
                    match data["button"]:
                        case "left":
                            button = mouse.Button.left
                        case "right":
                            button = mouse.Button.right
                        case "middle":
                            button = mouse.Button.middle
                        case _:
                            raise Exception(f"Unknown button: {data['button']}")
                    if data["pressed"]:
                        if button not in self.pressed_buttons:
                            self.controller.press(button)
                            self.pressed_buttons.add(button)
                        else:
                            logger.warn(f"{button} is already pressed")
                    else:
                        if button in self.pressed_buttons:
                            self.controller.release(button)
                            self.pressed_buttons.remove(button)
                        else:
                            logger.warn(f"{button} is already released")
            case "mouse_scroll":
                logger.debug(
                    f"Mouse scroll: {data['dx']}, {data['dy']}"
                    f"at {data['x']}, {data['y']}"
                )
                if MouseOptions.LOG_SCROLL in self.options:
                    self.controller.position = (data["x"], data["y"])
                    self.controller.scroll(data["dx"], data["dy"])

    def stop(self):
        for button in self.pressed_buttons:
            self.controller.release(button)
            logger.warn(f"{button} is still pressed\n" f"check the record file")


class KeyboardPlayer(Player):
    def __init__(self, event_time_zero: float, start_time: float) -> None:
        super().__init__(event_time_zero, start_time)
        self.controller: keyboard.Controller = keyboard.Controller()
        self.pressed_keys: set[Any] = set()

    def __compose_key(self, key: str | int) -> keyboard.Key | keyboard.KeyCode:
        if isinstance(key, str):
            return getattr(keyboard.Key, key[4:])
        elif isinstance(key, int):
            return keyboard.KeyCode.from_vk(key)
        else:
            raise Exception(f"Unknown key {key} with type: {type(key)}")

    def _execute(self, data: dict) -> None:
        key = self.__compose_key(data["key"])
        match data["action"]:
            case "down":
                if key not in self.pressed_keys:
                    logger.debug(f"{data['key']} down")
                    self.pressed_keys.add(key)
                    self.controller.press(key)
                else:
                    logger.warn(f"{data['key']} is already pressed")
            case "up":
                if key in self.pressed_keys:
                    logger.debug(f"{data['key']} up")
                    self.pressed_keys.remove(key)
                    self.controller.release(key)
                else:
                    logger.warn(f"{data['key']} is already released")

    def stop(self):
        for key in self.pressed_keys:
            self.controller.release(key)
            logger.warn(f"{key} is still pressed\n" f"check the record file")


class CodePlayer(Player):
    def _execute(self, data: dict) -> None:
        exec(data["code"])


class AllinOnePlayer:
    def __init__(self, record_path: str, mouse_options: MouseOptions) -> None:
        with open(record_path, "r") as f:
            records = json.load(f)

        self.events = records.pop("events")
        self.meta_data = records
        self.event_time_zero = self.meta_data["start_time"]
        self.start_time = time.time()
        self.players = {
            "mouse": MousePlayer(self.event_time_zero, self.start_time, mouse_options),
            "keyboard": KeyboardPlayer(self.event_time_zero, self.start_time),
            "code": CodePlayer(self.event_time_zero, self.start_time),
        }

    def run(self) -> None:
        logger.info("Start playing")
        for event in self.events:
            if event["event_type"] in self.players:
                self.players[event["event_type"]].run(event["time"], event["data"])
            else:
                if event["event_type"] != "switch_mode":
                    raise Exception(f"Unknown event type: {event['event_type']}")
        logger.info("Stop playing")

    def stop(self):
        for player in self.players.values():
            player.stop()


if __name__ == "__main__":
    player = AllinOnePlayer(
        record_path="record.json",
        mouse_options=MouseOptions.LOG_CLICK | MouseOptions.LOG_SCROLL,
    )
    player.run()
    player.stop()
