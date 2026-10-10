"""Bridge between the QML interface, saved state and the device runners."""
from __future__ import annotations

import colorsys
import copy
import json
import os
import random
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from . import devices as discovery, effects, hid, i18n, layout
from .engine import Runner
from .i18n import tr
from .oled_controller import OledController

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "aura-studio"
PROFILE_DIR = CONFIG_DIR / "profiles"
STATE_PATH = CONFIG_DIR / "state.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "sounds": True,      # interface sounds
    "volume": 55,        # 0..100
    "linked": False,     # edit all devices together
    "layout": "de",      # key legends / ISO vs ANSI
    "fps": 24,           # frames per second sent to the hardware
    "fallback": True,    # hand the keyboard back to a firmware effect on quit
    "tray": False,       # keep running in the system tray when the window closes
    "oledPauseAll": False,  # pause every device's lighting during an OLED transfer, not just the keyboard's
    "theme": "dark",     # "dark" | "light" | "system"
    "accentMode": "effect",  # "effect": follow the running effect, "custom": use accentColor
    "accentColor": "#9b7dff",
    "language": "system",  # "system" | "de" | "en"
}
CHOICES = {"theme": ("dark", "light", "system"), "accentMode": ("effect", "custom"),
           "language": ("system", *i18n.LANGUAGES)}
BATTERY_SECONDS = 120
FPS_CHOICES = (15, 24, 30)


class DeviceService(QObject):
    devicesChanged = Signal()
    configChanged = Signal()
    settingsChanged = Signal()
    profilesChanged = Signal()
    selectedChanged = Signal()
    activeProfileChanged = Signal()
    overviewChanged = Signal()
    languageChanged = Signal()
    statusChanged = Signal()
    logsChanged = Signal(str)
    frameReady = Signal(list)
    notify = Signal(str, str)  # text, kind: "info" | "success" | "error"
    _runnerError = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.logger = hid.app_logger()
        self.logger.info("Aura Studio started; log=%s", hid.LOG_PATH)
        self._devices: list[discovery.Device] = []
        self._runners: dict[str, Runner] = {}
        self._selected = ""
        self._status = ""
        self._profiles: list[dict[str, Any]] = []
        self._profile_configs: dict[str, dict[str, Any]] = {}
        self._active_profile = ""
        self._catalog: list[dict[str, Any]] = []
        self._settings = dict(DEFAULT_SETTINGS)
        self._store: dict[str, dict[str, Any]] = {}
        self._wanted_key = ""
        self._saved_oled: dict[str, Any] = {}
        self._load_state()
        i18n.set_language(self._settings["language"])
        self._catalog = effects.catalog()
        self.oled = OledController(self._saved_oled)
        self.oled.notify.connect(self.notify)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self._save_state)
        self._runnerError.connect(self._on_runner_error)
        self.oled.changed.connect(self._save_timer.start)
        self.oled.other_runners = lambda: list(self._runners.values()) if self._settings["oledPauseAll"] else []
        self._battery: dict[str, int] = {}
        self._thumbs: dict[str, list[str]] = {}
        self._battery_timer = QTimer(self)
        self._battery_timer.setInterval(BATTERY_SECONDS * 1000)
        self._battery_timer.timeout.connect(self._read_batteries)
        self._battery_timer.start()
        self.configChanged.connect(self.overviewChanged)
        self.devicesChanged.connect(self.overviewChanged)

    # ------------------------------------------------------------ persistence

    def _load_state(self) -> None:
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        for key, default in DEFAULT_SETTINGS.items():
            value = data.get("settings", {}).get(key, default)
            if type(value) is type(default):
                self._settings[key] = value
        if self._settings["layout"] not in layout.LAYOUTS:
            self._settings["layout"] = "de"
        if self._settings["fps"] not in FPS_CHOICES:
            self._settings["fps"] = DEFAULT_SETTINGS["fps"]
        for key, allowed in CHOICES.items():
            if self._settings[key] not in allowed:
                self._settings[key] = DEFAULT_SETTINGS[key]
        self._settings["accentColor"] = effects.rgb_to_hex(effects.hex_to_rgb(self._settings["accentColor"]))
        for key, entry in (data.get("devices") or {}).items():
            if isinstance(entry, dict):
                self._store[key] = self._clean_entry(entry)
        self._wanted_key = str(data.get("selected", ""))
        if isinstance(data.get("oled"), dict):
            self._saved_oled = data["oled"]

    def _save_state(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            selected = self._device(self._selected)
            payload = {"settings": self._settings, "devices": self._store,
                       "selected": selected.key if selected else self._wanted_key, "oled": self.oled.draft}
            temporary = STATE_PATH.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temporary.replace(STATE_PATH)
        except OSError:
            self.logger.exception("Could not save state")

    @staticmethod
    def _clean_entry(raw: dict[str, Any]) -> dict[str, Any]:
        effect = raw.get("effect") if raw.get("effect") in effects.EFFECTS else effects.DEFAULT_EFFECT
        try:
            brightness = max(0, min(100, int(raw.get("brightness", 85))))
        except (TypeError, ValueError):
            brightness = 85
        per = {name: effects.clean_settings(name, settings)
               for name, settings in (raw.get("per") or {}).items() if name in effects.EFFECTS}
        per.setdefault(effect, effects.default_settings(effect))
        return {"effect": effect, "enabled": bool(raw.get("enabled", True)), "brightness": brightness, "per": per}

    def _entry(self, key: str) -> dict[str, Any]:
        if key not in self._store:
            self._store[key] = self._clean_entry({})
        return self._store[key]

    @staticmethod
    def _flat(entry: dict[str, Any]) -> dict[str, Any]:
        return {"effect": entry["effect"], "enabled": entry["enabled"], "brightness": entry["brightness"],
                **copy.deepcopy(entry["per"][entry["effect"]])}

    # --------------------------------------------------------------- devices

    def _device(self, device_id: str) -> discovery.Device | None:
        return next((device for device in self._devices if device.id == device_id), None)

    def _keys(self) -> list[layout.Key]:
        return layout.azoth_keys(self._settings["layout"])

    def _field(self, device: discovery.Device) -> effects.Field:
        return effects.Field.keyboard(self._keys()) if device.kind == "keyboard" else effects.Field.single()

    @Slot()
    def scan(self) -> None:
        current = self._device(self._selected)
        wanted = current.key if current else self._wanted_key
        self._stop_runners(fallback=False)
        mode = os.environ.get("AURA_STUDIO_DEMO", "")
        found = [] if mode == "only" else discovery.scan()
        if mode or not any(device.controllable for device in found):
            found.insert(0, discovery.demo_keyboard())
        if mode:  # development aid: AURA_STUDIO_DEMO=1 adds simulated devices, "only" skips hardware
            found.insert(1, discovery.demo_mouse())
        self._devices = found
        controllable = [device for device in found if device.controllable]
        for device in controllable:
            runner = Runner(device, self._field(device), self._flat(self._entry(device.key)), self._settings["fps"],
                            self._emit_frame, self._runnerError.emit)
            self._runners[device.id] = runner
            runner.start()
        chosen = next((device for device in controllable if device.key == wanted), controllable[0])
        with_display = next((device for device in controllable if device.oled_path), None)
        self.oled.attach(with_display, self._runners.get(with_display.id) if with_display else None)
        self._selected = ""
        self._battery = {}
        self._read_batteries(announce=False)
        self.devicesChanged.emit()
        self.selectDevice(chosen.id)
        real = [device for device in controllable if not device.virtual]
        if not real:
            self._status = tr("Kein steuerbares Gerät – Vorschau-Modus")
        elif len(real) == 1:
            self._status = tr("{name} verbunden").format(name=real[0].name)
        else:
            self._status = tr("{count} Geräte verbunden").format(count=len(real))
        self.statusChanged.emit()

    def _stop_runners(self, fallback: bool) -> None:
        for runner in self._runners.values():
            runner.stop(fallback)
        self._runners = {}

    def _emit_frame(self, device_id: str, frame: list[str]) -> None:
        if device_id == self._selected:
            self.frameReady.emit(frame)

    @Slot(str, str)
    def _on_runner_error(self, device_id: str, message: str) -> None:
        self.notify.emit(message, "error")

    @Slot()
    def shutdown(self) -> None:
        self._save_timer.stop()
        self._save_state()
        self._stop_runners(fallback=self._settings["fallback"])

    def _device_view(self, device: discovery.Device) -> dict[str, Any]:
        view = asdict(device)
        view["keys"] = ([{"id": key.id, "label": key.label, "x": key.x, "y": key.y, "w": key.w, "h": key.h}
                         for key in self._keys()] if device.kind == "keyboard" else [])
        return view

    @Property("QVariantList", notify=devicesChanged)
    def devices(self) -> list[dict[str, Any]]:
        return [self._device_view(device) for device in self._devices]

    @Property(str, notify=selectedChanged)
    def selected(self) -> str:
        return self._selected

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property("QVariantList", notify=languageChanged)
    def catalog(self) -> list[dict[str, Any]]:
        return self._catalog

    @Property("QVariantList", notify=languageChanged)
    def groups(self) -> list[dict[str, Any]]:
        return effects.groups()

    @Property("QVariantMap", notify=languageChanged)
    def translations(self) -> dict[str, str]:
        """German source text -> active language, for the QML side (empty for German)."""
        return i18n.table()

    @Property(float, constant=True)
    def layoutWidth(self) -> float:
        return layout.WIDTH

    @Property(float, constant=True)
    def layoutHeight(self) -> float:
        return layout.HEIGHT

    @Property("QVariantList", notify=languageChanged)
    def keyGroups(self) -> list[dict[str, Any]]:
        keys = self._keys()

        def ids(labels: set[str]) -> list[int]:
            return [key.id for key in keys if key.label in labels]

        letters = [key.id for key in keys if len(key.label) == 1 and key.label.isalpha()]
        return [
            {"name": tr("Alle"), "ids": [key.id for key in keys]},
            {"name": "WASD", "ids": ids({"W", "A", "S", "D"})},
            {"name": tr("Pfeile"), "ids": ids({"↑", "←", "↓", "→"})},
            {"name": tr("Buchstaben"), "ids": letters},
            {"name": tr("Zahlen"), "ids": ids(set("1234567890"))},
            {"name": tr("F-Tasten"), "ids": [key.id for key in keys if re.fullmatch(r"F\d+", key.label)]},
            {"name": tr("Sondertasten"), "ids": [key.id for key in keys
                                            if (len(key.label) > 1 and not re.fullmatch(r"F\d+", key.label))
                                            or key.label in {"", "⇧", "⏎", "⌫", "❖"}]},
        ]

    def _read_batteries(self, announce: bool = True) -> None:
        changed = False
        for device in self._devices:
            if device.oled_path and not device.virtual and not self.oled.busy:
                level = hid.query_battery(device.oled_path, device.oled_report)
                if level is not None and self._battery.get(device.id) != level:
                    self._battery[device.id] = level
                    changed = True
        if changed and announce:
            self.overviewChanged.emit()

    @Property("QVariantList", notify=overviewChanged)
    def overview(self) -> list[dict[str, Any]]:
        """One card per controllable device for the start page."""
        cards = []
        for device in self._devices:
            if not device.controllable:
                continue
            flat = self._flat(self._entry(device.key))
            signature = json.dumps(self._signature(flat), sort_keys=True)
            if signature not in self._thumbs:
                if len(self._thumbs) > 64:
                    self._thumbs.clear()
                self._thumbs[signature] = effects.thumbnail(flat["effect"], effects.clean_settings(flat["effect"], flat))
            cards.append({"id": device.id, "name": device.name, "kind": device.kind, "source": device.source,
                          "detail": device.detail, "virtual": device.virtual, "hasOled": bool(device.oled_path),
                          "effectName": tr(effects.EFFECTS[flat["effect"]]["name"]), "thumb": self._thumbs[signature],
                          "colors": flat.get("colors", []), "brightness": flat["brightness"],
                          "enabled": flat["enabled"], "battery": self._battery.get(device.id, -1),
                          "lamps": len(self._keys()) if device.kind == "keyboard" else 1})
        return cards

    @Slot(str, bool)
    def setDeviceEnabled(self, device_id: str, enabled: bool) -> None:
        """Power switch on the start page; works without selecting the device first."""
        device = self._device(device_id)
        if not device or not device.controllable:
            return
        linked = self._settings["linked"]
        for target in self._devices:
            if target.controllable and (linked or target.key == device.key):
                self._entry(target.key)["enabled"] = enabled
                if target.id in self._runners:
                    self._runners[target.id].configure(self._flat(self._entry(target.key)))
        self.configChanged.emit()
        self._save_timer.start()

    @Slot(str)
    def selectDevice(self, device_id: str) -> None:
        device = self._device(device_id)
        if not device or not device.controllable or device_id == self._selected:
            return
        self._selected = device_id
        for runner_id, runner in self._runners.items():
            runner.preview = runner_id == device_id
        self.selectedChanged.emit()
        self.configChanged.emit()
        self._update_active_profile()
        self._save_timer.start()

    # ---------------------------------------------------------------- config

    @Property("QVariantMap", notify=configChanged)
    def config(self) -> dict[str, Any]:
        device = self._device(self._selected)
        return self._flat(self._entry(device.key)) if device else {}

    def _targets(self) -> list[discovery.Device]:
        selected = self._device(self._selected)
        if not selected:
            return []
        if self._settings["linked"]:
            return [device for device in self._devices if device.controllable]
        return [selected]

    def _mutate(self, change) -> None:
        """Apply ``change(entry)`` to the selected (or all linked) devices and push it live."""
        touched: set[str] = set()
        for device in self._targets():
            if device.key not in touched:
                change(self._entry(device.key))
                touched.add(device.key)
        for device in self._devices:
            if device.key in touched and device.id in self._runners:
                self._runners[device.id].configure(self._flat(self._entry(device.key)))
        self.configChanged.emit()
        self._update_active_profile()
        self._save_timer.start()

    @Slot(str)
    def setEffect(self, effect_id: str) -> None:
        if effect_id not in effects.EFFECTS:
            return

        def change(entry: dict[str, Any]) -> None:
            entry["effect"] = effect_id
            entry["per"].setdefault(effect_id, effects.default_settings(effect_id))
        self._mutate(change)

    @Slot(str, int)
    def setParam(self, key: str, value: int) -> None:
        def change(entry: dict[str, Any]) -> None:
            if key == "brightness":
                entry["brightness"] = max(0, min(100, value))
            elif key in effects.PARAM_KEYS and key in entry["per"][entry["effect"]]:
                entry["per"][entry["effect"]][key] = max(0, min(359 if key == "angle" else 100, value))
        self._mutate(change)

    @Slot(bool)
    def setEnabled(self, enabled: bool) -> None:
        self._mutate(lambda entry: entry.update(enabled=enabled))

    @Slot(int, str)
    def setColor(self, index: int, color: str) -> None:
        clean = effects.rgb_to_hex(effects.hex_to_rgb(color))

        def change(entry: dict[str, Any]) -> None:
            colors = entry["per"][entry["effect"]]["colors"]
            if 0 <= index < len(colors):
                colors[index] = clean
        self._mutate(change)

    @Slot()
    def addColor(self) -> None:
        def change(entry: dict[str, Any]) -> None:
            colors = entry["per"][entry["effect"]]["colors"]
            if effects.EFFECTS[entry["effect"]].get("flex") and len(colors) < effects.MAX_COLORS:
                hue, saturation, value = colorsys.rgb_to_hsv(*effects.hex_to_rgb(colors[-1]))
                colors.append(effects.rgb_to_hex(colorsys.hsv_to_rgb((hue + 0.11) % 1, max(saturation, 0.6), max(value, 0.9))))
        self._mutate(change)

    @Slot(int)
    def removeColor(self, index: int) -> None:
        def change(entry: dict[str, Any]) -> None:
            definition = effects.EFFECTS[entry["effect"]]
            colors = entry["per"][entry["effect"]]["colors"]
            if definition.get("flex") and len(colors) > min(2, len(definition["colors"])) and 0 <= index < len(colors):
                del colors[index]
        self._mutate(change)

    @Slot()
    def shuffleColors(self) -> None:
        """Replace the palette with a random harmonious one."""
        base = random.random()
        spread = random.choice((0.07, 0.11, 0.17, 0.33))

        def change(entry: dict[str, Any]) -> None:
            colors = entry["per"][entry["effect"]]["colors"]
            for index in range(len(colors)):
                _, _, value = colorsys.rgb_to_hsv(*effects.hex_to_rgb(colors[index]))
                # Keep each slot's brightness role (dark sky, bright star …).
                colors[index] = effects.rgb_to_hex(colorsys.hsv_to_rgb(
                    (base + index * spread) % 1, random.uniform(0.7, 1.0) if value > 0.25 else 0.85, max(value, 0.12)))
        self._mutate(change)

    @Slot()
    def resetEffect(self) -> None:
        self._mutate(lambda entry: entry["per"].__setitem__(entry["effect"], effects.default_settings(entry["effect"])))

    @Slot("QVariantList", str)
    def paintKeys(self, led_ids: list[Any], color: str) -> None:
        """Colour individual keys of the "Eigene Tasten" effect; an empty colour erases."""
        clean = effects.rgb_to_hex(effects.hex_to_rgb(color)) if color else ""

        def change(entry: dict[str, Any]) -> None:
            keys = entry["per"][entry["effect"]].get("keys")
            if keys is None:
                return
            for led in led_ids:
                if clean:
                    keys[str(int(led))] = clean
                else:
                    keys.pop(str(int(led)), None)
        self._mutate(change)

    # --------------------------------------------------------------- settings

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self) -> dict[str, Any]:
        return dict(self._settings)

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value: Any) -> None:
        default = DEFAULT_SETTINGS.get(key)
        if default is None or self._settings.get(key) == value:
            return
        if isinstance(default, bool):
            value = bool(value)
        elif isinstance(default, int):
            value = int(value)
        else:
            value = str(value)
        if (key == "layout" and value not in layout.LAYOUTS) or (key == "fps" and value not in FPS_CHOICES):
            return
        if key in CHOICES and value not in CHOICES[key]:
            return
        if key == "accentColor":
            value = effects.rgb_to_hex(effects.hex_to_rgb(value))
        self._settings[key] = value
        self.settingsChanged.emit()
        self._save_timer.start()
        if key == "fps":
            for runner in self._runners.values():
                runner.fps = value
        elif key == "layout":
            self.scan()
            self.languageChanged.emit()  # key groups depend on the layout
        elif key == "language":
            i18n.set_language(value)
            self._catalog = effects.catalog()
            self.languageChanged.emit()
            self.oled.retranslate()
            self.loadProfiles()
            self.scan()  # device descriptions and the status line are written at scan time
        elif key == "linked" and value:
            selected = self._device(self._selected)
            if selected:
                source = copy.deepcopy(self._entry(selected.key))
                for device in self._devices:
                    if device.controllable and device.key != selected.key:
                        self._store[device.key] = copy.deepcopy(source)
                        self._runners[device.id].configure(self._flat(self._store[device.key]))

    # --------------------------------------------------------------- profiles

    @Property("QVariantList", notify=profilesChanged)
    def profiles(self) -> list[dict[str, Any]]:
        return self._profiles

    @staticmethod
    def _profile_config(data: dict[str, Any]) -> dict[str, Any] | None:
        config = data.get("config")
        if isinstance(config, dict) and config.get("effect") in effects.EFFECTS:
            return config
        legacy = effects.LEGACY_EFFECTS.get(str(data.get("effect")))
        if legacy:  # written by the single-colour version of the app
            config = {"effect": legacy, "brightness": data.get("brightness", 85), "speed": data.get("speed", 50)}
            if effects.EFFECTS[legacy]["colors"] and legacy in ("static", "breathing"):
                config["colors"] = [str(data.get("color", "#8c6bff"))] * (2 if legacy == "breathing" else 1)
            return config
        return None

    @staticmethod
    def _signature(config: dict[str, Any]) -> dict[str, Any]:
        """The parts of a config that make two lighting setups "the same"."""
        return {"effect": config["effect"], "brightness": int(config.get("brightness", 85)),
                **effects.clean_settings(config["effect"], config)}

    @Property(str, notify=activeProfileChanged)
    def activeProfile(self) -> str:
        """File name of the profile that matches the selected device right now, if any."""
        return self._active_profile

    def _update_active_profile(self) -> None:
        device = self._device(self._selected)
        current = self._signature(self._flat(self._entry(device.key))) if device else None
        active = next((file for file, signature in self._profile_configs.items() if signature == current), "")
        if active != self._active_profile:
            self._active_profile = active
            self.activeProfileChanged.emit()

    @Slot()
    def loadProfiles(self) -> None:
        entries: list[dict[str, Any]] = []
        self._profile_configs = {}
        for file in sorted(PROFILE_DIR.glob("*.json")) if PROFILE_DIR.is_dir() else []:
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                config = self._profile_config(data)
                if not config:
                    continue
                signature = self._signature(config)
                entries.append({"name": str(data.get("name", file.stem)), "file": file.name, "effect": config["effect"],
                                "effectName": tr(effects.EFFECTS[config["effect"]]["name"]),
                                "colors": signature["colors"], "brightness": signature["brightness"],
                                "thumb": effects.thumbnail(config["effect"], signature)})
                self._profile_configs[file.name] = signature
            except (OSError, ValueError, TypeError, AttributeError):
                self.logger.exception("Invalid profile file=%s", file)
        self._profiles = entries
        self.profilesChanged.emit()
        self._update_active_profile()

    @Slot(str)
    def saveProfile(self, name: str) -> None:
        clean = re.sub(r"[^\w -]", "", name, flags=re.UNICODE).strip()[:40]
        device = self._device(self._selected)
        if not clean:
            self.notify.emit(tr("Bitte gib dem Profil einen Namen."), "error")
            return
        if not device:
            return
        try:
            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            payload = {"name": clean, "config": self._flat(self._entry(device.key))}
            (PROFILE_DIR / f"{clean}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            self.notify.emit(tr("Profil konnte nicht gespeichert werden: {error}").format(error=exc), "error")
            return
        self.loadProfiles()
        self.notify.emit(tr("Profil „{name}“ gespeichert").format(name=clean), "success")

    def _profile_path(self, file_name: str) -> Path | None:
        return PROFILE_DIR / file_name if any(profile["file"] == file_name for profile in self._profiles) else None

    @Slot(str)
    def applyProfile(self, file_name: str) -> None:
        path = self._profile_path(file_name)
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path else {}
        except (OSError, ValueError):
            data = {}
        config = self._profile_config(data) if isinstance(data, dict) else None
        if not config:
            self.notify.emit(tr("Profil konnte nicht geladen werden."), "error")
            return

        def change(entry: dict[str, Any]) -> None:
            entry["effect"] = config["effect"]
            entry["per"][config["effect"]] = effects.clean_settings(config["effect"], config)
            entry["enabled"] = True
            try:
                entry["brightness"] = max(0, min(100, int(config.get("brightness", entry["brightness"]))))
            except (TypeError, ValueError):
                pass
        self._mutate(change)
        self.notify.emit(tr("Profil „{name}“ geladen").format(name=data.get("name", path.stem)), "success")

    @Slot(str)
    def deleteProfile(self, file_name: str) -> None:
        path = self._profile_path(file_name)
        if not path:
            return
        try:
            path.unlink()
        except OSError as exc:
            self.notify.emit(tr("Profil konnte nicht gelöscht werden: {error}").format(error=exc), "error")
            return
        self.loadProfiles()
        self.notify.emit(tr("Profil gelöscht"), "info")

    # ------------------------------------------------------------ diagnostics

    @Slot(result=str)
    def readLogs(self) -> str:
        try:
            return hid.LOG_PATH.read_text(encoding="utf-8")[-60000:]
        except OSError as exc:
            return tr("Protokoll konnte nicht gelesen werden: {error}").format(error=exc)

    @Slot(result=str)
    def logLocation(self) -> str:
        return str(hid.LOG_PATH)

    @Slot()
    def refreshLogs(self) -> None:
        self.logsChanged.emit(self.readLogs())

    @Slot()
    def copyLogs(self) -> None:
        QApplication.clipboard().setText(self.readLogs())
        self.notify.emit(tr("Diagnoseprotokoll in die Zwischenablage kopiert"), "success")
