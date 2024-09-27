import ast
import importlib
import logging
import os

from agent_studio.llm.base_model import BaseModel
from agent_studio.utils.singleton import ThreadSafeSingleton

logger = logging.getLogger(__name__)


def register_models(
    base_path: str = "agent_studio/llm",
) -> dict[str, type[BaseModel]]:
    registered_classes = {}
    for file in os.listdir(base_path):
        if file.endswith(".py"):
            file_path = os.path.join(base_path, file)

            # Parse the Python file
            with open(file_path, "r") as f:
                file_contents = f.read()
            try:
                tree = ast.parse(file_contents)
            except SyntaxError:
                logger.error(f"Error parsing {file_path}. Skipping...")
                continue
            # Check each class definition in the file
            for node in ast.walk(tree):
                module_name = (
                    os.path.relpath(file_path, ".").replace(os.sep, ".").rstrip(".py")
                )
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "BaseModel":
                            try:
                                module = importlib.import_module(module_name)
                                new_class: type[BaseModel] | None = getattr(
                                    module, node.name, None
                                )
                                if (
                                    new_class is not None
                                    and new_class.name not in registered_classes
                                ):
                                    registered_classes[new_class.name] = new_class
                                else:
                                    raise AttributeError
                            except Exception as e:
                                logger.error(
                                    f"Error importing {module_name} {node.name}. "
                                    f"Due to {e}. Skipping..."
                                )
                            break
    return registered_classes


MODEL_PROVIDER_MAPPING = {
    "gpt-4o-2024-08-06": "openai",
    "gpt-4o-2024-05-13": "openai",
    "gpt-4-turbo-2024-04-09": "openai",
    "gemini-pro-vision": "gemini",
    "gemini-1.0-pro-001": "gemini",
    "gemini-1.5-pro-001": "vertexai",
    "gemini-1.5-flash-001": "gemini",
    "claude-3-haiku-20240307": "claude",
    "claude-3-sonnet-20240229": "claude",
    "claude-3-5-sonnet-20240620": "claude",
    "claude-3-5-sonnet@20240620": "vertexai-anthropic",
    "dummy": "dummy",
}


class ModelManager(metaclass=ThreadSafeSingleton):
    """
    A class to manage the model providers.
    It provides a method to get a new model instance
    """

    def __init__(self):
        self.models = register_models()

    def get_model(self, model_name: str) -> BaseModel:
        """
        Get a new model instance based on the model name.

        Args:
            model_name: The name of the model to get.

        Returns:
            The model instance.

        Raises:
            ValueError: If the model provider is not registered
        """
        if model_name not in MODEL_PROVIDER_MAPPING:
            logger.info(
                f"Model name '{model_name}' is not mapped to a provider, "
                "defaulting to huggingface"
            )
        provider_name = MODEL_PROVIDER_MAPPING.get(model_name, "huggingface")
        if provider_name not in self.models:
            logger.error(f"Model provider '{provider_name}' is not registered")
            raise ValueError(f"Model provider '{provider_name}' is not registered")
        else:
            logger.info(f"Setting up model provider: {provider_name}")
            model = self.models[provider_name]()

        return model


__all__ = [
    "ModelManager",
]
