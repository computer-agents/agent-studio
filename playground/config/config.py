from dataclasses import dataclass, field
from pathlib import Path

from playground.utils.singleton import Singleton


@dataclass(frozen=True)
class Config(metaclass=Singleton):
    """
    Singleton for config.
    """

    seed: int = 42
    python_timeout: int = 10

    task_config_paths: dict = field(default_factory=lambda: {
        "desktop": "playground/tasks/desktop.jsonl",
    })

    stop_code: str = "\nexit()"
    use_video = False

    # Recorder config
    record_path = "playground_data/trajectories"
    video_fps: int = 5
    mouse_fps: int = 5

    # Human annotator hotkeys
    stop_hotkeys: str = "<ctrl>+<shift>+s"

    # sleep_after_execution: float = 2.0
    max_step: int = 30
    system_prompt_path: str = "playground/agent/prompts/system_prompt.txt"
    # parsing_failure_th: int = 3
    # repeating_action_failure_th = 3

    # LM config
    provider: str = "openai"
    max_retries: int = 3
    model: str = "gpt-4-1106-vision-preview"
    eval_model: str = "gpt-4-1106-vision-preview"
    temperature: float = 0.0
    max_tokens: int = 4096
    OPENAI_API_KEY: str = "your_openai_api_key"

    google_credential_path: str = "playground/config/credentials.json"
    google_calendar_id: str = "primary"
    gmail_recipient: str = "gduser1@workspacesamples.dev"
    vscode_workspace_path: str = "tmp/vscode_workspace"
    vscode_executable_path: str = "code"

    # Pyrogram config
    telegram_workdir: str = "playground/config"
    telegram_api_id: int | str = "your telegram_api_id"
    telegram_api_hash: str = "your_telegram_api_hash"

    project_root: Path = Path(__file__).resolve().parents[2]
    log_dir: Path = project_root / "logs/"

    def __init__(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        return str(self.__dict__)
