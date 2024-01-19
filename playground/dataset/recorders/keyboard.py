import time
import logging
from typing import Callable

from pynput import keyboard

from utils import Event, MODE, Recorder

logger = logging.getLogger(__name__)

class KeyboardRecorder(Recorder):
    def __init__(self,
                 hotkey_binds: dict[str, tuple[str, Callable]]
                ):
        super().__init__()
        self.events : list[Event] = []

        self.hotkeys = {}
        for name, (hotkey, callback) in hotkey_binds.items():
            self.hotkeys[name] = keyboard.HotKey(
                keyboard.HotKey.parse(hotkey),
                callback
            )

    def __on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is not None:
            if self.mode == MODE.TYPING:
                if isinstance(key, keyboard.KeyCode):
                    key_id = key.vk
                else:
                    key_id = str(key)
                self.events.append(
                    Event(
                        time.time(),
                        'keyboard',
                        {
                            'action': 'down',
                            'key': key_id,
                            'note': str(key)
                        }
                    )
                )

            canonical_key = self.listener.canonical(key)
            for _, hotkey in self.hotkeys.items():
                hotkey.press(canonical_key)

    def __on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is not None:
            if self.mode == MODE.TYPING:
                if isinstance(key, keyboard.KeyCode):
                    key_id = key.vk
                else:
                    key_id = str(key)
                self.events.append(
                    Event(
                        time.time(),
                        'keyboard',
                        {
                            'action': 'up',
                            'key': key_id,
                            'note': str(key)
                        }
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
        self.start_time = time.time()
        logger.info(f"Keyboard recorder started")

    def stop(self):
        self.listener.stop()
        self.stop_time = time.time()
        logger.info(f"Keyboard recorder stopped. Captured {len(self.events)} events")

    def wait_exit(self):
        self.listener.join()
