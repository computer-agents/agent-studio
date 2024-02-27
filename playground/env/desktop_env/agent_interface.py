import logging
import queue
import time
from asyncio import open_connection
from datetime import datetime

import numpy as np
import requests
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QListWidget,
    QStatusBar,
    QMessageBox,
)
from qasync import asyncClose, asyncSlot

from playground.config.config import Config
from playground.env.desktop_env.vnc_client import VNCClient, VNCFrame
from playground.utils.json_utils import format_json
from playground.agent import setup_agent
from playground.utils.communication import bytes2str, \
    PlaygroundResponse, PlaygroundResetRequest, \
    PlaygroundStatusResponse, PlaygroundResultResponse, \
    PlaygroundEvalRequest, PlaygroundTextRequest

config = Config()
logger = logging.getLogger(__name__)


class AgentInterface(QMainWindow):
    layout_width = 300

    def __init__(
        self,
        task_configs: list,
        record_path: str = config.record_path,
    ):
        super().__init__()
        self.task_list = [task["instruction"] for task in task_configs]
        self.task_configs = task_configs
        self.action_queue: queue.Queue = queue.Queue()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1)
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.stop()
        self.refreshing_screen = False  # need for refresh flag
        self.last_message = ""
        self.agent = setup_agent(config.provider, config.env_type, config.agent)
        self.selected_task: dict | None = None

        self.setup_ui()

        self.vnc = None
        self.connect_vnc()
        self.reset()

    def setup_ui(self):
        """Sets up the UI, including the VNC frame (left) and the right layout."""
        self.setWindowTitle("Agent Recorder")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setMouseTracking(True)
        main_layout = QHBoxLayout(central_widget)

        left_layout = QVBoxLayout()
        self.vnc_frame = VNCFrame(self)
        left_layout.addWidget(self.vnc_frame)
        main_layout.addLayout(left_layout)

        middle_layout = QVBoxLayout()

        middle_layout.addWidget(QLabel("Prompt"))
        self.response_display = QTextEdit(self)
        middle_layout.addWidget(self.response_display)
        self.response_display.setReadOnly(True)
        self.response_display.setFixedWidth(self.layout_width)
        # self.response_display.setFixedHeight(300)

        middle_layout.addWidget(QLabel("Model Response"))
        self.response_display = QTextEdit(self)
        middle_layout.addWidget(self.response_display)
        self.response_display.setReadOnly(True)
        self.response_display.setFixedWidth(self.layout_width)
        # self.response_display.setFixedHeight(300)

        middle_layout.addWidget(QLabel("Parsed Actions"))
        self.parsed_action_display = QTextEdit(self)
        middle_layout.addWidget(self.parsed_action_display)
        self.parsed_action_display.setReadOnly(True)
        self.parsed_action_display.setFixedWidth(self.layout_width)

        confirm_button = QPushButton("Confirm and execute action")
        confirm_button.clicked.connect(self.step_action)
        middle_layout.addWidget(confirm_button)

        middle_layout.addWidget(QLabel("Runtime Response"))
        self.output_display = QTextEdit(self)
        # self.output_display.setFixedHeight(40)
        middle_layout.addWidget(self.output_display)
        self.output_display.setReadOnly(True)
        self.output_display.setFixedWidth(self.layout_width)

        main_layout.addLayout(middle_layout)

        right_layout = QVBoxLayout()

        reconnect_button = QPushButton("Re-connect")
        reconnect_button.clicked.connect(self.reconnect)
        right_layout.addWidget(reconnect_button)

        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.reset)
        right_layout.addWidget(clear_button)

        right_layout.addWidget(QLabel("Task Configuration"))
        self.task_config_display = QTextEdit(self)
        right_layout.addWidget(self.task_config_display)
        self.task_config_display.setReadOnly(True)
        # self.task_config_display.setFixedHeight(60)

        right_layout.addWidget(QLabel("Task Selection (double click to select)"))
        self.instruction_selection = QListWidget(self)
        self.instruction_selection.itemDoubleClicked.connect(self.select_task_instruction)
        right_layout.addWidget(self.instruction_selection)
        self.instruction_selection.clear()
        self.instruction_selection.addItems(self.task_list)

        right_layout.addWidget(QLabel("Trajectory"))
        self.trajectory_display = QTextEdit(self)
        right_layout.addWidget(self.trajectory_display)
        self.trajectory_display.setFixedWidth(self.layout_width)
        # self.trajectory_display.setFixedHeight(300)

        self.success_checkbox = QCheckBox("Is this task successful?")
        self.success_checkbox.setChecked(False)
        right_layout.addWidget(self.success_checkbox)

        start_button = QPushButton("Start")
        start_button.clicked.connect(self.eval_task)
        right_layout.addWidget(start_button)

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_task)
        right_layout.addWidget(reset_button)

        self.task_status_bar = QStatusBar()
        right_layout.addWidget(self.task_status_bar)
        self.task_status_bar.showMessage("Ready")

        main_layout.addLayout(right_layout)

        self.setMouseTracking(True)

    @asyncSlot()
    async def reconnect(self):
        """Reconnects to VNC server."""
        self.action_queue.queue.clear()
        if self.vnc is not None:
            await self.vnc.disconnect()
        await self.connect_vnc()

    @asyncSlot()
    async def connect_vnc(self):
        """Connects to VNC server."""
        self.statusBar().showMessage("Connecting")

        self._reader, self._writer = await open_connection(config.env_server_addr, config.vnc_port)
        self.vnc = await VNCClient.create(
            reader=self._reader, writer=self._writer, password=config.vnc_password
        )
        self.video_height = self.vnc.video.height
        self.video_width = self.vnc.video.width
        self.now_screenshot = np.zeros(
            (self.video_height, self.video_width, 4), dtype="uint8"
        )

        self.vnc_frame.setFixedSize(self.video_width, self.video_height)
        self.vnc_frame.setMouseTracking(True)
        self.showMaximized()

        self.refresh_timer.start()
        self.statusBar().showMessage("Connected")

    def reset(self):
        """Clears all the text fields."""
        self.task_config_display.clear()
        self.trajectory_display.clear()
        self.parsed_action_display.clear()

    def set_status_text(self):
        all_status_text = []
        all_status_text.append(self.last_message)
        if action_queue_size := self.action_queue.qsize():
            all_status_text.append(f"{action_queue_size} Actions Waiting to Execute.")
        if self.vnc is not None:
            if local_cursor_pos := self.vnc_frame.get_cursor_pos():
                all_status_text.append(f"Cursor Position: {str(local_cursor_pos)}")

        self.statusBar().showMessage(" ".join(all_status_text))

    def select_task_instruction(self, item):
        self.task_instruction = item.text()
        selected_task_idx = self.instruction_selection.currentRow()
        self.selected_task = self.task_configs[selected_task_idx]
        self.task_config_display.setText(format_json(self.selected_task))

    def _wait_finish(self):
        while True:
            response_raw = requests.get(f"http://{config.env_server_addr}:{config.env_server_port}/task/status")
            response = PlaygroundStatusResponse(**response_raw.json())
            if response.status == "finished":
                break
            elif response.status == "wait_for_input":
                self.task_status_bar.showMessage("Waiting for input")
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Need response")
                dlg.setText(response.content)
                dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

                confirmation: str = "y" \
                    if (dlg.exec() == QMessageBox.StandardButton.Yes) else "n"
                response_raw = requests.post(
                    url=f"http://{config.env_server_addr}:{config.env_server_port}/task/confirm",
                    json=PlaygroundTextRequest(message=str(confirmation)).model_dump()
                )
                response = PlaygroundResponse(**response_raw.json())
                assert response.status == "success"
            elif response.status == "pending":
                self.task_status_bar.showMessage("Pending")
            elif response.status == "in_progress":
                self.task_status_bar.showMessage("In Progress")
            else:
                raise ValueError(f"Unknown status: {response.status}")
            time.sleep(1)

    def reset_task(self):
        """Resets the task and waits for the environment to be ready."""
        if self.selected_task is None:
            self.task_status_bar.showMessage("No task selected")
            return
        response_raw = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/reset",
            json=PlaygroundResetRequest(task_config=self.selected_task).model_dump()
        )
        response = PlaygroundResponse(**response_raw.json())
        assert response.status == "submitted"
        self._wait_finish()
        self.agent.reset(
            task_id=self.selected_task["task_id"],
            instruction=self.selected_task["instruction"],
            record_screen=self.selected_task.get("visual", False)
        )
        self.task_status_bar.showMessage("Finished")

    def eval_task(self):
        if self.selected_task is None:
            self.task_status_bar.showMessage("No task selected")
            return
        response_raw = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/eval",
            json=PlaygroundEvalRequest(
                task_config=self.selected_task,
                trajectory=bytes2str(self.trajectory_display)
            ).model_dump()
        )
        response = PlaygroundResponse(**response_raw.json())
        assert response.status == "submitted"
        self._wait_finish()
        response_raw = requests.get(f"http://{config.env_server_addr}:{config.env_server_port}/task/result")
        response = PlaygroundResultResponse(**response_raw.json())
        assert response.status == "finished" and isinstance(response.message, dict)
        print(response.result, response.message["score"], response.message["feedback"])

    def run_agent(self):
        trajectory = self.agent.run()

    def step_action(self):
        """Steps the next action and adds it to the trajectory."""
        next_action_text = self.parsed_action_display.toPlainText()
        body = {"code": next_action_text}
        # Send the request to the runtime
        try:
            response_raw = requests.post("http://localhost:8000/execute", json=body)
            # Process and display the output
            runtime_output = response_raw.text
            if "output" in runtime_output:
                output_processed = eval(runtime_output)["output"]
                self.output_display.setText(str(output_processed))
            else:
                output_processed = eval(runtime_output)["error"]
                self.output_display.setText("Error: " + str(output_processed))
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
            self.parsed_action_display.clear()

    async def update_screen(self):
        try:
            if self.vnc is not None:
                self.now_screenshot = await self.vnc.screenshot()
        except Exception as e:
            logger.error("Fail to get screenshot.", e)

        rgba_array = self.now_screenshot
        if rgba_array is not None:
            qimage = QImage(
                rgba_array.tobytes(),
                self.video_width,
                self.video_height,
                QImage.Format.Format_RGBA8888,
            )
            self.vnc_frame.update(qimage)

    @asyncSlot()
    async def render(self):
        self.refresh_timer.stop()

        if self.refreshing_screen:
            self.refresh_timer.start()
            return

        self.refreshing_screen = True
        await self.update_screen()
        self.set_status_text()

        try:
            while not self.action_queue.empty():
                action = self.action_queue.get()
                action.action_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
                action.before_action_obs = self.now_screenshot
                await action.step(self.vnc)

                del action

        except Exception as e:
            logger.error(e)

        self.set_status_text()
        self.refreshing_screen = False
        self.refresh_timer.start()

    @asyncClose
    async def closeEvent(self, event):
        self.statusBar().showMessage("Closing")
        self.refresh_timer.stop()
        if self.vnc is not None:
            await self.vnc.disconnect()
        logger.info("VNC disconnected")
        exit(0)
