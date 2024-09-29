from dataclasses import dataclass
from pathlib import Path
from typing import Union, Optional, Any

import numpy as np
from pydantic import BaseModel


@dataclass
class Message:
    role: str
    content: Union[str, np.ndarray, Path]


MessageList = list[Message]


@dataclass
class StepInfo:
    """ We don't use pydantic for StepInfo because we need to save images in it. """
    obs: np.ndarray | None
    prompt: MessageList | None
    response: str | None
    action: str
    info: dict[str, Any]
    result: dict[str, Any]
    timestamp: float


TrajectoryInfo = list[StepInfo]


class Procedure(BaseModel):
    evaluator: str
    function: str
    params: dict


class TaskConfig(BaseModel):
    task_id: str
    instruction: str
    visual: bool
    max_steps: int
    max_time: float
    eval_procedure: list[Procedure]
    reset_procedure: Optional[list[Procedure]] = None
    cleanup_procedure: Optional[list[Procedure]] = None


class SavedMessage(BaseModel):
    role: str
    content: Union[str, Path]


class SavedStepInfo(BaseModel):
    obs: str | None
    prompt: list[SavedMessage] | None
    response: str | None
    action: str
    info: dict[str, Any]
    result: dict[str, Any]
    timestamp: float


class VideoMeta(BaseModel):
    fps: int
    frame_count: int
    video_path: str
    width: int
    height: int


class TaskResult(BaseModel):
    task_id: str
    instruction: str
    score: float
    feedback: str
    token_count: int
    time_cost: float
    video: Optional[VideoMeta]
    trajectory: list[SavedStepInfo]


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
