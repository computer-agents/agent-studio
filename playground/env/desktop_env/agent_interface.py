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
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
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
    def __init__(
        self,
        # agent: Agent,
        evaluator_router,
        task_configs: list,
        record_path: str = config.record_path,
    ):
        super().__init__()
        # self.agent = agent
        self.task_idx = -1
        self.task_configs = task_configs
        self.action_queue: queue.Queue = queue.Queue()

        assert not config.remote, "This interface is for local agent only."
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Agent Interface")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setMouseTracking(True)
        main_layout = QHBoxLayout(central_widget)

        left_layout = QVBoxLayout()

        left_layout.addWidget(QLabel("Model response"))
        self.response_display = QTextEdit(self)
        left_layout.addWidget(self.response_display)
        self.response_display.setReadOnly(True)
        self.response_display.setFixedHeight(200)

        left_layout.addWidget(QLabel("Parsed Actions"))
        self.parsed_action_display = QTextEdit(self)
        left_layout.addWidget(self.parsed_action_display)
        self.parsed_action_display.setReadOnly(True)
        self.parsed_action_display.setFixedHeight(200)

        confirm_button = QPushButton("Confirm and execute action")
        confirm_button.clicked.connect(self.step_action)
        left_layout.addWidget(confirm_button)

        left_layout.addWidget(QLabel("Runtime output"))
        self.output_display = QTextEdit(self)
        left_layout.addWidget(self.output_display)
        self.output_display.setReadOnly(True)
        self.output_display.setFixedHeight(115)

        interrupt_button = QPushButton("Interrupt action")
        interrupt_button.clicked.connect(self.interrupt_action)
        left_layout.addWidget(interrupt_button)

        main_layout.addLayout(left_layout)

        right_layout = QVBoxLayout()

        right_layout.addWidget(QLabel("Task configuration"))
        self.task_config_display = QTextEdit(self)
        right_layout.addWidget(self.task_config_display)
        self.task_config_display.setReadOnly(True)
        self.task_config_display.setFixedHeight(200)

        right_layout.addWidget(QLabel("Trajectory"))
        self.trajectory_display = QTextEdit(self)
        right_layout.addWidget(self.trajectory_display)
        self.trajectory_display.setReadOnly(True)
        self.trajectory_display.setFixedHeight(200)

        eval_button = QPushButton("Auto-eval")
        eval_button.clicked.connect(self.eval_task)
        right_layout.addWidget(eval_button)

        right_layout.addWidget(QLabel("Auto-eval result"))
        self.auto_eval_display = QTextEdit(self)
        right_layout.addWidget(self.auto_eval_display)
        self.auto_eval_display.setReadOnly(True)
        self.auto_eval_display.setFixedHeight(30)

        right_layout.addWidget(QLabel("Agent self-eval result"))
        self.agent_eval_display = QTextEdit(self)
        right_layout.addWidget(self.agent_eval_display)
        self.agent_eval_display.setReadOnly(True)
        self.agent_eval_display.setFixedHeight(30)

        self.success_checkbox = QCheckBox("Is this task successful?")
        self.success_checkbox.setChecked(False)
        right_layout.addWidget(self.success_checkbox)

        next_button = QPushButton("Run the next task")
        next_button.clicked.connect(self.run_agent)
        right_layout.addWidget(next_button)

        self.statusBar().showMessage("Ready")

        main_layout.addLayout(right_layout)

        self.statusBar().showMessage("Click button 'Run the next task' to start")

    def reset(self):
        """Clears all the text fields."""
        self.task_config_display.clear()
        self.trajectory_display.clear()
        self.parsed_action_display.clear()
        self.response_display.clear()
        self.output_display.clear()
        self.success_checkbox.setChecked(False)

    def run_agent(self):
        self.reset()
        self.statusBar().showMessage("Initializing new task...")
        self.task_idx += 1
        current_task = self.task_configs[self.task_idx]
        self.task_config_display.setText(format_json(current_task))
        comb = evaluator_router(current_task)
        comb.reset()

        self.statusBar().showMessage("Initializing agent...")
        self.agent.reset(
            task_id=current_task["task_id"],
            instruction=current_task["instruction"],
            record_screen=False,
        )
        self.statusBar().showMessage("Initialization finished. Running...")

    def eval_task(self):
        response_raw = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/eval",
            json=PlaygroundEvalRequest(
                task_config=self.selected_task,
                trajectory=bytes2str(self.trajectory_display),
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
        print(response.result, response.message["score"], response.message["feedback"])

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

    def interrupt_action(self):
        # TODO: send interrupt signal to the runtime
        pass

    @asyncClose
    async def closeEvent(self, event):
        self.statusBar().showMessage("Closing")
        exit(0)


class RemoteAgentInterface(QMainWindow):
    layout_width = 300

    def __init__(
        self,
        # agent: Agent,
        task_configs: list,
        record_path: str = config.record_path,
    ):
        super().__init__()
        # self.agent = agent
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

        self.setup_ui()

        self.vnc = None
        self.connect_vnc()
        self.reset()

    def setup_ui(self):
        """Sets up the UI, including the VNC frame (left) and the right layout."""
        self.setWindowTitle("Remote Agent Interface")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setMouseTracking(True)
        main_layout = QHBoxLayout(central_widget)

        left_layout = QVBoxLayout()
        self.vnc_frame = VNCFrame(self)
        left_layout.addWidget(self.vnc_frame)
        main_layout.addLayout(left_layout)

        middle_layout = QVBoxLayout()

        middle_layout.addWidget(QLabel("Model response"))
        self.response_display = QTextEdit(self)
        middle_layout.addWidget(self.response_display)
        self.response_display.setReadOnly(True)
        # self.response_display.setFixedHeight(300)

        middle_layout.addWidget(QLabel("Parsed Actions"))
        self.parsed_action_display = QTextEdit(self)
        middle_layout.addWidget(self.parsed_action_display)
        self.parsed_action_display.setReadOnly(True)

        confirm_button = QPushButton("Confirm and execute action")
        confirm_button.clicked.connect(self.step_action)
        middle_layout.addWidget(confirm_button)

        middle_layout.addWidget(QLabel("Runtime output"))
        self.output_display = QTextEdit(self)
        # self.output_display.setFixedHeight(40)
        middle_layout.addWidget(self.output_display)
        self.output_display.setReadOnly(True)

        interrupt_button = QPushButton("Interrupt action")
        interrupt_button.clicked.connect(self.interrupt_action)
        middle_layout.addWidget(interrupt_button)

        main_layout.addLayout(middle_layout)

        right_layout = QVBoxLayout()

        reconnect_button = QPushButton("Re-connect")
        reconnect_button.clicked.connect(self.reconnect)
        right_layout.addWidget(reconnect_button)

        start_button = QPushButton("Start")
        start_button.clicked.connect(self.run_agent)
        right_layout.addWidget(start_button)

        right_layout.addWidget(QLabel("Task configuration"))
        self.task_config_display = QTextEdit(self)
        right_layout.addWidget(self.task_config_display)
        self.task_config_display.setReadOnly(True)
        self.task_config_display.setFixedHeight(200)
        self.task_config_display.setFixedWidth(self.layout_width)

        right_layout.addWidget(QLabel("Trajectory"))
        self.trajectory_display = QTextEdit(self)
        right_layout.addWidget(self.trajectory_display)
        self.trajectory_display.setReadOnly(True)
        self.trajectory_display.setFixedWidth(self.layout_width)

        eval_button = QPushButton("Auto-eval")
        eval_button.clicked.connect(self.eval_task)
        right_layout.addWidget(eval_button)

        right_layout.addWidget(QLabel("Auto-eval result"))
        self.auto_eval_display = QTextEdit(self)
        right_layout.addWidget(self.auto_eval_display)
        self.auto_eval_display.setReadOnly(True)
        self.auto_eval_display.setFixedHeight(60)
        self.auto_eval_display.setFixedWidth(self.layout_width)

        right_layout.addWidget(QLabel("Agent self-eval result"))
        self.agent_eval_display = QTextEdit(self)
        right_layout.addWidget(self.agent_eval_display)
        self.agent_eval_display.setReadOnly(True)
        self.agent_eval_display.setFixedHeight(60)
        self.agent_eval_display.setFixedWidth(self.layout_width)

        self.success_checkbox = QCheckBox("Is this task successful?")
        self.success_checkbox.setChecked(False)
        right_layout.addWidget(self.success_checkbox)

        next_button = QPushButton("Next task")
        next_button.clicked.connect(self.reset)
        right_layout.addWidget(next_button)

        self.statusBar().showMessage("Ready")

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
        self.statusBar().showMessage("Connected")

    def set_status_text(self):
        all_status_text = []
        all_status_text.append(self.last_message)
        if action_queue_size := self.action_queue.qsize():
            all_status_text.append(f"{action_queue_size} Actions Waiting to Execute.")
        if self.vnc is not None:
            if local_cursor_pos := self.vnc_frame.get_cursor_pos():
                all_status_text.append(f"Cursor Position: {str(local_cursor_pos)}")

        self.statusBar().showMessage(" ".join(all_status_text))

    def _wait_finish(self):
        while True:
            response_raw = requests.get(
                f"http://{config.env_server_addr}:{config.env_server_port}/task/status"
            )
            response = PlaygroundStatusResponse(**response_raw.json())
            if response.status == "finished":
                break
            elif response.status == "wait_for_input":
                self.statusBar().showMessage("Waiting for input")
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Need response")
                dlg.setText(response.content)
                dlg.setStandardButtons(
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                confirmation: str = (
                    "y" if (dlg.exec() == QMessageBox.StandardButton.Yes) else "n"
                )
                response_raw = requests.post(
                    url=f"http://{config.env_server_addr}:{config.env_server_port}/task/confirm",
                    json=PlaygroundTextRequest(message=str(confirmation)).model_dump(),
                )
                response = PlaygroundResponse(**response_raw.json())
                assert response.status == "success"
            elif response.status == "pending":
                self.statusBar().showMessage("Pending")
            elif response.status == "in_progress":
                self.statusBar().showMessage("In Progress")
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
        self.success_checkbox.setChecked(False)
        self.selected_task = None
        self.statusBar().showMessage("Select a task from the list")

    def run_agent(self):
        if self.selected_task is None:
            self.statusBar().showMessage("No task selected")
            return
        else:
            self.statusBar().showMessage("Initializing...")

        response_raw = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/reset",
            json=PlaygroundResetRequest(task_config=self.selected_task).model_dump(),
        )
        response = PlaygroundResponse(**response_raw.json())
        assert response.status == "submitted"
        self._wait_finish()
        # self.agent.reset(
        #     task_id=self.selected_task["task_id"],
        #     instruction=self.selected_task["instruction"],
        #     record_screen=self.selected_task.get("visual", False),
        # )
        self.statusBar().showMessage("Initialization finished. Running...")

    def eval_task(self):
        response_raw = requests.post(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/eval",
            json=PlaygroundEvalRequest(
                task_config=self.selected_task,
                trajectory=bytes2str(self.trajectory_display),
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
        print(response.result, response.message["score"], response.message["feedback"])

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

    def interrupt_action(self):
        # TODO: send interrupt signal to the runtime
        pass

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


async def run_ui(remote: bool, task_configs: dict, record_path: str):
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

    if config.remote:
        interface = RemoteAgentInterface(
            # agent=agent,
            task_configs=task_configs,
            record_path=record_path,
        )
    else:
        interface = AgentInterface(
            # agent=agent,
            task_configs=task_configs,
            record_path=record_path,
        )

    interface.show()

    await future
