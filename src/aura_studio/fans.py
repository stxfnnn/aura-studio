"""Fan control through the kernel's hwmon interface (Super I/O chips such as the nct6775 family).

Fans follow a temperature curve with a smoothing window and rate-limited ramps, so a
short load spike neither revs them up nor lets them drop right away. A fan stays with
the BIOS until another mode is chosen, and goes back to it on quit.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import time
from collections import deque
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from . import hid
from .i18n import tr

HWMON = Path("/sys/class/hwmon")
MODES = ("bios", "fixed", "curve")
SOURCES = ("cpu", "gpu", "max")
DEFAULT_FAN: dict[str, Any] = {"mode": "bios", "fixed": 50, "source": "max", "name": "",
                               "points": [[40, 30], [75, 100]]}   # [°C, %] …, sorted by temperature
DEFAULT_RAMP: dict[str, Any] = {"window": 20, "up": 5, "down": 2}   # seconds; percent per second
LIMITS = {"fixed": (0, 100), "window": (0, 120), "up": (1, 100), "down": (1, 100)}
TEMP_RANGE, MAX_POINTS = (20, 100), 16
PANIC = {"cpu": 90, "gpu": 85}   # °C: full speed at once, whatever the ramp says
CPU_CHIPS = ("coretemp", "k10temp", "zenpower")
RULE = "sudo cp packaging/99-aura-studio.rules /etc/udev/rules.d/ && sudo udevadm control --reload && sudo udevadm trigger"


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _read_int(path: Path) -> int | None:
    text = _read(path)
    return int(text) if text and text.lstrip("-").isdigit() else None


class Fan:
    def __init__(self, chip: Path, chip_name: str, index: int) -> None:
        self.id = f"{chip_name}/pwm{index}"
        self.index = index
        self.chip_name = chip_name
        self.pwm = chip / f"pwm{index}"
        self.enable = chip / f"pwm{index}_enable"
        self.rpm = chip / f"fan{index}_input"
        self.label = _read(chip / f"fan{index}_label") or ""
        self.original = _read_int(self.enable)   # the BIOS mode to hand back
        self.writable = os.access(self.pwm, os.W_OK) and os.access(self.enable, os.W_OK)
        self.manual = False
        self.level = (_read_int(self.pwm) or 0) * 100 / 255   # percent we are at
        self.last = -1


class FanController(QObject):
    changed = Signal()          # settings; the service saves them
    statusChanged = Signal()    # live readings
    notify = Signal(str, str)

    def __init__(self, saved: dict[str, Any] | None = None, demo: bool = False) -> None:
        super().__init__()
        self.logger = hid.app_logger()
        self._demo = Path(tempfile.mkdtemp(prefix="aura-fans-")) if demo else None
        root = self._demo_tree() if self._demo else HWMON
        self._fans: list[Fan] = []
        self._chips: dict[str, list[Path]] = {"cpu": [], "gpu": []}
        for chip in sorted(root.glob("hwmon*")):
            name = _read(chip / "name") or chip.name
            if name in CPU_CHIPS:
                self._chips["cpu"].append(chip)
            elif name == "amdgpu":
                self._chips["gpu"].append(chip)
            for enable in sorted(chip.glob("pwm[0-9]_enable")):
                self._fans.append(Fan(chip, name, int(enable.name[3])))
        self._has_nvidia = shutil.which("nvidia-smi") is not None
        saved = saved or {}
        self._settings = {fan.id: self._clean(DEFAULT_FAN, (saved.get("fans") or {}).get(fan.id))
                          for fan in self._fans}
        self._ramp = self._clean(DEFAULT_RAMP, saved.get("ramp"))
        self._history: dict[str, deque] = {"cpu": deque(), "gpu": deque()}
        self._raw: dict[str, float | None] = {"cpu": None, "gpu": None}
        self._smooth: dict[str, float | None] = dict(self._raw)
        self._live: dict[str, dict[str, Any]] = {}
        self.logger.info("Fans: %s", [fan.id for fan in self._fans])
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        if self._fans:
            self._tick()
            self._timer.start()

    @staticmethod
    def _clean(defaults: dict[str, Any], raw: Any) -> dict[str, Any]:
        clean = dict(defaults)
        if isinstance(raw, dict) and "tempLow" in raw and "points" not in raw:   # written by the first version
            raw = {**raw, "points": [[raw["tempLow"], raw.get("low", 30)], [raw["tempHigh"], raw.get("high", 100)]]}
        for key, default in defaults.items():
            value = (raw or {}).get(key, default) if isinstance(raw, dict) else default
            if type(value) is not type(default):
                continue
            if key in LIMITS:
                value = max(LIMITS[key][0], min(LIMITS[key][1], value))
            if key == "points":
                value = FanController._clean_points(value)
                if not value:
                    continue
            if key == "name":
                value = value.strip()[:24]
            if (key == "mode" and value not in MODES) or (key == "source" and value not in SOURCES):
                continue
            clean[key] = value
        return clean

    @staticmethod
    def _clean_points(raw: list[Any]) -> list[list[int]]:
        points: dict[int, int] = {}
        for item in raw:
            try:
                temp, percent = int(item[0]), int(item[1])
            except (TypeError, ValueError, IndexError):
                continue
            points[max(TEMP_RANGE[0], min(TEMP_RANGE[1], temp))] = max(0, min(100, percent))
        return [[temp, points[temp]] for temp in sorted(points)][:MAX_POINTS]

    @property
    def state(self) -> dict[str, Any]:
        return {"fans": self._settings, "ramp": self._ramp}

    def retranslate(self) -> None:
        self.changed.emit()

    def stop(self) -> None:
        self._timer.stop()
        for fan in self._fans:
            self._release(fan)
        if self._demo:
            shutil.rmtree(self._demo, ignore_errors=True)

    # --------------------------------------------------------------- readings

    def _read_cpu(self) -> float | None:
        values = [_read_int(path) for chip in self._chips["cpu"] for path in chip.glob("temp*_input")]
        values = [value for value in values if value is not None]
        return max(values) / 1000 if values else None

    def _read_gpu(self) -> float | None:
        for chip in self._chips["gpu"]:
            value = _read_int(chip / "temp1_input")
            if value is not None:
                return value / 1000
        if not self._has_nvidia:
            return None
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=1)
            return float(out.stdout.split()[0])
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
            return None

    def _pick(self, temps: dict[str, float | None], source: str) -> float | None:
        if source == "max":
            values = [value for value in temps.values() if value is not None]
            return max(values) if values else None
        return temps[source]

    @staticmethod
    def _curve(points: list[list[int]], temp: float) -> float:
        """Linear between the points, flat beyond the first and last one."""
        for (t0, p0), (t1, p1) in zip(points, points[1:]):
            if temp <= t1:
                return float(p0) if temp <= t0 else p0 + (p1 - p0) * (temp - t0) / (t1 - t0)
        return float(points[-1][1])

    def _tick(self) -> None:
        now = time.monotonic()
        if self._demo:
            self._demo_tick(now)
        need_gpu = any(s["mode"] == "curve" and s["source"] != "cpu" for s in self._settings.values())
        self._raw = {"cpu": self._read_cpu(), "gpu": self._read_gpu() if need_gpu else None}
        for source, value in self._raw.items():
            history = self._history[source]
            if value is not None:
                history.append((now, value))
            while history and history[0][0] < now - self._ramp["window"]:
                history.popleft()
            self._smooth[source] = sum(v for _, v in history) / len(history) if history else None
        for fan in self._fans:
            setting = self._settings[fan.id]
            if setting["mode"] == "bios" or not fan.writable:
                self._release(fan)
                fan.level = (_read_int(fan.pwm) or 0) * 100 / 255   # ramp from wherever the BIOS left it
            else:
                if setting["mode"] == "fixed":
                    target = float(setting["fixed"])
                else:
                    temp = self._pick(self._smooth, setting["source"])
                    target = 100.0 if temp is None else self._curve(setting["points"], temp)  # no reading: play safe
                watched = ("cpu", "gpu") if setting["source"] == "max" else (setting["source"],)
                panic = any(self._raw[k] is not None and self._raw[k] >= PANIC[k] for k in watched)
                step = 100 - fan.level if panic else max(-self._ramp["down"], min(self._ramp["up"], target - fan.level))
                self._apply(fan, fan.level + step)
            self._live[fan.id] = {"rpm": _read_int(fan.rpm) or 0, "level": round(fan.level),
                                  "temp": self._pick(self._smooth, setting["source"]),
                                  "active": fan.manual}
        self.statusChanged.emit()

    def _apply(self, fan: Fan, level: float) -> None:
        level = max(0.0, min(100.0, level))
        value = round(level * 255 / 100)
        try:
            if not fan.manual:
                fan.enable.write_text("1")
                fan.manual = True
            if value != fan.last:
                fan.pwm.write_text(str(value))
                fan.last = value
            fan.level = level
        except OSError as exc:
            fan.writable = False
            self.logger.warning("Fan %s not writable: %s", fan.id, exc)
            self.notify.emit(tr("Lüfter {name} lässt sich nicht steuern: {error}")
                             .format(name=self._name(fan), error=exc), "error")

    def _release(self, fan: Fan) -> None:
        """Hand the fan back to the BIOS curve (the mode it had when we found it)."""
        if not fan.manual:
            return
        try:
            fan.enable.write_text(str(fan.original if fan.original not in (None, 1) else 5))
        except OSError as exc:
            self.logger.warning("Could not release fan %s: %s", fan.id, exc)
        fan.manual = False
        fan.last = -1

    def _name(self, fan: Fan) -> str:
        return self._settings[fan.id]["name"] or fan.label or tr("Lüfter {n}").format(n=fan.index)

    # ------------------------------------------------------------------- demo

    def _demo_tree(self) -> Path:
        chip = self._demo / "hwmon0"
        chip.mkdir()
        (chip / "name").write_text("demo")
        for index in (1, 2, 3):
            (chip / f"pwm{index}").write_text("128")
            (chip / f"pwm{index}_enable").write_text("5")
            (chip / f"fan{index}_input").write_text("900")
        cpu = self._demo / "hwmon1"
        cpu.mkdir()
        (cpu / "name").write_text("coretemp")
        (cpu / "temp1_input").write_text("45000")
        return self._demo

    def _demo_tick(self, now: float) -> None:
        (self._demo / "hwmon1" / "temp1_input").write_text(str(int((52 + 12 * math.sin(now / 25)) * 1000)))
        for fan in self._fans:
            fan.rpm.write_text(str(int(fan.level * 18) if fan.manual else 900))

    # -------------------------------------------------------------------- qml

    @Property(bool, constant=True)
    def available(self) -> bool:
        return bool(self._fans)

    @Property("QVariantList", constant=True)
    def ids(self) -> list[str]:
        return [fan.id for fan in self._fans]

    @Property("QVariantMap", notify=changed)
    def config(self) -> dict[str, Any]:
        return {fan.id: {**self._settings[fan.id], "name": self._name(fan), "chip": fan.chip_name,
                         "writable": fan.writable} for fan in self._fans}

    @Property("QVariantMap", notify=statusChanged)
    def live(self) -> dict[str, Any]:
        return self._live

    @Property("QVariantMap", notify=statusChanged)
    def temps(self) -> dict[str, Any]:
        return {"cpu": self._raw["cpu"], "gpu": self._raw["gpu"],
                "cpuSmooth": self._smooth["cpu"], "gpuSmooth": self._smooth["gpu"]}

    @Property("QVariantMap", notify=changed)
    def ramp(self) -> dict[str, Any]:
        return dict(self._ramp)

    @Property(str, constant=True)
    def rule(self) -> str:
        return RULE

    @Slot(str, str, "QVariant")
    def setFanOption(self, fan_id: str, key: str, value: Any) -> None:
        if fan_id not in self._settings or key not in DEFAULT_FAN:
            return
        default = DEFAULT_FAN[key]
        value = int(value) if isinstance(default, int) else list(value) if isinstance(default, list) else str(value)
        self._settings[fan_id] = self._clean(DEFAULT_FAN, {**self._settings[fan_id], key: value})
        self.changed.emit()

    @Slot(str)
    def copyPoints(self, fan_id: str) -> None:
        """Give every other fan this fan's curve."""
        if fan_id not in self._settings:
            return
        for other in self._settings:
            if other != fan_id:
                self._settings[other]["points"] = [point[:] for point in self._settings[fan_id]["points"]]
        self.changed.emit()
        self.notify.emit(tr("Kurve auf alle Lüfter übertragen"), "success")

    @Slot(str, int)
    def setRamp(self, key: str, value: int) -> None:
        if key in DEFAULT_RAMP:
            self._ramp = self._clean(DEFAULT_RAMP, {**self._ramp, key: value})
            self.changed.emit()
