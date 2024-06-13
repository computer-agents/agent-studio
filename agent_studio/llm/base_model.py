from dataclasses import dataclass
from typing import Any

import numpy as np

from agent_studio.utils.prompt import PromptSeg


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
