import os
import threading
import time
from typing import Tuple

import cv2
import mss
import numpy as np

from playground.config import Config
from playground.utils.logger import Logger

config = Config()
logger = Logger()


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


class VideoRecorder:
    def __init__(
        self,
        video_path: str,
        screen_region: Tuple[int, int] = config.resolution,
    ):
        self.fps = config.video_fps
        self.max_size = 10000
        self.video_path = video_path
        self.screen_region = screen_region
        self.frame_size = (self.screen_region[0], self.screen_region[1])

        self.current_frame_id = -1
        self.current_frame = None
        self.frame_buffer = FrameBuffer()
        self.thread_flag = True

        self.thread = threading.Thread(
            target=self.capture_screen, args=(self.frame_buffer,), name="Screen Capture"
        )
        self.thread.daemon = True

        self.video_splits_dir = os.path.join(
            os.path.dirname(self.video_path), "video_splits"
        )
        os.makedirs(self.video_splits_dir, exist_ok=True)

    def get_frames(self, start_frame_id, end_frame_id=None):
        return self.frame_buffer.get_frames(start_frame_id, end_frame_id)

    def get_frames_to_latest(self, frame_id, before_frame_nums=5):
        return self.frame_buffer.get_frames_to_latest(frame_id, before_frame_nums)

    def get_video(self, start_frame_id, end_frame_id=None):
        path = os.path.join(
            self.video_splits_dir, "video_{:06d}.mp4".format(start_frame_id)
        )
        writer = cv2.VideoWriter(
            path, cv2.VideoWriter_fourcc(*"mp4v"), self.fps, self.frame_size
        )

        frames = self.get_frames(start_frame_id, end_frame_id)
        for frame in frames:
            writer.write(frame[1])
        writer.release()
        return path

    def clear_frame_buffer(self):
        self.frame_buffer.clear()

    def get_current_frame(self):
        """
        Get the current frame
        """
        return self.current_frame

    def get_current_frame_id(self):
        """
        Get the current frame id
        """
        return self.current_frame_id

    def capture_screen(self, frame_buffer: FrameBuffer):
        logger.info("Screen capture started")
        video_writer = cv2.VideoWriter(
            self.video_path, cv2.VideoWriter.fourcc(*"mp4v"), self.fps, self.frame_size
        )
        with mss.mss() as sct:
            region = {
                "left": 0,
                "top": 1,
                "width": self.screen_region[0],
                "height": self.screen_region[1],
            }

            while self.thread_flag:
                try:
                    frame = sct.grab(region)
                    frame = np.array(frame)  # Convert to numpy array

                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    video_writer.write(frame)

                    self.current_frame = frame
                    # for i in range(config.duplicate_frames):
                    #     self.current_frame_id += 1
                    #     frame_buffer.add_frame(self.current_frame_id, frame)
                    # time.sleep(
                    #     config.duplicate_frames / config.video_fps - 0.05
                    # )  # 0.05: time for taking a screenshots

                    # Check the flag at regular intervals
                    if not self.thread_flag:
                        break
                except KeyboardInterrupt:
                    logger.info("Screen capture interrupted")
                    self.finish_capture()

            video_writer.release()

    def start_capture(self):
        self.thread.start()

    def finish_capture(self):
        if not self.thread.is_alive():
            logger.info("Screen capture thread is not executing")
        else:
            self.thread_flag = (
                False  # Set the flag to False to signal the thread to stop
            )
            self.thread.join()  # Now we wait for the thread to finish
            logger.info("Screen capture finished")


if __name__ == "__main__":
    capture_video = VideoRecorder("test.mp4")

    capture_video.start_capture()

    time.sleep(10)
    capture_video.get_video(start_frame_id=0)

    capture_video.finish_capture()
