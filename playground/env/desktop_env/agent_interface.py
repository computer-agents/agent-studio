import logging
import queue
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
)
from qasync import asyncClose, asyncSlot

from playground.config.config import Config
from playground.env.desktop_env.vnc_client import VNCClient, VNCFrame

config = Config()
logger = logging.getLogger(__name__)


class AgentInterface(QMainWindow):
    layout_width = 300

    def __init__(
        self,
        task_config: list,
        record_path: str = config.record_path,
    ):
        super().__init__()
        self.task_list = [task["instruction"] for task in task_config]
        self.action_queue: queue.Queue = queue.Queue()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1)
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.stop()
        self.refreshing_screen = False  # need for refresh flag
        self.last_message = ""

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

        right_layout.addWidget(QLabel("Task Instruction"))
        self.instruction_display = QTextEdit(self)
        right_layout.addWidget(self.instruction_display)
        self.instruction_display.setReadOnly(True)
        # self.instruction_display.setFixedHeight(60)

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

        clear_button = QPushButton("Save")
        right_layout.addWidget(clear_button)

        main_layout.addLayout(right_layout)

        self.setMouseTracking(True)

    @asyncSlot()
    async def reconnect(self):
        """Reconnects to VNC server."""
        self.action_queue.queue.clear()
        await self.vnc.disconnect()
        self.connect_vnc()

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
        self.instruction_display.clear()
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
        self.instruction_display.setText(self.task_instruction)

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
