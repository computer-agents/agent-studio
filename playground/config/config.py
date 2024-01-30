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
    resolution: tuple[int, int] = (1920, 1080)
    video_fps: int = 4
    log_dir: str = "logs"

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
