from typing import Any

from playground.utils.singleton import Singleton


class BaseModel(metaclass=Singleton):
    """Base class for models."""

    def generate_response(
        self, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[str, dict[str, int]]:
        """Generate a response given messages."""
        raise NotImplementedError
