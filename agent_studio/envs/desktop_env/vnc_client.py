import asyncio
import logging
import platform
import threading
from dataclasses import dataclass

import asyncvnc
import cv2
import mss
import numpy as np
from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QColor, QCursor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QLabel

logger = logging.getLogger(__name__)


@dataclass
class Position:
    width: int
    height: int

    def __str__(self):
        return "Position({},{})".format(self.width, self.height)


class VNCFrame(QLabel):
    """The VNC frame for rendering the VNC screen."""

    def __init__(self, parent, size_hint: QSize, enable_selection: bool = False):
        super().__init__(parent)
        self.start_pos = None
        self.end_pos = None
        self.is_selecting = False
        self.selection_rect = QRect()
        self.enable_selection = enable_selection
        self.scale_factor = 1.0
        if platform.system() == "Windows":
            import ctypes

            scaleFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100  # type: ignore  # noqa: E501
            size_hint /= scaleFactor
        # TODO: Fix the scale factor for Linux and macOS
        self.target_size = size_hint
        logger.info(f"VNC Frame target size: {self.target_size}")

    def reset(self):
        self.start_pos = None
        self.end_pos = None
        self.is_selecting = False
        self.selection_rect = QRect()

    def get_cursor_pos(self):
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        if (
            cursor_pos.x() < 0
            or cursor_pos.y() < 0
            or cursor_pos.x() > self.width()
            or cursor_pos.y() > self.height()
        ):
            return None
        else:
            cursor_pos = Position(
                int(cursor_pos.x() / self.scale_factor),
                int(cursor_pos.y() / self.scale_factor),
            )
            return cursor_pos

    def mousePressEvent(self, event):
        """Capture the starting point of the selection."""
        if self.enable_selection and event.button() == Qt.MouseButton.LeftButton:
            self.selection_rect = QRect()
            self.start_pos = event.pos()
            self.is_selecting = True
        elif self.enable_selection and event.button() == Qt.MouseButton.RightButton:
            self.reset()
            self.repaint()

    def mouseMoveEvent(self, event):
        """Update the selection end point and repaint the widget."""
        if self.enable_selection and self.is_selecting:
            self.end_pos = event.pos()
            self._update_selection_rect()
            self.repaint()

    def mouseReleaseEvent(self, event):
        """Finalize the selection on mouse release."""
        if (
            self.enable_selection
            and event.button() == Qt.MouseButton.LeftButton
            and self.is_selecting
        ):
            self.end_pos = event.pos()
            self.is_selecting = False
            self._update_selection_rect()
            self.repaint()

    def _update_selection_rect(self):
        if self.start_pos and self.end_pos:
            if self.start_pos.x() < self.end_pos.x():
                self.selection_rect.setLeft(self.start_pos.x())
                self.selection_rect.setRight(self.end_pos.x())
            else:
                self.selection_rect.setLeft(self.end_pos.x())
                self.selection_rect.setRight(self.start_pos.x())

            if self.start_pos.y() < self.end_pos.y():
                self.selection_rect.setTop(self.start_pos.y())
                self.selection_rect.setBottom(self.end_pos.y())
            else:
                self.selection_rect.setTop(self.end_pos.y())
                self.selection_rect.setBottom(self.start_pos.y())

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.enable_selection and not self.selection_rect.isEmpty():
            painter = QPainter(self)
            pen = QPen(QColor("red"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)

            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(
                self.selection_rect.topLeft() + QPoint(5, -5),
                f"({int(self.selection_rect.topLeft().x() / self.scale_factor)}, "
                f"{int(self.selection_rect.topLeft().y() / self.scale_factor)})",
            )
            painter.drawText(
                self.selection_rect.bottomRight() + QPoint(-50, 15),
                f"({int(self.selection_rect.bottomRight().x() / self.scale_factor)}, "
                f"{int(self.selection_rect.bottomRight().y() / self.scale_factor)})",
            )

    def get_selection(self) -> tuple[int, int, int, int] | None:
        """Return the coordinates of the selection."""
        if self.enable_selection and not self.selection_rect.isEmpty():
            return (
                int(self.selection_rect.topLeft().x() / self.scale_factor),
                int(self.selection_rect.topLeft().y() / self.scale_factor),
                int(self.selection_rect.width() / self.scale_factor),
                int(self.selection_rect.height() / self.scale_factor),
            )
        else:
            return None

    def update(self, qimage):
        scaled_qimage = qimage.scaled(
            self.target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.scale_factor = max(
            scaled_qimage.width() / qimage.width(),
            scaled_qimage.height() / qimage.height(),
        )

        self.setFixedSize(scaled_qimage.size())
        self.setPixmap(QPixmap.fromImage(scaled_qimage))


class VNCStreamer:
    def __init__(self, env_server_addr: str, vnc_port: int, vnc_password: str):
        self.env_server_addr = env_server_addr
        self.vnc_port = vnc_port
        self.vnc_password = vnc_password
        self.is_streaming = True
        self.streaming_thread = threading.Thread(
            target=self._between_callback, name="Screen Stream"
        )
        self.streaming_lock = threading.Lock()
        self.condition = threading.Condition()
        self.video_height = 0
        self.video_width = 0
        self.current_frame = np.zeros(
            (self.video_height, self.video_width, 3), dtype="uint8"
        )
        self.streaming_thread.start()
        with self.condition:
            if self.video_height == 0 or self.video_width == 0:
                self.condition.wait()

    def stop(self):
        if not self.streaming_thread.is_alive():
            logger.warning("VNC thread is not executing")
        else:
            self.is_streaming = False
            self.streaming_thread.join()

    async def _connect_vnc(self):
        """Connects to VNC server."""
        self.streaming_thread = threading.Thread(
            target=self._between_callback, name="Screen Stream"
        )
        self.streaming_thread.start()

    def _between_callback(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(self._capture_screen())
        loop.close()

    async def reconnect(self):
        self.stop()
        await self._connect_vnc()

    def get_current_frame(self) -> np.ndarray | None:
        with self.streaming_lock:
            return self.current_frame

    async def _capture_screen(self):
        logger.info("VNC Streamer started")
        async with asyncvnc.connect(
            host=self.env_server_addr,
            port=self.vnc_port,
            password=self.vnc_password,
        ) as vnc:
            while self.is_streaming:
                try:
                    frame = await vnc.screenshot()
                    if frame is not None:
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                        with self.streaming_lock:
                            self.current_frame = frame.copy()
                            self.video_height, self.video_width = frame.shape[:2]
                            with self.condition:
                                self.condition.notify_all()
                except Exception as e:
                    logger.warning(msg=f"Fail to capture frame: {e}")
        logger.info("VNC Streamer stopped")


class LocalStreamer:
    def __init__(self, monitor_idx: int):
        self.is_streaming = True
        self.streaming_thread = threading.Thread(
            target=self._capture_screen, name="Screen Stream"
        )
        self.streaming_lock = threading.Lock()
        self.condition = threading.Condition()
        self.video_height = 0
        self.video_width = 0
        self.monitor_idx = monitor_idx
        self.current_frame = None
        self.streaming_thread.start()
        with self.condition:
            if self.video_height == 0 or self.video_width == 0:
                self.condition.wait()
        self.current_frame = np.zeros(
            (self.video_height, self.video_width, 3), dtype="uint8"
        )

    def stop(self):
        if not self.streaming_thread.is_alive():
            logger.warning("VNC thread is not executing")
        else:
            self.is_streaming = False
            self.streaming_thread.join()

    def get_current_frame(self) -> np.ndarray | None:
        with self.streaming_lock:
            return self.current_frame

    def _capture_screen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[self.monitor_idx]
            logger.info("Local Streamer started")
            # self.streaming_lock.release()
            while self.is_streaming:
                try:
                    frame = sct.grab(monitor)
                    self.video_width, self.video_height = frame.width, frame.height
                    frame = np.array(frame)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                    with self.streaming_lock:
                        self.current_frame = frame.copy()
                        with self.condition:
                            self.condition.notify_all()
                except Exception as e:
                    logger.warning(f"Fail to capture frame: {e}")
            logger.info("Local Streamer stopped")
