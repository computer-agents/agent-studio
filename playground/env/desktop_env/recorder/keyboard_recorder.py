import logging
import time
from typing import Callable

from pynput import keyboard

from playground.env.desktop_env.recorder.base_recorder import MODE, Event, Recorder

logger = logging.getLogger(__name__)


class KeyboardRecorder(Recorder):
    def __init__(self, hotkey_binds: dict[str, tuple[str, Callable]]):
        super().__init__()
        self.events: list[Event] = []

        self.hotkeys = {}
        for name, (hotkey, callback) in hotkey_binds.items():
            self.hotkeys[name] = keyboard.HotKey(
                keyboard.HotKey.parse(hotkey), callback
            )

    def reset(self, **kwargs) -> None:
        self.events = []

    def start(self):
        self.listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self.listener.start()
        self.start_time = time.time()
        logger.info("Keyboard recorder started")

    def stop(self):
        self.listener.stop()
        self.stop_time = time.time()
        logger.info(f"Keyboard recorder stopped. Captured {len(self.events)} events")

    def wait_exit(self):
        self.listener.join()

    def filter_recorded_events(
        self, start_time: float, stop_time: float
    ) -> list[Event]:
        # Removes events outside the time range
        self.events = [e for e in self.events if start_time <= e.time <= stop_time]

        # Removes keys with only 'up' event or 'down' event
        in_func = lambda e: (e.data["key"], e.data["action"] == "down")
        out_func = lambda e: (e.data["key"], e.data["action"] == "up")
        self.events = self.remove_incomplete_events(in_func, out_func, self.events)
        self.events = list(reversed(self.events))
        in_func = lambda e: (e.data["key"], e.data["action"] == "up")
        out_func = lambda e: (e.data["key"], e.data["action"] == "down")
        self.events = self.remove_incomplete_events(in_func, out_func, self.events)
        self.events = list(reversed(self.events))

        return self.events

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        """The callback function when a key is pressed."""
        if key is not None:
            if self.mode == MODE.TYPING:
                if isinstance(key, keyboard.KeyCode):
                    key_id = key.vk
                else:
                    key_id = str(key)
                self.events.append(
                    Event(
                        time.time(),
                        "keyboard",
                        {"action": "down", "key": key_id, "note": str(key)},
                    )
                )

            canonical_key = self.listener.canonical(key)
            for hotkey in self.hotkeys.values():
                hotkey.press(canonical_key)

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        """The callback function when a key is released."""
        if key is not None:
            if self.mode == MODE.TYPING:
                if isinstance(key, keyboard.KeyCode):
                    key_id = key.vk
                else:
                    key_id = str(key)
                self.events.append(
                    Event(
                        time.time(),
                        "keyboard",
                        {"action": "up", "key": key_id, "note": str(key)},
                    )
                )

            canonical_key = self.listener.canonical(key)
            for hotkey in self.hotkeys.values():
                hotkey.release(canonical_key)
