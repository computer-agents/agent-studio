from typing import Any


class BaseModel:
    """Base class for models."""

    def __init__(self) -> None:
        self.token_count: int = 0

    def reset(self) -> None:
        self.token_count: int = 0

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
