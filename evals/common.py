import base64
import os
from io import BytesIO
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any

import jinja2
import matplotlib
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from tqdm import tqdm

matplotlib.use("Agg")  # Use the 'Agg' backend for non-GUI environments


Message = dict[str, Any]  # keys role, content
MessageList = list[Message]


def map_with_progress(f: callable, xs: list[Any], num_threads: int = 50):
    """
    Apply f to each element of xs, using a ThreadPool, and show progress.
    """
    if os.getenv("debug"):
        return list(map(f, tqdm(xs, total=len(xs))))
    else:
        with ThreadPool(min(num_threads, len(xs))) as pool:
            return list(tqdm(pool.imap(f, xs), total=len(xs)))


HTML_JINJA = """
<h3>Prompt</h3>
{% for message in prompt_messages %}
{{ message_to_html(message) | safe }}
{% endfor %}
<h3>Response</h3>
{{ message_to_html(next_message) | safe }}
<h3>Results</h3>
{{ render_image(prompt_messages, correct_bbox, pred_coord) | safe }}
<p>Correct Bounding Box: {{ correct_bbox }}</p>
<p>Predicted Coordinate: {{ pred_coord }}</p>
<p>Score: {{ score }}</p>
"""


jinja_env = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    undefined=jinja2.StrictUndefined,
    autoescape=jinja2.select_autoescape(["html", "xml"]),
)
_message_template = """
<div class="message {{ role }}">
    <div class="role">
    {{ role }}
    {% if variant %}<span class="variant">({{ variant }})</span>{% endif %}
    </div>
    <div class="content">
    <pre>{{ content }}</pre>
    </div>
</div>
"""


def message_to_html(message: Message) -> str:
    """
    Generate HTML snippet (inside a <div>) for a message.
    """
    return jinja_env.from_string(_message_template).render(
        role=message["role"],
        content=message["content"],
        variant=message.get("variant", None),
    )


def render_image(prompt_messages: MessageList, bbox, pred_coord):
    """
    Generate an image with bounding boxes and save it.
    """
    for message in prompt_messages:
        content = message["content"]
        if isinstance(content, Path):
            content = content.as_posix()
        if isinstance(content, str):
            if content.endswith((".png", ".jpg", ".jpeg")):
                image = Image.open(content).convert("RGB")
            else:
                continue
        elif isinstance(content, Image.Image):
            image = content
        elif isinstance(content, np.ndarray):
            image = Image.fromarray(content).convert("RGB")
        else:
            raise ValueError(f"Unknown message type: {content}")

        img_width, img_height = image.size
        dpi = 40
        figsize = img_width / float(dpi), img_height / float(dpi)

        # Plot image
        fig, ax = plt.subplots(1, figsize=figsize)
        ax.imshow(image)

        # Plot bounding box
        left, top, right, bottom = bbox
        rect = patches.Rectangle(
            (left, top),
            right - left,
            bottom - top,
            linewidth=6,
            edgecolor="r",
            facecolor="none",
        )
        ax.add_patch(rect)

        # Plot predicted coordinate
        if pred_coord is not None:
            x, y = pred_coord
            ax.plot(x, y, "ro", markersize=10)

        plt.axis("off")

        # Save the new image to a BytesIO object
        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=dpi)
        plt.close(fig)

        # Encode the image in base64
        base64_image = base64.b64encode(buf.getvalue()).decode("utf-8")

        image.close()

        return f'<div><img src="data:image/png;base64,{base64_image}" alt="Image with bounding box"></div>'  # noqa: E501


jinja_env.globals["message_to_html"] = message_to_html
jinja_env.globals["render_image"] = render_image


_report_template = """<!DOCTYPE html>
<html>
    <head>
        <style>
            .message {
                padding: 8px 16px;
                margin-bottom: 8px;
                border-radius: 4px;
            }
            .message.user {
                background-color: #B2DFDB;
                color: #00695C;
            }
            .message.assistant {
                background-color: #B39DDB;
                color: #4527A0;
            }
            .message.system {
                background-color: #EEEEEE;
                color: #212121;
            }
            .role {
                font-weight: bold;
                margin-bottom: 4px;
            }
            .variant {
                color: #795548;
            }
            table, th, td {
                border: 1px solid black;
            }
            pre {
                white-space: pre-wrap;
            }
        </style>
    </head>
    <body>
    {% if metrics %}
    <h1>Metrics</h1>
    <table>
    <tr>
        <th>Metric</th>
        <th>Value</th>
    </tr>
    <tr>
        <td><b>Score</b></td>
        <td>{{ score | float | round(3) }}</td>
    </tr>
    {% for name, value in metrics.items() %}
    <tr>
        <td>{{ name }}</td>
        <td>{{ value }}</td>
    </tr>
    {% endfor %}
    </table>
    {% endif %}
    <h1>Examples</h1>
    {% for html in htmls %}
    {{ html | safe }}
    <hr>
    {% endfor %}
    </body>
</html>
"""


def make_report(score: float, metrics: dict[str, float], htmls: list[str]) -> str:
    """
    Create a standalone HTML report from an EvalResult.
    """
    return jinja_env.from_string(_report_template).render(
        score=score,
        metrics=metrics,
        htmls=htmls,
    )
