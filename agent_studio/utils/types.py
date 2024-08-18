from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np
from pydantic import BaseModel


@dataclass
class Message:
    role: str
    content: Union[str, np.ndarray, Path]


MessageList = list[Message]


class Action(BaseModel):
    action_id: str | None
    obs_before: str | None
    obs_after: str | None
    operation: str
    bbox: dict | None
    metadata: dict[str, str | int | float | list | dict | None]


class Episode(BaseModel):
    instruction: str
    annotation_id: str
    actions: list[Action]
    source: str
    platform: str
    metadata: dict[str, str | int | float | dict]
    action_space: list[str]
    is_success: bool


class InverseAction(Action):
    instruction: str
    source: str
    platform: str
    action_space: list[str]
