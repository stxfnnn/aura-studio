"""Native Linux hidraw transport; no OpenRGB or vendor daemon required."""
from __future__ import annotations

import fcntl
import logging
import logging.handlers
import os
import select
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "aura-studio"
LOG_PATH = STATE_DIR / "aura-studio.log"

from .i18n import tr  # noqa: E402

Color = tuple[int, int, int]


def app_logger() -> logging.Logger:
    logger = logging.getLogger("aura_studio")
    if not logger.handlers:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=1_500_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger


def _feature_ioctl(number: int, size: int) -> int:
    return (3 << 30) | (size << 16) | (ord("H") << 8) | number


def get_feature(fd: int, report_id: int, size: int) -> bytes:
    buffer = bytearray(size)
    buffer[0] = report_id
    fcntl.ioctl(fd, _feature_ioctl(0x07, size), buffer, True)
    return bytes(buffer)


def set_feature(fd: int, report: bytes) -> None:
    data = bytearray(report)
    fcntl.ioctl(fd, _feature_ioctl(0x06, len(data)), data, True)


def query_omni_pairing(path: str) -> list[tuple[int, int, int]] | None:
    """Ask the documented, read-only Omni receiver paired-device list command."""
    logger = app_logger()
    fd = -1
    try:
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        request = bytearray(64)
        request[0:3] = b"\x01\xa0\x00"
        written = os.write(fd, request)
        logger.info("Omni pairing query tx path=%s bytes=%d/%d", path, written, len(request))
        ready, _, _ = select.select([fd], [], [], 0.25)
        if not ready:
            logger.info("Omni pairing query timeout path=%s", path)
            return None
        response = os.read(fd, 256)
        logger.info("Omni pairing query rx path=%s bytes=%s", path, response.hex(" "))
        # The receiver echoes [report id, command, subcommand], then returns
        # [count, reserved, (PID LE, channel, type) * count].
        if len(response) >= 5 and response[:3] == b"\x01\xa0\x00":
            count = min(response[3], 2)
            devices = []
            for index in range(count):
                offset = 5 + index * 4
                if offset + 4 > len(response):
                    break
                devices.append((int.from_bytes(response[offset:offset + 2], "little"),
                                response[offset + 2], response[offset + 3]))
            return devices
        logger.warning("Omni pairing query returned an unrecognized response path=%s", path)
        return []
    except OSError:
        logger.exception("Omni pairing query failed path=%s", path)
        return None
    finally:
        if fd >= 0:
            os.close(fd)


def query_battery(path: str, report_id: int, query: int, index: int, report_size: int = 64) -> int | None:
    """Battery level in percent via the receiver's vendor channel.

    Every paired device answers status queries ``12 <query>`` on its own report
    id: the keyboard reports its level with ``12 01`` (reply byte 6), ROG mice
    with ``12 07`` (reply byte 5).
    """
    fd = -1
    try:
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        os.write(fd, bytes((report_id, 0x12, query)) + bytes(report_size - 3))
        deadline = time.monotonic() + 0.3
        while time.monotonic() < deadline:
            if not select.select([fd], [], [], deadline - time.monotonic())[0]:
                break
            reply = os.read(fd, 256)
            if reply[:3] == bytes((report_id, 0x12, query)) and len(reply) > index:
                return reply[index] if reply[index] <= 100 else None
    except OSError:
        app_logger().debug("battery query failed path=%s", path)
    finally:
        if fd >= 0:
            os.close(fd)
    return None


# The devices' own sleep timers (wireless only): after this many minutes without input the
# firmware switches the device's lighting (and the keyboard's display) off by itself. Index
# into the table as Armoury Crate offers it; anything else means "never".
SLEEP_MINUTES = (1, 2, 3, 5, 10)


def _exchange(fd: int, report: bytes, wait: float) -> bytes | None:
    os.write(fd, report)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if not select.select([fd], [], [], deadline - time.monotonic())[0]:
            break
        reply = os.read(fd, 256)
        if reply[:3] == report[:3]:
            return reply
    return None


def _power_status(fd: int, report_id: int, mouse: bool, report_size: int) -> bytes | None:
    """Reply to the status query: keyboards ``12 01`` (sleep in byte 7), mice ``12 07`` (sleep 6, alert 7)."""
    reply = _exchange(fd, bytes((report_id, 0x12, 0x07 if mouse else 0x01)) + bytes(report_size - 3), 0.3)
    return reply if reply and len(reply) > 7 else None


def query_sleep(path: str, report_id: int, mouse: bool = False, report_size: int = 64) -> int | None:
    """Minutes until the device's firmware puts it to sleep, 0 for never, None if unknown."""
    fd = -1
    try:
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        reply = _power_status(fd, report_id, mouse, report_size)
        if reply:
            index = reply[6 if mouse else 7]
            return SLEEP_MINUTES[index] if index < len(SLEEP_MINUTES) else 0
    except OSError:
        app_logger().debug("sleep query failed path=%s", path)
    finally:
        if fd >= 0:
            os.close(fd)
    return None


def set_sleep(path: str, report_id: int, minutes: int, store: bool, mouse: bool = False,
              report_size: int = 64) -> bool:
    """Set the firmware sleep timer; ``store`` also saves it in the device.

    Keyboards take ``51 38 00 00 <index>`` and save with ``50 55``. Mice take
    ``51 37 00 00 <index> 00 <battery alert>`` and save with ``50 03``; the alert
    level travels in the same command, so it is read first and sent back unchanged.
    """
    index = SLEEP_MINUTES.index(minutes) if minutes in SLEEP_MINUTES else 0xFF
    fd = -1
    try:
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        if mouse:
            status = _power_status(fd, report_id, True, report_size)
            if not status:
                return False
            command, save = bytes((0x51, 0x37, 0, 0, index, 0, status[7])), bytes((0x50, 0x03))
        else:
            command, save = bytes((0x51, 0x38, 0, 0, index)), bytes((0x50, 0x55))
        pad = lambda body: bytes((report_id,)) + body + bytes(report_size - 1 - len(body))
        if not _exchange(fd, pad(command), 0.6):
            return False
        if store and not _exchange(fd, pad(save), 1.5):
            return False
        app_logger().info("Sleep timer path=%s report=%s minutes=%s stored=%s", path, report_id, minutes or "never", store)
        return True
    except OSError:
        app_logger().debug("sleep change failed path=%s", path)
        return False
    finally:
        if fd >= 0:
            os.close(fd)


class Link:
    """A sink for rendered frames. ``send`` takes one colour per lamp id."""

    fps_limit = 60.0

    def open(self) -> None:
        pass

    def send(self, frame: dict[int, Color]) -> None:
        pass

    def close(self, fallback: tuple[str, Color, int] | None = None) -> None:
        pass


class NullLink(Link):
    """Preview-only device used when no hardware is connected."""


class KeyboardLink(Link):
    """Aura TUF keyboard protocol: per-key direct frames plus firmware modes.

    Direct frames are ``C0 81 <count> 00`` followed by ``id r g b`` entries.
    Behind an Omni receiver the same payload travels on the keyboard's HID
    report id instead of report 0. That report is one byte shorter, so a 15th
    entry would lose its blue channel; only 14 fit there.
    """

    REPORT_SIZE = 65
    MODES = {"Static": 0x00, "Breathing": 0x01, "Rainbow": 0x02}
    REFRESH_SECONDS = 3.0
    fps_limit = 30.0

    def __init__(self, path: str, report_id: int = 0, save: bool = False) -> None:
        self.path = path
        self.report_id = report_id
        self.save = save
        self.per_packet = 14 if report_id else 15
        self.fd = -1
        self._sent: dict[int, Color] = {}
        self._refreshed = 0.0

    def open(self) -> None:
        self.fd = os.open(self.path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        self._sent = {}
        app_logger().info("Keyboard link opened path=%s report_id=%d", self.path, self.report_id)

    def _write(self, payload: bytes) -> None:
        packet = bytes((self.report_id,)) + payload[1:]
        written = os.write(self.fd, packet)
        if written != len(packet):
            raise OSError(tr("Unvollständiger HID-Bericht ({written}/{total} Bytes)").format(written=written, total=len(packet)))

    def _drain(self) -> None:
        # The keyboard acknowledges every direct packet; discard the replies so
        # the kernel queue never fills up.
        try:
            while select.select([self.fd], [], [], 0)[0]:
                if not os.read(self.fd, 256):
                    break
        except BlockingIOError:
            pass

    def send(self, frame: dict[int, Color]) -> None:
        now = time.monotonic()
        if now - self._refreshed > self.REFRESH_SECONDS:
            # Periodic full frame: recovers after the keyboard slept or reconnected.
            self._sent = {}
            self._refreshed = now
        changed = [(led, color) for led, color in frame.items() if self._sent.get(led) != color]
        for start in range(0, len(changed), self.per_packet):
            chunk = changed[start:start + self.per_packet]
            packet = bytearray(self.REPORT_SIZE)
            packet[1:4] = bytes((0xC0, 0x81, len(chunk)))
            for index, (led, color) in enumerate(chunk):
                packet[5 + index * 4:9 + index * 4] = bytes((led, *color))
            self._write(bytes(packet))
        if changed:
            self._sent.update(changed)
            self._drain()

    def firmware_mode(self, mode: str, color: Color, brightness: int, speed: int = 50) -> None:
        packet = bytearray(self.REPORT_SIZE)
        packet[1:4] = bytes((0x51, 0x2C, self.MODES.get(mode, 0)))
        packet[5] = round((100 - max(0, min(100, speed))) * 2.55)
        packet[6] = max(0, min(100, brightness))
        packet[7] = 0x10 if mode == "Breathing" else 0x00
        packet[9] = 0x02
        packet[10:13] = bytes(color)
        self._write(bytes(packet))
        app_logger().info("Keyboard firmware mode path=%s mode=%s color=%s brightness=%d", self.path, mode, color, brightness)
        if self.save:
            time.sleep(0.04)
            store = bytearray(self.REPORT_SIZE)
            store[1:3] = b"\x50\x55"
            self._write(bytes(store))

    def close(self, fallback: tuple[str, Color, int] | None = None) -> None:
        if self.fd < 0:
            return
        try:
            if fallback:
                self.firmware_mode(*fallback)
                time.sleep(0.03)
                self._drain()
        except OSError:
            app_logger().exception("Could not hand keyboard back to firmware path=%s", self.path)
        finally:
            os.close(self.fd)
            self.fd = -1


class LampArrayLink(Link):
    """Standard HID LampArray device with a single lamp (Harpe scroll wheel)."""

    REFRESH_SECONDS = 2.0

    def __init__(self, path: str) -> None:
        self.path = path
        self.fd = -1
        self._sent: Color | None = None
        self._refreshed = 0.0
        self._autonomous_disabled = False

    def open(self) -> None:
        logger = app_logger()
        self.fd = os.open(self.path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        try:
            attributes = get_feature(self.fd, 0x01, 23)
            lamp_count = int.from_bytes(attributes[1:3], "little")
            minimum_interval = int.from_bytes(attributes[19:23], "little") / 1_000_000
            # The HID spec initializes the LampId cursor to zero, so this reads lamp 0.
            lamp = get_feature(self.fd, 0x03, 29)
            logger.info("LampArray capabilities path=%s attr=%s lamp=%s", self.path, attributes.hex(" "), lamp.hex(" "))
            if lamp_count != 1 or not lamp[27] or min(lamp[23:26]) == 0:
                raise OSError(tr("Die Mausrad-LED meldet kein programmierbares RGB-LampArray."))
            self.fps_limit = 1 / min(max(minimum_interval, 0.02), 1.0)
            set_feature(self.fd, bytes((0x06, 0x00)))
            self._autonomous_disabled = True
            self._sent = None
            time.sleep(min(max(minimum_interval, 0.001), 1.0))
        except Exception:
            self.close()
            raise

    def send(self, frame: dict[int, Color]) -> None:
        color = next(iter(frame.values()))
        now = time.monotonic()
        if color == self._sent and now - self._refreshed < self.REFRESH_SECONDS:
            return
        # LampUpdateComplete, LampIdStart, LampIdEnd, then RGBI.
        set_feature(self.fd, bytes((0x05, 0x01, 0x00, 0x00, 0x00, 0x00, *color, 0xFF)))
        self._sent = color
        self._refreshed = now

    def close(self, fallback: tuple[str, Color, int] | None = None) -> None:
        if self.fd < 0:
            return
        try:
            if self._autonomous_disabled:
                set_feature(self.fd, bytes((0x06, 0x01)))
                app_logger().info("LampArray control released path=%s", self.path)
        except OSError:
            app_logger().exception("Could not release LampArray path=%s", self.path)
        finally:
            self._autonomous_disabled = False
            os.close(self.fd)
            self.fd = -1
