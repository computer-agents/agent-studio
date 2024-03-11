import platform
import time

import pytest

from agent_studio.envs.desktop_env.recorder.screen_recorder import (
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
    rec = ScreenRecorder(
        fps=fps,
    )
    rec.start()
    time.sleep(duration)
    rec.stop()
    frames = rec.frame_buffer.get_frames(start_frame_id=0, end_frame_id=None)
    assert len(frames) == duration * fps
    rec.save("data/trajectories/test/test.mp4", start_frame_id=0)
