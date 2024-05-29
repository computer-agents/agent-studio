import os
from collections import defaultdict
from multiprocessing.pool import ThreadPool
from typing import Any

import numpy as np
from tqdm import tqdm

from dataclasses import dataclass, field

from agent_studio.llm import BaseModel

Message = dict[str, Any]  # keys role, content
MessageList = list[Message]


@dataclass
class EvalResult:
    """
    Result of running an evaluation (usually consisting of many samples)
    """

    score: float | None  # top-line metric
    conversations: list[MessageList]
    metrics: dict[str, float] | None  # other metrics


@dataclass
class SingleEvalResult:
    """
    Result of evaluating a single sample
    """

    score: float | None
    conversation: MessageList | None = None
    metrics: dict[str, float] = field(default_factory=dict)


class Eval:
    """
    Base class for defining an evaluation.
    """

    def __call__(self, model: BaseModel) -> EvalResult:
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
    conversations = []
    for single_eval_result in single_eval_results:
        for name, value in single_eval_result.metrics.items():
            name2values[name].append(value)
        if single_eval_result.score is not None:
            name2values["score"].append(single_eval_result.score)
        conversations.append(single_eval_result.conversation)
    final_metrics = {}
    for name, values in name2values.items():
        stats = ("mean", "std", "min", "max")
        for stat in stats:
            key = name if stat == "mean" else f"{name}:{stat}"
            final_metrics[key] = _compute_stat(values, stat)
    return EvalResult(
        score=final_metrics.pop("score", None), metrics=final_metrics, conversations=conversations
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
