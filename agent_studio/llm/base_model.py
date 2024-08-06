from typing import Any

from agent_studio.utils.types import MessageList


class BaseModel:
    """Base class for models."""

    name: str = "base"

    def format_messages(
        self,
        raw_messages: MessageList,
    ) -> Any:
        raise NotImplementedError

    def generate_response(
        self, messages: MessageList, **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Generate a response given messages."""
        raise NotImplementedError
