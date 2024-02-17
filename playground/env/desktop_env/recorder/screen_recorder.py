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
        self.window: None | str | gw.Win32Window = None
        self.window_position: None | tuple[int, int] = None
        self.window_size: None | tuple[int, int] = None
        self.window_is_maximized: None | bool = None
        match platform.system():
            case "Windows":
                self.window = gw.getActiveWindow()
                assert self.window is not None, "No active window found"
                self.window_position = self.window.topleft
                self.window_size = self.window.size
                self.window_is_maximized = self.window.isMaximized
                logger.debug(
                    f"Active window: {self.window.title} "
                    f"at position {self.window_position} "
                    f"with size {self.window_size}"
                )
            case "Linux":
                self.window = (
                    subprocess.check_output(["xdotool", "getactivewindow"])
                    .strip()
                    .decode()
                )
            case "Darwin":
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
                    logger.warning(
                        f"Unsupported window name {window_name}. "
                        "There may be issues with the window."
                    )

    def send_to_background(self):
        """Sends the current window to the background."""
        match platform.system():
            case "Linux":
                try:
                    assert isinstance(self.window, str)
                    subprocess.run(["xdotool", "windowminimize", self.window])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "xdotool is required. Install it with `apt install xdotool`."
                    )
                logger.debug(f"Minimized window: {self.window}")
            case "Darwin":
                try:
                    # Minimize window
                    assert isinstance(self.window, str)
                    minimize_script = (
                        "tell application 'System Events' to set visible of "
                        f"process '{self.window}' to false"
                    )
                    subprocess.run(["osascript", "-e", minimize_script])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "AppleScript failed to send window to background."
                    )
                logger.debug(f"Minimized window: {self.window}")
            case "Windows":
                assert isinstance(self.window, gw.Win32Window), "Invalid window type"
                self.window.minimize()
                logger.debug(f"Minimized window: {self.window.title}")
            case _:
                raise RuntimeError(f"Unsupported OS {platform.system()}")
        # TODO: More elegant way?
        time.sleep(1.0)

    def bring_to_front(self):
        """Brings the minimized window to the front."""
        match platform.system():
            case "Linux":
                try:
                    assert isinstance(self.window, str)
                    subprocess.run(["xdotool", "windowactivate", self.window])
                except subprocess.CalledProcessError:
                    raise RuntimeError(
                        "xdotool is required. Install it with `apt install xdotool`."
                    )
                logger.debug(f"Restored window: {self.window}")
            case "Darwin":
                try:
                    assert isinstance(self.window, str)
                    restore_script = f'tell application "{self.window}" to activate'
                    subprocess.run(["osascript", "-e", restore_script])
                except subprocess.CalledProcessError:
                    raise RuntimeError("AppleScript failed to bring window to front.")
                logger.debug(f"Restored window: {self.window}")
            case "Windows":
                assert isinstance(self.window, gw.Win32Window), "Invalid window type"
                if self.window_is_maximized:
                    self.window.maximize()
                else:
                    self.window.moveTo(*self.window_position)
                    self.window.resize(*self.window_size)
                    self.window.restore()
                logger.debug(f"Restored window: {self.window.title}")
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
        self.is_recording = False
        self.window_manager = WindowManager()

        self.thread = threading.Thread(
            target=self._capture_screen, name="Screen Capture"
        )
        # release the lock when the thread starts
        self.recording_lock = threading.Lock()
        self.recording_lock.acquire()
        self.thread.daemon = True

    def reset(self) -> None:
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

    def get_current_frame(self) -> np.ndarray:
        if self.current_frame is None:
            raise RuntimeError("No frame is captured")
        return self.current_frame

    def _capture_screen(self):
        self.window_manager.send_to_background()
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
        self.window_manager.bring_to_front()
        logger.info("Screen recorder stopped")
