import pyautogui


class Mouse:
    def scroll(self, clicks):
        """Scrolls the mouse wheel up or down."""
        pyautogui.scroll(clicks)

    def move(self, x: float | None = None, y: float | None = None):
        """Moves the mouse cursor to the specified coordinates."""
        pyautogui.moveTo(x, y)

    def click(
        self, x: float | None = None, y: float | None = None, button="left", clicks=1
    ):
        """Performs a click at the specified coordinates."""
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)

    def down(self):
        """Presses the mouse button."""
        pyautogui.mouseDown()

    def up(self):
        """Releases the mouse button."""
        pyautogui.mouseUp()
