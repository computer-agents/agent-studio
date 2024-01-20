import json
import logging

# import keyboard
import os
import re
import subprocess as sp
import time
import uuid
from typing import Callable

from playground.desktop_env.recorder.base_recorder import (
    MODE,
    OS,
    Event,
    MouseOptions,
    Recorder,
)
from playground.desktop_env.recorder.keyboard_recorder import KeyboardRecorder
from playground.desktop_env.recorder.mouse_recorder import MouseRecorder
from playground.desktop_env.recorder.video_recorder import VideoRecorder

logger = logging.getLogger(__name__)


class AllinOneRecorder(Recorder):
    def __init__(
        self,
        mouse_options: MouseOptions,
        video_path: str,
        video_screen_region: dict[str, int],
        video_fps: int,
        output_file: str,
        mouse_fps: int = 10,
    ):
        self.video_path: str = video_path
        self.video_available: bool = False
        self.video_screen_region: dict[str, int] = video_screen_region
        self.output_file: str = output_file
        self.events: list[Event] = []
        self.prev_mode: MODE | None = None
        self.shebang_template = re.compile(r"^#!\s*(.+)")
        self.code_path = f"{str(uuid.uuid4())}.txt"
        self.mouse_recorder = MouseRecorder(mouse_options, mouse_fps)
        self.keyboard_recorder = KeyboardRecorder(
            {
                "stop": ("<ctrl>+<shift>+s", self.stop),
                "code": ("<ctrl>+<shift>+c", lambda: self.__set_mode(MODE.CODING)),
                "type": ("<ctrl>+<shift>+x", lambda: self.__set_mode(MODE.TYPING)),
            }
        )
        self.video_recorder = VideoRecorder(
            video_path=self.video_path,
            screen_region=video_screen_region,
            fps=video_fps,
        )

    def __save_code(self) -> None:
        if os.path.exists("code.txt"):
            with open("code.txt", "r") as f:
                code = f.read()
            if len(code) > 0:
                firstline = code.split("\n")[0]
                res = re.match(self.shebang_template, firstline)
                if res is not None:
                    interpreter = res.group(1)
                    code = "\n".join(code.split("\n")[1:])
                else:
                    interpreter = "unknown"
                code_event = self.events.pop()
                code_event.data = {"interpreter": interpreter, "code": code}
                self.events.append(code_event)

    def __set_mode(self, mode: MODE) -> None:
        if mode != self.prev_mode:
            self.events.append(Event(time.time(), "switch_mode", {"mode": mode.name}))
            logger.info(f"set mode to {mode}")
            self.mouse_recorder.set_mode(mode)
            self.keyboard_recorder.set_mode(mode)
            self.video_recorder.set_mode(mode)
            if mode == MODE.CODING:
                print(
                    "Coding mode, mouse and keyboard events will be ignored\n"
                    "please edit code.txt and save it\n"
                    "typing '#!<interpreter>' at the first line\n"
                )
                if not os.path.exists(self.code_path):
                    with open(self.code_path, "w") as f:
                        f.write("")
                if "Windows" in OS:
                    sp.Popen(["notepad.exe", self.code_path])
                elif "Linux" in OS:
                    sp.Popen(["gedit", self.code_path])
                elif "Darwin" in OS:
                    sp.Popen(["open", "-e", self.code_path])
                else:
                    logger.error("OS not supported")
                    self.stop()
                self.events.append(Event(time.time(), "code", {}))
            elif mode == MODE.TYPING:
                if not self.video_available:
                    self.video_available = True
                print("Typing mode, recording mouse and keyboard events\n")
                if self.prev_mode == MODE.CODING:
                    self.__save_code()
            else:
                assert False, "invalid mode"
            self.prev_mode = mode

    def start(self) -> None:
        self.keyboard_recorder.start()
        self.mouse_recorder.start()
        self.video_recorder.start()
        logger.info("start recording!")
        print("press <ctrl+shift+s> to stop recording")
        print("press <ctrl+shift+c> to enter code mode")
        print("press <ctrl+shift+x> to enter type mode")

    def stop(self) -> None:
        logger.info("STOPPING!")
        self.stop_time = time.time()
        self.keyboard_recorder.stop()
        self.mouse_recorder.stop()
        self.video_recorder.stop()
        logger.info("STOPPED!")

    def wait_exit(self) -> None:
        try:
            logger.info("waiting for exit")
            self.keyboard_recorder.wait_exit()
            self.mouse_recorder.wait_exit()
            self.video_recorder.wait_exit()
        finally:
            logger.info("start post processing")
            self.post_process()

    @staticmethod
    def __remove_incomplete_events(
        in_func: Callable, out_func: Callable, events: list[Event]
    ):
        clean_events = []
        occur_set = set()
        for event in events:
            name, is_in = in_func(event)
            if is_in and name not in occur_set:
                occur_set.add(name)
                clean_events.append(event)
            name, is_out = out_func(event)
            if is_out and name in occur_set:
                occur_set.remove(name)
                clean_events.append(event)
        return clean_events

    @staticmethod
    def remove_bad_keys(events: list[Event]) -> list[Event]:
        """
        Remove those keys that only have 'up' event or 'down' event
        """
        in_func = lambda e: (e.data["key"], e.data["action"] == "down")
        out_func = lambda e: (e.data["key"], e.data["action"] == "up")
        events = AllinOneRecorder.__remove_incomplete_events(in_func, out_func, events)
        in_func = lambda e: (e.data["key"], e.data["action"] == "up")
        out_func = lambda e: (e.data["key"], e.data["action"] == "down")
        events = list(reversed(events))
        events = AllinOneRecorder.__remove_incomplete_events(in_func, out_func, events)
        return list(reversed(events))

    @staticmethod
    def remove_bad_mouse(events: list[Event]) -> list[Event]:
        """
        Remove those mouse events that only have 'up' event or 'down' event
        """
        in_func = lambda e: (
            e.data["button"] if e.data["action"] == "button" else None,
            e.data["pressed"] == 1 if e.data["action"] == "button" else False,
        )
        out_func = lambda e: (
            e.data["button"] if e.data["action"] == "button" else None,
            e.data["pressed"] == 0 if e.data["action"] == "button" else False,
        )
        events = AllinOneRecorder.__remove_incomplete_events(in_func, out_func, events)
        in_func = lambda e: (
            e.data["button"] if e.data["action"] == "button" else None,
            e.data["pressed"] == 0 if e.data["action"] == "button" else False,
        )
        out_func = lambda e: (
            e.data["button"] if e.data["action"] == "button" else None,
            e.data["pressed"] == 1 if e.data["action"] == "button" else False,
        )
        events = list(reversed(events))
        events = AllinOneRecorder.__remove_incomplete_events(in_func, out_func, events)
        return list(reversed(events))

    def post_process(self) -> None:
        if self.video_available:
            self.video_recorder.get_video(start_frame_id=0)
        # if exit from coding mode, save the code
        if self.prev_mode == MODE.CODING:
            self.__save_code()
        # start and stop time of the whole recording
        video_start_time: float = max(
            self.video_recorder.start_time,
            self.keyboard_recorder.start_time,
            self.mouse_recorder.start_time,
        )
        video_stop_time: float = min(
            self.video_recorder.stop_time,
            self.keyboard_recorder.stop_time,
            self.mouse_recorder.stop_time,
        )
        # filter out mouse and keyboard events
        # that are not during the recording time
        filter_valid_events: Callable = lambda events: [
            e for e in events if video_start_time <= e.time <= video_stop_time
        ]
        valid_mouse_events = filter_valid_events(self.mouse_recorder.events)
        valid_mouse_events = self.remove_bad_mouse(valid_mouse_events)
        valid_key_events = filter_valid_events(self.keyboard_recorder.events)
        valid_key_events = self.remove_bad_keys(valid_key_events)
        valid_key_mouse_events = valid_mouse_events + valid_key_events
        # convert to json
        if self.video_available:
            video_json: dict | None = {
                "region": self.video_screen_region,
                "fps": self.video_recorder.fps,
                "path": self.video_path,
            }
        else:
            video_json = None
        # determine task type
        task_type: str = "unknown"
        code_start_time: float = float("inf")
        for e in self.events:
            if e.event_type == "code":
                code_start_time = e.time
                break
        if self.video_available:
            if code_start_time != float("inf"):
                task_type = "hybrid"
            else:
                task_type = "video_only"
        elif code_start_time != float("inf"):
            task_type = "api_only"
        start_time = min(video_start_time, code_start_time)
        stop_time = max(video_stop_time, self.stop_time)
        # offset = start_time
        record_json: dict = {
            "task_type": task_type,
            "start_time": start_time,  # - offset
            "stop_time": stop_time,  # - offset
            "video": video_json,
            "events": [],
        }
        events_all = valid_key_mouse_events + self.events
        events_all.sort()
        for event in events_all:
            record_json["events"].append(
                {
                    "time": event.time,  # - offset
                    "event_type": event.event_type,
                    "data": event.data,
                }
            )
        json.dump(record_json, open(self.output_file, "w"), indent=4)

    def __del__(self) -> None:
        if os.path.exists(self.code_path):
            os.remove(self.code_path)


if __name__ == "__main__":
    import pyautogui

    width, height = pyautogui.size()
    rec = AllinOneRecorder(
        mouse_options=MouseOptions.LOG_ALL,
        video_path="test.mp4",
        video_screen_region={
            "left": 0,
            "top": 0,
            "width": width,
            "height": height,
        },
        video_fps=5,
        output_file="record.json",
        mouse_fps=5,  # framerate of mouse movement
    )
    rec.start()
    rec.wait_exit()
