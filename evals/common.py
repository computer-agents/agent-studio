import os
from collections import defaultdict
from multiprocessing.pool import ThreadPool
from typing import Any
import numpy as np
from tqdm import tqdm
import jinja2
from dataclasses import dataclass, field
import base64
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from agent_studio.llm import BaseModel

Message = dict[str, Any]  # keys role, content
MessageList = list[Message]


@dataclass
class EvalResult:
    """
    Result of running an evaluation (usually consisting of many samples)
    """

    score: float | None  # top-line metric
    logs: list[dict]  # log to jsonl
    htmls: list[str]  # strings of valid HTML
    metrics: dict[str, float] | None  # other metrics


@dataclass
class SingleEvalResult:
    """
    Result of evaluating a single sample
    """

    score: float | None
    log: dict = field(default_factory=dict)
    html: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)


class Eval:
    """
    Base class for defining an evaluation.
    """

    def __call__(self, model_name: str, tokenizer_name: str, num_workers: int = 1) -> EvalResult:
        raise NotImplementedError


def _compute_stat(values: list, stat: str):
    if stat == "mean":
        return np.mean(values)
    elif stat == "std":
        return np.std(values)
    elif stat == "min":
        return np.min(values)
    elif stat == "max":
        return np.max(values)
    else:
        raise ValueError(f"Unknown {stat =}")


def aggregate_results(
    single_eval_results: list[SingleEvalResult],
) -> EvalResult:
    """
    Aggregate results from multiple evaluations into a single EvalResult.
    """
    name2values = defaultdict(list)
    htmls = []
    logs = []
    for single_eval_result in single_eval_results:
        for name, value in single_eval_result.metrics.items():
            name2values[name].append(value)
        if single_eval_result.score is not None:
            name2values["score"].append(single_eval_result.score)
        htmls.append(single_eval_result.html)
        logs.append(single_eval_result.log)
    final_metrics = {}
    for name, values in name2values.items():
        stats = ("mean",)
        for stat in stats:
            key = name if stat == "mean" else f"{name}:{stat}"
            final_metrics[key] = float(_compute_stat(values, stat))
    return EvalResult(
        score=final_metrics.pop("score", None), metrics=final_metrics, htmls=htmls, logs=logs
    )


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
        role=message["role"], content=message["content"], variant=message.get("variant", None)
    )


def render_image(prompt_messages: MessageList, bbox, pred_coord):
    """
    Generate an image with bounding boxes and save it.
    """
    for message in prompt_messages:
        content = message["content"]
        if content.endswith((".png", ".jpg", ".jpeg")):
            # Load the image
            image = Image.open(content)
            img_width, img_height = image.size
            dpi = 40
            figsize = img_width / float(dpi), img_height / float(dpi)

            # Plot image
            fig, ax = plt.subplots(1, figsize=figsize)
            ax.imshow(image)

            # Plot bounding box
            left, top, right, bottom = bbox
            rect = patches.Rectangle((left, top), right-left, bottom-top, linewidth=2, edgecolor='r', facecolor='none')
            ax.add_patch(rect)

            # Plot predicted coordinate
            if pred_coord is not None:
                x, y = pred_coord
                ax.plot(x, y, 'ro')  # red point

            plt.axis('off')

            # Save the new image to a BytesIO object
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, dpi=dpi)
            plt.close(fig)

            # Encode the image in base64
            base64_image = base64.b64encode(buf.getvalue()).decode('utf-8')

            return f'<div><img src="data:image/png;base64,{base64_image}" alt="Image with bounding box"></div>'


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


def make_report(eval_result: EvalResult) -> str:
    """
    Create a standalone HTML report from an EvalResult.
    """
    return jinja_env.from_string(_report_template).render(
        score=eval_result.score,
        metrics=eval_result.metrics,
        htmls=eval_result.htmls,
    )


def make_report_from_example_htmls(htmls: list[str]):
    """
    Create a standalone HTML report from a list of example htmls
    """
    return jinja_env.from_string(_report_template).render(score=None, metrics={}, htmls=htmls)
