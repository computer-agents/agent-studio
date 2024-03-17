import asyncio
import logging
import threading
import time
from asyncio import StreamReader, StreamWriter, open_connection
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from os import urandom
from struct import unpack
from typing import Callable
from zlib import decompressobj

import cv2
import numpy as np
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key
from PyQt6.QtGui import QCursor, QPixmap, QPainter, QPen, QFont, QColor
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QRect, QPoint

logger = logging.getLogger(__name__)

# Common screen aspect ratios
screen_ratios: set[Fraction] = {
    Fraction(3, 2),
    Fraction(4, 3),
    Fraction(16, 10),
    Fraction(16, 9),
    Fraction(32, 9),
    Fraction(64, 27),
}

# Colour channel orders
video_modes: dict[bytes, str] = {
    b"\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x10\x08\x00": "bgra",
    b"\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x00\x08\x10": "rgba",
    b"\x20\x18\x01\x01\x00\xff\x00\xff\x00\xff\x10\x08\x00": "argb",
    b"\x20\x18\x01\x01\x00\xff\x00\xff\x00\xff\x00\x08\x10": "abgr",
}


async def read_int(reader: StreamReader, length: int) -> int:
    """
    Reads, unpacks, and returns an integer of *length* bytes.
    """

    return int.from_bytes(await reader.readexactly(length), "big")


async def read_text(reader: StreamReader, encoding: str) -> str:
    """
    Reads, unpacks, and returns length-prefixed text.
    """

    length = await read_int(reader, 4)
    data = await reader.readexactly(length)
    return data.decode(encoding)


async def skip_to_eof(reader: StreamReader):
    logger.warn("[asyncvnc] skip to eof")
    await reader.read(-1)


def pack_ard(data):
    data = data.encode("utf-8") + b"\x00"
    if len(data) < 64:
        data += urandom(64 - len(data))
    else:
        data = data[:64]
    return data


@dataclass
class Position:
    width: int
    height: int

    def __str__(self):
        return "Position({},{})".format(self.width, self.height)


@dataclass
class Clipboard:
    """
    Shared clipboard.
    """

    writer: StreamWriter = field(repr=False)

    #: The clipboard text.
    text: str = ""

    def write(self, text: str):
        """
        Sends clipboard text to the server.
        """
        logger.info("[asyncvnc] send clipboard text: ", text)
        data = text.encode("latin-1")
        self.writer.write(b"\x06\x00" + len(data).to_bytes(4, "big") + data)


@dataclass
class Screen:
    x: int

    #: Vertical position in pixels.
    y: int

    #: Width in pixels.
    width: int

    #: Height in pixels.
    height: int

    @property
    def slices(self) -> tuple[slice, slice]:
        """
        Object that can be used to crop the video buffer to this screen.
        """

        return slice(self.y, self.y + self.height), slice(self.x, self.x + self.width)

    @property
    def score(self) -> float:
        """
        A measure of our confidence that this represents a real screen. For screens with standard aspect ratios, this  # noqa: E501
        is proportional to its pixel area. For non-standard aspect ratios, the score is further multiplied by the ratio  # noqa: E501
        or its reciprocal, whichever is smaller.
        """

        value = float(self.width * self.height)
        ratios = {
            Fraction(self.width, self.height).limit_denominator(64),
            Fraction(self.height, self.width).limit_denominator(64),
        }
        if not ratios & screen_ratios:
            value *= min(ratios) * 0.5
        return value


@dataclass
class Video:
    reader: StreamReader = field(repr=False)
    writer: StreamWriter = field(repr=False)
    decompress: Callable[[bytes], bytes] = field(repr=False)

    #: Desktop name.
    name: str

    #: Width in pixels.
    width: int

    #: Height in pixels.
    height: int

    #: Colour channel order.
    mode: str

    #: 3D numpy array of colour data.
    data: np.ndarray | None = None

    # bytes per pixel
    bypp = 4

    _switch_to_rre = False

    now_encoding: str | None = None

    @classmethod
    async def create(cls, reader: StreamReader, writer: StreamWriter) -> "Video":
        writer.write(b"\x01")
        width = await read_int(reader, 2)
        height = await read_int(reader, 2)
        mode_data = bytearray(await reader.readexactly(13))
        mode_data[2] &= 1  # set big endian flag to 0 or 1
        mode_data[3] &= 1  # set true colour flag to 0 or 1
        mode = video_modes.get(bytes(mode_data))
        await reader.readexactly(3)  # padding
        name = await read_text(reader, "utf-8")

        if mode is None:
            mode = "rgba"
            # https://github.com/TurboVNC/tightvnc/blob/main/vnc_winsrc/rfb/rfbproto.h#L406
            writer.write(
                b"\x00\x00\x00\x00\x20\x18\x00\x01\x00\xff"
                b"\x00\xff\x00\xff\x00\x08\x10\x00\x00\x00"
            )

        compress_code = [
            b"\x00\x00\x00\x05",  # Hextile
            b"\x00\x00\x00\x06",  # ZLib
            b"\x00\x00\x00\x00",  # raw
        ]
        compress_code_num = len(compress_code)
        compress_code_num_bytes = compress_code_num.to_bytes(2, "big")
        compress_code_send_message = (
            b"\x02\x00" + compress_code_num_bytes + b"".join(compress_code)
        )
        writer.write(compress_code_send_message)

        decompress = decompressobj().decompress
        return cls(reader, writer, decompress, name, width, height, mode)

    def refresh(
        self,
        x: int = 0,
        y: int = 0,
        width: int | None = None,
        height: int | None = None,
    ):
        """
        Sends a video buffer update request to the server.
        """
        incremental = self.data is not None
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        self.writer.write(
            b"\x03"
            + incremental.to_bytes(1, "big")
            + x.to_bytes(2, "big")
            + y.to_bytes(2, "big")
            + width.to_bytes(2, "big")
            + height.to_bytes(2, "big")
        )

    def _handle_rre_sub_rectangles(self, block, topx, topy):
        """
        # RRE Sub Rectangles
        :param block:
        :param topx:
        :param topy:
        :return:
        """
        pos = 0
        end = len(block)
        sz = self.bypp + 8
        format = "!%dsHHHH" % self.bypp
        while pos < end:
            (color, x, y, width, height) = unpack(format, block[pos : pos + sz])
            self.data[
                topy + y : topy + y + height, topx + x : topx + x + width
            ] = np.frombuffer(color, dtype="B").reshape(1, 1, 4)
            pos += sz

    def _handle_decode_hextile(self, block, bg, color, x, y, width, height, tx, ty):
        """
        # Hextile Decoding
        :param block:
        :param bg:
        :param color:
        :param x:
        :param y:
        :param width:
        :param height:
        :param tx:
        :param ty:
        :return:
        """
        (sub_encoding,) = unpack("!B", block)
        # calc tile size
        tw = th = 16
        if x + width - tx < 16:
            tw = x + width - tx

        if y + height - ty < 16:
            th = y + height - ty

        # decode tile
        if sub_encoding & 1:  # RAW
            self.expect(
                self._handle_decode_hextile_raw,
                tw * th * self.bypp,
                bg,
                color,
                x,
                y,
                width,
                height,
                tx,
                ty,
                tw,
                th,
            )
        else:
            num_bytes = 0
            if sub_encoding & 2:  # BackgroundSpecified
                num_bytes += self.bypp
            if sub_encoding & 4:  # ForegroundSpecified
                num_bytes += self.bypp
            if sub_encoding & 8:  # AnySubrects
                num_bytes += 1
            if num_bytes:
                self.expect(
                    self._handle_decode_hextile_subrect,
                    num_bytes,
                    sub_encoding,
                    bg,
                    color,
                    x,
                    y,
                    width,
                    height,
                    tx,
                    ty,
                    tw,
                    th,
                )
            else:
                self.fill_rectangle(tx, ty, tw, th, bg)
                self._do_next_hextile_subrect(bg, color, x, y, width, height, tx, ty)

    # @profile
    async def read(self):
        if self.data is None:
            self.data = np.zeros((self.height, self.width, 4), "B")

        info = await self.reader.read(12)
        x, y, width, height, encoding = unpack("!HHHHI", info)
        # print(f"x: {x}, y: {y}, width: {width}, height: {height}")
        # print("encoding: ", encoding)

        if encoding == 0:  # Raw
            self.now_encoding = "Raw"
            data = await self.reader.readexactly(height * width * 4)
            self.data[y : y + height, x : x + width] = np.frombuffer(
                data, dtype="B"
            ).reshape(height, width, 4)
            self.data[
                y : y + height, x : x + width, self.mode.index("a")
            ] = 255  # alpha channel

        elif encoding == 5:  # Hextile
            self.now_encoding = "Hextile"
            raw = 1
            backgroundSpecified = 2
            foregroundSpecified = 4
            anySubrects = 8
            subrectsColoured = 16
            background: np.ndarray | None = None

            for ty in range(y, y + height, 16):
                for tx in range(x, x + width, 16):
                    tw = th = 16
                    if tw + tx > self.width:
                        tw = self.width - tx
                    if th + ty > self.height:
                        th = self.height - ty

                    subencoding = await self.reader.read(1)
                    subencoding = unpack("!B", subencoding)[0]

                    if subencoding & raw:
                        data = await self.reader.readexactly(th * tw * 4)
                        self.data[ty : ty + th, tx : tx + tw] = np.frombuffer(
                            data, dtype="B"
                        ).reshape(th, tw, 4)
                    else:
                        if subencoding == 0:
                            self.data[ty : ty + th, tx : tx + tw] = background
                            continue

                        if subencoding & backgroundSpecified:
                            background = await self.reader.readexactly(4)
                            background = np.frombuffer(background, dtype="B").reshape(
                                1, 1, 4
                            )

                        if subencoding & foregroundSpecified:
                            foreground = await self.reader.readexactly(4)
                            foreground = np.frombuffer(foreground, dtype="B").reshape(
                                1, 1, 4
                            )

                        self.data[ty : ty + th, tx : tx + tw] = background

                        if subencoding & anySubrects:
                            num_subrects = await self.reader.read(1)
                            num_subrects = unpack("!B", num_subrects)[0]
                            # Define the size of each subrect, colored subrects have additional 4 bytes for the color  # noqa: E501
                            subrect_size = (
                                4 + 2 if subencoding & subrectsColoured else 2
                            )
                            subrects_data = await self.reader.readexactly(
                                num_subrects * subrect_size
                            )
                            subrects_data = np.frombuffer(subrects_data, dtype="B")

                            for i in range(num_subrects):
                                xywh_offset = 0
                                if subencoding & subrectsColoured:
                                    foreground = subrects_data[
                                        i * subrect_size : i * subrect_size + 4
                                    ].reshape(1, 1, 4)
                                    xywh_offset = 4

                                xywh = subrects_data[
                                    i * subrect_size
                                    + xywh_offset : i * subrect_size
                                    + xywh_offset
                                    + 2
                                ]
                                xywh = unpack("!H", xywh.tobytes())[0]
                                sx = xywh >> 12
                                sy = (xywh >> 8) & 0x0F
                                sw = (xywh >> 4) & 0x0F
                                sh = xywh & 0x0F
                                self.data[
                                    ty + sy : ty + sy + sh + 1,
                                    tx + sx : tx + sx + sw + 1,
                                ] = foreground

            self.data[:, :, self.mode.index("a")] = 255

        elif encoding == 6:  # ZLib
            self.now_encoding = "ZLib"
            length = await read_int(self.reader, 4)
            data = await self.reader.readexactly(length)
            data = self.decompress(data)
            self.data[y : y + height, x : x + width] = np.frombuffer(
                data, dtype="B"
            ).reshape(height, width, 4)
            self.data[y : y + height, x : x + width, self.mode.index("a")] = 255

    async def _read_set_cursor(self, x, y, width, height):
        # Calculate the length of data and mask
        data_len = width * height * 4  # assuming bpp/8 = 4
        mask_len = ((width + 7) // 8) * height

        # Read data and mask from the reader
        data = await self.reader.readexactly(data_len)
        mask = await self.reader.readexactly(mask_len)

        # Convert data and mask to numpy arrays
        data = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))
        mask = np.frombuffer(mask, dtype=np.uint8).reshape((height, (width + 7) // 8))

        # Prepare the output buffer
        buf = np.zeros((height, width, 4), dtype=np.uint8)

        # Process the data and mask
        for y in range(height):
            for x in range(width):
                byte_ = y * ((width + 7) // 8) + x // 8
                bit = 7 - x % 8

                # Set alpha channel
                if mask[byte_] & (1 << bit):
                    buf[y, x, 3] = 255
                else:
                    buf[y, x, 3] = 0

                # Set color channels
                self.data[y, x, :3] = data[y, x, :3]

    def as_rgba(self) -> np.ndarray:
        """
        Returns the video buffer as a 3D RGBA array.
        """

        if self.data is None:
            return np.zeros((self.height, self.width, 4), "B")
        if self.mode == "rgba":
            return self.data
        if self.mode == "abgr":
            return self.data[:, :, ::-1]
        return np.dstack(
            (
                self.data[:, :, self.mode.index("r")],
                self.data[:, :, self.mode.index("g")],
                self.data[:, :, self.mode.index("b")],
                self.data[:, :, self.mode.index("a")],
            )
        )

    def is_complete(self):
        """
        Returns true if the video buffer is entirely opaque.
        """

        if self.data is None:
            return False
        return self.data[:, :, self.mode.index("a")].all()


class UpdateType(Enum):
    """
    Update from server to client.
    """

    #: Video update.
    VIDEO = 0

    #: Clipboard update.
    CLIPBOARD = 2


@dataclass
class VNCClient:
    reader: StreamReader = field(repr=False)
    writer: StreamWriter = field(repr=False)

    #: The shared clipboard.
    clipboard: Clipboard

    #: The video buffer.
    video: Video

    #: The server's public key (Mac only)
    host_key: rsa.RSAPublicKey | None

    @classmethod
    async def create(
        cls,
        reader: StreamReader,
        writer: StreamWriter,
        username: str | None = None,
        password: str | None = None,
        host_key: rsa.RSAPublicKey | None = None,
    ) -> "VNCClient":
        intro = await reader.readline()
        if intro[:4] != b"RFB ":
            raise ValueError("not a VNC server")
        writer.write(b"RFB 003.008\n")

        auth_types = set(await reader.readexactly(await read_int(reader, 1)))
        if not auth_types:
            raise ValueError(await read_text(reader, "utf-8"))
        for auth_type in (33, 1, 2):
            if auth_type in auth_types:
                writer.write(auth_type.to_bytes(1, "big"))
                break
        else:
            raise ValueError(f"unsupported auth types: {auth_types}")

        # Apple authentication
        if auth_type == 33:
            if username is None or password is None:
                raise ValueError("server requires username and password")
            if host_key is None:
                writer.write(b"\x00\x00\x00\x0a\x01\x00RSA1\x00\x00\x00\x00")
                await reader.readexactly(4)  # packet length
                await reader.readexactly(2)  # packet version
                host_key_length = await read_int(reader, 4)
                host_key = await reader.readexactly(host_key_length)
                host_key = load_der_public_key(host_key)
                await reader.readexactly(1)  # unknown
            aes_key = urandom(16)
            cipher = Cipher(algorithms.AES(aes_key), modes.ECB())
            encryptor = cipher.encryptor()
            credentials = pack_ard(username) + pack_ard(password)
            writer.write(
                b"\x00\x00\x01\x8a\x01\x00RSA1"
                + b"\x00\x01"
                + encryptor.update(credentials)
                + b"\x00\x01"
                + host_key.encrypt(aes_key, padding=padding.PKCS1v15())
            )
            await reader.readexactly(4)  # unknown

        # VNC authentication
        if auth_type == 2:
            if password is None:
                raise ValueError("server requires password")
            des_key = password.encode("ascii")[:8].ljust(8, b"\x00")
            des_key = bytes(int(bin(n)[:1:-1].ljust(8, "0"), 2) for n in des_key)
            encryptor = Cipher(algorithms.TripleDES(des_key), modes.ECB()).encryptor()
            challenge = await reader.readexactly(16)
            writer.write(encryptor.update(challenge) + encryptor.finalize())

        auth_result = await read_int(reader, 4)
        if auth_result == 0:
            return cls(
                reader=reader,
                writer=writer,
                host_key=host_key,
                clipboard=Clipboard(writer),
                video=await Video.create(reader, writer),
            )

        elif auth_result == 1:
            raise PermissionError("Auth failed")
        elif auth_result == 2:
            raise PermissionError("Auth failed (too many attempts)")
        else:
            reason = await reader.readexactly(auth_result)
            raise PermissionError(reason.decode("utf-8"))

    async def read(self) -> UpdateType | None:
        try:
            type_id = await read_int(self.reader, 1)
            update_type = UpdateType(type_id)
        except ValueError:
            logger.warn(f"No such type_id: type_id: {type_id}")
            await skip_to_eof(self.reader)
            return None

        if update_type is UpdateType.CLIPBOARD:
            await self.reader.readexactly(3)  # padding
            self.clipboard.text = await read_text(self.reader, "latin-1")

        elif update_type is UpdateType.VIDEO:
            await self.reader.readexactly(1)  # padding
            for _ in range(await read_int(self.reader, 2)):
                await self.video.read()

        else:
            print(f"read update type error: type_id: {type_id}")
            await skip_to_eof(self.reader)

        return update_type

    async def screenshot(
        self,
        x: int = 0,
        y: int = 0,
        width: int | None = None,
        height: int | None = None,
    ) -> np.ndarray:
        self.video.data = None
        self.video.refresh(x, y, width, height)
        while True:
            update_type = await self.read()
            if update_type is UpdateType.VIDEO:
                if self.video.is_complete():
                    return self.video.as_rgba()

    async def disconnect(self) -> None:
        self.reader.feed_eof()
        del self.reader

        self.writer.close()
        await self.writer.wait_closed()


class VNCFrame(QLabel):
    """The VNC frame for rendering the VNC screen."""

    def __init__(self, parent, enable_selection: bool = False):
        super().__init__(parent)
        self.start_pos = None
        self.end_pos = None
        self.is_selecting = False
        self.selection_rect = QRect()
        self.enable_selection = enable_selection

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
            cursor_pos = Position(cursor_pos.x(), cursor_pos.y())
            return cursor_pos

    def mousePressEvent(self, event):
        """Capture the starting point of the selection."""
        if self.enable_selection and event.button() == Qt.MouseButton.LeftButton:
            self.selection_rect = QRect()
            self.start_pos = event.pos()
            self.is_selecting = True

    def mouseMoveEvent(self, event):
        """Update the selection end point and repaint the widget."""
        if self.enable_selection and self.is_selecting:
            self.end_pos = event.pos()
            self.update_selection_rect()
            self.repaint()

    def mouseReleaseEvent(self, event):
        """Finalize the selection on mouse release."""
        if self.enable_selection\
            and event.button() == Qt.MouseButton.LeftButton\
            and self.is_selecting:
            self.end_pos = event.pos()
            self.is_selecting = False
            self.update_selection_rect()
            self.repaint()

    def update_selection_rect(self):
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
            pen = QPen(QColor('red'), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect)

            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(
                self.selection_rect.topLeft() + QPoint(5, -5),
                f"({self.selection_rect.topLeft().x()}, {self.selection_rect.topLeft().y()})"
            )
            painter.drawText(
                self.selection_rect.bottomRight() + QPoint(-50, 15),
                f"({self.selection_rect.bottomRight().x()}, {self.selection_rect.bottomRight().y()})"
            )

    def get_selection(self) -> tuple[int, int, int, int] | None:
        """Return the coordinates of the selection."""
        if self.enable_selection and not self.selection_rect.isEmpty():
            return (
                self.selection_rect.topLeft().x(),
                self.selection_rect.topLeft().y(),
                self.selection_rect.width(),
                self.selection_rect.height(),
            )
        else:
            return None

    def update(self, qimage):
        self.setPixmap(QPixmap.fromImage(qimage))


class VNCStreamer:
    def __init__(self, env_server_addr: str, vnc_port: int, vnc_password: str):
        self.env_server_addr = env_server_addr
        self.vnc_port = vnc_port
        self.vnc_password = vnc_password
        self.is_streaming = False
        self.streaming_thread = threading.Thread(
            target=self.between_callback, name="Screen Stream"
        )
        self.streaming_lock = threading.Lock()
        self.video_height = 0
        self.video_width = 0

    def start(self) -> None:
        self.streaming_lock.acquire()
        self.is_streaming = True
        self.streaming_thread.start()
        with self.streaming_lock:
            pass
        while self.video_height == 0 or self.video_width == 0:
            time.sleep(0.2)

    def stop(self):
        if not self.streaming_thread.is_alive():
            logger.warning("VNC thread is not executing")
        else:
            self.is_streaming = False
            self.streaming_thread.join()

    async def connect_vnc(self):
        """Connects to VNC server."""
        try:
            self._reader, self._writer = await open_connection(
                self.env_server_addr, self.vnc_port
            )
            self.vnc: VNCClient = await VNCClient.create(
                reader=self._reader, writer=self._writer, password=self.vnc_password
            )
        except (ConnectionRefusedError, ValueError) as e:
            logger.warning(f"Fail to connect to VNC server: {e}")
            return
        self.video_height = self.vnc.video.height
        self.video_width = self.vnc.video.width
        self.current_frame = np.zeros(
            (self.video_height, self.video_width, 3), dtype="uint8"
        )

    def between_callback(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(self._capture_screen())
        loop.close()

    async def reconnect(self):
        if self.vnc is not None:
            await self.vnc.disconnect()
        await self.connect_vnc()

    def get_current_frame(self) -> np.ndarray | None:
        with self.streaming_lock:
            return self.current_frame

    async def _capture_screen(self):
        await self.connect_vnc()
        assert self.vnc is not None, "VNC client is not connected"
        logger.info("VNC Streamer started")
        self.streaming_lock.release()
        while self.is_streaming:
            try:
                frame = await self.vnc.screenshot()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                with self.streaming_lock:
                    self.current_frame = frame.copy()
            except Exception as e:
                logger.warning(f"Fail to capture frame: {e}")
        await self.vnc.disconnect()
        logger.info("VNC Streamer stopped")
