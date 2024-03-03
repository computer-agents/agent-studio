import asyncio
import functools
import logging
import sys
from asyncio import open_connection
import uuid

import numpy as np
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
    QStatusBar,
    QCheckBox,
)
from qasync import QApplication, asyncClose, asyncSlot

from playground.config.config import Config
from playground.env.desktop_env.vnc_client import VNCClient, VNCFrame
from playground.utils.json_utils import export_trajectories
from playground.agent.human_agent import HumanAgent

config = Config()
logger = logging.getLogger(__name__)


class Task:
    def __init__(
            self,
            instruction: str,
            trajectory: list[str],
            visual: bool
        ) -> None:
        self.task_id = str(uuid.uuid4())
        self.instruction = instruction
        self.trajectory = trajectory
        self.visual = visual

    def step_action(self, action: str) -> None:
        self.trajectory.append(action)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "trajectory": self.trajectory,
            "visual": self.visual
        }


class HumanInterface(QMainWindow):
    right_layout_width = 300

    def __init__(
        self,
        record_path: str,
    ) -> None:
        super().__init__()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1)
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.stop()
        self.refreshing_screen = False  # need for refresh flag
        self.last_message = ""

        # VNC
        self.record_path = record_path
        self.vnc = None
        self.vnc_lock = asyncio.Lock()
        self.current_task: Task | None = None

        self.setup_ui()
        self.agent = HumanAgent()

        self.reset()

    @classmethod
    async def create(cls, record_path: str):
        self = cls(record_path)
        await self.connect_vnc()
        return self

    def setup_ui(self) -> None:
        """Sets up the UI, including the VNC frame (left) and the right layout."""
        self.setWindowTitle("Playground Recorder")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setMouseTracking(True)
        main_layout = QHBoxLayout(central_widget)

        self.status_bar: QStatusBar = self.statusBar()

        left_layout = QVBoxLayout()
        self.vnc_frame = VNCFrame(self)
        left_layout.addWidget(self.vnc_frame)

        reconnect_button = QPushButton("Re-connect")
        reconnect_button.clicked.connect(self.reconnect)
        left_layout.addWidget(reconnect_button)

        main_layout.addLayout(left_layout)

        right_layout = QVBoxLayout()

        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.reset)
        right_layout.addWidget(clear_button)

        right_layout.addWidget(QLabel("Task Instruction"))
        self.instruction_editor = QTextEdit(self)
        right_layout.addWidget(self.instruction_editor)
        self.instruction_editor.setFixedWidth(self.right_layout_width)
        self.instruction_editor.setFixedHeight(60)

        self.is_visual_checkbox = QCheckBox("Is visual Task?")
        right_layout.addWidget(self.is_visual_checkbox)

        self.start_button = QPushButton("Start Record")
        self.start_button.clicked.connect(self.start_record)
        right_layout.addWidget(self.start_button)

        right_layout.addWidget(QLabel("Trajectory"))
        self.trajectory_display = QTextEdit(self)
        right_layout.addWidget(self.trajectory_display)
        self.trajectory_display.setFixedWidth(self.right_layout_width)
        self.trajectory_display.setFixedHeight(300)
        self.trajectory_display.setReadOnly(True)

        right_layout.addWidget(QLabel("Action"))
        self.next_action_editor = QTextEdit(self)
        right_layout.addWidget(self.next_action_editor)
        self.next_action_editor.setFixedWidth(self.right_layout_width)

        self.step_action_button = QPushButton("Step Action")
        self.step_action_button.clicked.connect(self.step_action)
        right_layout.addWidget(self.step_action_button)

        self.output_display = QTextEdit(self)
        self.output_display.setFixedWidth(self.right_layout_width)
        self.output_display.setFixedHeight(40)
        self.output_display.setReadOnly(True)
        right_layout.addWidget(QLabel("Runtime Response"))
        right_layout.addWidget(self.output_display)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_trajectory)
        right_layout.addWidget(self.save_button)

        main_layout.addLayout(right_layout)

        self.setMouseTracking(True)
        self.showMaximized()

    def reset(self) -> None:
        """Clears all the text fields."""
        self.instruction_editor.clear()
        self.trajectory_display.clear()
        self.next_action_editor.clear()
        self.output_display.clear()
        self.next_action_editor.setEnabled(False)
        self.instruction_editor.setEnabled(True)
        self.output_display.setEnabled(False)
        self.trajectory_display.setEnabled(False)
        self.start_button.setEnabled(True)
        self.save_button.setEnabled(False)
        self.step_action_button.setEnabled(False)
        self.is_visual_checkbox.setEnabled(True)
        self.current_task = None

    def start_record(self) -> None:
        """Starts the record."""
        self.instruction_editor.setEnabled(False)
        self.next_action_editor.setEnabled(True)
        self.output_display.setEnabled(True)
        self.trajectory_display.setEnabled(True)
        self.start_button.setEnabled(False)
        self.save_button.setEnabled(True)
        self.step_action_button.setEnabled(True)
        self.is_visual_checkbox.setEnabled(False)
        self.current_task = Task(
            instruction=self.instruction_editor.toPlainText(),
            trajectory=[],
            visual=self.is_visual_checkbox.isChecked()
        )
        self.agent.reset(self.current_task.instruction)

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
            result, _ = self.agent.step_action(next_action_text, obs)
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
        export_trajectories(
            self_eval_results=None,
            task_config=self.current_task.to_dict(),
            trajectory=self.agent.trajectory,
            record_path=self.record_path,
            score=None,
            feedback=None,
            jsonl_name="tasks.jsonl",
        )
        self.reset()

    @asyncSlot()
    async def reconnect(self) -> None:
        """Reconnects to VNC server."""
        async with self.vnc_lock:
            if self.vnc is not None:
                await self.vnc.disconnect()
            await self.connect_vnc()

    @asyncSlot()
    async def connect_vnc(self) -> None:
        """Connects to VNC server."""
        if not config.remote:
            return
        self.status_bar.showMessage("Connecting")

        self._reader, self._writer = await open_connection(
            config.env_server_addr, config.vnc_port
        )
        self.vnc = await VNCClient.create(
            reader=self._reader, writer=self._writer, password=config.vnc_password
        )
        self.video_height = self.vnc.video.height
        self.video_width = self.vnc.video.width
        self.now_screenshot = np.zeros(
            (self.video_height, self.video_width, 4), dtype="uint8"
        )

        # self.setGeometry(0, 0, self.video_width, self.video_height)
        self.vnc_frame.setFixedSize(self.video_width, self.video_height)
        self.vnc_frame.setMouseTracking(True)

        self.refresh_timer.start()
        self.status_bar.showMessage("Connected")

    async def update_screen(self) -> None:
        async with self.vnc_lock:
            if self.vnc is None:
                return
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
    async def render(self) -> None:
        self.refresh_timer.stop()

        if self.refreshing_screen:
            self.refresh_timer.start()
            return

        self.refreshing_screen = True
        await self.update_screen()
        if self.vnc is not None:
            if local_cursor_pos := self.vnc_frame.get_cursor_pos():
                self.status_bar.showMessage(
                    f"Cursor Position: {str(local_cursor_pos)}"
                )
        self.refreshing_screen = False
        self.refresh_timer.start()

    @asyncClose
    async def closeEvent(self, event):
        self.status_bar.showMessage("Closing")
        self.refresh_timer.stop()
        async with self.vnc_lock:
            if self.vnc is not None:
                await self.vnc.disconnect()
                self.vnc = None
                logger.info("VNC disconnected")
        exit(0)


async def run_ui(record_path: str):
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

    interface = await HumanInterface.create(record_path)

    interface.show()

    await future
