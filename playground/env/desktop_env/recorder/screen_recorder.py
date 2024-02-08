import logging
import os
import platform
import threading
import time

import cv2
import mss
import numpy as np

from playground.env.desktop_env.recorder.base_recorder import Recorder

if platform.system() == "Windows":
    import pygetwindow as gw
else:
    import subprocess


logger = logging.getLogger(__name__)


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


class WindowManager:
    def __init__(self):
        self.window = None

    def send_to_background(self):
        """Sends the current window to the background."""
        match platform.system():
            case "Linux":
                try:
                    self.window = (
                        subprocess.check_output(["xdotool", "getactivewindow"])
                        .strip()
                        .decode()
                    )
                    subprocess.run(["xdotool", "windowminimize", self.window])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "xdotool is required. Install it with `apt install xdotool`."
                    )
            case "Darwin":
                try:
                    # Get name of the frontmost application
                    get_name_script = (
                        'tell application "System Events" to get name of first '
                        "application process whose frontmost is true"
                    )
                    window_name = (
                        subprocess.check_output(["osascript", "-e", get_name_script])
                        .strip()
                        .decode()
                    )
                    if window_name == "Electron":
                        self.window = "Code"
                    elif window_name == "Terminal":
                        self.window = window_name
                    else:
                        # TODO: handle other window names
                        self.window = window_name
                        logger.warn(
                            f"Unsupported window name {window_name}. "
                            "There may be issues with the window."
                        )
                    # Minimize window
                    minimize_script = (
                        'tell application "System Events" to set visible of '
                        "first application process whose frontmost is true to false"
                    )
                    subprocess.run(["osascript", "-e", minimize_script])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "AppleScript failed to send window to background."
                    )
            case "Windows":
                try:
                    # TODO: find a way to get unique ID
                    fg_window = gw.getActiveWindow()
                    self.window = fg_window.title
                    fg_window.minimize()
                except Exception as e:
                    raise RuntimeError(f"Failed to send window to background: {e}")
            case _:
                raise RuntimeError(f"Unsupported OS {platform.system()}")

    def bring_to_front(self):
        """Brings the minimized window to the front."""
        if not self.window:
            logger.info("No minimized windows to restore.")
            return
        match platform.system():
            case "Linux":
                try:
                    subprocess.run(["xdotool", "windowactivate", self.window])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "xdotool is required. Install it with `apt install xdotool`."
                    )
            case "Darwin":
                try:
                    restore_script = f'tell application "{self.window}" to activate'
                    subprocess.run(["osascript", "-e", restore_script])
                except subprocess.CalledProcessError:
                    raise RuntimeError("AppleScript failed to bring window to front.")
            case "Windows":
                try:
                    # TODO: find a way to restore the window with unique ID
                    window = gw.getWindowsWithTitle(self.window)[0]
                    window.restore()
                except Exception as e:
                    raise RuntimeError(f"Failed to bring window to front: {e}")
            case _:
                raise RuntimeError(f"Unsupported OS {platform.system()}")


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
        self.is_recording = True
        self.window_manager = WindowManager()

        self.thread = threading.Thread(
            target=self._capture_screen, name="Screen Capture"
        )
        self.thread.daemon = True

    def reset(self, **kwargs) -> None:
        self.frame_buffer.clear()
        self.current_frame_id = -1
        self.current_frame = None

    def start(self):
        self.thread.start()

    def stop(self):
        if not self.thread.is_alive():
            logger.info("Screen capture thread is not executing")
        else:
            self.is_recording = False

    def pause(self):
        self.window_manager.bring_to_front()

    def resume(self):
        self.window_manager.send_to_background()

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

    def _capture_screen(self):
        self.window_manager.send_to_background()
        self.start_time = time.time()
        logger.info("Screen recorder started")
        with mss.mss(with_cursor=False) as sct:
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
                    logger.warn("Frame rate is too high")
        self.stop_time = time.time()
        self.window_manager.bring_to_front()
        logger.info("Screen recorder stopped")
