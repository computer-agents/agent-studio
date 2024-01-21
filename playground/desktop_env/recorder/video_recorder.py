import logging
import os
import threading
import time
from typing import Tuple

import cv2
import mss
import numpy as np

from playground.desktop_env.recorder.base_recorder import MODE, Recorder

logger = logging.getLogger(__name__)


class FrameBuffer:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()

    def add_frame(self, frame_id, frame):
        with self.lock:
            self.queue.append((frame_id, frame))

    def get_last_frame(self):
        with self.lock:
            if len(self.queue) == 0:
                return None
            else:
                return self.queue[-1]

    def get_frame_by_frame_id(self, frame_id):
        with self.lock:
            for frame in self.queue:
                if frame[0] == frame_id:
                    return frame
        return None

    def get_frames_to_latest(self, frame_id, before_frame_nums=5):
        frames = []
        with self.lock:
            for frame in self.queue:
                if frame[0] >= frame_id - before_frame_nums and frame[0] <= frame_id:
                    frames.append(frame)
        return frames

    def clear(self):
        with self.lock:
            self.queue.clear()

    def get_frames(self, start_frame_id, end_frame_id=None):
        frames = []
        with self.lock:
            for frame in self.queue:
                if frame[0] >= start_frame_id:
                    if end_frame_id is not None and frame[0] > end_frame_id:
                        break
                    frames.append(frame)
        return frames


class VideoRecorder(Recorder):
    def __init__(
        self,
        video_path: str,
        fps: int,
        screen_region: dict[str, int],
    ):
        super().__init__()
        self.video_path = video_path
        self.fps = fps
        self.screen_region = screen_region
        self.frame_size: Tuple[int, int] = (
            self.screen_region["width"],
            self.screen_region["height"],
        )
        logger.info(f"Frame size: {self.frame_size}")
        logger.info(f"Screen region: {self.screen_region}")

        self.current_frame_id = -1
        self.current_frame = None
        self.frame_buffer = FrameBuffer()
        self.is_recording = True

        self.thread = threading.Thread(
            target=self.__capture_screen, name="Screen Capture"
        )
        self.thread.daemon = True

    def __get_frames(self, start_frame_id, end_frame_id=None):
        return self.frame_buffer.get_frames(start_frame_id, end_frame_id)

    def __get_frames_to_latest(self, frame_id, before_frame_nums=5):
        return self.frame_buffer.get_frames_to_latest(frame_id, before_frame_nums)

    def get_video(self, start_frame_id: int, end_frame_id: int | None = None) -> str:
        output_dir = os.path.dirname(self.video_path)
        if output_dir != "" and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        writer = cv2.VideoWriter(
            self.video_path, cv2.VideoWriter.fourcc(*"mp4v"), self.fps, self.frame_size
        )

        frames = self.__get_frames(start_frame_id, end_frame_id)
        print(f"Get {len(frames)} frames with fps {self.fps}")
        for frame in frames:
            writer.write(frame[1])
        writer.release()
        return self.video_path

    def __clear_frame_buffer(self):
        self.frame_buffer.clear()

    def __get_current_frame(self):
        """
        Get the current frame
        """
        return self.current_frame

    def __get_current_frame_id(self):
        """
        Get the current frame id
        """
        return self.current_frame_id

    def __capture_screen(self):
        while self.mode == MODE.INIT and self.is_recording:
            pass
        self.start_time = time.time()
        logger.info("Screen capture started")
        with mss.mss(with_cursor=False) as sct:
            while self.is_recording:
                capture_time = time.time()
                frame = sct.grab(self.screen_region)
                frame = np.array(frame)  # Convert to numpy array
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                # add frame to buffer
                self.current_frame_id += 1
                self.current_frame = frame
                self.frame_buffer.add_frame(self.current_frame_id, frame)
                # preserve the frame rate
                wait_time = 1 / self.fps - (time.time() - capture_time)
                if wait_time > 0:
                    time.sleep(wait_time)
                elif wait_time < 0:
                    logger.warn("Frame rate is too high")

    def start(self):
        self.thread.start()

    def stop(self):
        if not self.thread.is_alive():
            logger.info("Screen capture thread is not executing")
        else:
            self.is_recording = (
                False  # Set the flag to False to signal the thread to stop
            )
        self.stop_time = time.time()
        logger.info(f"Video recorder stopped. Captured {self.current_frame_id} frames")

    def wait_exit(self) -> None:
        self.thread.join()  # Now we wait for the thread to finish
