import logging
import os
import threading
import time

import cv2
import mss
import numpy as np

from playground.config import Config
from playground.env.desktop_env.recorder.base_recorder import Recorder

logger = logging.getLogger(__name__)
config = Config()


class FrameBuffer:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()

    def add_frame(self, frame_id, frame):
        with self.lock:
            self.queue.append((frame_id, frame))

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


class ScreenRecorder(Recorder):
    def __init__(
        self,
        fps: int,
        screen_region: dict[str, int],
    ):
        super().__init__()
        self.fps = fps
        self.screen_region = screen_region
        self.current_frame_id = -1
        self.current_frame = None
        self.frame_buffer = FrameBuffer()
        self.is_recording = False

    def reset(self, **kwargs) -> None:
        self.thread = threading.Thread(
            target=self._capture_screen, name="Screen Capture"
        )
        # release the lock when the thread starts
        self.recording_lock = threading.Lock()
        self.recording_lock.acquire()

        self.frame_buffer.clear()
        self.current_frame_id = -1
        self.current_frame = None

    def start(self) -> None:
        self.is_recording = True
        self.thread.start()
        # wait until the recording starts
        with self.recording_lock:
            pass

    def stop(self):
        if not self.thread.is_alive():
            logger.warning("Screen capture thread is not executing")
        else:
            self.is_recording = False

    def wait_exit(self) -> None:
        self.thread.join()  # Now we wait for the thread to finish

    def save(
        self, video_path: str, start_frame_id: int, end_frame_id: int | None = None
    ) -> None:
        output_dir = os.path.dirname(video_path)
        if output_dir != "" and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        writer = cv2.VideoWriter(
            video_path,
            cv2.VideoWriter.fourcc(*"mp4v"),
            self.fps,
            (
                self.screen_region["width"],
                self.screen_region["height"],
            ),
        )

        frames = self.frame_buffer.get_frames(start_frame_id, end_frame_id)
        logger.info(f"Captured {len(frames)} frames with FPS={self.fps}")
        for frame in frames:
            writer.write(frame[1])
        writer.release()

    def get_current_frame(self) -> np.ndarray:
        if self.current_frame is None:
            raise RuntimeError("No frame is captured")
        return self.current_frame

    def _capture_screen(self):
        self.start_time = time.time()
        logger.info("Screen recorder started")
        with mss.mss(with_cursor=False) as sct:
            self.recording_lock.release()
            while self.is_recording:
                capture_time = time.time()
                frame = sct.grab(self.screen_region)
                frame = np.array(frame)
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
                    logger.warning("Frame rate is too high")
        self.stop_time = time.time()
        logger.info("Screen recorder stopped")
