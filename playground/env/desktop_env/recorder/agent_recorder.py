import logging
import os
import platform
import time

import pyautogui
from numpy.typing import NDArray

from playground.config import Config
from playground.env.desktop_env.recorder.base_recorder import Event, Recorder
from playground.env.desktop_env.recorder.screen_recorder import ScreenRecorder
from playground.utils.json_utils import add_jsonl

config = Config()
logger = logging.getLogger(__name__)


if platform.system() == "Windows":
    from ctypes import windll  # type: ignore

    PROCESS_PER_MONITOR_DPI_AWARE = 2
    windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)


class AgentRecorder(Recorder):
    """The recorder for agent code and screen recording."""

    def __init__(
        self,
        record_path: str,
        video_fps: int = config.video_fps,
    ):
        self.record_path: str = record_path
        width, height = pyautogui.size()
        self.screen_region: dict[str, int] = {
            "left": 0,
            "top": 0,
            "width": width,
            "height": height,
        }
        self.screen_recorder = ScreenRecorder(
            screen_region=self.screen_region,
            fps=video_fps,
        )

    def reset(self, **kwargs) -> None:
        task_id: str = kwargs["task_id"]
        instruction: str = kwargs["instruction"]
        self.record_screen: bool = kwargs.get("record_screen", True)
        self.video_path: str = os.path.join(self.record_path, f"{task_id}.mp4")
        self.record_dict: dict = {"task_id": task_id, "instruction": instruction}
        self.events: list[Event] = []
        if self.record_screen:
            self.screen_recorder.reset()

    def start(self) -> None:
        assert self.record_screen
        self.screen_recorder.start()

    def stop(self) -> None:
        assert self.record_screen
        self.screen_recorder.stop()

    def pause(self):
        assert self.record_screen
        self.screen_recorder.pause()
        self.events.append(Event(time.time(), "pause", {}))

    def resume(self):
        assert self.record_screen
        self.screen_recorder.resume()
        self.events.append(Event(time.time(), "resume", {}))

    def add_event(self, code: str) -> None:
        self.events.append(Event(time.time(), "code", code))

    def save(self) -> None:
        self.start_time = self.screen_recorder.start_time
        self.stop_time = self.screen_recorder.stop_time
        if self.record_screen:
            self.screen_recorder.save(self.video_path, start_frame_id=0)
            self.record_dict["video"] = {
                "metadata": {
                    "region": self.screen_region,
                    "fps": self.screen_recorder.fps,
                    "duration": round(self.stop_time - self.start_time, 2),
                },
                "path": self.video_path,
            }
        else:
            self.record_dict["video"] = None

        if len(self.events) > 0:
            self.record_dict["actions"] = []
            for event in self.events:
                self.record_dict["actions"].append(
                    {
                        "timestep": round(event.time - self.start_time, 2),
                        "type": event.event_type,
                        "data": event.data,
                    }
                )
        else:
            self.record_dict["actions"] = None

        add_jsonl(
            data=[self.record_dict],
            file_path=os.path.join(self.record_path, "tasks.jsonl"),
        )

    def get_screenshot(self) -> NDArray:
        return self.screen_recorder.current_frame
