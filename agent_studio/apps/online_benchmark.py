from __future__ import annotations

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
from PyQt6.QtCore import (
    QMutex,
    QObject,
    QSize,
    Qt,
    QThread,
    QTimer,
    QWaitCondition,
    pyqtSignal,
)
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from tqdm import tqdm

from agent_studio.agent import setup_agent
from agent_studio.agent.base_agent import BaseAgent
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
from agent_studio.utils.gui import (
    ChoiceDialog,
    ChoiceDialogPython,
    InputDialog,
    JSONEditor,
)
from agent_studio.utils.json_utils import export_trajectories, read_json
from agent_studio.utils.types import TaskConfig

config = Config()

logger = logging.getLogger(__name__)
REMOTE_SERVER_ADDR = f"http://{config.env_server_addr}:{config.env_server_port}"


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


class WorkerSignals(QObject):
    show_dialog_signal = pyqtSignal(str, str)
    show_dialog_signal_python = pyqtSignal(str, str)
    show_input_dialog_signal = pyqtSignal(str, str)
    runtime_output_signal = pyqtSignal(dict)
    evaluation_result_signal = pyqtSignal(str)
    finish_signal = pyqtSignal()
    status_bar_signal = pyqtSignal(str, str)


class TaskThread(QThread):
    def __init__(
        self,
        agent: BaseAgent,
        task_config: TaskConfig,
        signal: WorkerSignals,
        args: argparse.Namespace,
        interface: AgentMonitor,
    ):
        super().__init__()
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.agent: BaseAgent = agent
        self.task_config = task_config
        self.signals = signal
        self.args = args
        self.interface = interface

    def wait_finish(self, is_eval: bool, response: AgentStudioStatusResponse):
        if response.status == "finished":
            return response
        elif response.status == "wait_for_input":
            if is_eval:
                # evaluation
                self.mutex.lock()
                self.signals.status_bar_signal.emit(
                    "color: red;", "Waiting for user input..."
                )
                self.signals.show_input_dialog_signal.emit(
                    "Human Evaluation", response.content
                )
                self.wait_condition.wait(self.mutex)
                self.mutex.unlock()
                user_input = self.user_input
                self.signals.status_bar_signal.emit("color: blue;", "Evaluating...")
            else:
                # reset
                if config.need_human_confirmation:
                    self.mutex.lock()
                    self.signals.status_bar_signal.emit(
                        "color: red;", "Waiting for user input..."
                    )
                    self.signals.show_dialog_signal.emit(
                        "Confirm Action", response.content
                    )
                    self.wait_condition.wait(self.mutex)
                    self.mutex.unlock()
                    user_input = self.user_input
                else:
                    user_input = "y"
                self.signals.status_bar_signal.emit("color: blue;", "Resetting Task...")
            response_raw = requests.post(
                url=f"{REMOTE_SERVER_ADDR}/task/confirm",
                json=AgentStudioTextRequest(message=user_input).model_dump(),
            )
            assert response_raw.status_code == 200
            response = AgentStudioStatusResponse(**response_raw.json())
            return self.wait_finish(is_eval, response)
        else:
            raise ValueError(f"Unknown status: {response.status}, {response.content}")

    def run(self):
        log_dir = f"{self.args.log_dir}/{self.args.model}/{self.args.agent}"
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        try:
            # Reset
            if self.args.remote:
                self.signals.status_bar_signal.emit("color: blue;", "Resetting Task...")
                response_raw = requests.post(
                    f"{REMOTE_SERVER_ADDR}/task/reset",
                    json=AgentStudioResetRequest(
                        task_config=self.task_config
                    ).model_dump(),
                )
                response = AgentStudioStatusResponse(**response_raw.json())
                response = self.wait_finish(is_eval=False, response=response)
                assert (
                    response.status == "finished" and response.content == "success"
                ), f"Fail to reset task: {response.message}"
            else:
                raise ValueError("Local mode is not supported.")

            instruction = self.task_config.instruction
            logger.info(f"Task instruction: {instruction}")
            if "GMAIL_RECIPIENT" in instruction:
                gmail_recipient = config.gmail_recipient
                assert len(gmail_recipient) > 0, "GMAIL_RECIPIENT is not set."
                instruction = instruction.replace("GMAIL_RECIPIENT", gmail_recipient)

            # Reset the agent
            self.signals.status_bar_signal.emit("color: blue;", "Resetting Agent...")
            self.agent.reset(task_config=self.task_config)
            if self.task_config.visual:
                assert (
                    self.interface is not None
                ), "Interface has to be open for visual tasks."
                self.interface.start_recording()

            # Loop until the task is done or the max step is reached.
            for t in range(self.task_config.max_steps):
                logger.info(f"Step {t}")
                if self.task_config.visual:
                    obs = self.interface.get_screenshot()
                else:
                    obs = None
                self.signals.status_bar_signal.emit(
                    "color: blue;", "Generating Action..."
                )
                action = self.agent.generate_action(obs=obs, model_name=self.args.model)
                if config.need_human_confirmation:
                    self.mutex.lock()
                    self.signals.status_bar_signal.emit(
                        "color: red;", "Waiting for user input..."
                    )
                    self.signals.show_dialog_signal_python.emit(
                        "Execute Action?", action
                    )
                    self.wait_condition.wait(self.mutex)
                    self.mutex.unlock()
                    confirmed = self.user_input.strip().lower() == "y"
                else:
                    confirmed = True
                self.signals.status_bar_signal.emit(
                    "color: blue;", "Executing Command..."
                )
                runtime_output, done = self.agent.step_action(confirmed)
                self.signals.runtime_output_signal.emit(runtime_output)
                time.sleep(config.min_action_interval)
                if done:
                    break

            task_trajectory_path = Path(log_dir) / self.task_config.task_id
            video_meta = None
            if self.task_config.visual:
                task_trajectory_path.mkdir(parents=True, exist_ok=True)
                video_path = (task_trajectory_path / "video.mp4").as_posix()
                video_meta = self.interface.save_video(video_path)
                logger.info(f"Video saved to {video_path}")

            if self.args.remote:
                response_raw = requests.post(
                    f"{REMOTE_SERVER_ADDR}/task/eval",
                    json=AgentStudioEvalRequest(
                        task_config=self.task_config,
                        kwargs=str(
                            jsonpickle.encode({"trejectory": self.agent.trajectory})
                        ),
                    ).model_dump(),
                )
                response = AgentStudioStatusResponse(**response_raw.json())
                response = self.wait_finish(is_eval=True, response=response)
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
                raise ValueError("Local mode is not supported.")

            if score == 1.0:
                logger.info(f"[Result] (PASS): {feedback}")
            else:
                logger.info(f"[Result] (FAIL): {feedback}")
            self.signals.evaluation_result_signal.emit(
                f"Score: {score}\nFeedback: {feedback}"
            )

            self.signals.status_bar_signal.emit(
                "color: blue;", "Exporting Trajectory..."
            )
            export_trajectories(
                task_config=self.task_config,
                trajectory=self.agent.trajectory,
                record_path=log_dir,
                score=score,
                feedback=feedback,
                token_count=self.agent.get_token_count(),
                video_meta=video_meta,
                jsonl_name=os.path.basename(self.args.task_configs_path).replace(
                    ".json", ".jsonl"
                ),
            )
            self.signals.status_bar_signal.emit("color: green;", "Ready")
            self.signals.finish_signal.emit()
        except Exception as e:
            import traceback

            logger.error(f"[Unhandled Error] {repr(e)}]")
            logger.error(traceback.format_exc())

    def receive_user_input(self, text: str):
        self.mutex.lock()
        self.user_input = text  # Store the user input
        self.wait_condition.wakeAll()  # Resume the thread
        self.mutex.unlock()


class AgentMonitor(QMainWindow):
    """Main class for the agent monitor."""

    def __init__(
        self,
        args: argparse.Namespace,
        remote: bool,
        task_configs: list[TaskConfig],
        window_width: int,
        window_height: int,
    ) -> None:
        """Initializes the UI."""
        super().__init__()
        self.frame_buffer: FrameBuffer = FrameBuffer()
        self.args = args
        self.is_recording = False
        self.remote = remote
        self.task_configs = task_configs
        self.selected_task: TaskConfig
        self.window_width = window_width
        self.window_height = window_height

        # Setup a QTimer to periodically update the screen.
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(int(1000 / config.video_fps))
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.start()
        self.refreshing_screen = False

        self.dlg: QDialog | None = None
        self.task_thread: TaskThread | None = None

        self.agent = setup_agent(
            agent_name=self.args.agent,
            model=self.args.model,
            remote=self.args.remote,
            runtime_server_addr=config.env_server_addr,
            runtime_server_port=config.env_server_port,
        )

        # self.task_thread: None | TaskThread = None
        self.capture_thread: VNCStreamer | LocalStreamer | None = None
        if remote:
            self.capture_thread = VNCStreamer(
                config.env_server_addr, config.vnc_port, config.vnc_password
            )
        else:
            self.capture_thread = LocalStreamer(config.monitor_idx)

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

        self.setup_ui()

        self.reset()

    def setup_ui(self):
        """Sets up the UI, including the VNC frame (left) and the right layout."""
        # Setup the user interface for the application.
        self.setWindowTitle("Agent Monitor")

        # Central widget to hold the main layout.
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Setup the status bar.
        status_bar = self.statusBar()
        assert status_bar is not None
        self.status_bar: QStatusBar = status_bar
        self.task_status_bar = QLabel()
        self.set_task_status_bar_text("color: green;", "Task: Init")
        self.status_bar.addPermanentWidget(self.task_status_bar)

        if self.remote:
            # Setup the VNC frame for video display.
            self.frame_size_hint = QSize(self.window_width, self.window_height)
            # Left layout for VNC frame.
            left_layout = QVBoxLayout()
            self.vnc_frame = VNCFrame(
                self, self.frame_size_hint, enable_selection=False
            )
            left_layout.addWidget(self.vnc_frame)

            self.reconnect_button = QPushButton("Re-connect")
            self.reconnect_button.clicked.connect(self.reconnect)
            self.reconnect_button.setFixedWidth(150)
            self.reconnect_button.setFixedHeight(50)
            left_layout.addWidget(self.reconnect_button)

            vnc_widget = QWidget()
            vnc_widget.setLayout(left_layout)
            main_splitter.addWidget(vnc_widget)

        # Task layout #
        task_layout = QVBoxLayout()

        task_layout.addWidget(QLabel("Task configuration"))

        self.task_config_display = JSONEditor(editable=False, parent=self)

        # Add the JSONEditor to a splitter to allow resizing
        task_splitter = QSplitter(Qt.Orientation.Vertical)
        task_splitter.addWidget(self.task_config_display)

        task_layout.addWidget(task_splitter)

        task_layout.addWidget(QLabel("Task Selection (double click to select)"))
        self.instruction_selection = QListWidget(self)
        self.instruction_selection.itemDoubleClicked.connect(
            self.select_task_instruction
        )
        self.instruction_selection.clear()
        self.populate_instruction_selection_widget()

        # Add the QListWidget to the same splitter for resizing
        task_splitter.addWidget(self.instruction_selection)

        execution_button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.task_start)
        execution_button_layout.addWidget(self.start_button)

        task_layout.addLayout(execution_button_layout)

        self.interrupt_button = QPushButton("Interrupt")
        self.interrupt_button.clicked.connect(self.reset)
        task_layout.addWidget(self.interrupt_button)

        self.status_bar.showMessage("Ready")

        task_widget = QWidget()
        task_widget.setLayout(task_layout)
        main_splitter.addWidget(task_widget)

        # End of task layout #

        # Agent layout #
        agent_layout = QVBoxLayout()

        self.show_trajectory_button = QPushButton("Show Trajectory")
        agent_layout.addWidget(self.show_trajectory_button)

        agent_layout.addWidget(QLabel("Runtime output"))

        self.output_display = JSONEditor(editable=False, parent=self)
        self.output_display.setReadOnly(True)

        # Add the JSONEditor to a splitter to allow resizing
        agent_splitter = QSplitter(Qt.Orientation.Vertical)
        agent_splitter.addWidget(self.output_display)

        agent_layout.addWidget(agent_splitter)

        agent_layout.addWidget(QLabel("Evaluation Result"))

        self.evaluation_display = QTextEdit(self)
        self.evaluation_display.setReadOnly(True)

        # Add the QTextEdit to the same splitter for resizing
        agent_splitter.addWidget(self.evaluation_display)

        agent_widget = QWidget()
        agent_widget.setLayout(agent_layout)
        main_splitter.addWidget(agent_widget)

        main_layout.addWidget(main_splitter)
        # End of agent layout #

        self.setMouseTracking(True)

    def show_input_dialog(self, title: str, message: str):
        assert self.task_thread is not None
        self.dlg = InputDialog(title, message, self.task_thread.receive_user_input)
        self.dlg.setWindowModality(Qt.WindowModality.NonModal)
        self.dlg.show()

    def show_choice_dialog(self, title: str, message: str):
        self.dlg = ChoiceDialog(
            title,
            message,
            lambda: (
                self.task_thread.receive_user_input("y")
                if self.task_thread is not None
                else None
            ),
            lambda: (
                self.task_thread.receive_user_input("n")
                if self.task_thread is not None
                else None
            ),
        )
        self.dlg.setWindowModality(Qt.WindowModality.NonModal)
        self.dlg.show()

    def show_choice_dialog_python(self, title: str, message: str):
        assert self.task_thread is not None
        self.dlg = ChoiceDialogPython(
            title,
            message,
            lambda: (
                self.task_thread.receive_user_input("y")
                if self.task_thread is not None
                else None
            ),
            lambda: (
                self.task_thread.receive_user_input("n")
                if self.task_thread is not None
                else None
            ),
        )
        self.dlg.setWindowModality(Qt.WindowModality.NonModal)
        self.dlg.show()

    def set_task_status_bar_text(self, color: str, text: str) -> None:
        self.task_status_bar.setStyleSheet(color)
        self.task_status_bar.setText(text)

    def populate_instruction_selection_widget(self):
        self.instruction_selection.clear()
        for task in self.task_configs:
            item = QListWidgetItem(task.instruction)
            self.instruction_selection.addItem(item)

    def select_task_instruction(self, item):
        self.task_instruction = item.text()
        selected_task_idx = self.instruction_selection.currentRow()
        self.selected_task = self.task_configs[selected_task_idx]
        self.task_config_display.setText(self.selected_task.model_dump_json(indent=4))
        self.evaluation_display.clear()
        self.output_display.clear()
        # if self.selected_task.task_id in self.task_results:
        #     score = self.task_results[self.selected_task.task_id]["score"]
        #     feedback = self.task_results[self.selected_task.task_id]["feedback"]
        #     self.evaluation_display.setPlainText(
        #         f"Score: {score}\n" f"Feedback: {feedback}"
        #     )

        self.start_button.setEnabled(True)

    def task_start(self):
        self.start_button.setEnabled(False)
        self.output_display.clear()
        self.evaluation_display.clear()
        self.instruction_selection.setEnabled(False)
        signals = WorkerSignals()
        signals.show_dialog_signal.connect(self.show_choice_dialog)
        signals.show_dialog_signal_python.connect(self.show_choice_dialog_python)
        signals.show_input_dialog_signal.connect(self.show_input_dialog)
        signals.runtime_output_signal.connect(self.output_display.setText)
        signals.evaluation_result_signal.connect(self.evaluation_display.setPlainText)
        signals.finish_signal.connect(self.task_finished)
        signals.status_bar_signal.connect(self.set_task_status_bar_text)
        self.task_thread = TaskThread(
            agent=self.agent,
            task_config=self.selected_task,
            signal=signals,
            args=self.args,
            interface=self,
        )
        self.task_thread.start()

    def task_finished(self):
        if self.task_thread is not None:
            self.task_thread.wait()
            self.task_thread = None
        self.interrupt_button.setEnabled(True)
        self.instruction_selection.setEnabled(True)

    def reset(self) -> None:
        """Resets the UI elements to their default state."""
        self.vnc_frame.reset()
        self.refresh_timer.start()
        # set widgets to default state
        self.interrupt_button.setEnabled(True)
        self.start_button.setEnabled(False)
        self.instruction_selection.setEnabled(True)
        # clear displays and selections
        self.instruction_selection.clearSelection()
        self.output_display.clear()
        self.evaluation_display.clear()
        self.task_config_display.clear()
        # clear current dlg
        if self.dlg is not None:
            self.dlg.close()
            self.dlg = None
        # clear working thread
        if self.task_thread is not None:
            self.task_thread.terminate()
            self.task_thread = None
        # reset status bar
        self.set_task_status_bar_text("color: green;", "Ready")
        self.status_bar.showMessage(
            "Connected. Please go to the terminal to check outputs."
        )

    def reconnect(self):
        self.status_bar.showMessage("Reconnecting")
        self.now_screenshot = np.zeros(
            (self.video_height, self.video_width, 4), dtype="uint8"
        )
        if self.capture_thread is not None:
            self.capture_thread.stop()
        if self.remote:
            self.capture_thread = VNCStreamer(
                config.env_server_addr, config.vnc_port, config.vnc_password
            )
        else:
            self.capture_thread = LocalStreamer(config.monitor_idx)
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
            assert self.capture_thread is not None
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
        self.frame_buffer.clear()
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
        self.agent.close()

        self.refresh_timer.stop()
        if self.capture_thread is not None:
            self.capture_thread.stop()

        exit(0)


def wait_finish(is_eval: bool, response: AgentStudioStatusResponse):
    if response.status == "finished":
        return response
    elif response.status == "wait_for_input":
        # Can't override in eval mode
        if config.need_human_confirmation and not is_eval:
            user_input = input(response.content)
        else:
            user_input = "y"
        response_raw = requests.post(
            url=f"{REMOTE_SERVER_ADDR}/task/confirm",
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
    task_configs_json = read_json(args.task_configs_path, args.start_idx, args.end_idx)
    task_configs: list[TaskConfig] = []
    for task_config in task_configs_json:
        task_configs.append(TaskConfig.model_validate(task_config))

    # Run evaluation
    scores = {}
    for task_config in tqdm(task_configs, desc="Evaluating tasks"):
        try:
            # Reset
            if args.remote:
                response_raw = requests.post(
                    f"{REMOTE_SERVER_ADDR}/task/reset",
                    json=AgentStudioResetRequest(task_config=task_config).model_dump(),
                )
                response = AgentStudioStatusResponse(**response_raw.json())
                response = wait_finish(is_eval=False, response=response)
                assert (
                    response.status == "finished" and response.content == "success"
                ), f"Fail to reset task: {response.message}"
            else:
                evaluators = evaluator_router(task_config)
                evaluators.reset(task_config.reset_procedure)

            instruction = task_config.instruction
            logger.info(f"Task instruction: {instruction}")
            if "GMAIL_RECIPIENT" in instruction:
                gmail_recipient = config.gmail_recipient
                assert len(gmail_recipient) > 0, "GMAIL_RECIPIENT is not set."
                instruction = instruction.replace("GMAIL_RECIPIENT", gmail_recipient)

            # Reset the agent
            agent.reset(task_config=task_config)
            if task_config.visual:
                assert (
                    interface is not None
                ), "Interface has to be open for visual tasks."
                interface.start_recording()

            # Loop until the task is done or the max step is reached.
            for t in range(task_config.max_steps):
                logger.info(f"Step {t}")
                if task_config.visual:
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

            task_trajectory_path = Path(log_dir) / task_config.task_id
            video_meta = None
            if task_config.visual:
                task_trajectory_path.mkdir(parents=True, exist_ok=True)
                video_path = (task_trajectory_path / "video.mp4").as_posix()
                video_meta = interface.save_video(video_path)
                logger.info(f"Video saved to {video_path}")

            if args.remote:
                response_raw = requests.post(
                    f"{REMOTE_SERVER_ADDR}/task/eval",
                    json=AgentStudioEvalRequest(
                        task_config=task_config,
                        kwargs=str(jsonpickle.encode({"trajectory": agent.trajectory})),
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
                score, feedback = evaluators(task_config.eval_procedure)

            scores[task_config.task_id] = score
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
            # Setup tasks
            task_configs_json = read_json(
                args.task_configs_path, args.start_idx, args.end_idx
            )
            task_configs: list[TaskConfig] = []
            for task_config in task_configs_json:
                task_configs.append(TaskConfig.model_validate(task_config))
            # Create the main interface.
            interface = AgentMonitor(
                args=args,
                remote=args.remote,
                task_configs=task_configs,
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

            sys.exit(app.exec())
        except asyncio.exceptions.CancelledError:
            sys.exit(0)


if __name__ == "__main__":
    main()
