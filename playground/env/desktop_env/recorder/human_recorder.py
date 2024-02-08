import logging
import os
import platform

import pyautogui

from playground.config import Config
from playground.env.desktop_env.recorder.base_recorder import MODE, Event, Recorder
from playground.env.desktop_env.recorder.keyboard_recorder import KeyboardRecorder
from playground.env.desktop_env.recorder.mouse_recorder import MouseRecorder
from playground.env.desktop_env.recorder.screen_recorder import ScreenRecorder
from playground.utils.json_utils import add_jsonl

config = Config()
logger = logging.getLogger(__name__)


if platform.system() == "Windows":
    from ctypes import windll  # type: ignore

    PROCESS_PER_MONITOR_DPI_AWARE = 2
    windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)


class HumanRecorder(Recorder):
    """The recorder for keyboard-mouse events, code, and screen recording."""

    def __init__(
        self,
        record_path: str = config.record_path,
        video_fps: int = config.video_fps,
        mouse_fps: int = config.mouse_fps,
    ):
        self.record_path: str = record_path
        width, height = pyautogui.size()
        self.screen_region: dict[str, int] = {
            "left": 0,
            "top": 0,
            "width": width,
            "height": height,
        }

        self.keyboard_recorder = KeyboardRecorder(
            {
                "stop": (config.stop_hotkeys, self.stop),
            }
        )
        self.mouse_recorder = MouseRecorder(mouse_fps)
        self.screen_recorder = ScreenRecorder(
            screen_region=self.screen_region,
            fps=video_fps,
        )

    def reset(self, **kwargs) -> None:
        task_id = kwargs.get("task_id")
        instruction = kwargs.get("instruction")
        self.record_screen: bool = kwargs.get("record_screen", True)
        self.video_path: str = os.path.join(self.record_path, f"{task_id}.mp4")
        self.record_dict: dict = {"task_id": task_id, "instruction": instruction}
        self.events: list[Event] = []
        self.prev_mode: MODE = MODE.INIT
        if self.record_screen:
            self.keyboard_recorder.reset()
            self.mouse_recorder.reset()
            self.screen_recorder.reset()

    def start(self) -> None:
        assert self.record_screen
        self.keyboard_recorder.start()
        self.mouse_recorder.start()
        self.screen_recorder.start()

    def stop(self) -> None:
        assert self.record_screen
        self.screen_recorder.stop()
        self.mouse_recorder.stop()
        self.keyboard_recorder.stop()

    def wait_exit(self) -> None:
        try:
            logger.info("Waiting for exit...")
            self.keyboard_recorder.wait_exit()
            self.mouse_recorder.wait_exit()
            self.screen_recorder.wait_exit()
        finally:
            logger.info("Saving recording...")
            self.save()

    def save(self) -> None:
        self.start_time = max(
            self.screen_recorder.start_time,
            self.mouse_recorder.start_time,
            self.keyboard_recorder.start_time,
        )
        self.stop_time = min(
            self.screen_recorder.stop_time,
            self.mouse_recorder.stop_time,
            self.keyboard_recorder.stop_time,
        )
        valid_mouse_events = self.mouse_recorder.filter_recorded_events(
            self.start_time, self.stop_time
        )
        valid_key_events = self.keyboard_recorder.filter_recorded_events(
            self.start_time, self.stop_time
        )
        self.events += valid_mouse_events + valid_key_events

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
            self.events.sort()
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
            self.record_dict["events"] = None

        add_jsonl(
            data=[self.record_dict],
            file_path=os.path.join(self.record_path, "tasks.jsonl"),
        )
