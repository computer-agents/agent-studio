import asyncio
import functools
import logging
import queue
import sys
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
    QListWidget,
    QStatusBar,
    QInputDialog,
)
from qasync import QApplication, asyncClose, asyncSlot

from playground.agent.base_agent import Agent
from playground.config.config import Config
from playground.env.desktop_env.eval.evaluator_helper import evaluator_router
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
from playground.utils.json_utils import format_json

config = Config()
logger = logging.getLogger(__name__)


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
        self.action_queue: queue.Queue = queue.Queue()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1)
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.stop()
        self.refreshing_screen = False  # need for refresh flag
        self.last_message = ""
        self.selected_task: dict | None = None
        self.status_bar: QStatusBar

        self.setup_ui()

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

        interrupt_button = QPushButton("Interrupt action")
        interrupt_button.clicked.connect(self.interrupt_action)
        agent_layout.addWidget(interrupt_button)

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
        self.instruction_selection.addItems(self.task_list)

        execution_button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.run_task)
        execution_button_layout.addWidget(self.start_button)

        self.eval_button = QPushButton("Evaluate")
        self.eval_button.setEnabled(False)
        self.eval_button.clicked.connect(self.eval_task)
        execution_button_layout.addWidget(self.eval_button)

        task_layout.addLayout(execution_button_layout)

        task_layout.addWidget(QLabel("Evaluation result"))
        self.evaluation_display = QTextEdit(self)
        task_layout.addWidget(self.evaluation_display)
        self.evaluation_display.setReadOnly(True)
        # self.evaluation_display.setFixedHeight(60)
        # self.evaluation_display.setFixedWidth(self.layout_width)

        next_button = QPushButton("Next task")
        next_button.clicked.connect(self.reset)
        task_layout.addWidget(next_button)

        self.status_bar.showMessage("Ready")

        main_layout.addLayout(task_layout)

        self.setMouseTracking(True)

    def select_task_instruction(self, item):
        self.task_instruction = item.text()
        selected_task_idx = self.instruction_selection.currentRow()
        self.selected_task = self.task_configs[selected_task_idx]
        self.task_config_display.setText(format_json(self.selected_task))
        self.start_button.setEnabled(True)

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

        self.vnc_frame.setFixedSize(self.video_width, self.video_height)
        self.vnc_frame.setMouseTracking(True)
        self.showMaximized()

        self.refresh_timer.start()
        self.status_bar.showMessage("Connected")

    def set_status_text(self):
        all_status_text = []
        all_status_text.append(self.last_message)
        if action_queue_size := self.action_queue.qsize():
            all_status_text.append(f"{action_queue_size} Actions Waiting to Execute.")
        if self.vnc is not None:
            if local_cursor_pos := self.vnc_frame.get_cursor_pos():
                all_status_text.append(f"Cursor Position: {str(local_cursor_pos)}")

        self.status_bar.showMessage(" ".join(all_status_text))

    def _wait_finish(self):
        while True:
            response_raw = requests.get(
                f"http://{config.env_server_addr}:{config.env_server_port}/task/status"
            )
            response = PlaygroundStatusResponse(**response_raw.json())
            if response.status == "finished":
                break
            elif response.status == "wait_for_input":
                self.status_bar.showMessage("Waiting for input")
                dlg = QInputDialog(self)
                dlg.setLabelText(response.content)
                dlg.show()
                dlg.findChildren(QPushButton)[1].hide()
                result = dlg.exec()
                assert result == QInputDialog.DialogCode.Accepted
                user_input = dlg.textValue()
                response_raw = requests.post(
                    url=f"http://{config.env_server_addr}:{config.env_server_port}/task/confirm",
                    json=PlaygroundTextRequest(message=user_input).model_dump(),
                )
                response = PlaygroundResponse(**response_raw.json())
                assert response.status == "success"
            elif response.status == "pending":
                self.status_bar.showMessage("Pending")
            elif response.status == "in_progress":
                self.status_bar.showMessage("In Progress")
            else:
                raise ValueError(f"Unknown status: {response.status}")
            time.sleep(1)

    def reset(self):
        """Resets the task and waits for the environment to be ready."""
        # Clears all the text fields.
        self.task_config_display.clear()
        self.trajectory_display.clear()
        self.parsed_action_display.clear()
        self.response_display.clear()
        self.output_display.clear()
        self.evaluation_display.clear()
        self.selected_task = None
        self.status_bar.showMessage("Select a task from the list")

    def reset_task(self):
        if self.selected_task is None:
            self.status_bar.showMessage("No task selected")
            return
        else:
            self.status_bar.showMessage("Initializing...")

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
        self.status_bar.showMessage("Initialization finished. Running...")

    def run_task(self):
        self.start_button.setEnabled(False)
        self.eval_button.setEnabled(False)
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        self.reset_task()
        raw_code, code, _ = self.agent.generate_action()
        self.parsed_action_display.setPlainText(code)
        self.response_display.setPlainText(raw_code)
        self.confirm_button.setEnabled(True)
        self.decline_button.setEnabled(True)

    def eval_task(self):
        self.start_button.setEnabled(False)
        self.eval_button.setEnabled(False)
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
        if self.selected_task is None:
            self.status_bar.showMessage("No task selected")
            return
        response_raw = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/eval",
            json=PlaygroundEvalRequest(
                task_config=self.selected_task,
                trajectory=bytes2str(self.trajectory_display.toPlainText()),
            ).model_dump(),
        )
        response = PlaygroundResponse(**response_raw.json())
        assert response.status == "submitted"
        self._wait_finish()
        response_raw = requests.get(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/result"
        )
        response = PlaygroundResultResponse(**response_raw.json())
        assert response.status == "finished" and isinstance(response.message, dict)
        self.evaluation_display.setPlainText(
            f"Score: {response.message['score']}\nFeedback: {response.message['feedback']}"
        )
        self.start_button.setEnabled(True)

    def step_action(self):
        """Steps the next action and adds it to the trajectory."""
        self.confirm_button.setEnabled(False)
        self.decline_button.setEnabled(False)
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
            raw_code, code, _ = self.agent.generate_action()
            self.parsed_action_display.setPlainText(code)
            self.response_display.setPlainText(raw_code)
            self.confirm_button.setEnabled(True)
            self.decline_button.setEnabled(True)
        else:
            self.confirm_button.setEnabled(False)
            self.decline_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.eval_button.setEnabled(True)

    def interrupt_action(self):
        # TODO: send interrupt signal to the runtime
        pass

    async def update_screen(self):
        try:
            if self.vnc is not None:
                self.now_screenshot = await self.vnc.screenshot()

                rgba_array = self.now_screenshot
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
        self.status_bar.showMessage("Closing")
        self.refresh_timer.stop()
        if self.vnc is not None:
            await self.vnc.disconnect()
            logger.info("VNC disconnected")
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
