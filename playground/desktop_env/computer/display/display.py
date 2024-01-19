import logging
import os
import tempfile
import time
import warnings

import matplotlib.pyplot as plt
import mss
import mss.tools
import numpy as np
import pyautogui
from PIL import Image, ImageDraw, ImageFont

from playground.config import Config

config = Config()
logger = logging.getLogger(__name__)


class Display:
    def __init__(self, computer):
        self.computer = computer
        self.width, self.height = pyautogui.size()

    def size(self):
        return pyautogui.size()

    def center(self):
        return self.width // 2, self.height // 2

    def take_screenshot(
        self,
        tid: float = 0.0,
        screen_region: tuple[int, int] = config.resolution,
        draw_axis=False,
    ):
        region = {
            "left": 0,
            "top": 0,
            "width": screen_region[0],
            "height": screen_region[1],
        }

        output_dir = config.log_dir

        # save screenshots
        screen_image_filename = output_dir + "/screen_" + str(tid) + ".jpg"

        with mss.mss() as sct:
            screen_image = sct.grab(region)
            image = Image.frombytes(
                "RGB", screen_image.size, screen_image.bgra, "raw", "BGRX"
            )
            image.save(screen_image_filename)

        if draw_axis:
            # draw axis on the screenshot
            draw = ImageDraw.Draw(screen_image)
            width, height = screen_image.size
            cx, cy = width // 2, height // 2

            draw.line((cx, 0, cx, height), fill="blue", width=3)  # Y
            draw.line((0, cy, width, cy), fill="blue", width=3)  # X

            font = ImageFont.truetype("arial.ttf", 30)
            offset_for_text = 30
            interval = 0.1

            for i in range(10):
                if i > 0:
                    draw.text(
                        (cx + interval * (i) * width // 2, cy),
                        str(i),
                        fill="blue",
                        font=font,
                    )
                    draw.text(
                        (cx - interval * (i) * width // 2, cy),
                        str(-i),
                        fill="blue",
                        font=font,
                    )
                    draw.text(
                        (cx - offset_for_text - 10, cy + interval * (i) * height // 2),
                        str(-i),
                        fill="blue",
                        font=font,
                    )
                draw.text(
                    (cx - offset_for_text, cy - interval * (i) * height // 2),
                    str(i),
                    fill="blue",
                    font=font,
                )

            axes_image_filename = output_dir + "/axes_screen_" + str(tid) + ".jpg"
            screen_image.save(axes_image_filename)

        return screen_image_filename

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
                logger.error(str(e))

        if show:
            # Show the image using matplotlib
            plt.imshow(np.array(img))

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                plt.show()

        return img
