import json

from agent_studio.utils.singleton import ThreadSafeSingleton


class Config(ThreadSafeSingleton):
    """
    Singleton for config.
    """

    api_key_path: str = "agent_studio/config/api_key.json"
    headless: bool = False  # True for CLI, False for GUI
    remote: bool = True  # True for remote, False for local
    min_action_interval: float = 3.0
    env_server_addr: str = "127.0.0.1"
    env_server_host: str = "0.0.0.0"
    vnc_port: int = 5900
    env_server_port: int = 8000
    vnc_password: str = "123456"
    monitor_idx: int = 1  # 1 for the first monitor, 2 for the second monitor
    video_fps: int = 5
    need_human_confirmation: bool = False

    # LM config
    seed: int = 42
    max_retries: int = 3
    temperature: float = 0.0
    top_k: int = 1
    max_tokens: int = 4096
    gemini_api_key: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    openai_api_key: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    anthropic_api_key: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    vertexai_project_id: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    vertexai_location: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"

    # Google API config
    google_credential_path: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    google_calendar_id: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    gmail_recipient: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"

    # VSCode config
    vscode_workspace_path: str = "vscode_workspace"
    vscode_executable_path: str = "code"

    # Pyrogram config
    telegram_workdir: str = "agent_studio/config"
    telegram_api_id: int | str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    telegram_api_hash: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"

    # QA config
    qa_answer_pattern: str = r"\[\[\[(.*?)\]\]\]"

    def __init__(self) -> None:
        with open(self.api_key_path, "r") as f:
            api_keys = json.load(f)
        for api_key in api_keys:
            setattr(self, api_key, api_keys[api_key])

    def __str__(self) -> str:
        return str(self.__dict__)
