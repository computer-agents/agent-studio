import time

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pyautogui


class Mouse:
    def __init__(self, computer):
        self.computer = computer

    def scroll(self, clicks):
        pyautogui.scroll(clicks)

    def position(self):
        """
        Get the current mouse position.

        Returns:
            tuple: A tuple (x, y) representing the mouse's current position
            on the screen.
        """
        try:
            return pyautogui.position()
        except Exception as e:
            raise RuntimeError(
                f"An error occurred while retrieving the mouse position: {e}. "
            )

    def move(self, x=None, y=None):
        screenshot = None

        if self.computer.verbose:
            if not screenshot:
                screenshot = self.computer.display.screenshot(show=False)

            # Convert the screenshot to a numpy array for drawing
            img_array = np.array(screenshot)
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            img_draw = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

            # Scale drawing_x and drawing_y from screen size to screenshot size
            # for drawing purposes
            drawing_x = int(x * screenshot.width / self.computer.display.width)
            drawing_y = int(y * screenshot.height / self.computer.display.height)

            # Draw a solid blue circle around the place we're clicking
            cv2.circle(img_draw, (drawing_x, drawing_y), 20, (0, 0, 255), -1)

            plt.imshow(img_draw)
            plt.show()

            time.sleep(5)

        pyautogui.moveTo(x, y, duration=0.5)

    def click(self, *args, button="left", clicks=1, interval=0.1, **kwargs):
        if args or kwargs:
            self.move(*args, **kwargs)
        pyautogui.click(button=button, clicks=clicks, interval=interval)

    def double_click(self, *args, button="left", interval=0.1, **kwargs):
        if args or kwargs:
            self.move(*args, **kwargs)
        pyautogui.doubleClick(button=button, interval=interval)

    def triple_click(self, *args, button="left", interval=0.1, **kwargs):
        if args or kwargs:
            self.move(*args, **kwargs)
        pyautogui.tripleClick(button=button, interval=interval)

    def right_click(self, *args, **kwargs):
        if args or kwargs:
            self.move(*args, **kwargs)
        pyautogui.rightClick()

    def down(self):
        pyautogui.mouseDown()

    def up(self):
        pyautogui.mouseUp()
