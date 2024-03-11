import base64
import io
import os
import re

import cv2
import numpy as np
from PIL import Image


def extract_from_response(response: str, backtick="```") -> str:
    if backtick == "```":
        # Matches anything between ```<optional label>\n and \n```
        pattern = r"```(?:[a-zA-Z]*)\n?(.*?)\n?```"
    elif backtick == "`":
        pattern = r"`(.*?)`"
    else:
        raise ValueError(f"Unknown backtick: {backtick}")
    match = re.search(
        pattern, response, re.DOTALL
    )  # re.DOTALL makes . match also newlines
    if match:
        extracted_string = match.group(1)
    else:
        extracted_string = ""

    return extracted_string


def encode_image(image: str | Image.Image | np.ndarray | None) -> str:
    if isinstance(image, str):
        if os.path.exists(image):
            with open(image, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
            image_type = image.split(".")[-1].lower()
            encoded_image = f"data:image/{image_type};base64,{encoded_image}"
        else:
            encoded_image = image
    elif isinstance(image, Image.Image):  # PIL image
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        encoded_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        encoded_image = f"data:image/jpeg;base64,{encoded_image}"
    elif isinstance(image, np.ndarray):  # cv2 image array
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # convert to RGB
        image = Image.fromarray(image)
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        encoded_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
        encoded_image = f"data:image/jpeg;base64,{encoded_image}"
    else:
        raise ValueError(
            "Invalid image type. Please provide a valid image path, PIL "
            "image, or cv2 image array."
        )

    return encoded_image
