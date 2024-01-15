import os
import tempfile
import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pyautogui
from PIL import Image


class Display:
    def __init__(self, computer):
        self.computer = computer
        self.width, self.height = pyautogui.size()

    def size(self):
        return pyautogui.size()

    def center(self):
        return self.width // 2, self.height // 2

    def screenshot(self, show=True):
        time.sleep(2)

        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)

        screenshot = (
            pyautogui.screenshot()
        )  # TODO: pyautogui is slow, need to change to mss

        screenshot.save(temp_file.name)

        # Open the image file with PIL
        img = Image.open(temp_file.name)

        # Delete the temporary file
        try:
            os.remove(temp_file.name)
        except Exception as e:
            if self.computer.verbose:
                print(str(e))

        if show:
            # Show the image using matplotlib
            plt.imshow(np.array(img))

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                plt.show()

        return img
