import platform

import pyautogui
import pyperclip


class Keyboard:
    def __init__(self) -> None:
        if platform.platform() != "Darwin":
            self.modifier_key = "ctrl"
        else:
            self.modifier_key = "command"

    def type(self, text: str, interval: float | None = None) -> None:
        """Types a string of characters.

        Args:
            text (str): The string to be typed out.
            interval (float, optional): The delay between pressing each
            character key.
        """
        if interval:
            pyautogui.write(text, interval=interval)
        else:
            clipboard_history = pyperclip.paste()
            pyperclip.copy(text)
            self.hotkey([self.modifier_key, "v"])
            pyperclip.copy(clipboard_history)

    def press(self, keys: str | list[str], interval: float = 0.1) -> None:
        """Presses a key or a sequence of keys.

        Args:
            keys (str or list): The key(s) to be pressed. If keys is a list, each key
                in the list will be pressed once.
            interval (float, optional): The delay between each key press.
        """
        pyautogui.press(keys, presses=1, interval=interval)

    def hotkey(self, keys: list[str], interval: float = 0.1) -> None:
        """Presses a sequence of keys in the order they are provided,
            and then release them in reverse order.

        Args:
            keys (list): The keys to be pressed.
            interval (float, optional): The delay between each key press.
        """
        pyautogui.hotkey(*keys, interval=interval)

    def down(self, key: str):
        """Presses down a key."""
        pyautogui.keyDown(key)

    def up(self, key: str):
        """Releases a key."""
        pyautogui.keyUp(key)
