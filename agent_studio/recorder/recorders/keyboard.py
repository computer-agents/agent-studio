from time import time
from typing import Callable
import logging

from pynput import keyboard

from agent_studio.recorder.utils import KeyboardEvent, KeyboardAction, Recorder

logger = logging.getLogger(__name__)


class KeyboardRecorder(Recorder):
    def __init__(self,
                 hotkey_binds: dict[str, tuple[str, Callable]]
                 ):
        super().__init__()
        self.events: list[KeyboardEvent] = []

        self.hotkeys = {}
        for name, (hotkey, callback) in hotkey_binds.items():
            self.hotkeys[name] = keyboard.HotKey(
                keyboard.HotKey.parse(hotkey),
                callback
            )

    def __on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is not None:
            if isinstance(key, keyboard.KeyCode):
                key_code = key.vk
                ascii = ord(key.char) if key.char else None
                note = None
            else:
                key_code: int | None = key.value.vk
                ascii = None
                note = key.name
            self.events.append(
                KeyboardEvent(
                    time=time(),
                    event_type="keyboard",
                    action=KeyboardAction.DOWN,
                    key_code=key_code,
                    ascii=ascii,
                    note=note
                )
            )

            canonical_key = self.listener.canonical(key)
            for _, hotkey in self.hotkeys.items():
                hotkey.press(canonical_key)

    def __on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is not None:
            if isinstance(key, keyboard.KeyCode):
                key_code = key.vk
                ascii = ord(key.char) if key.char else None
                note = None
            else:
                key_code: int | None = key.value.vk
                ascii = None
                note = key.name
            print(f"Key {key_code} released")
            self.events.append(
                KeyboardEvent(
                    time=time(),
                    event_type="keyboard",
                    action=KeyboardAction.UP,
                    key_code=key_code,
                    ascii=ascii,
                    note=note
                )
            )

            canonical_key = self.listener.canonical(key)
            for _, hotkey in self.hotkeys.items():
                hotkey.release(canonical_key)

    def start(self):
        self.listener = keyboard.Listener(
            on_press=self.__on_press,
            on_release=self.__on_release)
        self.listener.start()
        self.start_time = time()

    def stop(self):
        self.listener.stop()
        self.stop_time = time()
        logger.info(f"Keyboard recorder stopped. Captured {len(self.events)} events")

    def wait_exit(self):
        self.listener.join()
