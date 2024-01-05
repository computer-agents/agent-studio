"""Config for environments."""
import argparse
import dataclasses
from dataclasses import dataclass
from typing import Any, List


@dataclass(frozen=True)
class ComputerEnvConfig:
    """A config for the computer env.

    Attributes:
        resolution: The resolution of the screen.
        video_fps: The FPS of the video.
    """

    resolution: List[int] = [1920, 1080]
    video_fps: int = 4
    gen_config: dict[str, Any] = dataclasses.field(default_factory=dict)


def construct_computer_env_config(args: argparse.Namespace) -> ComputerEnvConfig:
    computer_env_config = ComputerEnvConfig(
        resolution=args.resolution, video_fps=args.video_fps
    )
    return computer_env_config
