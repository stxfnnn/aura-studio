"""QML-facing side of the OLED: the draft being edited, its preview and the upload."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot

from . import hid, i18n, oled
from .devices import Device
from .engine import Runner
from .i18n import tr

DEFAULT_DRAFT: dict[str, Any] = {
    "source": "animation",   # "file" | "text" | "animation"
    "file": "",
    "mode": "fit",           # "fit" | "fill" | "stretch"
    "maxFrames": 32,
    "invert": False,
    "text": "Aura Studio",
    "size": 34,
    "bold": True,
    "scroll": False,
    "speed": 40,
    "animation": "waves",
    "brightness": 100,       # grey levels of the content are scaled; applies with the next transfer
    "power": True,           # last on/off state we set; the keyboard cannot be asked
}
FRAME_CHOICES = (16, 32, 64, 128)
SECONDS_PER_REPORT = 0.0095   # measured through the Omni receiver


class OledController(QObject):
    changed = Signal()
    availableChanged = Signal()
    busyChanged = Signal()
    progressChanged = Signal()
    notify = Signal(str, str)
    _finished = Signal(str, str)

    def __init__(self, saved: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.logger = hid.app_logger()
        self._draft = dict(DEFAULT_DRAFT)
        for key, default in DEFAULT_DRAFT.items():
            value = (saved or {}).get(key, default)
            if type(value) is type(default):
                self._draft[key] = value
        self._device: Device | None = None
        self._runner: Runner | None = None
        self._clip = oled.Clip([oled.blank()], [1000])
        self._preview: list[dict[str, Any]] = []
        self._error = ""
        self._busy = False
        self._progress = 0.0
        self._animations: list[dict[str, Any]] | None = None
        self._finished.connect(self._on_finished)
        # Runners of the other devices; set by the service, used when they should pause during a transfer.
        self.other_runners: Callable[[], list[Runner]] = lambda: []
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick_clock)

    def retranslate(self) -> None:
        """Rebuild everything that carries text after the language changed."""
        self._animations = None
        self._render()

    def attach(self, device: Device | None, runner: Runner | None) -> None:
        """Called after every scan with the keyboard that carries the display, if any."""
        self._device, self._runner = device, runner
        if not device:
            self._clock.stop()
        self.availableChanged.emit()
        if device and not self._preview:
            self._render()

    # ------------------------------------------------------------------ draft

    @Property(bool, notify=availableChanged)
    def available(self) -> bool:
        return self._device is not None

    @Property(str, notify=availableChanged)
    def deviceName(self) -> str:
        return self._device.name if self._device else ""

    @Property("QVariantMap", notify=changed)
    def draft(self) -> dict[str, Any]:
        return dict(self._draft)

    @Property("QVariantList", notify=changed)
    def preview(self) -> list[dict[str, Any]]:
        return self._preview

    @Property(str, notify=changed)
    def error(self) -> str:
        return self._error

    @Property(str, notify=changed)
    def fileName(self) -> str:
        return Path(self._draft["file"]).name if self._draft["file"] else ""

    @Property(str, notify=changed)
    def info(self) -> str:
        count = len(self._clip.frames)
        reports = (2 + 2 * count + count * oled.FRAME_BYTES) // 59 + 1
        seconds = max(1, round(reports * SECONDS_PER_REPORT))
        if count == 1:
            return tr("Standbild · Übertragung etwa {seconds} s").format(seconds=seconds)
        return tr("{count} Bilder · Schleife {loop} s · Übertragung etwa {seconds} s").format(
            count=count, loop=i18n.decimal(self._clip.seconds), seconds=seconds)

    @Property("QVariantList", notify=changed)
    def animations(self) -> list[dict[str, Any]]:
        if self._animations is None:
            self._animations = [{"id": key, "name": tr(entry[0]),
                                 "src": oled.to_png_url(oled.animation_clip(key).frames[entry[2] // 3])}
                                for key, entry in oled.ANIMATIONS.items()]
        return self._animations

    @Property(int, constant=True)
    def presetCount(self) -> int:
        return oled.FIRMWARE_PRESETS

    @Slot(str, "QVariant")
    def set(self, key: str, value: Any) -> None:
        default = DEFAULT_DRAFT.get(key)
        if default is None or key in ("file", "power"):
            return
        value = bool(value) if isinstance(default, bool) else int(value) if isinstance(default, int) else str(value)
        if key == "text":
            value = value[:200]
        if (key == "maxFrames" and value not in FRAME_CHOICES) or (key == "animation" and value not in oled.ANIMATIONS):
            return
        if self._draft[key] != value:
            self._draft[key] = value
            self._render()

    @Slot(QUrl)
    def openFile(self, url: QUrl) -> None:
        self._draft["file"] = url.toLocalFile()
        self._draft["source"] = "file"
        self._render()

    def _render(self) -> None:
        draft = self._draft
        self._error = ""
        try:
            if draft["source"] == "file":
                if not draft["file"]:
                    self._clip = oled.Clip([oled.blank()], [1000])
                    self._error = tr("Noch keine Datei gewählt.")
                else:
                    self._clip = oled.load_file(draft["file"], draft["mode"], draft["invert"], draft["maxFrames"])
            elif draft["source"] == "text":
                self._clip = oled.text_clip(draft["text"], draft["size"], draft["bold"], draft["scroll"],
                                            draft["speed"], draft["invert"])
            else:
                self._clip = oled.animation_clip(draft["animation"], draft["invert"])
        except OSError as exc:
            self._clip = oled.Clip([oled.blank()], [1000])
            self._error = str(exc)
        if draft["brightness"] < 100:
            self._clip = oled.Clip([oled.dimmed(frame, draft["brightness"]) for frame in self._clip.frames],
                                   self._clip.durations)
        self._preview = [{"src": oled.to_png_url(frame), "ms": duration}
                         for frame, duration in zip(self._clip.frames, self._clip.durations)]
        self.changed.emit()

    # ----------------------------------------------------------------- device

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        return self._progress

    def _set_progress(self, value: float) -> None:
        # Called from the worker thread; a few dozen updates are plenty for a progress bar.
        if value >= 1 or value - self._progress >= 0.01:
            self._progress = value
            self.progressChanged.emit()

    def _run(self, label: str, job, success: str) -> None:
        """Run ``job(link)`` on a worker thread while the key lighting stream is paused."""
        device, runner = self._device, self._runner
        if not device or self._busy:
            return
        self._busy = True
        self._progress = 0.0
        self.busyChanged.emit()
        self.progressChanged.emit()

        def work() -> None:
            message, kind = success, "success"
            paused = ([runner] if runner else []) + [other for other in self.other_runners() if other is not runner]
            for held in paused:
                held.hold = True
            if paused:
                time.sleep(0.08)  # let a frame that is already on its way finish
            try:
                if device.virtual:
                    for step in range(1, 41):
                        time.sleep(0.03)
                        self._set_progress(step / 40)
                else:
                    with oled.OledLink(device.oled_path, device.oled_report) as link:
                        job(link)
                self.logger.info("OLED %s done device=%s", label, device.name)
            except OSError as exc:
                self.logger.exception("OLED %s failed device=%s", label, device.name)
                message = (str(exc) if isinstance(exc, oled.OledError)
                           else tr("Display nicht erreichbar: {error}").format(error=exc))
                kind = "error"
            finally:
                for held in paused:
                    held.hold = False
            self._finished.emit(message, kind)

        threading.Thread(target=work, name="AuraOled", daemon=True).start()

    @Slot(str, str)
    def _on_finished(self, message: str, kind: str) -> None:
        self._busy = False
        self.busyChanged.emit()
        self.notify.emit(message, kind)

    @Slot()
    def upload(self) -> None:
        if self._error:
            self.notify.emit(self._error, "error")
            return
        self._stop_clock()
        frames = [oled.pack(frame) for frame in self._clip.frames]
        durations = list(self._clip.durations)
        self._run("upload", lambda link: link.upload(frames, durations, self._set_progress),
                  tr("Auf das Display übertragen"))

    @Slot(int)
    def selectPreset(self, number: int) -> None:
        self._stop_clock()
        self._run("preset", lambda link: link.select_preset(number), tr("Werksanimation {number} aktiv").format(number=number + 1))

    @Slot(bool)
    def setPower(self, on: bool) -> None:
        if self._busy:
            return
        self._draft["power"] = on
        self.changed.emit()
        self._run("power", lambda link: link.set_power(on), tr("Display eingeschaltet") if on else tr("Display ausgeschaltet"))

    def idle_power(self, on: bool) -> bool:
        """Switch the display for the idle timeout, without storing it. False if it could not be done now."""
        device = self._device
        if not device or self._busy or not self._draft["power"]:
            return False
        if device.virtual:
            return True
        try:
            with oled.OledLink(device.oled_path, device.oled_report) as link:
                link.set_power(on, store=False)
            return True
        except OSError as exc:
            self.logger.warning("OLED idle switch failed: %s", exc)
            return False

    # The firmware can draw date and time itself, but only when told the time: it does
    # not count on its own. While the live clock is on we send the time once a second.
    clockChanged = Signal()

    @Property(bool, notify=clockChanged)
    def clock(self) -> bool:
        return self._clock.isActive()

    @Slot(bool)
    def setClock(self, on: bool) -> None:
        if on == self._clock.isActive() or (on and (not self._device or self._busy)):
            return
        if on:
            self._clock.start()
            self._tick_clock()
        else:
            self._clock.stop()
        self.clockChanged.emit()

    def _stop_clock(self) -> None:
        if self._clock.isActive():
            self._clock.stop()
            self.clockChanged.emit()

    def _tick_clock(self) -> None:
        device = self._device
        if not device or device.virtual or self._busy:
            return
        try:
            with oled.OledLink(device.oled_path, device.oled_report) as link:
                link.show_clock()
        except OSError as exc:
            self.logger.warning("OLED clock update failed: %s", exc)
            self._stop_clock()
            self.notify.emit(tr("Uhr angehalten: Display nicht erreichbar ({error})").format(error=exc), "error")
