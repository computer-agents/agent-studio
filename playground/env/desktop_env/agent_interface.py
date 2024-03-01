import asyncio
import functools
import logging
import sys
from pathlib import Path
import time
from asyncio import open_connection
import threading
from typing import Any

import cv2
from PIL import Image
import numpy as np
import mss
import pyautogui
import requests
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QObject, QMutex, QWaitCondition
from PyQt6.QtGui import QImage, QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QStatusBar,
    QInputDialog,
    QListWidgetItem,
)
from qasync import QApplication, asyncClose, asyncSlot

from playground.agent.base_agent import Agent
from playground.config.config import Config
from playground.env.desktop_env.vnc_client import VNCClient, VNCFrame
from playground.utils.communication import (
    PlaygroundEvalRequest,
    PlaygroundResetRequest,
    PlaygroundResponse,
    PlaygroundResultResponse,
    PlaygroundStatusResponse,
    PlaygroundTextRequest,
    bytes2str,
)
from playground.utils.json_utils import format_json, add_jsonl, read_jsonl

config = Config()
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

class WorkerSignals(QObject):
    confirm_signal = pyqtSignal(bool)
    decline_signal = pyqtSignal(bool)
    start_signal = pyqtSignal(bool)
    eval_signal = pyqtSignal(bool)
    next_task_signal = pyqtSignal(bool)
    status_bar_signal = pyqtSignal(str, str)
    parsed_action_display_signal = pyqtSignal(str)
    response_display_signal = pyqtSignal(str)
    evaluation_display_signal = pyqtSignal(str)
    show_input_dialog_signal = pyqtSignal(str)
    save_trajectory_signal = pyqtSignal()

class RunTaskThread(QThread):
    def __init__(
            self,
            signals: WorkerSignals,
            selected_task: dict,
            obs: np.ndarray,
            agent: Agent
        ):
        super().__init__()
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.signals = signals
        self.agent = agent
        self.selected_task = selected_task
        self.obs = obs

    def _wait_finish(self):
        while True:
            response_raw = requests.get(
                f"http://{config.env_server_addr}:{config.env_server_port}/task/status"
            )
            response = PlaygroundStatusResponse(**response_raw.json())
            if response.status == "finished":
                break
            elif response.status == "wait_for_input":
                if config.need_human_confirmation:
                    self.signals.status_bar_signal.emit("color: blue;", "Waiting for input")
                    self.mutex.lock()
                    self.signals.show_input_dialog_signal.emit(response.content)
                    self.wait_condition.wait(self.mutex)
                    self.mutex.unlock()
                    user_input = self.user_input
                else:
                    user_input = "y"
                response_raw = requests.post(
                    url=f"http://{config.env_server_addr}:{config.env_server_port}/task/confirm",
                    json=PlaygroundTextRequest(message=user_input).model_dump(),
                )
                response = PlaygroundResponse(**response_raw.json())
                assert response.status == "success"
            elif response.status == "pending":
                self.signals.status_bar_signal.emit("color: green;", "Pending")
            elif response.status == "in_progress":
                self.signals.status_bar_signal.emit("color: green;", "In Progress")
            else:
                raise ValueError(f"Unknown status: {response.status}")
            time.sleep(1)

    def reset_task(self):
        assert self.selected_task is not None
        response_raw = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/reset",
            json=PlaygroundResetRequest(task_config=self.selected_task).model_dump(),
        )
        response = PlaygroundResponse(**response_raw.json())
        assert response.status == "submitted"
        self._wait_finish()
        response_raw = requests.get(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/result",
        )
        response = PlaygroundResultResponse(**response_raw.json())
        # TODO: handle failed reset
        assert response.status == "finished" and response.result == "success"
        self.agent.reset(
            instruction=self.selected_task["instruction"],
        )

    def run(self):
        self.reset_task()
        self.signals.status_bar_signal.emit("color: green;", "Task: Generating action...")

        raw_code, code, _ = self.agent.generate_action(self.obs)

        self.signals.status_bar_signal.emit("color: blue;", "Task: Waiting for confirmation...")
        self.signals.parsed_action_display_signal.emit(code)
        self.signals.response_display_signal.emit(raw_code)
        self.signals.confirm_signal.emit(True)
        self.signals.decline_signal.emit(True)

    def receive_user_input(self, text: str):
        self.mutex.lock()
        self.user_input = text  # Store the user input
        self.wait_condition.wakeAll()  # Resume the thread
        self.mutex.unlock()


class EvalTaskThread(QThread):
    def __init__(
            self,
            signals: WorkerSignals,
            trajectory_display: QTextEdit,
            selected_task: dict,
            agent: Agent
        ):
        super().__init__()
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.signals = signals
        self.agent = agent
        self.selected_task = selected_task
        self.trajectory_display = trajectory_display

    def _wait_finish(self):
        while True:
            response_raw = requests.get(
                f"http://{config.env_server_addr}:{config.env_server_port}/task/status"
            )
            response = PlaygroundStatusResponse(**response_raw.json())
            if response.status == "finished":
                break
            elif response.status == "wait_for_input":
                self.signals.status_bar_signal.emit("color: blue;", "Waiting for input")
                self.mutex.lock()
                self.signals.show_input_dialog_signal.emit(response.content)
                self.wait_condition.wait(self.mutex)
                self.mutex.unlock()
                user_input = self.user_input
                response_raw = requests.post(
                    url=f"http://{config.env_server_addr}:{config.env_server_port}/task/confirm",
                    json=PlaygroundTextRequest(message=user_input).model_dump(),
                )
                response = PlaygroundResponse(**response_raw.json())
                assert response.status == "success"
            elif response.status == "pending":
                self.signals.status_bar_signal.emit("color: green;", "Pending")
            elif response.status == "in_progress":
                self.signals.status_bar_signal.emit("color: green;", "In Progress")
            else:
                raise ValueError(f"Unknown status: {response.status}")
            time.sleep(1)

    def run(self):
        response_raw = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/eval",
            json=PlaygroundEvalRequest(
                task_config=self.selected_task,
                trajectory=bytes2str(self.trajectory_display.toPlainText()),
            ).model_dump(),
        )
        response = PlaygroundResponse(**response_raw.json())
        assert response.status == "submitted"
        self.signals.status_bar_signal.emit("color: green;", "Task: Evaluating...")
        self._wait_finish()
        response_raw = requests.get(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/result"
        )
        response = PlaygroundResultResponse(**response_raw.json())
        assert response.status == "finished" and isinstance(response.message, dict)
        self.signals.evaluation_display_signal.emit(
            f"Score: {response.message['score']}\nFeedback: {response.message['feedback']}"
        )
        self.signals.next_task_signal.emit(True)
        self.signals.status_bar_signal.emit("color: green;", "Task: Saving trajectory...")
        self.signals.save_trajectory_signal.emit()
        self.signals.status_bar_signal.emit("color: green;", "Task: Finished")

    def receive_user_input(self, text: str):
        self.mutex.lock()
        self.user_input = text  # Store the user input
        self.wait_condition.wakeAll()  # Resume the thread
        self.mutex.unlock()

class AgentInterface(QMainWindow):
    layout_width = 300

    def __init__(
        self,
        agent: Agent,
        task_configs: list,
        record_path: str = config.record_path,
    ):
        super().__init__()
        self.agent = agent
        self.task_list = [task["instruction"] for task in task_configs]
        self.task_configs = task_configs
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1)
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.stop()
        self.refreshing_screen = False  # need for refresh flag
        self.selected_task: dict | None = None
        self.status_bar: QStatusBar
        self.task_status_bar: QLabel
        self.on_close = False

        # screen recorder
        self.record_path: Path = Path(record_path)
        self.recording_lock = threading.Lock()
        self.frame_buffer = FrameBuffer()
        self.current_frame_id = -1
        self.is_recording = False
        if not config.remote:
            self.video_width, self.video_height = pyautogui.size()

        self.setup_ui()
        self.screenshot_thread = threading.Thread(target=self.capture_screen)
        self.screenshot_thread.start()

        self.vnc = None
        self.reset()

    def setup_ui(self):
        """Sets up the UI, including the VNC frame (left) and the right layout."""
        self.setWindowTitle("Remote Agent Interface")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setMouseTracking(True)
        main_layout = QHBoxLayout(central_widget)

        self.status_bar = self.statusBar()
        assert self.status_bar is not None

        self.task_status_bar = QLabel()
        self.set_task_status_bar_text("color: green;", "Task: Init")
        self.status_bar.addPermanentWidget(self.task_status_bar)

        if config.remote:
            self.connect_vnc()
            vnc_layout = QVBoxLayout()
            self.vnc_frame = VNCFrame(self)
            vnc_layout.addWidget(self.vnc_frame)
            reconnect_button = QPushButton("Re-connect")
            reconnect_button.clicked.connect(self.reconnect)
            vnc_layout.addWidget(reconnect_button)
            main_layout.addLayout(vnc_layout)

        agent_layout = QVBoxLayout()

        agent_layout.addWidget(QLabel("Model response"))
        self.response_display = QTextEdit(self)
        agent_layout.addWidget(self.response_display)
        self.response_display.setReadOnly(True)
        # self.response_display.setFixedHeight(300)

        agent_layout.addWidget(QLabel("Parsed Actions"))
        self.parsed_action_display = QTextEdit(self)
        agent_layout.addWidget(self.parsed_action_display)
        self.parsed_action_display.setReadOnly(True)

        self.confirm_button = QPushButton("Accept")
        self.decline_button = QPushButton("Reject")
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.step_action)
        # self.decline_button.clicked.connect(self.reset)
        consent_button_layout = QHBoxLayout()
        consent_button_layout.addWidget(self.confirm_button)
        consent_button_layout.addWidget(self.decline_button)

        agent_layout.addLayout(consent_button_layout)

        agent_layout.addWidget(QLabel("Runtime output"))
        self.output_display = QTextEdit(self)
        # self.output_display.setFixedHeight(40)
        agent_layout.addWidget(self.output_display)
        self.output_display.setReadOnly(True)

        # interrupt_button = QPushButton("Interrupt action")
        # interrupt_button.clicked.connect(self.interrupt_action)
        # agent_layout.addWidget(interrupt_button)

        agent_layout.addWidget(QLabel("Trajectory"))
        self.trajectory_display = QTextEdit(self)
        agent_layout.addWidget(self.trajectory_display)
        self.trajectory_display.setReadOnly(True)
        # self.trajectory_display.setFixedWidth(self.layout_width)

        main_layout.addLayout(agent_layout)

        task_layout = QVBoxLayout()


        task_layout.addWidget(QLabel("Task configuration"))
        self.task_config_display = QTextEdit(self)
        task_layout.addWidget(self.task_config_display)
        self.task_config_display.setReadOnly(True)
        # self.task_config_display.setFixedHeight(200)
        # self.task_config_display.setFixedWidth(self.layout_width)

        task_layout.addWidget(QLabel("Task Selection (double click to select)"))
        self.instruction_selection = QListWidget(self)
        self.instruction_selection.itemDoubleClicked.connect(self.select_task_instruction)
        task_layout.addWidget(self.instruction_selection)
        self.instruction_selection.clear()
        self.populate_instruction_selection_widget()
        # self.instruction_selection.addItems(self.task_list)

        execution_button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.run_task)
        execution_button_layout.addWidget(self.start_button)

        self.eval_button = QPushButton("Evaluate")
        self.eval_button.setEnabled(False)
        self.eval_button.clicked.connect(self.eval_task)
        execution_button_layout.addWidget(self.eval_button)

        # auto_eval_button = QPushButton("Auto-evaluate")
        # auto_eval_button.clicked.connect(self.auto_eval)
        # agent_layout.addWidget(auto_eval_button)

        task_layout.addLayout(execution_button_layout)

        task_layout.addWidget(QLabel("Evaluation result"))
        self.evaluation_display = QTextEdit(self)
        task_layout.addWidget(self.evaluation_display)
        self.evaluation_display.setReadOnly(True)
        # self.evaluation_display.setFixedHeight(60)
        # self.evaluation_display.setFixedWidth(self.layout_width)

        self.next_button = QPushButton("Next task")
        self.next_button.clicked.connect(self.reset)
        task_layout.addWidget(self.next_button)

        self.status_bar.showMessage("Ready")

        main_layout.addLayout(task_layout)

        self.setMouseTracking(True)

    def load_task_results(self):
        jsonl_path = self.record_path / "tasks.jsonl"
        if jsonl_path.exists():
            evaluated_tasks = read_jsonl(jsonl_path.as_posix())
            self.task_results = {
                task_result["task_config"]["task_id"]: task_result \
                    for task_result in evaluated_tasks
            }
        else:
            self.task_results = {}

    def populate_instruction_selection_widget(self):
        self.load_task_results()
        self.instruction_selection.clear()
        for task in self.task_configs:
            item = QListWidgetItem(task["instruction"])
            if task["task_id"] in self.task_results:
                if self.task_results[task["task_id"]]["score"] == "1.0":
                    item.setForeground(QColor('green'))
                else:
                    item.setForeground(QColor('red'))
            self.instruction_selection.addItem(item)

    def select_task_instruction(self, item):
        self.task_instruction = item.text()
        selected_task_idx = self.instruction_selection.currentRow()
        self.selected_task = self.task_configs[selected_task_idx]
        self.task_config_display.setText(format_json(self.selected_task))
        self.evaluation_display.clear()
        if self.selected_task["task_id"] in self.task_results:
            self.evaluation_display.setPlainText(
                f"Score: {self.task_results[self.selected_task['task_id']]['score']}\n"
                    f"Feedback: {self.task_results[self.selected_task['task_id']]['feedback']}"
                )

        self.start_button.setEnabled(True)

    def capture_screen(self) -> None:
        if config.remote:
            while True:
                if self.on_close:
                    break
                if self.is_recording:
                    frame = self.now_screenshot.copy()
                    capture_time = time.time()
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    # add frame to buffer
                    self.current_frame_id += 1
                    self.frame_buffer.add_frame(self.current_frame_id, frame)
                    # preserve the frame rate
                    wait_time = 1 / config.video_fps - (time.time() - capture_time)
                    if wait_time > 0:
                        time.sleep(wait_time)
                    elif wait_time < 0:
                        logger.warning("Frame rate is too high")
                else:
                    time.sleep(1 / config.video_fps)
        else:
            with mss.mss(with_cursor=False) as sct:
                while True:
                    if self.on_close:
                        break
                    if self.is_recording:
                        frame = sct.grab(
                            {
                                "left": 0,
                                "top": 0,
                                "width": self.video_width,
                                "height": self.video_height,
                            }
                        )
                        capture_time = time.time()
                        frame = np.array(frame)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        # add frame to buffer
                        self.current_frame_id += 1
                        self.frame_buffer.add_frame(self.current_frame_id, frame)
                        # preserve the frame rate
                        wait_time = 1 / config.video_fps - (time.time() - capture_time)
                        if wait_time > 0:
                            time.sleep(wait_time)
                        elif wait_time < 0:
                            logger.warning("Frame rate is too high")
                    else:
                        time.sleep(1 / config.video_fps)

    @asyncSlot()
    async def reconnect(self):
        """Reconnects to VNC server."""
        if self.vnc is not None:
            await self.vnc.disconnect()
        await self.connect_vnc()

    @asyncSlot()
    async def connect_vnc(self):
        """Connects to VNC server."""
        self.status_bar.showMessage("Connecting")

        try:
            self._reader, self._writer = await open_connection(
                config.env_server_addr, config.vnc_port
            )
            self.vnc = await VNCClient.create(
                reader=self._reader, writer=self._writer, password=config.vnc_password
            )
        except (ConnectionRefusedError, ValueError) as e:
            logger.warning(f"Fail to connect to VNC server: {e}")
            self.status_bar.showMessage(f"VNC not available.")
            return
        self.video_height = self.vnc.video.height
        self.video_width = self.vnc.video.width
        with self.recording_lock:
            self.now_screenshot = np.zeros(
                (self.video_height, self.video_width, 4), dtype="uint8"
            )

        self.vnc_frame.setFixedSize(self.video_width, self.video_height)
        self.vnc_frame.setMouseTracking(True)
        self.showMaximized()

        self.refresh_timer.start()
        self.status_bar.showMessage("Connected")

    def set_task_status_bar_text(self, color: str, text: str) -> None:
        self.task_status_bar.setStyleSheet(color)
        self.task_status_bar.setText(text)

    def show_input_dialog(self, message: str):
        dlg = QInputDialog()
        dlg.setLabelText(message)
        dlg.show()
        dlg.findChildren(QPushButton)[1].hide()
        result = dlg.exec()
        assert result == QInputDialog.DialogCode.Accepted
        user_input = dlg.textValue()
        self.current_thread.receive_user_input(user_input)

    def reset(self):
        """Resets the task and waits for the environment to be ready."""
        # Clears all the text fields.
        self.eval_button.setEnabled(False)
        self.start_button.setEnabled(True)
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.instruction_selection.setEnabled(True)
        self.task_config_display.clear()
        self.trajectory_display.clear()
        self.parsed_action_display.clear()
        self.response_display.clear()
        self.output_display.clear()
        self.evaluation_display.clear()
        self.selected_task = None
        self.populate_instruction_selection_widget()
        self.set_task_status_bar_text("color: green;", "Task: Init")

    def save_trajectory(self):
        assert self.selected_task is not None
        self.is_recording = False

        task_trajectory_path: Path = self.record_path / self.selected_task["task_id"]
        video_path: Path = task_trajectory_path / ("video.mp4")
        if task_trajectory_path != Path("") and not task_trajectory_path.exists():
            task_trajectory_path.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            video_path.as_posix(),
            cv2.VideoWriter.fourcc(*"mp4v"),
            config.video_fps,
            (
                self.video_width,
                self.video_height,
            ),
        )

        frames = self.frame_buffer.get_frames(0)
        logger.info(f"Captured {len(frames)} frames with FPS={config.video_fps}")
        for frame in frames:
            writer.write(frame[1])
        writer.release()

        record_dict: dict[str, Any] = {
            "task_config": self.selected_task
        }
        record_dict["video"] = {
            "path": video_path.as_posix(),
        }

        trajectory = self.agent.get_trajectory()
        record_dict["actions"] = []
        for idx, action in enumerate(trajectory):
            im = Image.fromarray(action["obs"])
            img_path = (task_trajectory_path / (f"{idx}.png")).as_posix()
            im.save(img_path)
            record_dict["actions"].append(
                {
                    "timestamp": action["timestamp"],
                    "obs": img_path,
                    "action": action["act"],
                    "result": action["res"],
                }
            )

        record_dict["score"] = self.evaluation_display.toPlainText().split("\n")[0].split(":")[1].strip()
        record_dict["feedback"] = self.evaluation_display.toPlainText().split("\n")[1].split(":")[1].strip()

        add_jsonl(
            data=[record_dict],
            file_path=(self.record_path / "tasks.jsonl").as_posix(),
        )

        self.frame_buffer.clear()
        self.current_frame_id = -1

    def run_task(self):
        self.instruction_selection.setEnabled(False)
        self.evaluation_display.clear()

        if self.selected_task is None:
            self.set_task_status_bar_text("color: red;", "Task: No task selected")
            self.instruction_selection.setEnabled(True)
            return
        else:
            self.set_task_status_bar_text("color: green;", "Task: Initializing...")
        self.is_recording = True
        self.start_button.setEnabled(False)
        self.eval_button.setEnabled(False)
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.next_button.setEnabled(False)

        signals = WorkerSignals()
        signals.confirm_signal.connect(self.confirm_button.setEnabled)
        signals.decline_signal.connect(self.decline_button.setEnabled)
        signals.status_bar_signal.connect(self.set_task_status_bar_text)
        signals.parsed_action_display_signal.connect(self.parsed_action_display.setPlainText)
        signals.response_display_signal.connect(self.response_display.setPlainText)
        signals.show_input_dialog_signal.connect(self.show_input_dialog)
        obs=self.now_screenshot.copy()
        self.current_thread = RunTaskThread(
            signals=signals,
            selected_task=self.selected_task,
            agent=self.agent,
            obs=obs,
        )
        self.current_thread.start()

    def eval_task(self):
        self.start_button.setEnabled(False)
        self.eval_button.setEnabled(False)
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.next_button.setEnabled(False)
        if self.selected_task is None:
            self.set_task_status_bar_text("color: red;", "Task: No task selected")
            return
        else:
            self.set_task_status_bar_text("color: green;", "Task: Evaluating...")

        signals = WorkerSignals()
        signals.status_bar_signal.connect(self.set_task_status_bar_text)
        signals.evaluation_display_signal.connect(self.evaluation_display.setPlainText)
        signals.next_task_signal.connect(self.next_button.setEnabled)
        signals.show_input_dialog_signal.connect(self.show_input_dialog)
        signals.save_trajectory_signal.connect(self.save_trajectory)
        self.current_thread = EvalTaskThread(
            signals=signals,
            selected_task=self.selected_task,
            agent=self.agent,
            trajectory_display=self.trajectory_display
        )
        self.current_thread.start()

    def step_action(self):
        """Steps the next action and adds it to the trajectory."""
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.set_task_status_bar_text("color: green;", "Task: Executing...")
        next_action_text = self.parsed_action_display.toPlainText()
        result, done = self.agent.step_action(confirmed=True)
        self.output_display.setPlainText(str(result))

        if next_action_text.strip():
            current_trajectory_text = self.trajectory_display.toPlainText()
            new_trajectory_text = (
                current_trajectory_text + "\n" + next_action_text
                if current_trajectory_text
                else next_action_text
            )
            self.trajectory_display.setPlainText(new_trajectory_text)
            self.parsed_action_display.clear()

        if not done:
            obs=self.now_screenshot.copy()
            raw_code, code, _ = self.agent.generate_action(obs)
            self.parsed_action_display.setPlainText(code)
            self.response_display.setPlainText(raw_code)
            self.confirm_button.setEnabled(True)
            self.decline_button.setEnabled(True)
        else:
            self.confirm_button.setEnabled(False)
            self.decline_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.eval_button.setEnabled(True)
        self.set_task_status_bar_text("color: green;", "Task: Executed")

    def interrupt_action(self):
        # TODO: send interrupt signal to the runtime
        pass

    async def update_screen(self):
        try:
            if config.remote and self.vnc is not None:
                with self.recording_lock:
                    self.now_screenshot = await self.vnc.screenshot()

                    rgba_array = self.now_screenshot.copy()
                if rgba_array is not None:
                    qimage = QImage(
                        rgba_array.tobytes(),
                        self.video_width,
                        self.video_height,
                        QImage.Format.Format_RGBA8888,
                    )
                    self.vnc_frame.update(qimage)
        except Exception as e:
            logger.error("Fail to get screenshot.", e)

    @asyncSlot()
    async def render(self):
        self.refresh_timer.stop()

        if self.refreshing_screen:
            self.refresh_timer.start()
            return

        self.refreshing_screen = True
        await self.update_screen()
        if self.vnc is not None:
            if local_cursor_pos := self.vnc_frame.get_cursor_pos():
                self.status_bar.showMessage(f"Cursor Position: {str(local_cursor_pos)}")

        self.refreshing_screen = False
        self.refresh_timer.start()

    @asyncClose
    async def closeEvent(self, event):
        self.status_bar.showMessage("Closing")
        self.on_close = True
        self.screenshot_thread.join()
        self.refresh_timer.stop()
        if self.vnc is not None:
            await self.vnc.disconnect()
            logger.info("VNC disconnected")
        logger.info("GUI closed")
        exit(0)


async def run_ui(agent: Agent, task_configs: list[dict], record_path: str):
    def close_future(future, loop):
        loop.call_later(10, future.cancel)
        future.cancel()

    loop = asyncio.get_event_loop()
    future: asyncio.Future = asyncio.Future()

    app = QApplication(sys.argv)
    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            functools.partial(close_future, future, loop)
        )

    interface = AgentInterface(
        agent=agent,
        task_configs=task_configs,
        record_path=record_path,
    )

    interface.show()

    await future
