import argparse
import asyncio
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import jsonpickle
import numpy as np
import requests
from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from tqdm import tqdm

from agent_studio.agent import setup_agent
from agent_studio.config.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator_helper import evaluator_router
from agent_studio.envs.desktop_env.vnc_client import (
    LocalStreamer,
    VNCFrame,
    VNCStreamer,
)
from agent_studio.utils.communication import (
    AgentStudioEvalRequest,
    AgentStudioResetRequest,
    AgentStudioStatusResponse,
    AgentStudioTextRequest,
)
from agent_studio.utils.json_utils import export_trajectories, read_json

config = Config()

logger = logging.getLogger("agent_studio")
format = "%(asctime)s\t%(levelname)s %(filename)s:%(lineno)s -- %(message)s"
formatter = logging.Formatter(format)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)
file_handler = logging.FileHandler(
    filename=os.path.join("logs", f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"),
    mode="w",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logging.basicConfig(level=logging.DEBUG, handlers=[handler, file_handler])
logger.propagate = False


class FrameBuffer:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()

    def add_frame(self, frame):
        with self.lock:
            self.queue.append(frame)

    def clear(self):
        with self.lock:
            self.queue.clear()

    def get_frames(self):
        with self.lock:
            frames = self.queue.copy()
        return frames


class AgentMonitor(QMainWindow):
    """Main class for the agent monitor."""

    def __init__(
        self,
        remote: bool,
        window_width: int,
        window_height: int,
    ) -> None:
        """Initializes the UI."""
        super().__init__()
        self.frame_buffer = None
        self.is_recording = False

        # Setup a QTimer to periodically update the screen.
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(int(1000 / config.video_fps))
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.start()
        self.refreshing_screen = False

        if remote:
            self.capture_thread: VNCStreamer = VNCStreamer(
                config.env_server_addr, config.vnc_port, config.vnc_password
            )
        else:
            self.capture_thread: LocalStreamer = LocalStreamer(config.monitor_idx)

        # Setup the user interface for the application.
        self.setWindowTitle("Agent Monitor")

        # Central widget to hold the main layout.
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left layout for VNC frame.
        self.vnc_container = QWidget()
        left_layout = QVBoxLayout(self.vnc_container)

        # Start the capture thread to get video feed.
        assert self.capture_thread is not None
        self.capture_thread.start()

        # Initialize the screenshot as a blank image.
        self.video_height, self.video_width = (
            self.capture_thread.video_height,
            self.capture_thread.video_width,
        )
        self.now_screenshot = np.zeros(
            (self.video_height, self.video_width, 4), dtype="uint8"
        )

        # Setup the VNC frame for video display.
        frame_size_hint = QSize(window_width, window_height)
        self.vnc_frame = VNCFrame(self, frame_size_hint, enable_selection=True)
        left_layout.addWidget(self.vnc_frame)
        main_layout.addWidget(self.vnc_container)

        if remote:
            right_layout = QVBoxLayout()
            right_layout.setSpacing(10)
            right_layout.setContentsMargins(10, 10, 10, 10)

            self.reconnect_button = QPushButton("Re-connect")
            self.reconnect_button.clicked.connect(self.reconnect)
            self.reconnect_button.setFixedWidth(150)
            self.reconnect_button.setFixedHeight(50)
            right_layout.addWidget(self.reconnect_button)

            main_layout.addLayout(right_layout)

        # Setup the status bar.
        status_bar = self.statusBar()
        assert status_bar is not None
        self.status_bar: QStatusBar = status_bar
        self.task_status_bar = QLabel()
        self.status_bar.addPermanentWidget(self.task_status_bar)

        self.reset()

    def reset(self) -> None:
        """Resets the UI elements to their default state."""
        self.vnc_frame.reset()
        self.vnc_container.show()
        self.refresh_timer.start()
        self.screenshot_uuid = None
        self.status_bar.showMessage(
            "Connected. Please go to the terminal to check outputs."
        )

    def reconnect(self):
        self.status_bar.showMessage("Reconnecting")
        self.now_screenshot = np.zeros(
            (self.video_height, self.video_width, 4), dtype="uint8"
        )
        if self.capture_thread is not None:
            self.capture_thread = VNCStreamer(
                env_server_addr=config.env_server_addr,
                vnc_port=config.vnc_port,
                vnc_password=config.vnc_password,
            )
            self.capture_thread.start()
        self.status_bar.showMessage(
            "Connected. Please go to the terminal to check outputs."
        )

    def render(self):
        """Renders the screen by periodically updating the frame."""
        self.refresh_timer.stop()
        if self.refreshing_screen:
            self.refresh_timer.start()
            return
        self.refreshing_screen = True

        # Update the screen with the latest frame from the capture thread.
        try:
            frame = self.capture_thread.get_current_frame()
            if frame is not None:
                self.now_screenshot = frame
                qimage = QImage(
                    frame.tobytes(),
                    self.video_width,
                    self.video_height,
                    QImage.Format.Format_RGB888,
                )
                self.vnc_frame.update(qimage)

                if self.is_recording:
                    self.frame_buffer.add_frame(self.now_screenshot)
        except Exception as e:
            print("Failed to get screenshot.", e)

        self.refreshing_screen = False
        self.refresh_timer.start()

    def start_recording(self):
        """Starts recording the video."""
        assert not self.is_recording, "Recording is already in progress."
        self.is_recording = True
        self.start_time = time.time()
        if self.frame_buffer is None:
            self.frame_buffer = FrameBuffer()
        self.status_bar.showMessage("Recording started.")

    def get_screenshot(self) -> np.ndarray:
        """Returns the current frame as a numpy array."""
        while np.all(self.now_screenshot == 0):
            print("Waiting for the first frame.")
            time.sleep(0.5)
        frame = cv2.cvtColor(self.now_screenshot, cv2.COLOR_BGRA2RGB)
        return np.array(frame)

    def save_video(self, record_path: str) -> dict:
        """Stops recording and saves the video to the file system.

        Returns:
            dict: Metadata about the saved video.
        """
        os.makedirs(os.path.dirname(record_path), exist_ok=True)
        assert (
            self.is_recording and self.frame_buffer is not None
        ), "No recording in progress."
        self.is_recording = False
        self.stop_time = time.time()
        writer = cv2.VideoWriter(
            record_path,
            cv2.VideoWriter.fourcc(*"mp4v"),
            config.video_fps,
            (self.video_width, self.video_height),
        )
        frames = self.frame_buffer.get_frames()
        logger.info(f"Captured {len(frames)} frames with FPS={config.video_fps}")
        for frame in frames:
            writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        writer.release()
        self.frame_buffer.clear()
        self.status_bar.showMessage("Recording stopped and video saved.")

        return {
            "start_time": self.start_time,
            "stop_time": self.stop_time,
            "fps": config.video_fps,
            "frame_count": len(frames),
            "video_path": record_path,
            "width": self.video_width,
            "height": self.video_height,
        }

    def closeEvent(self, event):
        """Handles the close event by stopping the capture thread and timer.

        Args:
            event: The close event.
        """
        self.refresh_timer.stop()
        if self.capture_thread is not None:
            self.capture_thread.stop()

        exit(0)


def wait_finish(is_eval: bool, response: AgentStudioStatusResponse):
    remote_server_addr = f"http://{config.env_server_addr}:{config.env_server_port}"
    if response.status == "finished":
        return response
    elif response.status == "wait_for_input":
        # Can't override in eval mode
        if config.need_human_confirmation and not is_eval:
            user_input = input(response.content)
        else:
            user_input = "y"
        response_raw = requests.post(
            url=f"{remote_server_addr}/task/confirm",
            json=AgentStudioTextRequest(message=user_input).model_dump(),
        )
        assert response_raw.status_code == 200
        response = AgentStudioStatusResponse(**response_raw.json())
        return wait_finish(is_eval, response)
    else:
        raise ValueError(f"Unknown status: {response.status}, {response.content}")


def eval(args, interface: AgentMonitor | None = None) -> None:
    # Setup agent
    agent = setup_agent(
        agent_name=args.agent,
        model=args.model,
        remote=args.remote,
        runtime_server_addr=config.env_server_addr,
        runtime_server_port=config.env_server_port,
    )
    log_dir = f"{args.log_dir}/{args.model}/{args.agent}"
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Setup tasks
    task_configs = read_json(args.task_configs_path, args.start_idx, args.end_idx)

    # Run evaluation
    scores = {}
    for task_config in tqdm(task_configs, desc="Evaluating tasks"):
        try:
            # Reset
            if args.remote:
                remote_server_addr = (
                    f"http://{config.env_server_addr}:{config.env_server_port}"
                )
                response_raw = requests.post(f"{remote_server_addr}/runtime/reset")
                response = AgentStudioStatusResponse(**response_raw.json())
                assert (
                    response.status == "success"
                ), f"Fail to reset runtime: {response_raw.text}"
                response_raw = requests.post(
                    f"{remote_server_addr}/task/reset",
                    json=AgentStudioResetRequest(task_config=task_config).model_dump(),
                )
                response = AgentStudioStatusResponse(**response_raw.json())
                response = wait_finish(is_eval=False, response=response)
                assert (
                    response.status == "finished" and response.content == "success"
                ), f"Fail to reset task: {response.message}"
            else:
                evaluators = evaluator_router(task_config)
                evaluators.reset()

            instruction = task_config["instruction"]
            logger.info(f"Task instruction: {instruction}")
            if "GMAIL_RECIPIENT" in instruction:
                gmail_recipient = config.gmail_recipient
                assert len(gmail_recipient) > 0, "GMAIL_RECIPIENT is not set."
                instruction = instruction.replace("GMAIL_RECIPIENT", gmail_recipient)

            # Reset the agent
            agent.reset(task_config=task_config)
            if task_config["visual"]:
                assert (
                    interface is not None
                ), "Interface has to be open for visual tasks."
                interface.start_recording()

            # Loop until the task is done or the max step is reached.
            for t in range(task_config["max_steps"]):
                logger.info(f"Step {t}")
                if task_config["visual"]:
                    obs = interface.get_screenshot()
                else:
                    obs = None
                action = agent.generate_action(obs=obs, model_name=args.model)
                if config.need_human_confirmation:
                    confirmed = (
                        input(f"Action:\n{action}\nConfirm action (y/n): ")
                        .strip()
                        .lower()
                        == "y"
                    )
                else:
                    confirmed = True
                _, done = agent.step_action(confirmed)
                time.sleep(config.min_action_interval)
                if done:
                    break

            task_trajectory_path = Path(log_dir) / task_config["task_id"]
            video_meta = None
            if task_config["visual"]:
                task_trajectory_path.mkdir(parents=True, exist_ok=True)
                video_path = (task_trajectory_path / "video.mp4").as_posix()
                video_meta = interface.save_video(video_path)
                logger.info(f"Video saved to {video_path}")

            if args.remote:
                response_raw = requests.post(
                    f"{remote_server_addr}/task/eval",
                    json=AgentStudioEvalRequest(
                        task_config=task_config,
                        trajectory=str(jsonpickle.encode(agent.trajectory)),
                    ).model_dump(),
                )
                response = AgentStudioStatusResponse(**response_raw.json())
                response = wait_finish(is_eval=True, response=response)
                if not (
                    response.status == "finished"
                    and isinstance(response.message, dict)  # noqa: E501
                ):
                    raise ValueError(f"Fail to evaluate task: {response.message}")
                score, feedback = (
                    response.message["score"],
                    response.message["feedback"],
                )
            else:
                logger.info("Start evaluation")
                score, feedback = evaluators()

            scores[task_config["task_id"]] = score
            if score == 1.0:
                logger.info(f"[Result] (PASS): {feedback}")
            else:
                logger.info(f"[Result] (FAIL): {feedback}")

            export_trajectories(
                task_config=task_config,
                trajectory=agent.trajectory,
                record_path=log_dir,
                score=score,
                feedback=feedback,
                token_count=agent.get_token_count(),
                video_meta=video_meta,
                jsonl_name=os.path.basename(args.task_configs_path).replace(
                    ".json", ".jsonl"
                ),
            )
        except Exception as e:
            import traceback

            logger.error(f"[Unhandled Error] {repr(e)}]")
            logger.error(traceback.format_exc())

    agent.close()
    logger.info(
        f"Average score: {sum(scores.values())}/{len(scores)}="
        f"{sum(scores.values()) / max(len(scores), 1)}"
    )
    if interface is not None:
        logger.info("Please close the interface to exit.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, help="Model name")
    parser.add_argument("--agent", type=str, default="direct", help="Agent type")
    parser.add_argument("--task_configs_path", type=str, help="Path to the task config")
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)
    parser.add_argument(
        "--log_dir",
        type=str,
        default="logs",
        help="Path to save the logs",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Run with rendering (should be enabled for visual tasks)",
    )
    parser.add_argument("--remote", action="store_true", help="Run in remote mode")
    parser.add_argument(
        "--window_width", type=int, default=800, help="Width of the window"
    )
    parser.add_argument(
        "--window_height", type=int, default=600, help="Height of the window"
    )
    parser.add_argument(
        "--need_human_confirmation",
        action="store_true",
        help="Need human confirmation for actions",
    )
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")
    assert args.task_configs_path is not None, "Task config is not set."

    config.remote = args.remote
    config.headless = not args.render
    config.need_human_confirmation = args.need_human_confirmation

    # Ensure a second screen is available.
    app = QApplication(sys.argv)
    screens = QApplication.screens()
    if not args.remote and len(screens) < 2:
        raise RuntimeError("A second screen is required for local annotation.")

    if not args.render:
        eval(args)
    else:
        try:
            # Create the main interface.
            interface = AgentMonitor(
                remote=args.remote,
                window_width=args.window_width,
                window_height=args.window_height,
            )
            interface.resize(args.window_width, args.window_height)

            if not args.remote:
                # Move window to the second screen
                second_screen = screens[1]
                geometry = second_screen.geometry()
                interface.move(geometry.topLeft())
            interface.show()

            timer = QTimer()
            timer.timeout.connect(lambda: eval(args, interface))
            timer.setSingleShot(True)  # Set the timer to single-shot mode
            timer.start(100)  # Executes main_task once after 100 ms

            sys.exit(app.exec())
        except asyncio.exceptions.CancelledError:
            sys.exit(0)


if __name__ == "__main__":
    main()
