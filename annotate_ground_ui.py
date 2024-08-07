import argparse
import asyncio
import json
import os
import sys
import uuid

import cv2
import numpy as np
from PyQt6.QtCore import QSize, QTimer
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agent_studio.envs.desktop_env.vnc_client import (
    LocalStreamer,
    VNCFrame,
    VNCStreamer,
)


class GUIGroundingAnnotator(QMainWindow):
    """Main class for the GUI grounding annotator."""

    def __init__(
        self,
        record_path: str,
        remote: bool,
        window_width: int,
        window_height: int,
        local_monitor_idx: int,
        vnc_server_addr: str,
        vnc_server_port: int,
        vnc_passwprd: str,
    ) -> None:
        """Initializes the UI.

        Args:
            record_path: Path to save the recordings.
        """
        super().__init__()
        self.vnc_server_addr = vnc_server_addr
        self.vnc_server_port = vnc_server_port
        self.vnc_password = vnc_passwprd

        # Setup a QTimer to periodically update the screen.
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(10)
        self.refresh_timer.timeout.connect(self.render)
        self.refresh_timer.start()
        self.refreshing_screen = False

        self.record_path = record_path
        if remote:
            self.capture_thread: VNCStreamer = VNCStreamer(
                vnc_server_addr, vnc_server_port, vnc_passwprd
            )
        else:
            self.capture_thread: LocalStreamer = LocalStreamer(local_monitor_idx)

        # Setup the user interface for the application.
        self.setWindowTitle("GUI Grounding Annotator")

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

        # Right layout for buttons and text box.
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(10, 10, 10, 10)

        if remote:
            self.reconnect_button = QPushButton("Re-connect")
            self.reconnect_button.clicked.connect(self.reconnect)
            self.reconnect_button.setFixedWidth(150)
            self.reconnect_button.setFixedHeight(50)
            right_layout.addWidget(self.reconnect_button)

        # Button to capture a screenshot.
        self.capture_button = QPushButton("Capture")
        self.capture_button.clicked.connect(self.capture_screenshot)
        self.capture_button.setFixedWidth(150)
        self.capture_button.setFixedHeight(50)
        right_layout.addWidget(self.capture_button)

        # Text editor for adding instructions.
        self.instruction_editor = QTextEdit(self)
        self.instruction_editor.setPlaceholderText("Enter instruction here.")
        self.instruction_editor.setFixedWidth(150)
        self.instruction_editor.setFixedHeight(150)
        right_layout.addWidget(self.instruction_editor)

        # Button to save JSONL and raise error if missing info.
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save)
        self.save_button.setFixedWidth(150)
        self.save_button.setFixedHeight(50)
        right_layout.addWidget(self.save_button)

        # Button to clear the text box and reset the UI.
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset)
        self.reset_button.setFixedWidth(150)
        self.reset_button.setFixedHeight(50)
        right_layout.addWidget(self.reset_button)

        main_layout.addLayout(right_layout)

        # Setup the status bar.
        status_bar = self.statusBar()
        assert status_bar is not None
        self.status_bar: QStatusBar = status_bar
        self.task_status_bar = QLabel()
        self.status_bar.addPermanentWidget(self.task_status_bar)

        # Enable mouse tracking and maximize the window.
        self.setMouseTracking(True)
        # self.showMaximized()

        self.reset()

    def reset(self) -> None:
        """Resets the UI elements to their default state."""
        self.instruction_editor.clear()
        self.instruction_editor.setReadOnly(False)
        self.vnc_frame.reset()
        self.vnc_container.show()
        self.refresh_timer.start()
        self.screenshot_uuid = None
        self.status_bar.showMessage("Please capture the screenshot.")

    def capture_screenshot(self) -> None:
        """Captures the current screenshot and pause the screen streaming."""
        # Generate a unique path for the screenshot and save it.
        self.screenshot_uuid = uuid.uuid4()
        screenshot_path = os.path.join(
            self.record_path, "screenshots", f"{self.screenshot_uuid}.jpg"
        )
        screenshot_bgr = cv2.cvtColor(self.now_screenshot, cv2.COLOR_RGB2BGR)
        cv2.imwrite(screenshot_path, screenshot_bgr)
        # Pause the refresh timer and update the status bar.
        self.refresh_timer.stop()
        self.status_bar.showMessage(
            "Screenshot captured. Please input the instruction and draw the bounding box."  # noqa: E501
        )

    def save(self) -> None:
        """Saves the screenshot UUID, input instruction, and coordinates into a JSONL file."""  # noqa: E501
        bounding_box = self.vnc_frame.get_selection()
        instruction = self.instruction_editor.toPlainText()
        if not self.screenshot_uuid:
            self.status_bar.showMessage("Please capture the screenshot.")
            return
        if not bounding_box or not instruction:
            self.status_bar.showMessage(
                "Please input the instruction and draw the bounding box."
            )
            return
        data = {
            "screenshot_uuid": str(self.screenshot_uuid),
            "instruction": instruction,
            "bbox": bounding_box,
        }
        jsonl_path = os.path.join(self.record_path, "annotations.jsonl")
        with open(jsonl_path, "a") as f:
            f.write(json.dumps(data) + "\n")

        self.status_bar.showMessage(
            "Annotation saved. Please click 'Reset' to continue."
        )

    def reconnect(self):
        self.status_bar.showMessage("Reconnecting")
        self.now_screenshot = np.zeros(
            (self.video_height, self.video_width, 4), dtype="uint8"
        )
        if self.capture_thread is not None:
            self.capture_thread = VNCStreamer(
                env_server_addr=self.vnc_server_addr,
                vnc_port=self.vnc_server_port,
                vnc_password=self.vnc_password,
            )
            self.capture_thread.start()
        self.status_bar.showMessage("Connected. Please capture the screenshot.")

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
        except Exception as e:
            print("Failed to get screenshot.", e)

        self.refreshing_screen = False
        self.refresh_timer.start()

    def closeEvent(self, event):
        """Handles the close event by stopping the capture thread and timer.

        Args:
            event: The close event.
        """
        self.refresh_timer.stop()
        if self.capture_thread is not None:
            self.capture_thread.stop()
        exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote", action="store_true", help="Run in remote mode")
    parser.add_argument(
        "--record_path",
        type=str,
        default="recordings",
        help="Path to save the recordings",
    )
    parser.add_argument(
        "--window_width", type=int, default=800, help="Width of the window"
    )
    parser.add_argument(
        "--window_height", type=int, default=600, help="Height of the window"
    )
    parser.add_argument(
        "--local_monitor_idx", type=int, default=1, help="Index of the local monitor"
    )
    parser.add_argument(
        "--vnc_server_addr", type=str, default="localhost", help="VNC server address"
    )
    parser.add_argument(
        "--vnc_server_port", type=int, default=5900, help="VNC server port"
    )
    parser.add_argument(
        "--vnc_password", type=str, default="", help="VNC server password"
    )
    args = parser.parse_args()

    # Ensure a second screen is available.
    app = QApplication(sys.argv)
    screens = QApplication.screens()
    if len(screens) < 2:
        raise RuntimeError("A second screen is required for local annotation.")

    # Main entry point for the application.
    os.makedirs(args.record_path, exist_ok=True)
    os.makedirs(os.path.join(args.record_path, "screenshots"), exist_ok=True)

    try:
        # Create the main interface.
        interface = GUIGroundingAnnotator(
            record_path=args.record_path,
            remote=args.remote,
            window_width=args.window_width,
            window_height=args.window_height,
            local_monitor_idx=args.local_monitor_idx,
            vnc_server_addr=args.vnc_server_addr,
            vnc_server_port=args.vnc_server_port,
            vnc_passwprd=args.vnc_password,
        )
        interface.resize(args.window_width, args.window_height)

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
