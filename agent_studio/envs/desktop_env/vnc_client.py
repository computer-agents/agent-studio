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
        self.scale_factor = 1.0
        if platform.system() == "Windows":
            import ctypes

            scaleFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100  # type: ignore  # noqa: E501
            size_hint /= scaleFactor
        # TODO: Fix the scale factor for Linux and macOS
        self.target_size = size_hint
        logger.info(f"VNC Frame target size: {self.target_size}")

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
                frame = await vnc.screenshot()
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                    with self.streaming_lock:
                        self.current_frame = frame.copy()
                        self.video_height, self.video_width = frame.shape[:2]
                        with self.condition:
                            self.condition.notify_all()
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
