import logging
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

import chime
import toml

from agent_studio.recorder.recorders.keyboard import KeyboardRecorder
from agent_studio.recorder.recorders.mouse import MouseRecorder
from agent_studio.recorder.recorders.video import VideoRecorder
from agent_studio.recorder.utils import (
    Event,
    KeyboardAction,
    KeyboardEvent,
    MouseOptions,
    Record,
    Recorder,
    VideoInfo,
)

logger = logging.getLogger(__name__)

chime.theme("material")


class AllinOneRecorder(Recorder):
    def __init__(
        self,
        mouse_options: MouseOptions,
        instruction: str,
        video_screen_region: dict[str, int],
        video_fps: int,
        output_folder: str,
        delay_src: int = 5,
        mouse_fps: int = 10,
    ):
        self.delay_src: int = delay_src
        self.instruction: str = instruction
        self.video_screen_region: dict[str, int] = video_screen_region
        self.output_folder: str = output_folder
        self.events: list[Event] = []
        self.shebang_template = re.compile(r"^#!\s*(.+)")
        self.mouse_recorder = MouseRecorder(mouse_options, mouse_fps)
        self.keyboard_recorder = KeyboardRecorder(
            {
                "stop": ("<alt>+s", self.stop),
            }
        )
        self.video_recorder = VideoRecorder(
            screen_region=video_screen_region,
            fps=video_fps,
        )

    def start(self) -> None:
        # count down 3 seconds
        print(f"recording will start in {self.delay_src} seconds")
        print("You will hear a sound when recording starts")
        for i in range(self.delay_src, 0, -1):
            print(i)
            time.sleep(1)
        chime.info()

        self.keyboard_recorder.start()
        self.mouse_recorder.start()
        self.video_recorder.start()
        logger.info("start recording!")
        print("press alt+s to stop recording")

    def stop(self) -> None:
        logger.info("STOPPING!")
        self.keyboard_recorder.stop()
        self.mouse_recorder.stop()
        self.video_recorder.stop()
        logger.info("STOPPED!")
        chime.success()

    @staticmethod
    def remove_bad_keys(events: list[KeyboardEvent]) -> list[KeyboardEvent]:
        """
        Remove those keys that only have 'up' event or 'down' event
        """
        clean_events = []
        pressed_keys = set()
        for event in events:
            if event.action == KeyboardAction.KEY_DOWN:
                if event.key_code not in pressed_keys:
                    clean_events.append(event)
                    pressed_keys.add(event.key_code)
            elif event.action == KeyboardAction.KEY_UP:
                if event.key_code in pressed_keys:
                    clean_events.append(event)
                    pressed_keys.remove(event.key_code)
            else:
                assert False, f"invalid keyboard event {event}"
        events = clean_events
        clean_events = []
        released_key = set()
        for event in reversed(events):
            if event.action == KeyboardAction.KEY_DOWN:
                if event.key_code in released_key:
                    clean_events.append(event)
                    released_key.remove(event.key_code)
            elif event.action == KeyboardAction.KEY_UP:
                if event.key_code not in released_key:
                    clean_events.append(event)
                    released_key.add(event.key_code)
            else:
                assert False, f"invalid keyboard event {event}"
        return list(reversed(clean_events))

    def post_process(self) -> None:
        annotation_id = uuid.uuid4().hex
        video_path = f"{self.output_folder}/{annotation_id}.mp4"
        self.video_recorder.get_video(video_path=video_path, start_frame_id=0)
        # if exit from coding mode, save the code
        keyboard_events = self.remove_bad_keys(self.keyboard_recorder.events)
        video_events: list = keyboard_events + self.mouse_recorder.events
        # start and stop time of the whole recording
        video_start_time: float = self.video_recorder.start_time
        video_stop_time: float = self.video_recorder.stop_time
        # filter out mouse and keyboard events
        # that are not during the recording time
        valid_key_mouse_events: list = [
            e for e in video_events if video_start_time <= e.time <= video_stop_time
        ]
        # convert to json
        video_json: VideoInfo | None = VideoInfo(
            region=self.video_screen_region,
            fps=self.video_recorder.fps,
            path=Path(video_path).relative_to(self.output_folder).as_posix(),
        )
        start_time = video_start_time
        stop_time = video_stop_time
        offset = start_time
        record_json: Record = Record(
            instruction=self.instruction,
            annotation_id=annotation_id,
            start_time=start_time - offset,
            stop_time=stop_time - offset,
            events=[],
            video=video_json,
        )
        events_all = valid_key_mouse_events + self.events
        events_all.sort()
        record_json.events = events_all
        for event in record_json.events:
            event.time -= offset
        json_str = record_json.model_dump_json(indent=4)
        with open(f"{self.output_folder}/record.json", "w") as f:
            f.write(json_str)

    def wait_exit(self) -> None:
        try:
            logger.info("waiting for exit")
            self.keyboard_recorder.wait_exit()
            self.mouse_recorder.wait_exit()
            self.video_recorder.wait_exit()
        finally:
            logger.info("start post processing")
            self.post_process()


def main():
    config_file_path = Path.home().joinpath(".agent-studio")
    conf = {
        "output_folder": (Path.home() / datetime.now().strftime("%Y%m%d_%H%M%S")).as_posix()
    }

    if config_file_path.exists():
        with open(config_file_path, "r") as f:
            full_conf = toml.load(f)
            if "as-trajectory-recorder" in full_conf:
                conf = full_conf["as-trajectory-recorder"]
    else:
        full_conf = {}

    output_folder = Path(conf["output_folder"])

    user_input = input(
        "Please enter the folder path where you want to save the record"
        f" (Press Enter to use the default path: {output_folder}): ")
    if user_input:
        output_folder = Path(user_input)
        conf["output_folder"] = output_folder.as_posix()

    os.makedirs(output_folder, exist_ok=True)

    # save the folder name to config file in user's home directory
    with open(config_file_path, "w") as f:
        full_conf["as-trajectory-recorder"] = conf
        toml.dump(full_conf, f)

    instruction = input("Please input the instruction:")

    rec = AllinOneRecorder(
        mouse_options=MouseOptions.LOG_CLICK | MouseOptions.LOG_SCROLL,
        instruction=instruction,
        video_screen_region={
            "left": 0,
            "top": 0,
            "width": 2560,
            "height": 1600,
        },
        video_fps=10,
        output_folder=output_folder.as_posix(),
        mouse_fps=5,  # valid if recording mouse movement
    )
    rec.start()
    rec.wait_exit()


if __name__ == "__main__":
    main()
