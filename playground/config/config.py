import json
from pathlib import Path

from playground.utils.singleton import Singleton


class Config(metaclass=Singleton):
    """
    Singleton for config.
    """

    seed: int = 42
    headless: bool = False  # True for CLI, False for GUI
    python_timeout: int = 10
    need_human_confirmation: bool = True
    minimal_action_interval: float = 3.0

    task_config_paths: dict = {
        "desktop": "playground_data/tasks/filesystem.jsonl",
        # "desktop": "playground_data/tasks/windows_easy.jsonl",
    }
    api_key_path: str = "playground/config/api_key.json"

    stop_code: str = "exit()"

    # Env server config
    remote: bool = True  # True for remote, False for local
    env_type: str = "desktop"
    env_server_addr: str = "127.0.0.1"
    env_server_host: str = "0.0.0.0"
    vnc_port: int = 5900
    env_server_port: int = 8000
    vnc_password: str = "123456"

    # Recorder config
    record_path = "playground_data/trajectories"
    video_fps: int = 5
    mouse_fps: int = 5

    # Human annotator hotkeys
    stop_hotkeys: str = "<ctrl>+<shift>+h"

    # sleep_after_execution: float = 2.0
    max_step: int = 30
    system_prompt_path: str = "playground/agent/prompts/system_prompt.txt"
    init_code_path: str = "playground/agent/prompts/init_code.txt"
    # parsing_failure_th: int = 3
    # repeating_action_failure_th = 3

    # LM config
    provider: str = "gemini"
    agent: str = "direct"
    max_retries: int = 3
    # exec_model: str = "gpt-4-1106-vision-preview"
    exec_model: str = "gemini-pro"
    eval_model: str = "gemini-pro"
    temperature: float = 0.0
    max_tokens: int = 4096
    gemini_api_key: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    openai_api_key: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"

    # Google API config
    google_credential_path: str = "playground/config/credentials.json"
    google_calendar_id: str = "LOAD_FROM_API_KEY_PATH_AUTOMATICALLY"
    gmail_recipient: str = "gduser1@workspacesamples.dev"

    # VSCode config
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
