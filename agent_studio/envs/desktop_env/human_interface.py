import ast
import json
import logging
import os
import queue
import threading
import uuid
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
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
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

from agent_studio.agent.human_agent import HumanAgent
from agent_studio.config.config import Config
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
from agent_studio.utils.json_utils import (
    add_jsonl,
    export_trajectories,
    format_json,
    read_jsonl,
)

config = Config()
logger = logging.getLogger(__name__)
REMOTE_SERVER_ADDR = f"{config.env_server_addr}:{config.env_server_port}"


class WorkerSignals(QObject):
    status_bar_signal = pyqtSignal(str, str)
    next_action_editor_signal = pyqtSignal(bool)
    save_button_signal = pyqtSignal(bool)
    step_action_button_signal = pyqtSignal(bool)
    show_dialog_signal = pyqtSignal(str)
    evaluation_display_signal = pyqtSignal(str)
    eval_button_signal = pyqtSignal(bool)
    annotator_panel_signal = pyqtSignal(bool)
    popup_window_signal = pyqtSignal(str, str)


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


class ResetThread(QThread):
    def __init__(
        self,
        agent: HumanAgent,
        signals: WorkerSignals,
        task_config: dict,
    ):
        super().__init__()
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.signals = signals
        self.task_config = task_config
        self.agent = agent

    def _wait_finish(
        self, response: AgentStudioStatusResponse
    ) -> AgentStudioStatusResponse:
        if response.status == "finished":
            self.signals.status_bar_signal.emit("color: green;", "Finished")
            return response
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
            self.signals.status_bar_signal.emit("color: green;", "In Progress")
            response = AgentStudioStatusResponse(**response_raw.json())
            return self._wait_finish(response=response)
        else:
            raise ValueError(f"Unknown status: {response.status}, {response.content}")

    def run(self):
        # reset remote runtime
        self.signals.status_bar_signal.emit(
            "color: green;", "Task: Resetting runtime..."
        )
        response_raw = requests.post(f"http://{REMOTE_SERVER_ADDR}/runtime/reset")
        assert response_raw.status_code == 200, f"{response_raw.status_code}"
        response = AgentStudioStatusResponse(**response_raw.json())
        assert (
            response.status == "success"
        ), f"Fail to reset runtime: {response_raw.text}"
        self.agent.reset(task_config=self.task_config, registered_evaluators={})
        self.signals.status_bar_signal.emit(
            "color: green;", "Task: Preparing the environment..."
        )
        response_raw = requests.post(
            f"http://{REMOTE_SERVER_ADDR}/task/reset",
            json=AgentStudioResetRequest(task_config=self.task_config).model_dump(),
        )
        assert response_raw.status_code == 200, f"{response_raw.status_code}"
        response = AgentStudioStatusResponse(**response_raw.json())
        response = self._wait_finish(response)
        if response.status == "finished" and response.content == "success":
            self.signals.status_bar_signal.emit("color: green;", "Task: Ready")

            self.signals.next_action_editor_signal.emit(True)
            self.signals.save_button_signal.emit(True)
            self.signals.step_action_button_signal.emit(True)
            self.signals.eval_button_signal.emit(True)
            self.signals.annotator_panel_signal.emit(True)
        else:
            self.signals.popup_window_signal.emit(
                "Error",
                f"Fail to reset environment: {response_raw.text}",
            )

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
        result_queue: queue.Queue,
    ):
        super().__init__()
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.signals = signals
        self.selected_task = selected_task
        self.trajectory_display = trajectory_display
        self.result_queue = result_queue

    def _wait_finish(
        self, response: AgentStudioStatusResponse
    ) -> AgentStudioStatusResponse:
        if response.status == "finished":
            self.signals.status_bar_signal.emit("color: green;", "Finished")
            return response
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
            self.signals.status_bar_signal.emit("color: green;", "In Progress")
            response = AgentStudioStatusResponse(**response_raw.json())
            return self._wait_finish(response=response)
        else:
            raise ValueError(f"Unknown status: {response.status}, {response.content}")

    def run(self):
        self.signals.status_bar_signal.emit("color: green;", "Task: Auto-Evaluating...")
        response_raw = requests.post(
            f"http://{REMOTE_SERVER_ADDR}/task/eval",
            json=AgentStudioEvalRequest(
                task_config=self.selected_task,
                trajectory=json.loads(self.trajectory_display.toPlainText()),
            ).model_dump(),
        )
        response = AgentStudioStatusResponse(**response_raw.json())
        response = self._wait_finish(response)
        if response.status == "finished" and isinstance(response.message, dict):
            self.result_queue.put(response.message)
            self.signals.evaluation_display_signal.emit(
                "Auto-evaluation result:\n"
                f"Score: {response.message['score']}\n"
                f"Feedback: {response.message['feedback']}\n"
            )
            self.signals.status_bar_signal.emit("color: green;", "Task: Finished")
            self.signals.save_button_signal.emit(True)
            self.signals.annotator_panel_signal.emit(True)
        else:
            self.signals.popup_window_signal.emit(
                "Error",
                f"Fail to evaluate task: {response_raw.text}",
            )

    def receive_user_input(self, text: str):
        self.mutex.lock()
        self.user_input = text  # Store the user input
        self.wait_condition.wakeAll()  # Resume the thread
        self.mutex.unlock()


def extract_evaluator_meta(file_path) -> tuple[str, list[dict]]:
    """Extracts the reset_handler and evaluate_handler \
        and their metadata from the evaluator."""
    with open(file_path, "r") as file:
        tree = ast.parse(file.read(), filename=file_path)

    # Initialize a list to hold the extracted information
    extracted_info = []
    evaluator_name = None

    for node in ast.walk(tree):
        # Check for class definitions that are derived from "Evaluator"
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Evaluator":
                    # Iterate through the body of the class to find methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Check for decorators
                            for decorator in item.decorator_list:
                                if (
                                    isinstance(decorator, ast.Call)
                                    and hasattr(decorator.func, "id")
                                    and decorator.func.id
                                    in [
                                        "evaluation_handler",
                                        "reset_handler",
                                    ]
                                ):
                                    # Extract decorator name and arguments
                                    decorator_name = decorator.func.id
                                    decorator_args = [
                                        ast.literal_eval(arg) for arg in decorator.args
                                    ]

                                    # Extract function name, arguments, and docstring
                                    function_name = item.name
                                    function_args = [
                                        {arg.arg: ast.unparse(arg.annotation)}
                                        for arg in item.args.args
                                        if arg.annotation is not None
                                    ]
                                    docstring = ast.get_docstring(item)

                                    # Add extracted information to the list
                                    extracted_info.append(
                                        {
                                            "decorator": decorator_name,
                                            "decorator_args": decorator_args,
                                            "function_name": function_name,
                                            "function_args": function_args,
                                            "docstring": docstring,
                                        }
                                    )
                        elif isinstance(item, ast.AnnAssign):
                            target = item.target
                            if isinstance(target, ast.Name) and target.id == "name":
                                if item.value is not None and hasattr(item.value, "n"):
                                    if evaluator_name is None:
                                        evaluator_name = item.value.n
                                    else:
                                        raise ValueError(
                                            "Multiple evaluator names found in "
                                            f"{file_path}"
                                        )
                        elif isinstance(item, ast.Assign):
                            for assign in item.targets:
                                if isinstance(assign, ast.Name) and assign.id == "name":
                                    if item.value is not None and hasattr(
                                        item.value, "n"
                                    ):
                                        if evaluator_name is None:
                                            evaluator_name = item.value.n
                                        else:
                                            raise ValueError(
                                                "Multiple evaluator names found in "
                                                f"{file_path}"
                                            )
    if evaluator_name is None:
        raise ValueError(f"No evaluator name found in {file_path}")
    return evaluator_name, extracted_info


class Task:
    def __init__(
        self,
        instruction: str,
        trajectory: list[str],
        evals: list[dict],
        visual: bool,
        task_id: str | None = None,
    ) -> None:
        if task_id is None:
            self.task_id = str(uuid.uuid4())
        else:
            self.task_id = task_id
        self.instruction = instruction
        self.trajectory = trajectory
        self.evals = evals
        self.visual = visual

    def step_action(self, action: str) -> None:
        self.trajectory.append(action)

    def to_record(self) -> dict:
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "trajectory": self.trajectory,
            "visual": self.visual,
        }

    def to_task_config(self) -> dict:
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "evals": self.evals,
            "visual": self.visual,
        }


class HumanInterface(QMainWindow):
    def __init__(
        self,
        record_path: str,
        task_config_path: str,
    ) -> None:
        super().__init__()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(10)
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.start()
        self.refreshing_screen = False  # need for refresh flag
        self.last_message = ""
        self.task_config_path = task_config_path
        self.current_thread: ResetThread | EvalTaskThread | None = None
        self.task_status_bar: QLabel

        # Task
        self.selected_task: dict | None = None
        self.task_configs: list[dict] = []
        self.current_task: Task | None = None

        self.record_path = record_path
        self.capture_thread: VNCStreamer | LocalStreamer | None
        if config.remote:
            # VNC remote desktop
            self.capture_thread = VNCStreamer(
                config.env_server_addr, config.vnc_port, config.vnc_password
            )
        else:
            self.capture_thread = LocalStreamer(config.monitor_idx)

        self.screen_width, self.screen_height = pyautogui.size()
        self.evaluator_infos: dict[str, list[dict]] = {}
        self.load_evaluator_meta()

        self.setup_ui()
        self.agent = HumanAgent()

        self.reset()

    def setup_ui(self) -> None:
        """Sets up the UI, including the VNC frame (left) and the right layout."""
        self.setWindowTitle("AgentStudio Annotator")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setMouseTracking(True)
        main_layout = QHBoxLayout(central_widget)

        status_bar = self.statusBar()
        assert status_bar is not None
        self.status_bar: QStatusBar = status_bar

        self.task_status_bar = QLabel()
        self.status_bar.addPermanentWidget(self.task_status_bar)

        self.vnc_container = QWidget()
        left_layout = QVBoxLayout(self.vnc_container)
        assert self.capture_thread is not None
        self.capture_thread.start()
        self.recording_lock = threading.Lock()
        self.video_height, self.video_width = (
            self.capture_thread.video_height,
            self.capture_thread.video_width,
        )

        self.now_screenshot = np.zeros(
            (self.video_height, self.video_width, 4), dtype="uint8"
        )
        frame_size_hint = QSize(*config.vnc_frame_size)
        self.vnc_frame = VNCFrame(self, frame_size_hint, enable_selection=True)
        left_layout.addWidget(self.vnc_frame)

        if config.remote:
            reconnect_button = QPushButton("Re-connect")
            reconnect_button.clicked.connect(self.reconnect)
            left_layout.addWidget(reconnect_button)

        main_layout.addWidget(self.vnc_container)

        self.task_eval_info_container = QGroupBox("Task Information Panel")

        middle_layout = QVBoxLayout()
        task_eval_info_layout = QVBoxLayout()

        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.reset)
        middle_layout.addWidget(clear_button)

        task_eval_info_layout.addWidget(QLabel("Task Instruction"))
        self.instruction_editor = QTextEdit(self)
        self.instruction_editor.setFixedHeight(100)
        task_eval_info_layout.addWidget(self.instruction_editor)

        self.is_visual_checkbox = QCheckBox("Is visual Task?")
        task_eval_info_layout.addWidget(self.is_visual_checkbox)

        self.json_preview_label = QLabel("JSON format Preview")
        task_eval_info_layout.addWidget(self.json_preview_label)
        self.json_preview_display = QTextEdit(self)
        self.json_preview_display.setReadOnly(True)
        task_eval_info_layout.addWidget(self.json_preview_display)

        task_eval_info_layout.addWidget(QLabel("Evaluation Steps"))
        self.eval_steps_display = QTextEdit(self)
        task_eval_info_layout.addWidget(self.eval_steps_display)

        self.task_eval_info_container.setLayout(task_eval_info_layout)

        middle_layout.addWidget(self.task_eval_info_container)

        self.annotator_container = QGroupBox("Annotation Panel")
        annotator_layout = QVBoxLayout()
        annotator_layout.addWidget(QLabel("Mouse Action"))
        self.leftClickCheckbox = QCheckBox("Left Click")
        self.rightClickCheckbox = QCheckBox("Right Click")
        self.middleClickCheckbox = QCheckBox("Middle Click")
        self.doubleClickCheckbox = QCheckBox("Double Click")
        annotator_layout.addWidget(self.leftClickCheckbox)
        annotator_layout.addWidget(self.rightClickCheckbox)
        annotator_layout.addWidget(self.middleClickCheckbox)
        annotator_layout.addWidget(self.doubleClickCheckbox)
        annotate_button = QPushButton("Generate Annotation/Action")
        annotate_button.clicked.connect(self.generate_annotation)
        annotator_layout.addWidget(annotate_button)

        self.annotator_container.setLayout(annotator_layout)
        middle_layout.addWidget(self.annotator_container)

        main_layout.addLayout(middle_layout)

        evaluator_sel_layout = QVBoxLayout()

        evaluator_sel_layout.addWidget(
            QLabel(
                "[Existing Task]: Select from existing tasks (double click to select)"
            )
        )
        self.existing_task_list = QListWidget()
        self.existing_task_list.itemDoubleClicked.connect(self.task_list_double_clicked)
        evaluator_sel_layout.addWidget(self.existing_task_list)

        evaluator_sel_layout.addWidget(QLabel("[New Task]: Evaluator"))
        self.evaluator_dropdown = QComboBox()
        self.evaluator_dropdown.addItems(list(self.evaluator_infos.keys()))
        self.evaluator_dropdown.currentIndexChanged.connect(self.evaluator_changed)
        evaluator_sel_layout.addWidget(self.evaluator_dropdown)

        evaluator_sel_layout.addWidget(
            QLabel("[New Task]: Evaluator Method (Double click to select.)")
        )
        self.eval_method_list = QListWidget()
        self.eval_method_list.currentItemChanged.connect(self.list_item_changed)
        self.eval_method_list.itemDoubleClicked.connect(self.method_list_double_clicked)
        evaluator_sel_layout.addWidget(self.eval_method_list)

        evaluator_sel_layout.addWidget(QLabel("[New Task]: Docs"))
        self.eval_method_doc_display = QTextEdit(self)
        self.eval_method_doc_display.setReadOnly(True)
        evaluator_sel_layout.addWidget(self.eval_method_doc_display)

        self.start_button = QPushButton("Save Task Config/Start Recording")
        self.start_button.clicked.connect(self.start_record)
        evaluator_sel_layout.addWidget(self.start_button)

        self.evaluator_sel_container = QGroupBox("Evaluator Helper Panel")
        self.evaluator_sel_container.setLayout(evaluator_sel_layout)
        main_layout.addWidget(self.evaluator_sel_container)
        trajectory_layout = QVBoxLayout()

        trajectory_layout.addWidget(QLabel("Trajectory"))
        self.trajectory_display = QTextEdit(self)
        trajectory_layout.addWidget(self.trajectory_display)
        self.trajectory_display.setFixedHeight(300)
        self.trajectory_display.setReadOnly(True)

        trajectory_layout.addWidget(QLabel("Action"))
        self.next_action_editor = QTextEdit(self)
        trajectory_layout.addWidget(self.next_action_editor)

        self.step_action_button = QPushButton("Step Action")
        self.step_action_button.clicked.connect(self.step_action)
        trajectory_layout.addWidget(self.step_action_button)

        self.output_display = QTextEdit(self)
        # self.output_display.setFixedWidth(self.right_layout_width)
        # self.output_display.setFixedHeight(40)
        self.output_display.setReadOnly(True)
        trajectory_layout.addWidget(QLabel("Runtime Response"))
        trajectory_layout.addWidget(self.output_display)

        trajectory_layout.addWidget(QLabel("Evaluation Result"))
        self.evaluation_display = QTextEdit(self)
        trajectory_layout.addWidget(self.evaluation_display)
        self.evaluation_display.setReadOnly(True)

        self.eval_button = QPushButton("Evaluate")
        self.eval_button.clicked.connect(self.eval_task)
        trajectory_layout.addWidget(self.eval_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_trajectory)
        trajectory_layout.addWidget(self.save_button)

        self.trajectory_container = QGroupBox("Trajectory Panel")
        self.trajectory_container.setLayout(trajectory_layout)
        main_layout.addWidget(self.trajectory_container)

        self.setMouseTracking(True)
        self.showMaximized()

    def reset(self) -> None:
        """Clears all the text fields."""
        self.instruction_editor.clear()
        self.instruction_editor.setReadOnly(False)
        self.trajectory_display.clear()
        self.trajectory_display.setEnabled(False)
        self.next_action_editor.clear()
        self.next_action_editor.setEnabled(False)
        self.eval_method_doc_display.clear()
        self.json_preview_display.clear()
        self.eval_steps_display.clear()
        self.eval_steps_display.setReadOnly(False)
        self.output_display.clear()
        self.output_display.setEnabled(False)
        self.evaluation_display.clear()
        self.evaluation_display.setEnabled(True)
        self.evaluator_changed(0)
        self.evaluator_dropdown.setEnabled(True)
        self.eval_method_list.clear()
        self.eval_method_list.setEnabled(True)
        self.eval_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.step_action_button.setEnabled(False)
        self.is_visual_checkbox.setEnabled(True)
        self.current_task = None
        self.selected_task = None
        self.vnc_frame.reset()
        self.trajectory_container.hide()
        self.vnc_container.hide()
        self.annotator_container.hide()
        self.evaluator_sel_container.show()
        self.json_preview_label.show()
        self.json_preview_display.show()
        self.populate_instruction_selection_widget()

    def show_popup_dialog(self, title: str, message: str) -> None:
        """Shows a popup message."""
        dlg = QMessageBox(self)
        dlg.setWindowTitle(title)
        dlg.setText(message)
        dlg.show()

    def start_record(self) -> None:
        """Starts the record."""
        try:
            evals: list = json.loads(
                f"{self.eval_steps_display.toPlainText().strip().strip(',')}"
            )
            if not isinstance(evals, list):
                raise ValueError("Evaluation Steps should be a list")
        except Exception as e:
            self.show_popup_dialog(
                "Invalid JSON format!", f"[Error] Check Evaluation Steps Editor:\n{e}"
            )
            return

        if self.selected_task is not None:
            task_id = self.selected_task["task_id"]
        else:
            task_id = None
        self.current_task = Task(
            instruction=self.instruction_editor.toPlainText(),
            trajectory=[],
            evals=evals,
            visual=self.is_visual_checkbox.isChecked(),
            task_id=task_id,
        )
        if self.selected_task is None:
            add_jsonl([self.current_task.to_task_config()], self.task_config_path)

        self.evaluator_sel_container.hide()
        self.trajectory_container.show()
        self.vnc_container.show()
        self.json_preview_label.hide()
        self.json_preview_display.hide()
        self.instruction_editor.setReadOnly(True)
        self.output_display.setEnabled(True)
        self.trajectory_display.setEnabled(True)
        self.eval_steps_display.setReadOnly(True)
        self.save_button.setEnabled(False)
        self.step_action_button.setEnabled(False)
        self.is_visual_checkbox.setEnabled(False)
        if self.current_task.visual:
            self.annotator_container.show()
            self.annotator_container.setEnabled(False)

        self.worker_signals = WorkerSignals()
        self.worker_signals.status_bar_signal.connect(self.set_task_status_bar_text)
        self.worker_signals.next_action_editor_signal.connect(
            self.next_action_editor.setEnabled
        )
        self.worker_signals.save_button_signal.connect(self.save_button.setEnabled)
        self.worker_signals.step_action_button_signal.connect(
            self.step_action_button.setEnabled
        )
        self.worker_signals.show_dialog_signal.connect(self.show_choice_dialog)
        self.worker_signals.eval_button_signal.connect(self.eval_button.setEnabled)
        self.worker_signals.annotator_panel_signal.connect(
            self.annotator_container.setEnabled
        )
        self.worker_signals.popup_window_signal.connect(self.show_popup_dialog)
        self.current_thread = ResetThread(
            agent=self.agent,
            signals=self.worker_signals,
            task_config=self.current_task.to_task_config(),
        )
        self.current_thread.start()

    def generate_annotation(self) -> None:
        bounding_box = self.vnc_frame.get_selection()
        if bounding_box is not None:
            # generate click action in the middle of the bounding box
            x, y = (
                bounding_box[0] + bounding_box[2] // 2,
                bounding_box[1] + bounding_box[3] // 2,
            )
            left, right, middle, double = (
                self.leftClickCheckbox.isChecked(),
                self.rightClickCheckbox.isChecked(),
                self.middleClickCheckbox.isChecked(),
                self.doubleClickCheckbox.isChecked(),
            )
            if (
                not any([left, right, middle, double])
                or sum([left, right, middle, double]) > 1
            ):
                self.show_popup_dialog("Error", "Wrong mouse action combination!")
                return
            if self.leftClickCheckbox.isChecked():
                button = "left"
            elif self.rightClickCheckbox.isChecked():
                button = "right"
            elif self.middleClickCheckbox.isChecked():
                button = "middle"
            if self.doubleClickCheckbox.isChecked():
                button = "left"
                clicks = 2
                interval = 0.25
            else:
                clicks = 1
                interval = 0.0
            self.next_action_editor.setPlainText(
                f'mouse.click({x}, {y}, button="{button}", '
                f"clicks={clicks}, interval={interval})"
            )

    def show_input_dialog(self, message: str) -> None:
        dlg = InputDialog(self, message)
        result = dlg.exec()
        assert result == QDialog.DialogCode.Accepted
        user_input = dlg.inputBox.text()
        assert self.current_thread is not None
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
        self.current_thread.receive_user_input(user_input)

    def set_task_status_bar_text(self, color: str, text: str) -> None:
        self.task_status_bar.setStyleSheet(color)
        self.task_status_bar.setText(text)

    def load_evaluator_meta(
        self,
        base_path: str = "agent_studio/envs/desktop_env/evaluators",
    ) -> None:
        """Loads the evaluator arguments."""
        evaluator_args = {}
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        evaluator_name, evaluator_info = extract_evaluator_meta(
                            file_path
                        )
                        evaluator_args[evaluator_name] = evaluator_info
                    except Exception:
                        # logger.warn(f"Fail to parse {file_path}: {e}")
                        pass

        self.evaluator_infos = evaluator_args

    def evaluator_changed(self, index):
        evaluator_name = self.evaluator_dropdown.currentText()
        self.load_functions(evaluator_name)

    def load_functions(self, evaluator_name):
        self.eval_method_list.clear()
        self.eval_method_doc_display.clear()
        for func in self.evaluator_infos[evaluator_name]:
            item = QListWidgetItem(func["function_name"])
            if func["decorator"] == "evaluation_handler":
                item.setForeground(QColor("green"))
            elif func["decorator"] == "reset_handler":
                item.setForeground(QColor("blue"))
            self.eval_method_list.addItem(item)

    def list_item_changed(self, current, previous):
        if current:
            function_name = current.text()
            evaluator_name = self.evaluator_dropdown.currentText()
            for func in self.evaluator_infos[evaluator_name]:
                if func["function_name"] == function_name:
                    args = ""
                    for func_arg in func["function_args"]:
                        args += f"{list(func_arg.keys())[0]}: \
                            {list(func_arg.values())[0]}\n"
                    docs = f"{args}\n{func['docstring']}"
                    self.eval_method_doc_display.setText(docs)
                    break

    def load_existing_task_configs(self) -> None:
        jsonl_path = Path(self.task_config_path)
        if jsonl_path.exists():
            self.task_configs = read_jsonl(jsonl_path.as_posix())
        else:
            self.task_configs = []

    def populate_instruction_selection_widget(self) -> None:
        self.load_existing_task_configs()
        self.existing_task_list.clear()
        for task_config in self.task_configs:
            item = QListWidgetItem(task_config["instruction"])
            self.existing_task_list.addItem(item)

    def task_list_double_clicked(self, item: QListWidgetItem) -> None:
        self.task_instruction = item.text()
        selected_task_idx = self.existing_task_list.currentRow()
        self.selected_task = self.task_configs[selected_task_idx]
        assert self.selected_task is not None
        self.eval_steps_display.setPlainText(
            f"{format_json(self.selected_task['evals'])}"
        )
        self.is_visual_checkbox.setChecked(self.selected_task["visual"])
        self.instruction_editor.setPlainText(self.selected_task["instruction"])
        self.instruction_editor.setReadOnly(True)
        self.evaluator_dropdown.setEnabled(False)
        self.eval_method_list.setEnabled(False)
        self.eval_steps_display.setReadOnly(True)
        self.is_visual_checkbox.setEnabled(False)
        self.instruction_editor.setReadOnly(True)

    def method_list_double_clicked(self, item: QListWidgetItem) -> None:
        function_name = item.text()
        evaluator_name = self.evaluator_dropdown.currentText()
        for func in self.evaluator_infos[evaluator_name]:
            if func["function_name"] == function_name:
                if func["decorator"] == "evaluation_handler":
                    cfgs = {
                        "eval_type": evaluator_name,
                        "eval_procedure": [
                            {
                                func["decorator_args"][0]: {
                                    list(item.keys())[0]: list(item.values())[0]
                                    for item in func["function_args"]
                                }
                            }
                        ],
                    }
                elif func["decorator"] == "reset_handler":
                    cfgs = {
                        "eval_type": evaluator_name,
                        "reset_procedure": [
                            {
                                func["decorator_args"][0]: {
                                    list(item.keys())[0]: list(item.values())[0]
                                    for item in func["function_args"]
                                }
                            }
                        ],
                    }
                else:
                    raise ValueError(f"Unknown decorator: {func['decorator']}")
                self.json_preview_display.setPlainText(f"{format_json(cfgs)},\n\n")
                break

    def step_action(self) -> None:
        """Steps the next action and adds it to the trajectory."""
        assert self.current_task is not None
        next_action_text = self.next_action_editor.toPlainText()
        # Send the request to the runtime
        try:
            if self.current_task.visual:
                obs = self.now_screenshot
            else:
                obs = None

            bounding_box = self.vnc_frame.get_selection()
            if bounding_box is not None:
                annotation = {
                    "mouse_action": {
                        "x": bounding_box[0],
                        "y": bounding_box[1],
                        "width": bounding_box[2],
                        "height": bounding_box[3],
                        "click_type": {
                            "left_click": self.leftClickCheckbox.isChecked(),
                            "right_click": self.rightClickCheckbox.isChecked(),
                            "middle_click": self.middleClickCheckbox.isChecked(),
                            "double_click": self.doubleClickCheckbox.isChecked(),
                        },
                    }
                }
            else:
                annotation = None
            result, _ = self.agent.step_action(
                confirmed=True,
                code=next_action_text,
                obs=obs,
                annotation=annotation,
            )
            self.output_display.setText(str(result))
        except Exception as e:
            self.output_display.setText(f"Error: {str(e)}")

        if next_action_text.strip():
            current_trajectory_text = self.trajectory_display.toPlainText()
            new_trajectory_text = (
                current_trajectory_text + "\n" + next_action_text
                if current_trajectory_text
                else next_action_text
            )
            self.trajectory_display.setPlainText(new_trajectory_text)
            self.next_action_editor.clear()

    def save_trajectory(self) -> None:
        """Saves the trajectory to the record path."""
        assert self.current_task is not None
        self.step_action_button.setEnabled(False)
        self.save_button.setEnabled(False)

        if self.agent.trajectory != []:
            export_trajectories(
                self_eval_results=None,
                task_config=self.current_task.to_record(),
                trajectory=self.agent.trajectory,
                record_path=self.record_path,
                score=None,
                feedback=None,
                token_count=None,
                video_meta=None,
                jsonl_name=config.result_jsonl_file,
            )
        self.reset()

    def eval_task(self):
        self.step_action_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.eval_button.setEnabled(False)
        self.annotator_container.setEnabled(False)
        assert self.current_task is not None, "No task selected"

        signals = WorkerSignals()
        signals.save_button_signal.connect(self.save_button.setEnabled)
        signals.status_bar_signal.connect(self.set_task_status_bar_text)
        signals.evaluation_display_signal.connect(self.evaluation_display.setPlainText)
        signals.show_dialog_signal.connect(self.show_input_dialog)
        signals.annotator_panel_signal.connect(self.annotator_container.setEnabled)
        signals.popup_window_signal.connect(self.show_popup_dialog)
        self.current_thread_result = queue.Queue()
        self.current_thread = EvalTaskThread(
            signals=signals,
            selected_task=self.current_task.to_task_config(),
            trajectory_display=self.trajectory_display,
            result_queue=self.current_thread_result,
        )
        self.current_thread.start()

    def reconnect(self):
        if config.remote:
            self.status_bar.showMessage("Reconnecting")
            self.now_screenshot = np.zeros(
                (self.video_height, self.video_width, 4), dtype="uint8"
            )
            if self.capture_thread is not None:
                with self.recording_lock:
                    self.capture_thread = VNCStreamer(
                        env_server_addr=config.env_server_addr,
                        vnc_port=config.vnc_port,
                        vnc_password=config.vnc_password,
                    )
                    self.capture_thread.start()
            self.status_bar.showMessage("Connected")

    def update_screen(self):
        try:
            with self.recording_lock:
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
        except Exception as e:
            logger.error("Fail to get screenshot.", e)

    def render(self):
        self.refresh_timer.stop()

        if self.refreshing_screen:
            self.refresh_timer.start()
            return

        self.refreshing_screen = True
        self.update_screen()
        if self.capture_thread is not None:
            if local_cursor_pos := self.vnc_frame.get_cursor_pos():
                self.status_bar.showMessage(f"Cursor Position: {str(local_cursor_pos)}")

        self.refreshing_screen = False
        self.refresh_timer.start()

    def closeEvent(self, event):
        self.status_bar.showMessage("Closing")
        self.on_close = True
        if self.capture_thread is not None:
            self.capture_thread.stop()
        self.refresh_timer.stop()
        logger.info("GUI closed")
        exit(0)
