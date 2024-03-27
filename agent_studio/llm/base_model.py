from typing import Any


class BaseModel:
    """Base class for models."""

    name: str = "base"

    def compose_messages(
        self,
        intermediate_msg: list[dict[str, Any]],
    ) -> Any:
        raise NotImplementedError

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Generate a response given messages."""
        raise NotImplementedError
