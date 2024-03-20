import mss
import pyautogui

pyautogui.FAILSAFE = False

w, h = pyautogui.size()
with mss.mss() as sct:
    monitor = {"top": 0, "left": 0, "width": w, "height": h}
    mss_image = sct.grab(monitor)
    scaling_factor = int(mss_image.width / w)


class Mouse:
    def scroll(self, clicks):
        """Scrolls the mouse wheel up or down."""
        pyautogui.scroll(clicks)

    def move(self, x: float | None = None, y: float | None = None):
        """Moves the mouse cursor to the specified coordinates."""
        if x is not None:
            x = x / scaling_factor
        if y is not None:
            y = y / scaling_factor
        pyautogui.moveTo(x, y)

    def click(
        self,
        x: float | None = None,
        y: float | None = None,
        button="left",
        clicks=1,
        interval=0.0,
    ):
        """Performs a click at the specified coordinates."""
        if x is not None:
            x = x / scaling_factor
        if y is not None:
            y = y / scaling_factor
        pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=interval)

    def down(self):
        """Presses the mouse button."""
        pyautogui.mouseDown()

    def up(self):
        """Releases the mouse button."""
        pyautogui.mouseUp()
