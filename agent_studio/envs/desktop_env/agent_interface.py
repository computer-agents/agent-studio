import logging
import queue
import threading
import time
from pathlib import Path

import numpy as np
import pyautogui
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
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agent_studio.agent.base_agent import Agent
from agent_studio.config.config import Config
from agent_studio.envs.desktop_env.recorder.screen_recorder import (
    ScreenRecorder,
    VNCRecorder,
)
from agent_studio.envs.desktop_env.vnc_client import VNCFrame, VNCStreamer
from agent_studio.utils.communication import (
    AgentStudioEvalRequest,
    AgentStudioResetRequest,
    AgentStudioResponse,
    AgentStudioResultResponse,
    AgentStudioStatusResponse,
    AgentStudioTextRequest,
)
from agent_studio.utils.json_utils import export_trajectories, format_json, read_jsonl

config = Config()
logger = logging.getLogger(__name__)
REMOTE_SERVER_ADDR = f"{config.env_server_addr}:{config.env_server_port}"


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
    status_bar_signal = pyqtSignal(str, str)
    parsed_action_display_signal = pyqtSignal(str)
    response_display_signal = pyqtSignal(str)
    evaluation_display_signal = pyqtSignal(str)
    show_dialog_signal = pyqtSignal(str)
    output_display_signal = pyqtSignal(str)
    save_trajectory_signal = pyqtSignal()
    finish_run_task_signal = pyqtSignal()
    trajectory_display_signal = pyqtSignal(str)
    generate_action_signal = pyqtSignal()


class InputDialog(QDialog):
    def __init__(self, parent=None, message=""):
        super().__init__(parent)
        self.setWindowTitle("Input Dialog")
        self.setModal(True)

        layout = QVBoxLayout(self)

        self.messageLabel = QLabel(message, self)
        layout.addWidget(self.messageLabel)

        self.inputBox = QLineEdit(self)
        layout.addWidget(self.inputBox)

        self.confirmButton = QPushButton("Confirm", self)
        self.confirmButton.clicked.connect(self.accept)
        layout.addWidget(self.confirmButton)

        self.setWindowFlag(Qt.WindowType.CustomizeWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

    def accept(self):
        super().accept()


class ResetRuntimeThread(QThread):
    def __init__(self, signals: WorkerSignals):
        super().__init__()
        self.signals = signals

    def run(self):
        # reset remote runtime
        response_raw = requests.post(f"http://{REMOTE_SERVER_ADDR}/runtime/reset")
        assert response_raw.status_code == 200, f"{response_raw.status_code}"
        response = AgentStudioResponse(**response_raw.json())
        assert (
            response.status == "success"
        ), f"Fail to reset runtime: {response_raw.text}"
        self.signals.status_bar_signal.emit("color: green;", "Task: Ready")
        self.signals.start_signal.emit(True)

    def receive_user_input(self, text: str):
        raise NotImplementedError


class ResetTaskThread(QThread):
    def __init__(
        self,
        agent: Agent,
        signals: WorkerSignals,
        selected_task: dict,
    ):
        super().__init__()
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.signals = signals
        self.selected_task = selected_task
        self.agent = agent

    def _wait_finish(self):
        while True:
            response_raw = requests.get(f"http://{REMOTE_SERVER_ADDR}/task/status")
            assert response_raw.status_code == 200, f"{response_raw.status_code}"
            response = AgentStudioStatusResponse(**response_raw.json())
            if response.status == "finished":
                break
            elif response.status == "wait_for_input":
                self.signals.status_bar_signal.emit("color: blue;", "Waiting for input")
                self.mutex.lock()
                self.signals.show_dialog_signal.emit(response.content)
                self.wait_condition.wait(self.mutex)
                self.mutex.unlock()
                user_input = self.user_input
                response_raw = requests.post(
                    url=f"http://{REMOTE_SERVER_ADDR}/task/confirm",
                    json=AgentStudioTextRequest(message=user_input).model_dump(),
                )
                assert response_raw.status_code == 200, f"{response_raw.status_code}"
                response = AgentStudioResponse(**response_raw.json())
                assert response.status == "success"
            elif response.status == "pending":
                self.signals.status_bar_signal.emit("color: green;", "Pending")
            elif response.status == "in_progress":
                self.signals.status_bar_signal.emit("color: green;", "In Progress")
            else:
                raise ValueError(f"Unknown status: {response.status}")
            time.sleep(1)

    def run(self):
        assert self.selected_task is not None
        self.signals.status_bar_signal.emit("color: green;", "Task: Resetting Agent...")
        self.agent.reset(instruction=self.selected_task["instruction"])
        self.signals.status_bar_signal.emit("color: green;", "Task: Resetting Task...")
        response_raw = requests.post(
            f"http://{REMOTE_SERVER_ADDR}/task/reset",
            json=AgentStudioResetRequest(task_config=self.selected_task).model_dump(),
        )
        assert (
            response_raw.status_code == 200
        ), f"{response_raw.status_code} {response_raw.text}"
        response = AgentStudioResponse(**response_raw.json())
        assert response.status == "submitted"
        self._wait_finish()
        response_raw = requests.get(
            f"http://{REMOTE_SERVER_ADDR}/task/result",
        )
        assert response_raw.status_code == 200, f"{response_raw.status_code}"
        response = AgentStudioResultResponse(**response_raw.json())
        assert (
            response.status == "finished" and response.result == "success"
        ), f"Failed to reset task: {response.message}"
        self.signals.generate_action_signal.emit()

    def receive_user_input(self, text: str):
        self.mutex.lock()
        self.user_input = text  # Store the user input
        self.wait_condition.wakeAll()  # Resume the thread
        self.mutex.unlock()


class GenerateActionThread(QThread):
    def __init__(
        self,
        signals: WorkerSignals,
        selected_task: dict,
        obs: np.ndarray | None,
        agent: Agent,
    ) -> None:
        super().__init__()
        self.signals = signals
        self.selected_task = selected_task
        self.agent = agent
        self.obs = obs

    def run(self):
        self.signals.status_bar_signal.emit(
            "color: green;", "Task: Generating action..."
        )

        response, raw_code = self.agent.generate_action(self.obs)

        self.signals.status_bar_signal.emit(
            "color: blue;", "Task: Please Confirm Agent Action"
        )
        self.signals.parsed_action_display_signal.emit(raw_code)
        self.signals.response_display_signal.emit(response)
        self.signals.confirm_signal.emit(True)
        self.signals.decline_signal.emit(True)


class EvalTaskThread(QThread):
    def __init__(
        self,
        signals: WorkerSignals,
        trajectory_display: QTextEdit,
        selected_task: dict,
        agent: Agent,
        result_queue: queue.Queue,
        final_obs: np.ndarray | None = None,
    ):
        super().__init__()
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.signals = signals
        self.agent = agent
        self.selected_task = selected_task
        self.trajectory_display = trajectory_display
        self.result_queue = result_queue
        self.final_obs = final_obs

    def _wait_finish(self):
        while True:
            response_raw = requests.get(f"http://{REMOTE_SERVER_ADDR}/task/status")
            assert response_raw.status_code == 200, f"{response_raw.status_code}"
            response = AgentStudioStatusResponse(**response_raw.json())
            if response.status == "finished":
                break
            elif response.status == "wait_for_input":
                self.signals.status_bar_signal.emit("color: blue;", "Waiting for input")
                self.mutex.lock()
                self.signals.show_dialog_signal.emit(response.content)
                self.wait_condition.wait(self.mutex)
                self.mutex.unlock()
                user_input = self.user_input
                response_raw = requests.post(
                    url=f"http://{REMOTE_SERVER_ADDR}/task/confirm",
                    json=AgentStudioTextRequest(message=user_input).model_dump(),
                )
                assert response_raw.status_code == 200, f"{response_raw.status_code}"
                response = AgentStudioResponse(**response_raw.json())
                assert response.status == "success"
            elif response.status == "pending":
                self.signals.status_bar_signal.emit("color: green;", "Pending")
            elif response.status == "in_progress":
                self.signals.status_bar_signal.emit("color: green;", "In Progress")
            else:
                raise ValueError(f"Unknown status: {response.status}")
            time.sleep(1)

    def run(self):
        self.signals.status_bar_signal.emit("color: green;", "Task: Auto-Evaluating...")
        response_raw = requests.post(
            f"http://{REMOTE_SERVER_ADDR}/task/eval",
            json=AgentStudioEvalRequest(
                task_config=self.selected_task,
            ).model_dump(),
        )
        assert response_raw.status_code == 200, f"{response_raw.status_code}"
        response = AgentStudioResponse(**response_raw.json())
        assert response.status == "submitted"
        self._wait_finish()
        response_raw = requests.get(f"http://{REMOTE_SERVER_ADDR}/task/result")
        assert response_raw.status_code == 200, f"{response_raw.status_code}"
        response = AgentStudioResultResponse(**response_raw.json())
        assert response.status == "finished" and isinstance(
            response.message, dict
        ), f"Failed to evaluate task: {response.message}"
        self.signals.status_bar_signal.emit("color: green;", "Task: Self-Evaluating...")
        self_eval_result = self.agent.eval(self.final_obs)
        self.result_queue.put(response.message)
        self.result_queue.put(self_eval_result)
        self.signals.evaluation_display_signal.emit(
            "Auto-evaluation result:\n"
            f"Score: {response.message['score']}\n"
            f"Feedback: {response.message['feedback']}\n"
            "\nSelf-evaluation result:\n"
            f"Score: {self_eval_result['score']}\n"
            f"Feedback: {self_eval_result['response']}"
        )
        self.signals.status_bar_signal.emit(
            "color: green;", "Task: Saving trajectory..."
        )
        self.signals.save_trajectory_signal.emit()
        self.signals.status_bar_signal.emit("color: green;", "Task: Finished")

    def receive_user_input(self, text: str):
        self.mutex.lock()
        self.user_input = text  # Store the user input
        self.wait_condition.wakeAll()  # Resume the thread
        self.mutex.unlock()


class StepActionThread(QThread):
    def __init__(
        self,
        signals: WorkerSignals,
        trajectory_display: QTextEdit,
        parsed_action_display: QTextEdit,
        screen_recorder: ScreenRecorder | None,
        current_step_num: int,
        max_steps: int,
        agent: Agent,
    ):
        super().__init__()
        self.signals = signals
        self.agent = agent
        self.trajectory_display = trajectory_display
        self.parsed_action_display = parsed_action_display
        self.screen_recorder = screen_recorder
        self.current_step_num = current_step_num
        self.max_steps = max_steps

    def run(self):
        """Steps the next action and adds it to the trajectory."""
        next_action_text = self.parsed_action_display.toPlainText()
        result, done = self.agent.step_action(confirmed=True)
        self.signals.output_display_signal.emit(str(result))
        time.sleep(config.minimal_action_interval)

        if next_action_text.strip():
            current_trajectory_text = self.trajectory_display.toPlainText()
            new_trajectory_text = (
                current_trajectory_text + "\n" + next_action_text
                if current_trajectory_text
                else next_action_text
            )
            self.signals.trajectory_display_signal.emit(new_trajectory_text)

        if done or self.current_step_num >= self.max_steps:
            self.signals.finish_run_task_signal.emit()
        else:
            if self.screen_recorder is not None:
                obs = self.screen_recorder.get_current_frame()
                assert obs is not None
            else:
                obs = None
            response, raw_code = self.agent.generate_action(obs)
            self.signals.parsed_action_display_signal.emit(raw_code)
            self.signals.response_display_signal.emit(response)
            self.signals.confirm_signal.emit(True)
            self.signals.decline_signal.emit(True)

    def receive_user_input(self, text: str):
        raise NotImplementedError


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
        self.refresh_timer.setInterval(10)
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.start()
        self.refreshing_screen = False  # need for refresh flag
        self.selected_task: dict | None = None
        self.status_bar: QStatusBar
        self.task_status_bar: QLabel
        self.on_close = False

        self.vnc_thread: VNCStreamer | None = None
        self.current_thread: (
            ResetTaskThread
            | EvalTaskThread
            | StepActionThread
            | ResetRuntimeThread
            | GenerateActionThread
            | None
        )
        self.current_thread = None
        self.current_thread_result: queue.Queue = queue.Queue()

        self.current_step_num = 1
        self.action_token_count = 0

        # screen recorder
        self.record_path: Path = Path(record_path)
        self.recording_lock = threading.Lock()
        self.screen_recorder: ScreenRecorder | None = None
        self.video_meta: dict | None = None
        self.screen_width, self.screen_height = pyautogui.size()
        if not config.remote:
            self.video_width, self.video_height = pyautogui.size()

        self.setup_ui()

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
            self.vnc_thread = VNCStreamer(
                env_server_addr=config.env_server_addr,
                vnc_port=config.vnc_port,
                vnc_password=config.vnc_password,
            )
            self.vnc_thread.start()
            self.video_height, self.video_width = (
                self.vnc_thread.video_height,
                self.vnc_thread.video_width,
            )
            vnc_layout = QVBoxLayout()
            frame_size_hint = QSize(*config.vnc_frame_size)
            self.vnc_frame = VNCFrame(self, frame_size_hint)
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
        # goto evaluation step if user rejects the action
        self.decline_button.clicked.connect(self.reject_action)
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
        self.instruction_selection.itemDoubleClicked.connect(
            self.select_task_instruction
        )
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

        task_layout.addWidget(QLabel("Evaluation Result"))
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
        jsonl_path = self.record_path / config.result_jsonl_file
        if jsonl_path.exists():
            evaluated_tasks = read_jsonl(jsonl_path.as_posix())
            self.task_results = {
                task_result["task_id"]: task_result for task_result in evaluated_tasks
            }
        else:
            self.task_results = {}

    def populate_instruction_selection_widget(self):
        self.load_task_results()
        self.instruction_selection.clear()
        for task in self.task_configs:
            item = QListWidgetItem(task["instruction"])
            if task["task_id"] in self.task_results:
                if self.task_results[task["task_id"]]["score"] == 1.0:
                    item.setForeground(QColor("green"))
                else:
                    item.setForeground(QColor("red"))
            self.instruction_selection.addItem(item)

    def select_task_instruction(self, item):
        self.task_instruction = item.text()
        selected_task_idx = self.instruction_selection.currentRow()
        self.selected_task = self.task_configs[selected_task_idx]
        self.task_config_display.setText(format_json(self.selected_task))
        self.evaluation_display.clear()
        if self.selected_task["task_id"] in self.task_results:
            score = self.task_results[self.selected_task["task_id"]]["score"]
            feedback = self.task_results[self.selected_task["task_id"]]["feedback"]
            self.evaluation_display.setPlainText(
                f"Score: {score}\n" f"Feedback: {feedback}"
            )

        self.start_button.setEnabled(True)

    def set_task_status_bar_text(self, color: str, text: str) -> None:
        self.task_status_bar.setStyleSheet(color)
        self.task_status_bar.setText(text)

    def show_input_dialog(self, message: str):
        dlg = InputDialog(self, message)
        result = dlg.exec()
        assert result == QDialog.DialogCode.Accepted
        user_input = dlg.inputBox.text()
        assert self.current_thread is not None
        assert isinstance(self.current_thread, ResetTaskThread) or isinstance(
            self.current_thread, EvalTaskThread
        )
        self.current_thread.receive_user_input(user_input)

    def show_choice_dialog(self, message: str) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Confirm Action")
        dlg.setText(message)
        accept = dlg.addButton("Confirm", QMessageBox.ButtonRole.AcceptRole)
        dlg.addButton("Reject", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()

        if dlg.clickedButton() == accept:
            user_input = "y"
        else:
            user_input = "n"
        assert self.current_thread is not None
        assert isinstance(self.current_thread, ResetTaskThread) or isinstance(
            self.current_thread, EvalTaskThread
        )
        self.current_thread.receive_user_input(user_input)

    def reset(self):
        """Resets the task and waits for the environment to be ready."""
        self.set_task_status_bar_text("color: green;", "Task: Preparing...")
        # Clears all the text fields.
        self.eval_button.setEnabled(False)
        self.start_button.setEnabled(False)  # move to ResetRuntimeThread
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
        self.action_token_count = 0
        # Reset screen recorder
        self.video_meta = None
        if self.screen_recorder is not None:
            del self.screen_recorder
            self.screen_recorder = None
        # Reset remote runtime
        signals = WorkerSignals()
        signals.start_signal.connect(self.start_button.setEnabled)
        signals.status_bar_signal.connect(self.set_task_status_bar_text)
        self.current_thread = ResetRuntimeThread(signals)
        self.current_thread.start()
        self.populate_instruction_selection_widget()

    def reconnect(self):
        self.status_bar.showMessage("Reconnecting")
        if self.vnc_thread is not None:
            self.vnc_thread = VNCStreamer(
                env_server_addr=config.env_server_addr,
                vnc_port=config.vnc_port,
                vnc_password=config.vnc_password,
            )
            self.vnc_thread.start()
        if (
            self.screen_recorder is not None
            and isinstance(self.screen_recorder, VNCRecorder)
            and self.vnc_thread is not None
        ):
            self.screen_recorder.vnc_streamer = self.vnc_thread
        self.status_bar.showMessage("Connected")

    def save_trajectory(self):
        assert self.selected_task is not None
        assert isinstance(self.current_thread, EvalTaskThread)
        logger.info(f"Save trajectory for task: {self.selected_task['task_id']}")
        auto_eval_result = self.current_thread_result.get()
        export_trajectories(
            self_eval_results=self.current_thread_result.get(),
            task_config=self.selected_task,
            trajectory=self.agent.trajectory,
            record_path=self.record_path.as_posix(),
            score=float(auto_eval_result["score"]),
            feedback=auto_eval_result["feedback"],
            token_count=self.action_token_count,
            video_meta=self.video_meta,
            jsonl_name=config.result_jsonl_file,
        )
        self.next_button.setEnabled(True)

    def run_task(self):
        self.instruction_selection.setEnabled(False)
        self.evaluation_display.clear()

        if self.selected_task is None:
            self.set_task_status_bar_text("color: red;", "Task: No task selected")
            self.instruction_selection.setEnabled(True)
            return
        else:
            self.set_task_status_bar_text("color: green;", "Task: Initializing...")
        logger.info(f"Run task: {self.selected_task['task_id']}")

        self.start_button.setEnabled(False)
        self.eval_button.setEnabled(False)
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.next_button.setEnabled(False)

        signals = WorkerSignals()
        signals.status_bar_signal.connect(self.set_task_status_bar_text)
        signals.show_dialog_signal.connect(self.show_choice_dialog)
        signals.generate_action_signal.connect(self.generate_action)
        self.current_thread_result = queue.Queue()
        self.current_thread = ResetTaskThread(
            agent=self.agent, signals=signals, selected_task=self.selected_task
        )
        self.current_thread.start()

    def generate_action(self) -> None:
        assert self.selected_task is not None
        logger.info(f"Generate action for task: {self.selected_task['task_id']}")

        if self.selected_task["visual"]:
            if config.remote:
                assert self.vnc_thread is not None
                self.screen_recorder = VNCRecorder(
                    fps=config.video_fps, vnc_streamer=self.vnc_thread
                )
            else:
                # assert False, "Local recording is not supported"
                self.screen_recorder = ScreenRecorder(fps=config.video_fps)
            self.screen_recorder.start()

        if self.selected_task["visual"]:
            assert self.screen_recorder is not None
            obs = self.screen_recorder.get_current_frame()
        else:
            obs = None
        signals = WorkerSignals()
        signals.confirm_signal.connect(self.confirm_button.setEnabled)
        signals.decline_signal.connect(self.decline_button.setEnabled)
        signals.status_bar_signal.connect(self.set_task_status_bar_text)
        signals.parsed_action_display_signal.connect(
            self.parsed_action_display.setPlainText
        )
        signals.response_display_signal.connect(self.response_display.setPlainText)
        self.current_thread = GenerateActionThread(
            signals=signals,
            selected_task=self.selected_task,
            obs=obs,
            agent=self.agent,
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
        signals.show_dialog_signal.connect(self.show_input_dialog)
        signals.save_trajectory_signal.connect(self.save_trajectory)
        self.current_thread_result = queue.Queue()
        self.current_thread = EvalTaskThread(
            signals=signals,
            selected_task=self.selected_task,
            agent=self.agent,
            trajectory_display=self.trajectory_display,
            result_queue=self.current_thread_result,
            final_obs=self.screen_recorder.get_current_frame()
            if self.screen_recorder
            else None,
        )
        self.current_thread.start()

    def finish_run_task(self) -> None:
        assert self.selected_task is not None
        self.action_token_count = self.agent.get_token_count()
        task_trajectory_path = self.record_path / self.selected_task["task_id"]
        task_trajectory_path.mkdir(parents=True, exist_ok=True)
        if self.selected_task["visual"]:
            assert self.screen_recorder is not None
            video_path = (task_trajectory_path / "video.mp4").as_posix()
            self.screen_recorder.stop()
            self.screen_recorder.wait_exit()
            self.video_meta = self.screen_recorder.save(video_path, 0)
        else:
            video_path = None
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.eval_button.setEnabled(True)
        self.set_task_status_bar_text("color: green;", "Task: Executed")

    def reject_action(self) -> None:
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.set_task_status_bar_text("color: green;", "Task: Executing...")
        result, done = self.agent.step_action(confirmed=False)
        self.output_display.setPlainText(str(result))
        self.finish_run_task()

    def step_action(self) -> None:
        """Steps the next action and adds it to the trajectory."""
        assert self.selected_task is not None
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.set_task_status_bar_text("color: green;", "Task: Executing...")

        signals = WorkerSignals()
        signals.status_bar_signal.connect(self.set_task_status_bar_text)
        signals.response_display_signal.connect(self.response_display.setPlainText)
        signals.output_display_signal.connect(self.output_display.setPlainText)
        signals.trajectory_display_signal.connect(self.trajectory_display.setPlainText)
        signals.parsed_action_display_signal.connect(
            self.parsed_action_display.setPlainText
        )
        signals.confirm_signal.connect(self.confirm_button.setEnabled)
        signals.decline_signal.connect(self.decline_button.setEnabled)
        signals.finish_run_task_signal.connect(self.finish_run_task)
        self.current_thread_result = queue.Queue()
        self.current_thread = StepActionThread(
            signals=signals,
            trajectory_display=self.trajectory_display,
            parsed_action_display=self.parsed_action_display,
            screen_recorder=self.screen_recorder,
            current_step_num=self.current_step_num,
            max_steps=self.selected_task["max_steps"],
            agent=self.agent,
        )
        self.current_thread.start()
        self.current_step_num += 1

    def interrupt_action(self):
        # TODO: send interrupt signal to the runtime
        pass

    def update_screen(self):
        try:
            if config.remote:
                with self.recording_lock:
                    assert self.vnc_thread is not None
                    frame = self.vnc_thread.get_current_frame()
                if frame is not None:
                    qimage = QImage(
                        frame.tobytes(),
                        self.video_width,
                        self.video_height,
                        QImage.Format.Format_RGB888,
                    )
                    self.vnc_frame.update(qimage)
        except Exception as e:
            logger.error("Fail to get screenshot.", e)

    def render(self):
        self.refresh_timer.stop()

        if self.refreshing_screen:
            self.refresh_timer.start()
            return

        self.refreshing_screen = True
        self.update_screen()
        if self.vnc_thread is not None:
            if local_cursor_pos := self.vnc_frame.get_cursor_pos():
                self.status_bar.showMessage(f"Cursor Position: {str(local_cursor_pos)}")

        self.refreshing_screen = False
        self.refresh_timer.start()

    def closeEvent(self, event):
        self.status_bar.showMessage("Closing")
        self.on_close = True
        if self.screen_recorder is not None:
            self.screen_recorder.stop()
            self.screen_recorder.wait_exit()
        if self.vnc_thread is not None:
            self.vnc_thread.stop()
        self.refresh_timer.stop()
        logger.info("GUI closed")
        exit(0)
