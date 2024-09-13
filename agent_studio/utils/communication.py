import base64
import pickle
from typing import Any, Callable

from pydantic import BaseModel

from agent_studio.utils.types import TaskConfig

bytes2str: Callable[..., str] = lambda x: base64.b64encode(pickle.dumps(obj=x)).decode(
    "utf-8"
)

str2bytes: Callable[..., Any] = lambda x: (
    pickle.loads(base64.b64decode(x.encode("utf-8")))
    if isinstance(x, str)
    else "Error encoding string to bytes"
)


class AgentStudioStatusResponse(BaseModel):
    status: str
    content: str = ""
    message: dict | str = ""


class AgentStudioTextRequest(BaseModel):
    message: str


class AgentStudioResetRequest(BaseModel):
    task_config: TaskConfig


class AgentStudioEvalRequest(BaseModel):
    task_config: TaskConfig
    kwargs: str
