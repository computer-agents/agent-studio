from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

import numpy as np


@dataclass
class PromptSeg:
    role: str
    content: Union[str, np.ndarray, Path]


@dataclass
class TrajectorySeg:
    obs: np.ndarray | None
    prompt: list[PromptSeg]
    response: str | None
    info: dict[str, Any]
    act: str
    res: dict[str, Any]
    timestamp: float
    annotation: dict[str, Any] | None = None


class BaseModel:
    """Base class for models."""

    name: str = "base"

    def compose_messages(
        self,
        intermediate_msg: list[PromptSeg],
    ) -> Any:
        raise NotImplementedError

    def generate_response(
        self, messages: list[PromptSeg], **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Generate a response given messages."""
        raise NotImplementedError
