import json

from agent_studio.utils.singleton import ThreadSafeSingleton


class Config(metaclass=ThreadSafeSingleton):
    """
    Singleton for config.
    """

    api_key_path: str = "agent_studio/config/api_key.json"
    min_action_interval: float = 3.0
    video_fps: int = 5
    need_human_confirmation: bool = False

    # LM config
    seed: int = 42
    max_retries: int = 3
    temperature: float = 0.0
    max_tokens: int = 4096

    # VSCode config
    vscode_workspace_path: str = "vscode_workspace"
    vscode_executable_path: str = "code"

    # Pyrogram config
    telegram_workdir: str = "agent_studio/config"

    # QA config
    qa_answer_pattern: str = r"\[\[\[(.*?)\]\]\]"

    def __init__(self) -> None:
        with open(self.api_key_path, "r") as f:
            api_keys = json.load(f)
        for api_key in api_keys:
            setattr(self, api_key, api_keys[api_key])

    def __str__(self) -> str:
        return str(self.__dict__)
