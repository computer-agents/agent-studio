import os
from pathlib import Path

from playground.utils.singleton import Singleton


class Config(metaclass=Singleton):
    """Singleton for config.

    Attributes:
        seed: The random seed.
        resolution: The resolution of the screen.
        video_fps: The FPS of the video.
    """

    seed: int = 42
    python_timeout: int = 10

    task_config_paths: dict = {
        "desktop": "playground/tasks/desktop.jsonl",
    }

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

    def __init__(self) -> None:
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.log_dir = os.path.join(project_root, "./logs/")
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        return str(self.__dict__)
