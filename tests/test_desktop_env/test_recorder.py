import platform
import time

import pyautogui
import pytest

from playground.env.desktop_env.recorder.screen_recorder import (
    DarwinWindowManager,
    LinuxWindowManager,
    ScreenRecorder,
    WindowManagerDummy,
    WindowsWindowManager,
)


@pytest.mark.skip(reason="Can only be tested manually.")
def test_window_manager() -> None:
    wm = WindowManagerDummy()
    match platform.system():
        case "Windows":
            wm = WindowsWindowManager()
        case "Linux":
            wm = LinuxWindowManager()
        case "Darwin":
            wm = DarwinWindowManager()
        case _:
            raise RuntimeError(f"Unsupported OS {platform.system()}")

    wm.send_to_background()  # Minimize the current window
    time.sleep(1)
    wm.bring_to_front()  # Restore the minimized window


def test_screen_recorder(fps: int = 5, duration: int = 10) -> None:
    width, height = pyautogui.size()
    rec = ScreenRecorder(
        fps=fps,
        screen_region={
            "left": 0,
            "top": 0,
            "width": width,
            "height": height,
        },
    )
    rec.start()
    time.sleep(duration)
    rec.stop()
    frames = rec.frame_buffer.get_frames(start_frame_id=0, end_frame_id=None)
    assert len(frames) == duration * fps
    rec.save("playground_data/trajectories/test/test.mp4", start_frame_id=0)
