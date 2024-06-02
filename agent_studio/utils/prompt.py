from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
from typing import Union

import numpy as np
import toml


logger = logging.getLogger(__name__)


@dataclass
class PromptSeg:
    role: str
    content: Union[str, np.ndarray, Path]


class PromptTag(Enum):
    """
    Prompt tags. Defines the type of prompt.
    """
    NONE = "none"
    SYSTEM = "system"
    EVALUATOR = "evaluator"


class Prompt:
    """
    Args:
        name (str): The name of the prompt. Here is the file relative path.
        prompt (str): The prompt string.
        tag (PromptTag): Not used.
        params (dict[str, str], optional): The parameters of the prompt. Defaults to {}.
        parent (str | None, optional): The parent prompt name. Defaults to None.
    """

    def __init__(
        self,
        name: str,
        prompt: str,
        tag: PromptTag,
        params: dict[str, str] = {},
        parent: str | None = None
    ) -> None:
        self.name = name
        self.prompt = prompt
        self.tag = tag
        self.params: dict[str, str] = params
        self.parent: str | None = parent
        self.children: set[Prompt] = set()

    def list(self, indent: int = 0) -> str:
        return f"├{'─' * indent}{self.name}\n" + "".join(
            [child.list(indent + 2) for child in self.children]
        )

    def compose(self, use_tag: bool = False) -> str:
        prompt = self.prompt
        for name, param in self.params.items():
            prompt = prompt.replace(f"{{{name}}}", param)

        for child in self.children:
            prompt += f"{child.compose(use_tag)}"

        return prompt


class SysPromptComposer:

    def __init__(self, prompt_path_base: str = "agent_studio/agent/prompts") -> None:
        self.prompts: dict[str, Prompt] = {}
        self.prompt_path_base: str = prompt_path_base
        self.root: Prompt | None = None

    def add(self, prompt_name: str) -> Prompt:
        """
        Add a prompt and all its parents to the composer.
        """
        if prompt_name in self.prompts:
            return self.prompts[prompt_name]
        file_path = Path.joinpath(Path(self.prompt_path_base),
                                  Path(prompt_name)).with_suffix(".toml")
        if not file_path.exists():
            raise ValueError(f"Prompt {prompt_name} does not exist")
        with open(file_path, "r") as f:
            data = toml.load(f)
            prompt_text = data.get("prompt", {}).get("text", None)
            if not prompt_text:
                raise ValueError(f"Prompt file {prompt_name} does not have prompt")
            prompt = Prompt(
                name=prompt_name,
                prompt=prompt_text,
                tag=PromptTag.NONE,
                parent=data.get("prompt", {}).get("parent", None),
            )
        self.prompts[prompt.name] = prompt
        logger.info(f"Adding prompt {prompt_name}, parent: {prompt.parent}")
        if prompt.parent:
            parent = self.add(prompt.parent)
            parent.children.add(prompt)
        else:
            self.root = prompt
        return prompt

    def list(self) -> str:
        if self.root is None:
            raise ValueError("No prompt added")
        return self.root.list()

    def compose(self, use_tag: bool = False, dry_run: bool = False) -> str:
        if self.root is None:
            raise ValueError("No prompt added")
        prompt = self.root.compose(use_tag=use_tag)

        return prompt
