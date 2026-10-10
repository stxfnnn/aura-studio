"""Software macros: watch keys and mouse buttons, play key sequences.

Triggers are read from the devices' HID input reports (hidraw), which needs no
permissions beyond the ones lighting already uses. Playback goes through a
virtual keyboard/mouse created with uinput. The trigger itself is not hidden
from the system: that would require grabbing the event device.

Keys are identified by their Linux input codes (KEY_* / BTN_*) throughout.
Key presses are only held in memory to match triggers; they are never logged.
"""
from __future__ import annotations

import fcntl
import json
import os
import select
import struct
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import hid
from .devices import ASUS_VID, _descriptor_summary
from .i18n import tr

MACRO_PATH = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "aura-studio" / "macros.json"

# ------------------------------------------------------------------ key tables

BTN_LEFT, BTN_RIGHT, BTN_MIDDLE, BTN_SIDE, BTN_EXTRA = 0x110, 0x111, 0x112, 0x113, 0x114
MOUSE_BUTTONS = (BTN_LEFT, BTN_RIGHT, BTN_MIDDLE, BTN_SIDE, BTN_EXTRA)
LEFT_SHIFT, RIGHT_ALT = 42, 100

# HID keyboard usage -> Linux key code.
_LETTERS = (30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, 49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44)
USAGE_TO_KEY: dict[int, int] = {0x04 + index: code for index, code in enumerate(_LETTERS)}
USAGE_TO_KEY.update({0x1E + index: 2 + index for index in range(10)})
USAGE_TO_KEY.update({
    0x28: 28, 0x29: 1, 0x2A: 14, 0x2B: 15, 0x2C: 57, 0x2D: 12, 0x2E: 13, 0x2F: 26, 0x30: 27, 0x31: 43, 0x32: 43,
    0x33: 39, 0x34: 40, 0x35: 41, 0x36: 51, 0x37: 52, 0x38: 53, 0x39: 58, 0x44: 87, 0x45: 88, 0x46: 99, 0x47: 70,
    0x48: 119, 0x49: 110, 0x4A: 102, 0x4B: 104, 0x4C: 111, 0x4D: 107, 0x4E: 109, 0x4F: 106, 0x50: 105, 0x51: 108,
    0x52: 103, 0x53: 69, 0x54: 98, 0x55: 55, 0x56: 74, 0x57: 78, 0x58: 96, 0x62: 82, 0x63: 83, 0x64: 86, 0x65: 127,
    0xE0: 29, 0xE1: 42, 0xE2: 56, 0xE3: 125, 0xE4: 97, 0xE5: 54, 0xE6: 100, 0xE7: 126,
})
USAGE_TO_KEY.update({0x3A + index: 59 + index for index in range(10)})                    # F1..F10
USAGE_TO_KEY.update({0x59 + index: code for index, code in enumerate((79, 80, 81, 75, 76, 77, 71, 72, 73))})
USAGE_TO_KEY.update({0x68 + index: 183 + index for index in range(12)})                   # F13..F24

MEDIA_KEYS = {113: "Stumm", 114: "Leiser", 115: "Lauter", 164: "Wiedergabe/Pause", 163: "Nächster Titel",
              165: "Vorheriger Titel"}

_NAMES: dict[int, str] = {
    1: "Esc", 14: "⌫", 15: "Tab", 28: "Enter", 57: "Leertaste", 58: "Caps Lock", 29: "Strg", 97: "Strg rechts",
    42: "Umschalt", 54: "Umschalt rechts", 56: "Alt", 100: "AltGr", 125: "Super", 126: "Super rechts", 99: "Druck",
    70: "Rollen", 119: "Pause", 110: "Einfg", 111: "Entf", 102: "Pos1", 107: "Ende", 104: "Bild↑", 109: "Bild↓",
    103: "↑", 108: "↓", 105: "←", 106: "→", 69: "Num", 127: "Menü", 86: "<", 12: "ß / -", 13: "´ / =", 26: "Ü / [",
    27: "+ / ]", 43: "# / \\", 39: "Ö / ;", 40: "Ä / '", 41: "^ / `", 51: ",", 52: ".", 53: "- / /", 98: "Num /",
    55: "Num *", 74: "Num -", 78: "Num +", 96: "Num Enter", 82: "Num 0", 83: "Num ,",
    BTN_LEFT: "Linke Maustaste", BTN_RIGHT: "Rechte Maustaste", BTN_MIDDLE: "Mittlere Maustaste",
    BTN_SIDE: "Seitentaste hinten", BTN_EXTRA: "Seitentaste vorn",
}
_NAMES.update({code: letter for code, letter in zip(_LETTERS, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
_NAMES.update({2 + index: str((index + 1) % 10) for index in range(10)})
_NAMES.update({59 + index: f"F{index + 1}" for index in range(10)})
_NAMES.update({87: "F11", 88: "F12"})
_NAMES.update({183 + index: f"F{13 + index}" for index in range(12)})
_NAMES.update({code: f"Num {digit}" for code, digit in zip((79, 80, 81, 75, 76, 77, 71, 72, 73), "123456789")})
_NAMES.update(MEDIA_KEYS)
_MODIFIERS = (29, 97, 42, 54, 56, 100, 125, 126)


_layout = "de"   # set by the controller; decides how the Y/Z keys are labelled


def key_name(code: int) -> str:
    if _layout == "de" and code in (21, 44):
        return "Z" if code == 21 else "Y"
    name = _NAMES.get(code)
    return tr(name) if name else tr("Taste {code}").format(code=code)


def combo_name(codes: list[int]) -> str:
    ordered = sorted(codes, key=lambda code: (code not in _MODIFIERS, code))
    return " + ".join(key_name(code) for code in ordered)


# Characters for the "type text" step: (key code, shift, AltGr) per keyboard layout.
def _text_map(layout: str) -> dict[str, tuple[int, bool, bool]]:
    letters = dict(zip("abcdefghijklmnopqrstuvwxyz", _LETTERS))
    if layout == "de":
        letters["y"], letters["z"] = letters["z"], letters["y"]
    table: dict[str, tuple[int, bool, bool]] = {" ": (57, False, False), "\n": (28, False, False), "\t": (15, False, False)}
    for letter, code in letters.items():
        table[letter] = (code, False, False)
        table[letter.upper()] = (code, True, False)
    for index, digit in enumerate("1234567890"):
        table[digit] = (2 + index, False, False)
    if layout == "de":
        plain = {"ß": 12, "´": 13, "ü": 26, "+": 27, "#": 43, "ö": 39, "ä": 40, "^": 41, ",": 51, ".": 52, "-": 53, "<": 86}
        shifted = {"!": 2, '"': 3, "§": 4, "$": 5, "%": 6, "&": 7, "/": 8, "(": 9, ")": 10, "=": 11, "?": 12, "`": 13,
                   "Ü": 26, "*": 27, "'": 43, "Ö": 39, "Ä": 40, "°": 41, ";": 51, ":": 52, "_": 53, ">": 86}
        altgr = {"@": 16, "€": 18, "{": 8, "[": 9, "]": 10, "}": 11, "\\": 12, "~": 27, "|": 86}
    else:
        plain = {"-": 12, "=": 13, "[": 26, "]": 27, "\\": 43, ";": 39, "'": 40, "`": 41, ",": 51, ".": 52, "/": 53}
        shifted = {"!": 2, "@": 3, "#": 4, "$": 5, "%": 6, "^": 7, "&": 8, "*": 9, "(": 10, ")": 11, "_": 12, "+": 13,
                   "{": 26, "}": 27, "|": 43, ":": 39, '"': 40, "~": 41, "<": 51, ">": 52, "?": 53}
        altgr = {}
    table.update({char: (code, False, False) for char, code in plain.items()})
    table.update({char: (code, True, False) for char, code in shifted.items()})
    table.update({char: (code, False, True) for char, code in altgr.items()})
    return table


# ---------------------------------------------------------------------- uinput

class VirtualInput:
    """A virtual keyboard + mouse that plays the macro steps."""

    EV_SYN, EV_KEY, EV_REL = 0x00, 0x01, 0x02
    UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_RELBIT = 0x40045564, 0x40045565, 0x40045566
    UI_DEV_CREATE, UI_DEV_DESTROY = 0x5501, 0x5502

    def __init__(self) -> None:
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_CLOEXEC)
        try:
            fcntl.ioctl(self.fd, self.UI_SET_EVBIT, self.EV_KEY)
            # Relative axes make the desktop accept the device as a pointer, so button steps work.
            fcntl.ioctl(self.fd, self.UI_SET_EVBIT, self.EV_REL)
            for axis in (0x00, 0x01, 0x08):
                fcntl.ioctl(self.fd, self.UI_SET_RELBIT, axis)
            for code in sorted(set(USAGE_TO_KEY.values()) | set(MEDIA_KEYS) | set(MOUSE_BUTTONS)):
                fcntl.ioctl(self.fd, self.UI_SET_KEYBIT, code)
            # struct uinput_user_dev: name[80], input_id (bus, vendor, product, version), ff_effects_max, absinfo[4 * 64]
            os.write(self.fd, struct.pack("80sHHHHi", b"Aura Studio Macros", 0x06, 0x1209, 0xA5A5, 1, 0) + bytes(4 * 64 * 4))
            fcntl.ioctl(self.fd, self.UI_DEV_CREATE)
        except OSError:
            os.close(self.fd)
            raise
        self._lock = threading.Lock()
        self._down: dict[int, int] = {}   # key -> how many running macros hold it

    def _emit(self, kind: int, code: int, value: int) -> None:
        os.write(self.fd, struct.pack("llHHi", 0, 0, kind, code, value))

    def key(self, code: int, down: bool) -> None:
        with self._lock:
            held = self._down.get(code, 0)
            if down:
                self._down[code] = held + 1
                if held:
                    return
            else:
                if not held:
                    return
                if held > 1:
                    self._down[code] = held - 1
                    return
                del self._down[code]
            self._emit(self.EV_KEY, code, 1 if down else 0)
            self._emit(self.EV_SYN, 0, 0)

    def release_all(self) -> None:
        with self._lock:
            for code in list(self._down):
                self._emit(self.EV_KEY, code, 0)
            if self._down:
                self._emit(self.EV_SYN, 0, 0)
            self._down.clear()

    def close(self) -> None:
        self.release_all()
        try:
            fcntl.ioctl(self.fd, self.UI_DEV_DESTROY)
        finally:
            os.close(self.fd)


# -------------------------------------------------------------------- watching

def input_nodes() -> list[tuple[str, str]]:
    """hidraw nodes that report key or button state: [(path, "keyboard" | "mouse")]."""
    nodes = []
    for node in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
        try:
            fields = dict(line.split("=", 1) for line in (node / "device" / "uevent").read_text(errors="ignore").splitlines() if "=" in line)
            if int(fields.get("HID_ID", "0:0:0").split(":")[1], 16) != ASUS_VID:
                continue
            descriptor = (node / "device" / "report_descriptor").read_bytes()
        except (OSError, ValueError, IndexError):
            continue
        pages, report_ids = _descriptor_summary(node)
        pages = pages.split(",")
        if "0x0007" in pages and "0x0001" in pages and "1" in report_ids.split(","):
            nodes.append((f"/dev/{node.name}", "keyboard"))
        elif "0x0009" in pages and report_ids == "none" and b"\x75\x10\x95\x02\x81\x06\x05\x09" in descriptor:
            # Relative mouse with 16-bit X/Y followed by the button bits.
            nodes.append((f"/dev/{node.name}", "mouse"))
    return nodes


class Watcher(threading.Thread):
    """Tracks which keys and buttons are down and reports every change."""

    def __init__(self, on_change: Callable[[frozenset[int], int, bool], None]) -> None:
        super().__init__(name="AuraMacroWatcher", daemon=True)
        self._on_change = on_change
        self._stop_read, self._stop_write = os.pipe()
        self.nodes = input_nodes()

    def stop(self) -> None:
        os.write(self._stop_write, b"x")
        if self.is_alive():
            self.join(timeout=1.0)

    @staticmethod
    def _keyboard(report: bytes, state: dict[int, set[int]]) -> None:
        if report[:1] == b"\x01" and len(report) >= 9:       # modifiers + up to six keys
            usages = {0xE0 + bit for bit in range(8) if report[1] >> bit & 1} | {usage for usage in report[3:9] if usage > 3}
            state[1] = {USAGE_TO_KEY[usage] for usage in usages if usage in USAGE_TO_KEY}
        elif report[:1] == b"\x02":                          # one bit per usage
            state[2] = {USAGE_TO_KEY[usage] for usage in range(min(0x98, (len(report) - 1) * 8))
                        if report[1 + usage // 8] >> usage % 8 & 1 and usage in USAGE_TO_KEY}

    def run(self) -> None:
        files: dict[int, tuple[str, dict[int, set[int]]]] = {}
        for path, kind in self.nodes:
            try:
                files[os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK)] = (kind, {})
            except OSError:
                hid.app_logger().warning("Macro watcher cannot open %s", path)
        pressed: frozenset[int] = frozenset()
        try:
            while files:
                ready, _, _ = select.select([*files, self._stop_read], [], [])
                if self._stop_read in ready:
                    break
                for fd in ready:
                    kind, state = files[fd]
                    try:
                        report = os.read(fd, 64)
                    except BlockingIOError:
                        continue
                    except OSError:
                        os.close(fd)
                        del files[fd]
                        continue
                    if kind == "keyboard":
                        self._keyboard(report, state)
                    elif len(report) >= 5:
                        state[0] = {button for bit, button in enumerate(MOUSE_BUTTONS) if report[4] >> bit & 1}
                now = frozenset().union(*(codes for _, state in files.values() for codes in state.values()))
                for code in now - pressed:
                    self._on_change(now, code, True)
                for code in pressed - now:
                    self._on_change(now, code, False)
                pressed = now
        finally:
            for fd in files:
                os.close(fd)
            os.close(self._stop_read)
            os.close(self._stop_write)


# ---------------------------------------------------------------------- engine

MODES = ("once", "hold", "toggle")
STEP_TYPES = ("key", "text", "delay")
ACTIONS = ("tap", "down", "up")


def clean_macro(raw: Any) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    steps = []
    for step in raw.get("steps", []) if isinstance(raw.get("steps"), list) else []:
        if not isinstance(step, dict) or step.get("type") not in STEP_TYPES:
            continue
        if step["type"] == "key":
            steps.append({"type": "key", "code": int(step.get("code", 0)),
                          "action": step.get("action") if step.get("action") in ACTIONS else "tap"})
        elif step["type"] == "text":
            steps.append({"type": "text", "text": str(step.get("text", ""))[:500]})
        else:
            steps.append({"type": "delay", "ms": max(1, min(60000, int(step.get("ms", 100))))})
    trigger = [int(code) for code in raw.get("trigger", []) if isinstance(code, int)][:4]
    return {"id": str(raw.get("id") or uuid.uuid4().hex[:8]), "name": str(raw.get("name", ""))[:40],
            "enabled": bool(raw.get("enabled", True)), "trigger": trigger,
            "mode": raw.get("mode") if raw.get("mode") in MODES else "once", "steps": steps[:200]}


class Player(threading.Thread):
    def __init__(self, macro: dict[str, Any], output: VirtualInput, text_map: dict[str, tuple[int, bool, bool]],
                 loop: bool, delay: float = 0.0) -> None:
        super().__init__(name="AuraMacro", daemon=True)
        self.macro, self.output, self.text_map, self.loop, self.delay = macro, output, text_map, loop, delay
        self.cancel = threading.Event()
        self._held: list[int] = []

    def _key(self, code: int, down: bool) -> None:
        self.output.key(code, down)
        if down:
            self._held.append(code)
        elif code in self._held:
            self._held.remove(code)

    def _tap(self, code: int, shift: bool = False, altgr: bool = False) -> None:
        for modifier, wanted in ((LEFT_SHIFT, shift), (RIGHT_ALT, altgr)):
            if wanted:
                self._key(modifier, True)
        self._key(code, True)
        self.cancel.wait(0.012)
        self._key(code, False)
        for modifier, wanted in ((RIGHT_ALT, altgr), (LEFT_SHIFT, shift)):
            if wanted:
                self._key(modifier, False)
        self.cancel.wait(0.012)

    def run(self) -> None:
        try:
            if self.cancel.wait(self.delay):
                return
            while not self.cancel.is_set():
                for step in self.macro["steps"]:
                    if self.cancel.is_set():
                        break
                    if step["type"] == "delay":
                        self.cancel.wait(step["ms"] / 1000)
                    elif step["type"] == "text":
                        for char in step["text"]:
                            if self.cancel.is_set():
                                break
                            if char in self.text_map:
                                self._tap(*self.text_map[char])
                    elif step["action"] == "tap":
                        self._tap(step["code"])
                    else:
                        self._key(step["code"], step["action"] == "down")
                if not self.loop:
                    break
                self.cancel.wait(0.02)  # never spin without a pause
        except OSError:
            hid.app_logger().exception("Macro playback failed name=%r", self.macro["name"])
        finally:
            for code in list(self._held):  # nothing stays pressed when a macro ends or is stopped
                self.output.key(code, False)


class MacroController(QObject):
    changed = Signal()
    stateChanged = Signal()
    notify = Signal(str, str)
    _captured = Signal(list)
    _recorded = Signal(int, bool, float)

    def __init__(self) -> None:
        super().__init__()
        self.logger = hid.app_logger()
        self._macros: list[dict[str, Any]] = []
        self._enabled = True
        self._layout = "de"
        self._output: VirtualInput | None = None
        self._watcher: Watcher | None = None
        self._problem = ""
        self._players: dict[str, Player] = {}
        self._capture = ""                 # "" | "trigger:<id>" | "step:<id>:<index>"
        self._capture_keys: set[int] = set()
        self._recording = ""
        self._record_last = 0.0
        self._lock = threading.Lock()
        self._captured.connect(self._finish_capture)
        self._recorded.connect(self._add_recorded)
        self._load()

    # ------------------------------------------------------------ persistence

    def _load(self) -> None:
        try:
            data = json.loads(MACRO_PATH.read_text(encoding="utf-8"))
            self._macros = [clean_macro(entry) for entry in data] if isinstance(data, list) else []
        except (OSError, ValueError, TypeError):
            self._macros = []

    def _save(self) -> None:
        try:
            MACRO_PATH.parent.mkdir(parents=True, exist_ok=True)
            temporary = MACRO_PATH.with_suffix(".tmp")
            temporary.write_text(json.dumps(self._macros, indent=2), encoding="utf-8")
            temporary.replace(MACRO_PATH)
        except OSError:
            self.logger.exception("Could not save macros")

    def _touch(self) -> None:
        self._save()
        self.changed.emit()

    # ----------------------------------------------------------------- engine

    def start(self, enabled: bool, layout: str) -> None:
        """(Re)start watching the input devices; called after every device scan."""
        global _layout
        self.stop()
        self._enabled, self._layout = enabled, layout
        _layout = layout
        self._problem = ""
        try:
            self._output = VirtualInput()
        except OSError as exc:
            self._problem = tr("Kein Zugriff auf /dev/uinput ({error}). Makros können nicht abgespielt werden.").format(error=exc)
            self.logger.warning("uinput unavailable: %s", exc)
        self._watcher = Watcher(self._on_input)
        if not self._watcher.nodes and not self._problem:
            self._problem = tr("Kein Gerät gefunden, dessen Tasten als Auslöser gelesen werden können.")
        self._watcher.start()
        self.stateChanged.emit()

    def set_options(self, enabled: bool, layout: str) -> None:
        global _layout
        self._enabled, self._layout = enabled, layout
        _layout = layout
        if not enabled:
            self._stop_players()
        self.changed.emit()

    def _stop_players(self) -> None:
        with self._lock:
            players, self._players = list(self._players.values()), {}
        for player in players:
            player.cancel.set()
        for player in players:
            player.join(timeout=1.0)

    def stop(self) -> None:
        self._stop_players()
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        if self._output:
            self._output.close()
            self._output = None

    def _on_input(self, pressed: frozenset[int], code: int, down: bool) -> None:
        """Runs on the watcher thread for every key or button change."""
        if self._capture:
            if down:
                self._capture_keys.add(code)
            elif self._capture_keys:
                keys, self._capture_keys = sorted(self._capture_keys), set()
                self._captured.emit(keys)
            return
        if self._recording:
            self._recorded.emit(code, down, time.monotonic())
            return
        if not self._enabled or not self._output:
            return
        for macro in self._macros:
            trigger = macro["trigger"]
            if not macro["enabled"] or not trigger or not macro["steps"] or code not in trigger:
                continue
            with self._lock:
                running = self._players.get(macro["id"])
                alive = running is not None and running.is_alive()
                if down and all(key in pressed for key in trigger):
                    if macro["mode"] == "toggle" and alive:
                        running.cancel.set()
                        del self._players[macro["id"]]
                    elif not alive:
                        player = Player(macro, self._output, _text_map(self._layout), loop=macro["mode"] != "once")
                        self._players[macro["id"]] = player
                        player.start()
                elif not down and macro["mode"] == "hold" and alive:
                    running.cancel.set()

    # -------------------------------------------------------------------- QML

    @Property(str, notify=stateChanged)
    def problem(self) -> str:
        return self._problem

    @Property(str, notify=stateChanged)
    def capturing(self) -> str:
        return self._capture

    @Property(str, notify=stateChanged)
    def recording(self) -> str:
        return self._recording

    @Property("QVariantList", notify=changed)
    def macros(self) -> list[dict[str, Any]]:
        def view(step: dict[str, Any]) -> dict[str, Any]:
            return {**step, "label": key_name(step["code"])} if step["type"] == "key" else dict(step)
        return [{**macro, "triggerLabel": combo_name(macro["trigger"]) if macro["trigger"] else "",
                 "steps": [view(step) for step in macro["steps"]]} for macro in self._macros]

    @Property("QVariantList", notify=changed)
    def mediaKeys(self) -> list[dict[str, Any]]:
        return [{"code": code, "label": tr(label)} for code, label in MEDIA_KEYS.items()]

    def retranslate(self) -> None:
        self.changed.emit()

    def _find(self, macro_id: str) -> dict[str, Any] | None:
        return next((macro for macro in self._macros if macro["id"] == macro_id), None)

    @Slot(result=str)
    def add(self) -> str:
        macro = clean_macro({"name": tr("Neues Makro")})
        self._macros.append(macro)
        self._touch()
        return macro["id"]

    @Slot(str)
    def remove(self, macro_id: str) -> None:
        self._macros = [macro for macro in self._macros if macro["id"] != macro_id]
        self._touch()

    @Slot(str, str, "QVariant")
    def update(self, macro_id: str, key: str, value: Any) -> None:
        macro = self._find(macro_id)
        if not macro:
            return
        if key == "name":
            macro["name"] = str(value)[:40]
        elif key == "enabled":
            macro["enabled"] = bool(value)
        elif key == "mode" and value in MODES:
            macro["mode"] = value
        elif key == "trigger" and not value:
            macro["trigger"] = []
        self._touch()

    @Slot(str, str, int)
    def addStep(self, macro_id: str, kind: str, code: int = 0) -> None:
        macro = self._find(macro_id)
        if not macro or kind not in STEP_TYPES or len(macro["steps"]) >= 200:
            return
        macro["steps"].append({"key": {"type": "key", "code": code or 30, "action": "tap"},
                               "text": {"type": "text", "text": ""},
                               "delay": {"type": "delay", "ms": 100}}[kind])
        self._touch()

    @Slot(str, int, str, "QVariant")
    def updateStep(self, macro_id: str, index: int, key: str, value: Any) -> None:
        macro = self._find(macro_id)
        if not macro or not 0 <= index < len(macro["steps"]):
            return
        step = macro["steps"][index]
        if step["type"] == "key" and key == "action" and value in ACTIONS:
            step["action"] = value
        elif step["type"] == "text" and key == "text":
            step["text"] = str(value)[:500]
        elif step["type"] == "delay" and key == "ms":
            try:
                step["ms"] = max(1, min(60000, int(value)))
            except (TypeError, ValueError):
                return
        self._touch()

    @Slot(str, int)
    def removeStep(self, macro_id: str, index: int) -> None:
        macro = self._find(macro_id)
        if macro and 0 <= index < len(macro["steps"]):
            del macro["steps"][index]
            self._touch()

    @Slot(str, int, int)
    def moveStep(self, macro_id: str, index: int, delta: int) -> None:
        macro = self._find(macro_id)
        if macro and 0 <= index < len(macro["steps"]) and 0 <= index + delta < len(macro["steps"]):
            steps = macro["steps"]
            steps[index], steps[index + delta] = steps[index + delta], steps[index]
            self._touch()

    @Slot(str)
    def clearSteps(self, macro_id: str) -> None:
        macro = self._find(macro_id)
        if macro:
            macro["steps"] = []
            self._touch()

    # Capturing: the next key (or key combination) pressed on a device is taken over.
    @Slot(str)
    def capture(self, target: str) -> None:
        self._recording = ""
        self._capture_keys = set()
        self._capture = "" if target == self._capture else target
        self.stateChanged.emit()

    @Slot(list)
    def _finish_capture(self, keys: list[int]) -> None:
        target, self._capture = self._capture, ""
        parts = target.split(":")
        macro = self._find(parts[1]) if len(parts) > 1 else None
        if macro and parts[0] == "trigger":
            macro["trigger"] = keys[:4]
        elif macro and parts[0] == "step" and int(parts[2]) < len(macro["steps"]):
            step = macro["steps"][int(parts[2])]
            if step["type"] == "key":
                # For a single step the last key of a combination is the one meant.
                step["code"] = next((key for key in keys if key not in _MODIFIERS), keys[0])
        self.stateChanged.emit()
        self._touch()

    # Recording: every key change becomes a step, with the pauses in between.
    @Slot(str)
    def record(self, macro_id: str) -> None:
        self._capture = ""
        self._recording = "" if macro_id == self._recording else macro_id
        self._record_last = 0.0
        self.stateChanged.emit()

    @Slot(int, bool, float)
    def _add_recorded(self, code: int, down: bool, moment: float) -> None:
        macro = self._find(self._recording)
        if not macro or len(macro["steps"]) >= 198:
            return
        if self._record_last:
            pause = round((moment - self._record_last) * 1000)
            if pause >= 8:
                macro["steps"].append({"type": "delay", "ms": min(pause, 60000)})
        self._record_last = moment
        macro["steps"].append({"type": "key", "code": code, "action": "down" if down else "up"})
        self._touch()

    @Slot(str)
    def play(self, macro_id: str) -> None:
        """Test run after three seconds, so there is time to click into another window."""
        macro = self._find(macro_id)
        if not macro or not macro["steps"]:
            return
        if not self._output:
            self.notify.emit(self._problem or tr("Makros können gerade nicht abgespielt werden."), "error")
            return
        player = Player(macro, self._output, _text_map(self._layout), loop=False, delay=3.0)
        with self._lock:
            old = self._players.get(macro_id)
            if old:
                old.cancel.set()
            self._players[macro_id] = player
        player.start()
        self.notify.emit(tr("Makro startet in 3 Sekunden – jetzt ins Zielfenster klicken"), "info")
