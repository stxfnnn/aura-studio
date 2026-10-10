"""ROG Azoth OLED: frame rendering and the upload protocol.

The panel is 208 x 64 pixels with 16 grey levels. Content is not streamed live:
an image or a whole animation is uploaded once, stored in the keyboard and then
looped by the firmware, so it keeps playing without this app.

Protocol after the reverse-engineering notes in Timeroot/azoth-nn (PROTOCOL.md)
and IcyBlue17/ROG-AzothOLED-HIDProtocol. Every report starts with report id 2:

    12 03, 12 01                    enter picture mode
    61 00 00 00 <n> + 50 55         select built-in animation n
    61 01 00 00 <count LE16>        start upload of <count> data reports
    61 02 <index LE16> <payload>    data, index counts down to 0
    61 03                           end
    50 55                           commit (stores the upload in flash)
    69 00 00 00 <0|1> + 50 55       switch the display off / on (found in the firmware decompile)
    63 00 00 00 <fmt> <year LE16> <month> <day> <hour> <minute> <second>   show date and time
                                    (fmt bit 7 = with seconds; the screen is static until sent again)

The payload stream is ``<frames> 00 <duration ms LE16 per frame>`` followed by
the frames, each 6656 bytes with two pixels per byte (low nibble = left pixel).
The keyboard echoes every data report; the next one may only follow that echo.
"""
from __future__ import annotations

import math
import os
import select
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QImageReader, QPainter, QPen

from .i18n import tr

WIDTH, HEIGHT = 208, 64
FRAME_BYTES = WIDTH * HEIGHT // 2
MAX_FRAMES = 196          # limit of the vendor software
MIN_FRAME_MS = 40         # the panel plays at most 25 frames per second
FIRMWARE_PRESETS = 6      # the firmware rejects preset numbers above 5
TICKER_FRAMES = 72        # most frames a scrolling text is rendered to


class OledError(OSError):
    pass


@dataclass
class Clip:
    """Greyscale frames (Format_Grayscale8, 208 x 64) with a duration each."""
    frames: list[QImage]
    durations: list[int]

    @property
    def seconds(self) -> float:
        return sum(self.durations) / 1000


# ------------------------------------------------------------------ rendering

def blank() -> QImage:
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_Grayscale8)
    image.fill(0)
    return image


def fit(source: QImage, mode: str = "fit", invert: bool = False) -> QImage:
    """Scale any image onto the panel: "fit" letterboxes, "fill" crops, "stretch" distorts."""
    if source.hasAlphaChannel():
        # Transparent pixels are simply unlit.
        flat = QImage(source.size(), QImage.Format.Format_RGB32)
        flat.fill(0)
        painter = QPainter(flat)
        painter.drawImage(0, 0, source)
        painter.end()
        source = flat
    aspect = {"fit": Qt.AspectRatioMode.KeepAspectRatio, "fill": Qt.AspectRatioMode.KeepAspectRatioByExpanding,
              "stretch": Qt.AspectRatioMode.IgnoreAspectRatio}.get(mode, Qt.AspectRatioMode.KeepAspectRatio)
    scaled = source.scaled(WIDTH, HEIGHT, aspect, Qt.TransformationMode.SmoothTransformation)
    canvas = QImage(WIDTH, HEIGHT, QImage.Format.Format_RGB32)
    canvas.fill(0)
    painter = QPainter(canvas)
    painter.drawImage((WIDTH - scaled.width()) // 2, (HEIGHT - scaled.height()) // 2, scaled)
    painter.end()
    grey = canvas.convertToFormat(QImage.Format.Format_Grayscale8)
    if invert:
        grey.invertPixels()
    return grey


def load_file(path: str, mode: str, invert: bool, max_frames: int) -> Clip:
    """Read a still image or an animation (GIF, WebP, APNG) and thin it out to ``max_frames``."""
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    frames: list[QImage] = []
    durations: list[int] = []
    while len(frames) < 2000:
        image = reader.read()
        if image.isNull():
            break
        frames.append(image)
        durations.append(reader.nextImageDelay() or 100)
        if not reader.supportsAnimation():
            break
    if not frames:
        raise OledError(reader.errorString() or tr("Die Datei konnte nicht gelesen werden."))
    limit = max(1, min(max_frames, MAX_FRAMES))
    if len(frames) > limit:
        # Keep evenly spaced frames and let each stand for the ones dropped after it.
        total = len(frames)
        picks = [index * total // limit for index in range(limit)]
        bounds = picks[1:] + [total]
        durations = [sum(durations[start:end]) for start, end in zip(picks, bounds)]
        frames = [frames[index] for index in picks]
    return Clip([fit(frame, mode, invert) for frame in frames],
                [max(MIN_FRAME_MS, min(60000, duration)) for duration in durations])


def _painter(image: QImage) -> QPainter:
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    return painter


def text_clip(text: str, size: int, bold: bool, scroll: bool, speed: int, invert: bool) -> Clip:
    """Render text; long or scrolling text becomes a seamless ticker."""
    lines = [line for line in text.split("\n")][:3] or [""]
    font = QFont()
    font.setPixelSize(max(8, min(60, size if len(lines) == 1 else min(size, HEIGHT // len(lines) - 2))))
    font.setBold(bold)
    metrics = QFontMetricsF(font)
    ink = QColor(0, 0, 0) if invert else QColor(255, 255, 255)
    paper = 255 if invert else 0

    def draw(offset: float, content: str | None = None) -> QImage:
        image = blank()
        image.fill(paper)
        painter = _painter(image)
        painter.setFont(font)
        painter.setPen(ink)
        if content is not None:
            painter.drawText(QPointF(offset, (HEIGHT + metrics.ascent() - metrics.descent()) / 2), content)
        else:
            block = metrics.lineSpacing() * len(lines)
            for row, line in enumerate(lines):
                painter.drawText(QRectF(0, (HEIGHT - block) / 2 + row * metrics.lineSpacing(), WIDTH, metrics.lineSpacing()),
                                 Qt.AlignmentFlag.AlignCenter, line)
        painter.end()
        return image

    single = " ".join(line.strip() for line in lines).strip()
    if not scroll or not single:
        return Clip([draw(0)], [1000])
    # Ticker: the text plus a gap travels exactly one period, so the loop is seamless.
    period = metrics.horizontalAdvance(single) + max(40.0, WIDTH * 0.35)
    pixels_per_second = 30 + max(0, min(100, speed)) * 1.5
    # Long texts take coarser steps so the upload stays reasonably short.
    count = max(2, min(TICKER_FRAMES, round(period / 3)))
    duration = max(MIN_FRAME_MS, round(period / count / pixels_per_second * 1000))
    frames = []
    for index in range(count):
        shift = -period * index / count
        image = draw(WIDTH * 0.1 + shift, single)
        if WIDTH * 0.1 + shift + period < WIDTH:
            painter = _painter(image)
            painter.setFont(font)
            painter.setPen(ink)
            painter.drawText(QPointF(WIDTH * 0.1 + shift + period, (HEIGHT + metrics.ascent() - metrics.descent()) / 2), single)
            painter.end()
        frames.append(image)
    return Clip(frames, [duration] * count)


def _noise(a: int, b: int = 0) -> float:
    n = (a * 374761393 + b * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def _grey(level: float) -> QColor:
    value = max(0, min(255, round(level * 255)))
    return QColor(value, value, value)


def _waves(painter: QPainter, phase: float) -> None:
    for layer, (amplitude, wavelength, level) in enumerate(((7, 52, 0.35), (10, 78, 0.6), (13, 104, 1.0))):
        painter.setPen(QPen(_grey(level), 1.6))
        points = [QPointF(x, HEIGHT / 2 + (layer - 1) * 9 + amplitude * math.sin(
            2 * math.pi * (x / wavelength + phase * (layer + 1)))) for x in range(0, WIDTH + 2, 2)]
        painter.drawPolyline(points)


def _stars(painter: QPainter, phase: float) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    for star in range(70):
        depth = (_noise(star, 1) + phase) % 1.0          # 0 = far away, 1 = flying past
        angle = _noise(star, 2) * 2 * math.pi
        reach = depth ** 2 * 130
        x, y = WIDTH / 2 + math.cos(angle) * reach, HEIGHT / 2 + math.sin(angle) * reach * 0.45
        painter.setBrush(_grey(0.15 + depth * 0.85))
        radius = 0.4 + depth * 1.3
        painter.drawEllipse(QPointF(x, y), radius, radius)


def _rain(painter: QPainter, phase: float) -> None:
    for column in range(0, WIDTH, 8):
        laps = 1 + int(_noise(column, 3) * 2)              # whole laps per loop keep it seamless
        head = ((phase * laps + _noise(column, 4)) % 1.0) * (HEIGHT + 30) - 10
        for step in range(7):
            painter.setPen(QPen(_grey(1.0 - step / 7), 2))
            y = head - step * 4
            painter.drawLine(QPointF(column + 3, y), QPointF(column + 3, y - 3))


def _equalizer(painter: QPainter, phase: float) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    bars = 26
    for bar in range(bars):
        level = 0.5 + 0.3 * math.sin(2 * math.pi * (phase * (1 + bar % 3) + _noise(bar, 5)))
        level += 0.2 * math.sin(2 * math.pi * (phase * 2 + _noise(bar, 6)))
        height = 4 + max(0.0, min(1.0, level)) * (HEIGHT - 8)
        painter.setBrush(_grey(0.45 + 0.55 * level))
        painter.drawRoundedRect(QRectF(bar * 8 + 1, HEIGHT - height - 1, 5.5, height), 1.5, 1.5)


def _pulse(painter: QPainter, phase: float) -> None:
    beat = [(0.0, 0), (0.30, 0), (0.34, -6), (0.38, 0), (0.43, 4), (0.47, -26), (0.52, 18), (0.56, 0),
            (0.66, -8), (0.74, 0), (1.0, 0)]

    def height(position: float) -> float:
        position %= 1.0
        for (start, a), (end, b) in zip(beat, beat[1:]):
            if position <= end:
                return a + (b - a) * (position - start) / (end - start)
        return 0.0

    head = phase * WIDTH
    for x in range(WIDTH):
        age = (head - x) % WIDTH / WIDTH                   # 0 at the writing head
        painter.setPen(QPen(_grey(max(0.0, 1.0 - age * 1.25)), 1.7))
        painter.drawLine(QPointF(x, HEIGHT / 2 + 4 + height(x / 104)), QPointF(x + 1, HEIGHT / 2 + 4 + height((x + 1) / 104)))


def _scanner(painter: QPainter, phase: float) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    centre = WIDTH / 2 + math.sin(2 * math.pi * phase) * (WIDTH / 2 - 16)
    for cell in range(26):
        x = cell * 8 + 1
        distance = abs(x + 3 - centre)
        painter.setBrush(_grey(0.08 + 0.92 * math.exp(-(distance / 22) ** 2)))
        painter.drawRoundedRect(QRectF(x, 22, 6, 20), 2, 2)


def _orbit(painter: QPainter, phase: float) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for ring, (radius, turns) in enumerate(((14, 3), (24, 2), (30, 1))):
        painter.setPen(QPen(_grey(0.22), 1))
        painter.drawEllipse(QPointF(WIDTH / 2, HEIGHT / 2), radius * 2.6, radius * 0.9)
        angle = 2 * math.pi * (phase * turns + ring / 3)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_grey(1.0))
        painter.drawEllipse(QPointF(WIDTH / 2 + math.cos(angle) * radius * 2.6, HEIGHT / 2 + math.sin(angle) * radius * 0.9),
                            3 - ring * 0.5, 3 - ring * 0.5)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_grey(0.8))
    painter.drawEllipse(QPointF(WIDTH / 2, HEIGHT / 2), 5, 5)


def _fire(painter: QPainter, phase: float) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    for column in range(0, WIDTH, 4):
        sway = math.sin(2 * math.pi * (phase * 2 + _noise(column, 7)))
        lick = math.sin(2 * math.pi * (phase * 3 + _noise(column, 8)))
        height = 14 + 22 * _noise(column // 12, 9) + 9 * sway + 5 * lick
        for step in range(int(max(4, height)) // 3):
            level = 1.0 - step * 3 / max(4.0, height)
            painter.setBrush(_grey(level ** 1.4))
            painter.drawRect(QRectF(column, HEIGHT - 3 - step * 3, 4, 3))


def _radar(painter: QPainter, phase: float) -> None:
    centre = QPointF(WIDTH / 2, HEIGHT - 4)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for radius in (18, 36, 54):
        painter.setPen(QPen(_grey(0.22), 1))
        painter.drawArc(QRectF(centre.x() - radius * 1.8, centre.y() - radius, radius * 3.6, radius * 2), 0, 180 * 16)
    sweep = math.pi * (0.5 - 0.5 * math.cos(2 * math.pi * phase))
    for trail in range(10):
        angle = sweep - trail * 0.05 * (1 if phase < 0.5 else -1)
        painter.setPen(QPen(_grey(1.0 - trail / 10), 1.6))
        painter.drawLine(centre, QPointF(centre.x() - math.cos(angle) * 100, centre.y() - math.sin(angle) * 56))
    painter.setPen(Qt.PenStyle.NoPen)
    for blip in range(4):
        angle, reach = 0.4 + _noise(blip, 10) * 2.3, 0.35 + _noise(blip, 11) * 0.55
        glow = max(0.0, 1.0 - abs(angle - sweep) * 2.2)
        painter.setBrush(_grey(0.15 + 0.85 * glow))
        painter.drawEllipse(QPointF(centre.x() - math.cos(angle) * 100 * reach, centre.y() - math.sin(angle) * 56 * reach), 2, 2)


def _tunnel(painter: QPainter, phase: float) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for ring in range(6):
        depth = (ring + phase) / 6
        scale = depth ** 2.2
        painter.setPen(QPen(_grey(0.15 + 0.85 * depth), 1 + depth))
        painter.drawRoundedRect(QRectF(WIDTH / 2 - WIDTH * scale / 2, HEIGHT / 2 - HEIGHT * scale / 2,
                                       WIDTH * scale, HEIGHT * scale), 6 * depth, 6 * depth)


def _bounce(painter: QPainter, phase: float) -> None:
    def triangle(value: float) -> float:
        return 1 - abs((value % 1.0) * 2 - 1)

    painter.setPen(QPen(_grey(0.3), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(QRectF(0.5, 0.5, WIDTH - 1, HEIGHT - 1))
    painter.setPen(Qt.PenStyle.NoPen)
    for ball, (laps_x, laps_y, radius) in enumerate(((1, 2, 6), (2, 3, 4), (3, 1, 5))):
        x = radius + 2 + triangle(phase * laps_x + ball * 0.31) * (WIDTH - 2 * radius - 4)
        y = radius + 2 + triangle(phase * laps_y + ball * 0.17) * (HEIGHT - 2 * radius - 4)
        painter.setBrush(_grey(1.0 - ball * 0.25))
        painter.drawEllipse(QPointF(x, y), radius, radius)


def _snow(painter: QPainter, phase: float) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    for flake in range(46):
        laps = 1 + int(_noise(flake, 12) * 2)
        y = ((phase * laps + _noise(flake, 13)) % 1.0) * (HEIGHT + 6) - 3
        x = _noise(flake, 14) * WIDTH + 5 * math.sin(2 * math.pi * (phase * 2 + _noise(flake, 15)))
        size = 0.7 + _noise(flake, 16) * 1.4
        painter.setBrush(_grey(0.35 + 0.65 * _noise(flake, 17)))
        painter.drawEllipse(QPointF(x, y), size, size)


def _ripples(painter: QPainter, phase: float) -> None:
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for ring in range(5):
        progress = (ring / 5 + phase) % 1.0
        painter.setPen(QPen(_grey((1.0 - progress) ** 1.3), 1.5))
        painter.drawEllipse(QPointF(WIDTH / 2, HEIGHT / 2), progress * 125, progress * 46)


def _lissajous(painter: QPainter, phase: float) -> None:
    points = []
    for step in range(181):
        t = step / 180 * 2 * math.pi
        points.append(QPointF(WIDTH / 2 + 92 * math.sin(3 * t + 2 * math.pi * phase), HEIGHT / 2 + 26 * math.sin(2 * t)))
    painter.setPen(QPen(_grey(0.3), 3))
    painter.drawPolyline(points)
    painter.setPen(QPen(_grey(1.0), 1.2))
    painter.drawPolyline(points)


def _eyes(painter: QPainter, phase: float) -> None:
    blink = max(0.0, 1.0 - abs(phase - 0.82) * 14)          # one quick blink per loop
    look = math.sin(2 * math.pi * phase) * 9
    painter.setPen(Qt.PenStyle.NoPen)
    for centre in (WIDTH / 2 - 38, WIDTH / 2 + 38):
        painter.setBrush(_grey(1.0))
        painter.drawRoundedRect(QRectF(centre - 22, HEIGHT / 2 - 22 * (1 - blink), 44, max(3.0, 44 * (1 - blink))), 14, 14)
        if blink < 0.6:
            painter.setBrush(_grey(0.0))
            painter.drawEllipse(QPointF(centre + look, HEIGHT / 2 + 3), 9, 9)


def _typing(painter: QPainter, phase: float) -> None:
    message = "> aura studio"
    shown = message[:max(2, round(min(1.0, phase * 1.6) * len(message)))]
    font = QFont("monospace")
    font.setPixelSize(22)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(_grey(1.0))
    metrics = QFontMetricsF(font)
    baseline = (HEIGHT + metrics.ascent() - metrics.descent()) / 2
    painter.drawText(QPointF(10, baseline), shown)
    if int(phase * 8) % 2 == 0:
        painter.fillRect(QRectF(10 + metrics.horizontalAdvance(shown) + 2, baseline - metrics.ascent() + 2, 11, metrics.ascent()), _grey(1.0))


def _dna(painter: QPainter, phase: float) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    for x in range(4, WIDTH, 9):
        angle = 2 * math.pi * (x / 70 + phase)
        top, bottom = HEIGHT / 2 + 22 * math.sin(angle), HEIGHT / 2 - 22 * math.sin(angle)
        front = math.cos(angle)
        painter.setPen(QPen(_grey(0.25), 1))
        painter.drawLine(QPointF(x, top), QPointF(x, bottom))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_grey(0.55 + 0.45 * front))
        painter.drawEllipse(QPointF(x, top), 2.4 + front, 2.4 + front)
        painter.setBrush(_grey(0.55 - 0.45 * front))
        painter.drawEllipse(QPointF(x, bottom), 2.4 - front, 2.4 - front)


# id -> (name, painter function, frame count, frame duration in ms)
ANIMATIONS: dict[str, tuple[str, Callable[[QPainter, float], None], int, int]] = {
    "waves": ("Wellen", _waves, 24, 60),
    "stars": ("Sternenflug", _stars, 24, 50),
    "rain": ("Regen", _rain, 24, 50),
    "equalizer": ("Equalizer", _equalizer, 20, 70),
    "pulse": ("Herzlinie", _pulse, 26, 45),
    "scanner": ("Scanner", _scanner, 24, 45),
    "orbit": ("Umlaufbahn", _orbit, 24, 55),
    "fire": ("Flammen", _fire, 20, 60),
    "radar": ("Radar", _radar, 28, 55),
    "tunnel": ("Tunnel", _tunnel, 16, 55),
    "bounce": ("Bälle", _bounce, 32, 45),
    "snow": ("Schnee", _snow, 24, 70),
    "ripples": ("Ringe", _ripples, 20, 60),
    "lissajous": ("Schleife", _lissajous, 24, 55),
    "dna": ("Doppelhelix", _dna, 24, 55),
    "eyes": ("Augen", _eyes, 24, 110),
    "typing": ("Tippen", _typing, 24, 110),
}


def animation_clip(animation_id: str, invert: bool = False) -> Clip:
    _, draw, count, duration = ANIMATIONS[animation_id]
    frames = []
    for index in range(count):
        image = blank()
        painter = _painter(image)
        draw(painter, index / count)
        painter.end()
        if invert:
            image.invertPixels()
        frames.append(image)
    return Clip(frames, [duration] * count)


def dimmed(image: QImage, percent: int) -> QImage:
    """Scale the grey levels; the panel itself has no known brightness command."""
    if percent >= 100:
        return image
    out = image.copy()
    painter = QPainter(out)
    painter.fillRect(out.rect(), QColor(0, 0, 0, round(255 * (1 - max(5, percent) / 100))))
    painter.end()
    return out


def to_png_url(image: QImage) -> str:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return "data:image/png;base64," + bytes(data.toBase64()).decode("ascii")


def pack(image: QImage) -> bytes:
    """208 x 64 greyscale image -> 6656 bytes, low nibble = left pixel."""
    if image.format() != QImage.Format.Format_Grayscale8 or image.width() != WIDTH or image.height() != HEIGHT:
        image = fit(image, "stretch")
    out = bytearray(FRAME_BYTES)
    position = 0
    for y in range(HEIGHT):
        row = bytes(image.constScanLine(y)[:WIDTH])
        for x in range(0, WIDTH, 2):
            out[position] = (row[x + 1] & 0xF0) | (row[x] >> 4)
            position += 1
    return bytes(out)


# ------------------------------------------------------------------- protocol

class OledLink:
    """Serial command channel to the display. ``report_size`` includes the report id."""

    ACK_SECONDS = 0.25
    RETRIES = 6

    def __init__(self, path: str, report_size: int) -> None:
        self.path = path
        self.report_size = report_size
        self.payload = report_size - 5
        self.fd = -1

    def __enter__(self) -> "OledLink":
        self.fd = os.open(self.path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        return self

    def __exit__(self, *_: object) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def _read(self, timeout: float) -> bytes:
        if not select.select([self.fd], [], [], timeout)[0]:
            return b""
        try:
            return os.read(self.fd, 256)
        except BlockingIOError:
            return b""

    def _drain(self) -> None:
        while self._read(0):
            pass

    def _command(self, *body: int, payload: bytes = b"", echo: int = 2, retries: int = 1,
                 wait: float = ACK_SECONDS) -> bool:
        """Send one report and wait until the keyboard echoes its first ``echo`` bytes."""
        report = bytes((0x02, *body)) + payload
        report += bytes(self.report_size - len(report))
        expect = report[1:1 + echo]
        for _ in range(retries):
            self._drain()
            if os.write(self.fd, report) != len(report):
                raise OledError(tr("Unvollständiger HID-Bericht an das Display."))
            deadline = time.monotonic() + wait
            while time.monotonic() < deadline:
                reply = self._read(deadline - time.monotonic())
                if reply[1:1 + echo] == expect:
                    return True
                if reply[1:3] == b"\xff\xaa":
                    raise OledError(tr("Die Tastatur hat den Befehl abgelehnt."))
        return False

    def _require(self, *body: int, wait: float = ACK_SECONDS) -> None:
        if not self._command(*body, retries=3, wait=wait):
            raise OledError(tr("Das Display antwortet nicht. Ist die Tastatur eingeschaltet und wach?"))

    def select_preset(self, number: int) -> None:
        if not 0 <= number < FIRMWARE_PRESETS:
            raise ValueError(number)
        self._require(0x12, 0x03)
        self._require(0x12, 0x01)
        self._require(0x61, 0x00, 0x00, 0x00, number)
        self._require(0x50, 0x55, wait=1.5)

    def set_power(self, on: bool) -> None:
        """The display's own on/off setting, the one Armoury Crate offers as a switch."""
        self._require(0x69, 0x00, 0x00, 0x00, 1 if on else 0)
        self._require(0x50, 0x55, wait=1.5)

    def show_clock(self, now: datetime | None = None, seconds: bool = True) -> None:
        """Switch to the firmware's date/time screen. It does not tick on its own: send it again to update."""
        now = now or datetime.now()
        report = bytes((0x02, 0x63, 0x00, 0x00, 0x80 if seconds else 0x00, now.year & 0xFF, now.year >> 8,
                        now.month, now.day, now.hour, now.minute, now.second))
        os.write(self.fd, report + bytes(self.report_size - len(report)))

    def upload(self, frames: list[bytes], durations: list[int],
               progress: Callable[[float], None] = lambda _: None) -> None:
        """Store frames in the keyboard. Nothing is committed unless every report was acknowledged."""
        if not 1 <= len(frames) <= MAX_FRAMES or len(frames) != len(durations):
            raise ValueError("frame count")
        if any(len(frame) != FRAME_BYTES for frame in frames):
            raise ValueError("frame size")
        stream = bytes((len(frames), 0x00))
        stream += b"".join(max(MIN_FRAME_MS, min(0xFFFF, duration)).to_bytes(2, "little") for duration in durations)
        stream += b"".join(frames)
        total = (len(stream) + self.payload - 1) // self.payload
        self._require(0x12, 0x03)
        self._require(0x12, 0x01)
        self._require(0x61, 0x01, 0x00, 0x00, total & 0xFF, total >> 8)
        for sent in range(total):
            index = (total - 1 - sent).to_bytes(2, "little")
            chunk = stream[sent * self.payload:(sent + 1) * self.payload]
            if not self._command(0x61, 0x02, *index, payload=chunk, echo=4, retries=self.RETRIES):
                raise OledError(tr("Übertragung bei {percent} % abgebrochen: keine Bestätigung von der Tastatur. "
                                   "Es wurde nichts gespeichert; falls das Display schwarz bleibt, die Tastatur kurz aus- und einschalten.")
                                .format(percent=sent * 100 // total))
            progress((sent + 1) / total)
        # The data is complete at this point, so finish even if an echo goes missing.
        self._command(0x61, 0x03, retries=3)
        self._command(0x50, 0x55, retries=3, wait=1.5)
