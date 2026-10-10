from __future__ import annotations

import json
import colorsys
import fcntl
import logging
import logging.handlers
import math
import os
import re
import select
import stat
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication


PROFILE_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "aura-studio" / "profiles"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "aura-studio"
LOG_PATH = STATE_DIR / "aura-studio.log"
ASUS_VID = 0x0B05
AZOTH_PIDS = {0x1A83: "USB", 0x1A85: "2.4 GHz"}
SOFTWARE_EFFECTS = {"Color cycle", "Pulse", "Ocean", "Aurora", "Fire", "Pastel flow"}
AVAILABLE_EFFECTS = ["Static", "Breathing", "Rainbow", "Color cycle", "Pulse", "Ocean", "Aurora", "Fire", "Pastel flow"]


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


@dataclass
class Device:
    id: str
    name: str
    source: str
    connected: bool = True
    category: str = "Peripherie"
    modes: list[str] | None = None
    oled: bool = False
    controllable: bool = False
    detail: str = ""
    product_id: str = ""


class AsusHid:
    """Native Linux hidraw transport; no OpenRGB or vendor daemon required."""

    REPORT_SIZE = 65
    MODE = {"Static": 0x00, "Breathing": 0x01, "Rainbow": 0x02}

    @staticmethod
    def _feature_ioctl(number: int, size: int) -> int:
        return (3 << 30) | (size << 16) | (ord("H") << 8) | number

    @staticmethod
    def _get_feature(fd: int, report_id: int, size: int) -> bytes:
        buffer = bytearray(size)
        buffer[0] = report_id
        fcntl.ioctl(fd, AsusHid._feature_ioctl(0x07, size), buffer, True)
        return bytes(buffer)

    @staticmethod
    def _set_feature(fd: int, report: bytes) -> None:
        data = bytearray(report)
        fcntl.ioctl(fd, AsusHid._feature_ioctl(0x06, len(data)), data, True)

    @staticmethod
    def set_lamparray_autonomous(path: str, enabled: bool) -> None:
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        try:
            report = bytes((0x06, 0x01 if enabled else 0x00))
            AsusHid._set_feature(fd, report)
            app_logger().info("LampArray autonomous mode path=%s enabled=%s report=%s", path, enabled, report.hex(" "))
        finally:
            os.close(fd)

    @staticmethod
    def apply_lamparray(path: str, color: str, brightness: int) -> dict[str, int]:
        """Set the single Harpe wheel LED through its standard HID LampArray reports."""
        logger = app_logger()
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
        autonomous_disabled = False
        try:
            attributes = AsusHid._get_feature(fd, 0x01, 23)
            lamp_count = int.from_bytes(attributes[1:3], "little")
            minimum_interval_us = int.from_bytes(attributes[19:23], "little")
            if lamp_count != 1:
                raise OSError(f"Unerwartete Anzahl Mausrad-LEDs: {lamp_count}")
            # The HID spec initializes the LampId cursor to zero, so query lamp 0.
            lamp = AsusHid._get_feature(fd, 0x03, 29)
            lamp_id = int.from_bytes(lamp[1:3], "little")
            red_levels, green_levels, blue_levels, intensity_levels, programmable = lamp[23:28]
            logger.info("LampArray capabilities path=%s attr=%s lamp=%s id=%d rgb_levels=%d,%d,%d intensity_levels=%d programmable=%d min_interval_us=%d",
                        path, attributes.hex(" "), lamp.hex(" "), lamp_id, red_levels, green_levels,
                        blue_levels, intensity_levels, programmable, minimum_interval_us)
            if lamp_id != 0 or not programmable or min(red_levels, green_levels, blue_levels) == 0:
                raise OSError("Die Mausrad-LED meldet kein programmierbares RGB-LampArray.")
            rgb = bytes.fromhex(re.sub(r"[^0-9a-fA-F]", "", color)[:6].ljust(6, "0"))
            intensity = round(max(0, min(100, brightness)) * 2.55) if intensity_levels else 0xFF
            AsusHid._set_feature(fd, bytes((0x06, 0x00)))
            autonomous_disabled = True
            time.sleep(min(max(minimum_interval_us / 1_000_000, 0.001), 1.0))
            # LampUpdateComplete, LampIdStart, LampIdEnd, then RGBI.
            report = bytes((0x05, 0x01, 0x00, 0x00, 0x00, 0x00, *rgb, intensity))
            AsusHid._set_feature(fd, report)
            logger.info("LampArray range update tx path=%s report=%s bytes=%d", path, report.hex(" "), len(report))
            return {"lamp_count": lamp_count, "lamp_id": lamp_id, "min_interval_us": minimum_interval_us}
        except Exception:
            if autonomous_disabled:
                try:
                    AsusHid._set_feature(fd, bytes((0x06, 0x01)))
                    logger.info("LampArray autonomous mode restored after failed write path=%s", path)
                except OSError:
                    logger.exception("LampArray failed to restore autonomous mode path=%s", path)
            raise
        finally:
            os.close(fd)

    @staticmethod
    def _animation_color(effect: str, base_color: str, base_brightness: int, phase: float) -> tuple[str, int]:
        rgb_hex = re.sub(r"[^0-9a-fA-F]", "", base_color)[:6].ljust(6, "0")
        rgb = tuple(int(rgb_hex[index:index + 2], 16) / 255 for index in (0, 2, 4))
        hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
        brightness_scale = 1.0
        if effect == "Rainbow":
            hue, saturation, value = (phase / (2 * math.pi)) % 1.0, 1.0, 1.0
        elif effect == "Color cycle":
            hue = (hue + phase / (2 * math.pi)) % 1.0
        elif effect == "Pulse":
            brightness_scale = 0.14 + 0.86 * (0.5 + 0.5 * math.sin(phase))
        elif effect == "Ocean":
            hue, saturation, value = 0.53 + 0.035 * math.sin(phase), 0.78, 0.9
        elif effect == "Aurora":
            hue, saturation, value = 0.36 + 0.065 * math.sin(phase), 0.72, 0.92
        elif effect == "Fire":
            hue, saturation = 0.025 + 0.045 * (0.5 + 0.5 * math.sin(phase)), 0.95
            value = 0.48 + 0.52 * (0.5 + 0.5 * math.sin(phase * 1.7))
        elif effect == "Pastel flow":
            hue, saturation, value = (hue + phase / (2 * math.pi)) % 1.0, 0.42, 1.0
        channels = colorsys.hsv_to_rgb(hue % 1.0, max(0, min(1, saturation)), max(0, min(1, value)))
        color = "#" + "".join(f"{round(channel * 255):02x}" for channel in channels)
        animated_brightness = round(max(0, min(100, base_brightness * brightness_scale)))
        return color, animated_brightness

    @staticmethod
    def _lamp_frame(fd: int, color: str, brightness: int) -> None:
        rgb_hex = re.sub(r"[^0-9a-fA-F]", "", color)[:6].ljust(6, "0")
        rgb = bytes.fromhex(rgb_hex)
        report = bytes((0x05, 0x01, 0x00, 0x00, 0x00, 0x00, *rgb, round(max(0, min(100, brightness)) * 2.55)))
        AsusHid._set_feature(fd, report)

    @staticmethod
    def _write_keyboard_frame(fd: int, device_id: str, color: str, brightness: int, speed: int) -> None:
        payload = AsusHid.report("Static", color, brightness, speed)
        if "#report-" in device_id:
            report_id = int(device_id.rsplit("#report-", 1)[1])
            frame = bytes((report_id,)) + payload[1:]
        else:
            frame = payload
        written = os.write(fd, frame)
        if written != len(frame):
            raise OSError(f"Unvollständiger Animationsbericht ({written}/{len(frame)} Bytes)")

    @staticmethod
    def report(mode: str, color: str, brightness: int, speed: int) -> bytes:
        frame = bytearray(AsusHid.REPORT_SIZE)
        frame[1:4] = bytes((0x51, 0x2C, AsusHid.MODE.get(mode, 0)))
        frame[5] = round((100 - max(0, min(100, speed))) * 2.55)
        frame[6] = max(0, min(100, brightness))
        frame[7] = 0x10 if mode == "Breathing" else 0x00
        frame[9] = 0x02
        if mode != "Color cycle":
            rgb = bytes.fromhex(re.sub(r"[^0-9a-fA-F]", "", color)[:6].ljust(6, "0"))
            frame[10:13] = rgb
        return bytes(frame)

    @staticmethod
    def apply(path: str, mode: str, color: str, brightness: int, speed: int) -> None:
        logger = app_logger()
        frame = AsusHid.report(mode, color, brightness, speed)
        logger.info("HID write begin path=%s effect=%s color=%s brightness=%d speed=%d report=%s", path, mode, color, brightness, speed, frame.hex(" "))
        fd = os.open(path, os.O_WRONLY | os.O_CLOEXEC | os.O_NONBLOCK)
        try:
            written = os.write(fd, frame)
            logger.info("HID effect report result path=%s bytes=%d/%d", path, written, len(frame))
            if written != AsusHid.REPORT_SIZE:
                raise OSError(f"Unvollständiger HID-Bericht ({written}/65 Bytes)")
            time.sleep(0.04)
            save = bytearray(AsusHid.REPORT_SIZE)
            save[1:3] = b"\x50\x55"
            saved = os.write(fd, save)
            logger.info("HID save report result path=%s bytes=%d/%d report=%s", path, saved, len(save), save.hex(" "))
        finally:
            os.close(fd)

    @staticmethod
    def query_omni_pairing(path: str) -> list[tuple[int, int, int]]:
        """Ask the documented, read-only Omni receiver paired-device list command."""
        logger = app_logger()
        fd = -1
        try:
            fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NONBLOCK)
            request = bytearray(64)
            request[0:3] = b"\x01\xa0\x00"
            written = os.write(fd, request)
            logger.info("Omni pairing query tx path=%s report=%s bytes=%d/%d", path, request.hex(" "), written, len(request))
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


class DeviceService(QObject):
    devicesChanged = Signal("QVariantList")
    statusChanged = Signal(str)
    profilesChanged = Signal("QVariantList")
    errorRaised = Signal(str)
    applyingChanged = Signal(bool)
    logsChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.devices: list[Device] = []
        self._active_lamparrays: set[str] = set()
        self._animation_stop: threading.Event | None = None
        self._animation_thread: threading.Thread | None = None
        self.logger = app_logger()
        self.logger.info("Aura Studio started; log=%s", LOG_PATH)

    @Slot()
    def scan(self) -> None:
        self.statusChanged.emit("ASUS-HID-Geräte werden gesucht …")
        candidates: dict[tuple[str, int], list[Device]] = {}
        paired_devices: dict[str, list[tuple[int, int, int]]] = {}
        lamp_arrays: dict[str, str] = {}
        self.logger.info("HID scan started")
        nodes = sorted(Path("/sys/class/hidraw").glob("hidraw*"))
        self.logger.info("HID scan found %d hidraw node(s)", len(nodes))
        for node in nodes:
            uevent = node / "device" / "uevent"
            try:
                fields = dict(line.split("=", 1) for line in uevent.read_text(errors="ignore").splitlines() if "=" in line)
            except OSError as exc:
                self.logger.debug("skip node=%s reason=uevent-read-failed error=%s", node.name, exc)
                continue
            hid_id = fields.get("HID_ID", "").split(":")
            if len(hid_id) < 3:
                continue
            try:
                bus, vid, pid = (int(part, 16) for part in hid_id[:3])
            except ValueError:
                self.logger.warning("skip node=%s malformed HID_ID=%r", node.name, fields.get("HID_ID"))
                continue
            if vid != ASUS_VID:
                continue
            name = fields.get("HID_NAME", "ASUS HID-Gerät").strip() or "ASUS HID-Gerät"
            path = f"/dev/{node.name}"
            resolved = str((node / "device").resolve())
            parent = DeviceService._physical_parent(node)
            interface = DeviceService._interface_number(node)
            usage_pages, report_ids = DeviceService._descriptor_summary(node)
            if pid == 0x1ACE and "0x0059" in usage_pages.lower().split(","):
                lamp_arrays[parent] = path
                self.logger.info("LampArray interface candidate path=%s report_ids=%s", path, report_ids)
            try:
                node_stat = os.stat(path)
                permissions = f"mode={stat.S_IMODE(node_stat.st_mode):04o} owner={node_stat.st_uid} group={node_stat.st_gid} can_read={os.access(path, os.R_OK)} can_write={os.access(path, os.W_OK)}"
            except OSError as exc:
                permissions = f"stat_error={exc}"
            # HID_UNIQ may contain a serial; it is deliberately not written to logs or identifiers.
            self.logger.info("ASUS interface node=%s path=%s bus=%03x vid=%04x pid=%04x name=%r interface=%s usage_pages=%s report_ids=%s %s sysfs=%s parent=%s", node.name, path, bus, vid, pid, name, interface, usage_pages, report_ids, permissions, resolved, parent)

            product_name = DeviceService._known_name(pid, name)
            omni_channel = DeviceService._omni_keyboard_channel(pid, interface, usage_pages, report_ids)
            direct_azoth = pid in AZOTH_PIDS and interface == 2
            supported = direct_azoth or omni_channel is not None
            if direct_azoth:
                device_id = path
                source = "Aura HID · USB" if pid == 0x1A83 else "Aura HID · 2.4 GHz direkt"
                detail = "Native Aura-TUF HID · " + AZOTH_PIDS[pid]
            elif omni_channel is not None:
                device_id = f"{path}#report-{omni_channel}"
                product_name = "ROG Azoth (Omni Receiver)"
                source = "Aura HID · Omni Receiver"
                detail = f"TUF keyboard channel · HID report ID {omni_channel} · ohne USB-Speichern"
                pairing = AsusHid.query_omni_pairing(path)
                if pairing:
                    paired_devices[parent] = pairing
                    self.logger.info("Omni paired devices discovered receiver=%s devices=%s", path,
                                     [(f"0x{pid:04x}", channel, kind) for pid, channel, kind in pairing])
            elif pid == 0x1ACE:
                device_id = f"{parent}#omni"
                product_name = "ROG Omni Receiver"
                source = "ASUS Omni Receiver"
                detail = f"Dongle-Schnittstelle {interface} · gekoppelte Geräte werden als HID-Kanäle geführt"
            else:
                device_id = f"{parent}#{pid:04x}"
                source = "ASUS HID"
                detail = "Erkannt · noch kein nativer Adapter"
            device = Device(id=device_id, name=product_name, source=source,
                            category=DeviceService._category(product_name),
                            modes=AVAILABLE_EFFECTS.copy() if supported else [],
                            controllable=supported, detail=detail, product_id=f"0x{pid:04X}")
            candidates.setdefault((parent, pid), []).append(device)

        found: list[Device] = []
        for (parent, pid), interfaces in candidates.items():
            controllable = next((d for d in interfaces if d.controllable), None)
            if pid == 0x1ACE and controllable:
                found.append(controllable)
                self.logger.info("selected receiver child=%s from %d HID interface(s)", controllable.name, len(interfaces))
            elif pid == 0x1ACE:
                # One physical dongle, despite several HID collections/interfaces.
                found.append(interfaces[0])
                self.logger.info("selected receiver=%s interfaces=%d; paired child identity not yet queried", interfaces[0].id, len(interfaces))
            else:
                found.append(controllable or interfaces[0])
                self.logger.info("selected device=%s source=%s interfaces=%d controllable=%s", found[-1].name, found[-1].source, len(interfaces), found[-1].controllable)

        self.devices = found
        for parent, paired in paired_devices.items():
            for mouse_pid, mouse_channel, mouse_kind in paired:
                # Receiver reports both paired slots. Skip keyboard-family PIDs.
                if mouse_pid in AZOTH_PIDS:
                    continue
                mouse_name = "ROG Harpe Ace Extreme" if mouse_pid in (0x1B68, 0x1B69) else f"ROG Maus via Omni (0x{mouse_pid:04X})"
                lamp_path = lamp_arrays.get(parent)
                controllable = lamp_path is not None
                device_id = f"{lamp_path}#lamp-array" if lamp_path else f"{parent}#paired-{mouse_pid:04x}-{mouse_channel}"
                detail = ("Scrollrad-LED · 1 Lamp · HID LampArray" if controllable else
                          f"Gekoppeltes Gerät · report ID {mouse_channel} · keine LampArray-Schnittstelle")
                found.append(Device(id=device_id, name=mouse_name,
                                    source="Omni Receiver · Mausrad-LED" if controllable else "Omni Receiver · gekoppelt",
                                    category="Maus", modes=AVAILABLE_EFFECTS.copy() if controllable else [], controllable=controllable,
                                    product_id=f"0x{mouse_pid:04X}", detail=detail))
                self.logger.info("selected paired mouse=%s pid=0x%04x channel=%d kind=%d lamp_path=%s controllable=%s",
                                 mouse_name, mouse_pid, mouse_channel, mouse_kind, lamp_path, controllable)
        self.devices = found
        self.devicesChanged.emit([asdict(device) for device in found])
        controllable_count = sum(device.controllable for device in found)
        self.logger.info("HID scan complete devices=%d controllable=%d", len(found), controllable_count)
        if not found:
            self.statusChanged.emit("Keine ASUS-HID-Geräte gefunden")
        else:
            self.statusChanged.emit(f"{len(found)} ASUS-Gerät(e) erkannt · {controllable_count} direkt steuerbar")

    @staticmethod
    def _physical_parent(node: Path) -> str:
        try:
            resolved = (node / "device").resolve()
            for parent in (resolved, *resolved.parents):
                if (parent / "idVendor").exists() and (parent / "idProduct").exists():
                    return str(parent)
            return str(resolved)
        except OSError:
            return str(node)

    @staticmethod
    def _interface_number(node: Path) -> int | None:
        try:
            device = (node / "device").resolve()
        except OSError:
            return None
        for parent in (device, *device.parents):
            interface_file = parent / "bInterfaceNumber"
            if interface_file.exists():
                try:
                    return int(interface_file.read_text().strip(), 16)
                except (OSError, ValueError):
                    return None
        return None

    @staticmethod
    def _descriptor_summary(node: Path) -> tuple[str, str]:
        try:
            descriptor = (node / "device" / "report_descriptor").read_bytes()
        except OSError:
            return "unknown", "unknown"
        pages: set[int] = set()
        ids: set[int] = set()
        index = 0
        while index < len(descriptor):
            prefix = descriptor[index]
            index += 1
            if prefix == 0xFE:
                if index + 1 >= len(descriptor):
                    break
                index += descriptor[index] + 1
                continue
            size = prefix & 0x03
            size = 4 if size == 3 else size
            if index + size > len(descriptor):
                break
            value = int.from_bytes(descriptor[index:index + size], "little") if size else 0
            item_type, tag = (prefix >> 2) & 3, (prefix >> 4) & 0xF
            if item_type == 1 and tag == 0:
                pages.add(value)
            if item_type == 1 and tag == 8:
                ids.add(value)
            index += size
        return (",".join(f"0x{x:04x}" for x in sorted(pages)) or "none",
                ",".join(f"{x}" for x in sorted(ids)) or "none")

    @staticmethod
    def _omni_keyboard_channel(pid: int, interface: int | None, usage_pages: str, report_ids: str) -> int | None:
        # Omni vendor collections route keyboard reports on report ID 2. We only
        # select the interface whose descriptor advertises that report ID.
        if pid != 0x1ACE or "0xff00" not in usage_pages.lower().split(",") or "2" not in report_ids.split(","):
            return None
        return 2

    @staticmethod
    def _known_name(pid: int, hid_name: str) -> str:
        known = {0x1A83: "ROG Azoth (USB)", 0x1A85: "ROG Azoth (2.4 GHz)",
                 0x1ACE: "ROG Omni Receiver", 0x19AF: "AURA LED Controller"}
        if pid in known:
            return known[pid]
        return hid_name if "ASUS" in hid_name.upper() or "ROG" in hid_name.upper() else f"ASUS · {hid_name}"

    @staticmethod
    def _category(name: str) -> str:
        lowered = name.lower()
        if any(k in lowered for k in ("keyboard", "azoth", "falchion", "scope")):
            return "Tastatur"
        if any(k in lowered for k in ("mouse", "gladius", "keris", "chakram", "harpe")):
            return "Maus"
        if "receiver" in lowered:
            return "Empfänger"
        if "aura" in lowered or "motherboard" in lowered:
            return "Beleuchtung"
        return "ASUS-Gerät"

    @Slot(str, str, str, int, int)
    def applyEffect(self, device_id: str, effect: str, color: str, brightness: int, speed: int) -> None:
        device = next((d for d in self.devices if d.id == device_id), None)
        self.logger.info("apply requested device_id=%s effect=%s color=%s brightness=%d speed=%d", device_id, effect, color, brightness, speed)
        if not device:
            self.logger.error("apply rejected: selected device no longer exists")
            self.errorRaised.emit("Das Gerät ist nicht mehr verbunden. Bitte erneut suchen.")
            return
        if not device.controllable:
            self.logger.warning("apply rejected device=%s reason=no-adapter", device.name)
            self.errorRaised.emit(f"{device.name}: Dafür gibt es noch keinen passenden nativen Adapter.")
            return
        animation_effect = "Pulse" if "#lamp-array" in device.id and effect == "Breathing" else effect
        is_software_effect = animation_effect in SOFTWARE_EFFECTS or ("#lamp-array" in device.id and animation_effect in {"Rainbow"})
        if is_software_effect:
            self.applyingChanged.emit(True)
            try:
                self._start_animation(device, animation_effect, color, brightness, speed)
                self.statusChanged.emit(f"✓ {effect} läuft auf {device.name}")
            except OSError as exc:
                self.logger.exception("Could not start software effect=%s device=%s", effect, device.name)
                if isinstance(exc, PermissionError):
                    self.errorRaised.emit(f"Keine Berechtigung für {device.id.split('#', 1)[0]}. Prüfe die HID-Regel im Diagnoseprotokoll.")
                else:
                    self.errorRaised.emit(f"Animation konnte nicht gestartet werden: {exc}")
            finally:
                self.applyingChanged.emit(False)
            return
        self._stop_animation()
        self.applyingChanged.emit(True)
        try:
            path = device.id.split("#", 1)[0]
            success_message = f"✓ {effect} an {device.name} gesendet"
            if "#lamp-array" in device.id:
                if effect != "Static":
                    raise ValueError("Die Harpe hat eine einzelne Mausrad-LED; dafür ist aktuell der Effekt Static verfügbar.")
                result = AsusHid.apply_lamparray(path, color, brightness)
                self._active_lamparrays.add(path)
                self.logger.info("LampArray color applied device=%s result=%s", device.name, result)
                success_message = f"✓ Mausrad-LED auf {color.upper()} gesetzt"
            elif "#report-" in device.id:
                report_id = int(device.id.rsplit("#report-", 1)[1])
                payload = AsusHid.report(effect, color, brightness, speed)[1:]
                frame = bytes((report_id,)) + payload
                self.logger.info("Omni keyboard tx path=%s report_id=%d report=%s", path, report_id, frame.hex(" "))
                fd = os.open(path, os.O_WRONLY | os.O_CLOEXEC | os.O_NONBLOCK)
                try:
                    written = os.write(fd, frame)
                    self.logger.info("Omni keyboard tx result bytes=%d/%d", written, len(frame))
                    if written != len(frame):
                        raise OSError(f"Unvollständiger Omni-HID-Bericht ({written}/{len(frame)} Bytes)")
                finally:
                    os.close(fd)
            else:
                AsusHid.apply(path, effect, color, brightness, speed)
            self.statusChanged.emit(success_message)
        except OSError as exc:
            self.logger.exception("HID apply failed device=%s", device.name)
            if isinstance(exc, PermissionError):
                self.errorRaised.emit(f"Keine Berechtigung für {path}. Installiere einmalig die Regel aus packaging/99-aura-studio.rules; Anleitung im Diagnoseprotokoll.")
            else:
                self.errorRaised.emit(f"HID-Steuerung fehlgeschlagen: {exc}. Details stehen im Diagnoseprotokoll.")
        except ValueError as exc:
            self.logger.warning("apply rejected device=%s reason=%s", device.name, exc)
            self.errorRaised.emit(str(exc))
        finally:
            self.applyingChanged.emit(False)

    def _start_animation(self, device: Device, effect: str, color: str, brightness: int, speed: int) -> None:
        self._stop_animation()
        stop_event = threading.Event()
        ready = threading.Event()
        startup_error: list[BaseException] = []
        path = device.id.split("#", 1)[0]

        def run() -> None:
            fd = -1
            lamp = "#lamp-array" in device.id
            autonomous_disabled = False
            try:
                flags = os.O_RDWR if lamp else os.O_WRONLY
                fd = os.open(path, flags | os.O_CLOEXEC | os.O_NONBLOCK)
                minimum_interval = 0.0
                if lamp:
                    attributes = AsusHid._get_feature(fd, 0x01, 23)
                    lamp_count = int.from_bytes(attributes[1:3], "little")
                    minimum_interval = int.from_bytes(attributes[19:23], "little") / 1_000_000
                    lamp_info = AsusHid._get_feature(fd, 0x03, 29)
                    if lamp_count != 1 or not lamp_info[27]:
                        raise OSError("Das LampArray der Maus unterstützt keine programmierte RGB-Ausgabe.")
                    AsusHid._set_feature(fd, bytes((0x06, 0x00)))
                    autonomous_disabled = True
                    self._active_lamparrays.add(path)
                    time.sleep(minimum_interval)

                started = time.monotonic()
                interval = max(0.05, 0.12 - max(0, min(100, speed)) * 0.0006, minimum_interval)
                phase_speed = 0.5 + max(0, min(100, speed)) * 0.035
                frame = 0
                while True:
                    phase = (time.monotonic() - started) * phase_speed
                    animated_color, animated_brightness = AsusHid._animation_color(effect, color, brightness, phase)
                    if lamp:
                        AsusHid._lamp_frame(fd, animated_color, animated_brightness)
                    else:
                        AsusHid._write_keyboard_frame(fd, device.id, animated_color, animated_brightness, speed)
                    if frame == 0:
                        ready.set()
                    frame += 1
                    if stop_event.wait(interval):
                        break
            except Exception as exc:
                if not ready.is_set():
                    startup_error.append(exc)
                elif not stop_event.is_set():
                    self.logger.exception("Animation stopped unexpectedly device=%s effect=%s", device.name, effect)
                    self.errorRaised.emit(f"{effect} wurde unterbrochen: {exc}")
                ready.set()
            finally:
                if lamp and autonomous_disabled:
                    try:
                        AsusHid._set_feature(fd, bytes((0x06, 0x01)))
                    except OSError:
                        self.logger.exception("Could not restore LampArray mode after animation device=%s", device.name)
                if fd >= 0:
                    os.close(fd)

        thread = threading.Thread(target=run, name=f"AuraEffect-{device.name}", daemon=True)
        self._animation_stop = stop_event
        self._animation_thread = thread
        thread.start()
        if not ready.wait(2.0):
            stop_event.set()
            raise OSError("Das Gerät hat nicht rechtzeitig auf den ersten Animationsschritt reagiert.")
        if startup_error:
            stop_event.set()
            thread.join(timeout=1.0)
            error = startup_error[0]
            if isinstance(error, OSError):
                raise error
            raise OSError(str(error))
        self.logger.info("Software effect started device=%s effect=%s speed=%d interval_ms=%.0f", device.name, effect, speed, interval * 1000)

    def _stop_animation(self) -> None:
        stop_event, thread = self._animation_stop, self._animation_thread
        self._animation_stop = None
        self._animation_thread = None
        if stop_event:
            stop_event.set()
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    @Slot(result=str)
    def readLogs(self) -> str:
        try:
            return LOG_PATH.read_text(encoding="utf-8")[-60000:]
        except OSError as exc:
            self.logger.exception("Could not read log")
            return f"Protokoll konnte nicht gelesen werden: {exc}"

    @Slot(result=str)
    def logLocation(self) -> str:
        return str(LOG_PATH)

    @Slot()
    def refreshLogs(self) -> None:
        self.logsChanged.emit(self.readLogs())

    @Slot()
    def copyLogs(self) -> None:
        QApplication.clipboard().setText(self.readLogs())
        self.statusChanged.emit("Diagnoseprotokoll in die Zwischenablage kopiert")

    @Slot(str, str)
    def uiAction(self, action: str, target: str) -> None:
        self.logger.info("UI action=%r target=%r", action, target)

    @Slot(str, str, str, int, int)
    def saveProfile(self, name: str, effect: str, color: str, brightness: int, speed: int) -> None:
        clean = re.sub(r"[^\w -]", "", name, flags=re.UNICODE).strip()[:40]
        if not clean:
            self.errorRaised.emit("Bitte gib dem Profil einen Namen.")
            return
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"name": clean, "effect": effect, "color": color, "brightness": brightness, "speed": speed}
        (PROFILE_DIR / f"{clean}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.logger.info("profile saved name=%r effect=%s color=%s brightness=%d speed=%d", clean, effect, color, brightness, speed)
        self.loadProfiles()
        self.statusChanged.emit(f"Profil „{clean}“ gespeichert")

    @Slot()
    def releaseControls(self) -> None:
        self._stop_animation()
        for path in tuple(self._active_lamparrays):
            try:
                AsusHid.set_lamparray_autonomous(path, True)
                self.logger.info("LampArray control released path=%s", path)
            except OSError:
                self.logger.exception("Could not release LampArray path=%s", path)

    @Slot()
    def loadProfiles(self) -> None:
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        entries: list[dict[str, Any]] = []
        for file in sorted(PROFILE_DIR.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                entries.append({"name": str(data.get("name", file.stem)), "effect": str(data.get("effect", "Static")),
                                "color": str(data.get("color", "#8C6BFF")),
                                "brightness": int(data.get("brightness", 75)), "speed": int(data.get("speed", 50))})
            except (OSError, ValueError, TypeError):
                self.logger.exception("Invalid profile file=%s", file)
        self.profilesChanged.emit(entries)
