import base64
import pickle
from typing import Any, Callable

from pydantic import BaseModel

bytes2str: Callable[..., str] = lambda x: base64.b64encode(pickle.dumps(obj=x)).decode(
    "utf-8"
)

str2bytes: Callable[..., Any] = (
    lambda x: pickle.loads(base64.b64decode(x.encode("utf-8")))
    if isinstance(x, str)
    else "Error encoding string to bytes"
)


class PlaygroundResponse(BaseModel):
    status: str


class PlaygroundStatusResponse(BaseModel):
    status: str
    content: str = ""


class PlaygroundResultResponse(BaseModel):
    status: str
    result: str
    message: dict | str


class PlaygroundTextRequest(BaseModel):
    message: str


class PlaygroundResetRequest(BaseModel):
    task_config: dict


class PlaygroundEvalRequest(BaseModel):
    task_config: dict
    trajectory: str
