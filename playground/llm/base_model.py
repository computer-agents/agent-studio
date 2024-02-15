class BaseModel:
    """Base class for models."""

    def generate_response(self, messages: list, **kwargs) -> tuple[str, dict[str, int]]:
        """Generate a response given messages."""
        raise NotImplementedError
