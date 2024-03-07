import json
from pathlib import Path

from playground.utils.singleton import Singleton


class Config(metaclass=Singleton):
    """
    Config class for agent server. Do not change the default values.
    """

    seed: int = 42
    headless: bool = False
    python_timeout: int = 10
    need_human_confirmation: bool = True

    # Env server config
    remote: bool = False
    env_type: str = "desktop"
    env_server_host: str = "0.0.0.0"
    env_server_port: int = 8000

    api_key_path: str = "playground/config/api_key.json"

    google_credential_path: str = "playground/config/credentials.json"
    google_calendar_id: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    gmail_recipient: str = "gduser1@workspacesamples.dev"
    vscode_workspace_path: str = "tmp/vscode_workspace"
    vscode_executable_path: str = "code"

    # Pyrogram config
    telegram_workdir: str = "playground/config"
    telegram_api_id: int | str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    telegram_api_hash: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"

    project_root: Path = Path(__file__).resolve().parents[2]
    log_dir: Path = project_root / "logs/"

    def __init__(self) -> None:
        with open(self.api_key_path, "r") as f:
            api_keys = json.load(f)
        for api_key in api_keys:
            setattr(self, api_key, api_keys[api_key])
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        return str(self.__dict__)
