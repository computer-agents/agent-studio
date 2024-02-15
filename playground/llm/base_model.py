from typing import Any

from numpy.typing import NDArray


class BaseModel:
    """Base class for models."""

    def _compose_messages(
        self,
        obs: NDArray | None,
        trajectory: list[dict[str, Any]],
        system_prompt: str,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Generate a response given messages."""
        raise NotImplementedError
