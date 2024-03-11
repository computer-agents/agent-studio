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


class AgentStudioResponse(BaseModel):
    status: str


class AgentStudioStatusResponse(BaseModel):
    status: str
    content: str = ""


class AgentStudioResultResponse(BaseModel):
    status: str
    result: str
    message: dict | str


class AgentStudioTextRequest(BaseModel):
    message: str


class AgentStudioResetRequest(BaseModel):
    task_config: dict


class AgentStudioEvalRequest(BaseModel):
    task_config: dict
