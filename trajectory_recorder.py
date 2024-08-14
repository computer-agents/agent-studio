import re
import logging

from agent_studio.recorder.utils import (
    OS,
    Event,
    MouseOptions,
    Recorder,
    Record,
    KeyboardEvent,
    KeyboardAction,
    VideoInfo,
)
from agent_studio.recorder.recorders.mouse import MouseRecorder
from agent_studio.recorder.recorders.keyboard import KeyboardRecorder
from agent_studio.recorder.recorders.video import VideoRecorder

logger = logging.getLogger(__name__)


class AllinOneRecorder(Recorder):
    def __init__(
        self,
        mouse_options: MouseOptions,
        with_video: bool,
        video_path: str,
        video_screen_region: dict[str, int],
        video_fps: int,
        output_file: str,
        mouse_fps: int = 10,
    ):
        self.video_path: str = video_path
        self.video_available: bool = with_video
        self.video_screen_region: dict[str, int] = video_screen_region
        self.output_file: str = output_file
        self.events: list[Event] = []
        self.shebang_template = re.compile(r"^#!\s*(.+)")
        self.mouse_recorder = MouseRecorder(
            mouse_options,
            mouse_fps
        )
        self.keyboard_recorder = KeyboardRecorder(
            {
                'stop': ('<alt>+s', self.stop),
            }
        )
        self.video_recorder = VideoRecorder(
            video_path=self.video_path,
            screen_region=video_screen_region,
            fps=video_fps,
        )

    def start(self) -> None:
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

    @staticmethod
    def remove_bad_keys(events: list[KeyboardEvent]) -> list[KeyboardEvent]:
        """
        Remove those keys that only have 'up' event or 'down' event
        """
        clean_events = []
        pressed_keys = set()
        for event in events:
            if event.action == KeyboardAction.DOWN:
                if event.key not in pressed_keys:
                    clean_events.append(event)
                    pressed_keys.add(event.key)
            elif event.action == KeyboardAction.UP:
                if event.key in pressed_keys:
                    clean_events.append(event)
                    pressed_keys.remove(event.key)
            else:
                assert False, f"invalid keyboard event {event}"
        events = clean_events
        clean_events = []
        released_key = set()
        for event in reversed(events):
            if event.action == KeyboardAction.DOWN:
                if event.key in released_key:
                    clean_events.append(event)
                    released_key.remove(event.key)
            elif event.action == KeyboardAction.UP:
                if event.key not in released_key:
                    clean_events.append(event)
                    released_key.add(event.key)
            else:
                assert False, f"invalid keyboard event {event}"
        return list(reversed(clean_events))

    def post_process(self) -> None:
        if self.video_available:
            self.video_recorder.get_video(start_frame_id=0)
        # if exit from coding mode, save the code
        keyboard_events = self.remove_bad_keys(
            self.keyboard_recorder.events
        )
        video_events: list = keyboard_events + \
            self.mouse_recorder.events
        # start and stop time of the whole recording
        video_start_time: float = self.video_recorder.start_time
        video_stop_time: float = self.video_recorder.stop_time
        # filter out mouse and keyboard events
        # that are not during the recording time
        valid_key_mouse_events: list = [
            e for e in video_events if video_start_time <= e.time <= video_stop_time
        ]
        # convert to json
        if self.video_available:
            video_json: VideoInfo | None = VideoInfo(
                region=self.video_screen_region,
                fps=self.video_recorder.fps,
                path=self.video_path
            )
        else:
            video_json: VideoInfo | None = None
        # determine task type
        task_type: str = 'no_vision' if video_json is None else 'vision'
        start_time = video_start_time
        stop_time = video_stop_time
        offset = start_time
        record_json: Record = Record(
            task_type=task_type,
            start_time=start_time - offset,
            stop_time=stop_time - offset,
            events=[],
            video=video_json
        )
        events_all = valid_key_mouse_events + self.events
        events_all.sort()
        record_json.events = events_all
        for event in record_json.events:
            event.time -= offset
        json_str = record_json.model_dump_json(indent=4)
        with open(self.output_file, 'w') as f:
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


if __name__ == "__main__":
    rec = AllinOneRecorder(
        mouse_options=MouseOptions.LOG_ALL,
        with_video=True,
        video_path='test.mp4',
        video_screen_region={
            "left": 0,
            "top": 0,
            "width": 2560,
            "height": 1600,
        },
        video_fps=10,
        output_file='record.json',
        mouse_fps=5,   # valid if recording mouse movement
    )
    rec.start()
    rec.wait_exit()
