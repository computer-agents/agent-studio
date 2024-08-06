from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np


@dataclass
class Message:
    role: str
    content: Union[str, np.ndarray, Path]


MessageList = list[Message]
