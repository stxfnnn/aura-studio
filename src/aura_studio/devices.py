"""Discovery of ASUS HID devices through Linux sysfs."""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from . import hid
from .i18n import tr

ASUS_VID = 0x0B05
AZOTH_PIDS = {0x1A83: "USB", 0x1A85: "2.4 GHz"}
OMNI_PID = 0x1ACE
DEMO_ID = "demo#keyboard"


@dataclass
class Device:
    id: str
    name: str
    source: str
    category: str = "Peripherie"
    controllable: bool = False
    detail: str = ""
    product_id: str = ""
    kind: str = ""  # "keyboard" (per-key), "mouse" (single lamp) or "" (not controllable)
    virtual: bool = False
    oled_path: str = ""   # hidraw node of the OLED command channel, if the device has a display
    oled_report: int = 0  # size of one report on that node, including the report id
    # How to ask for the battery level: (hidraw path, report id, status query, reply index), or empty.
    battery_query: tuple = ()

    @property
    def path(self) -> str:
        return self.id.split("#", 1)[0]

    @property
    def key(self) -> str:
        """Stable identity for saved settings; hidraw numbers change between boots."""
        return f"{self.kind}:{self.name}"

    def link(self) -> hid.Link:
        if self.virtual:
            return hid.NullLink()
        if self.kind == "mouse":
            return hid.LampArrayLink(self.path)
        if "#report-" in self.id:
            return hid.KeyboardLink(self.path, int(self.id.rsplit("#report-", 1)[1]))
        return hid.KeyboardLink(self.path, save=True)


def demo_keyboard() -> Device:
    return Device(id=DEMO_ID, name=tr("Vorschau-Tastatur"), source="Simulation", category="Tastatur",
                  controllable=True, detail=tr("Kein Gerät verbunden · Effekte laufen nur in der Vorschau"),
                  kind="keyboard", virtual=True, oled_path="demo", oled_report=64)


def demo_mouse() -> Device:
    return Device(id="demo#mouse", name=tr("Vorschau-Maus"), source="Simulation", category="Maus", controllable=True,
                  detail=tr("Mausrad-LED · nur Vorschau"), kind="mouse", virtual=True)


def scan() -> list[Device]:
    logger = hid.app_logger()
    candidates: dict[tuple[str, int], list[Device]] = {}
    paired_devices: dict[str, list[tuple[int, int, int]]] = {}
    lamp_arrays: dict[str, str] = {}
    oled_nodes: dict[str, str] = {}
    receiver_nodes: dict[str, str] = {}
    logger.info("HID scan started")
    nodes = sorted(Path("/sys/class/hidraw").glob("hidraw*"))
    logger.info("HID scan found %d hidraw node(s)", len(nodes))
    for node in nodes:
        uevent = node / "device" / "uevent"
        try:
            fields = dict(line.split("=", 1) for line in uevent.read_text(errors="ignore").splitlines() if "=" in line)
        except OSError as exc:
            logger.debug("skip node=%s reason=uevent-read-failed error=%s", node.name, exc)
            continue
        hid_id = fields.get("HID_ID", "").split(":")
        if len(hid_id) < 3:
            continue
        try:
            bus, vid, pid = (int(part, 16) for part in hid_id[:3])
        except ValueError:
            logger.warning("skip node=%s malformed HID_ID=%r", node.name, fields.get("HID_ID"))
            continue
        if vid != ASUS_VID:
            continue
        name = fields.get("HID_NAME", "").strip() or tr("ASUS HID-Gerät")
        path = f"/dev/{node.name}"
        parent = _physical_parent(node)
        interface = _interface_number(node)
        usage_pages, report_ids = _descriptor_summary(node)
        if pid == OMNI_PID and "0x0059" in usage_pages.lower().split(","):
            lamp_arrays[parent] = path
            logger.info("LampArray interface candidate path=%s report_ids=%s", path, report_ids)
        try:
            node_stat = os.stat(path)
            permissions = (f"mode={stat.S_IMODE(node_stat.st_mode):04o} owner={node_stat.st_uid} group={node_stat.st_gid} "
                           f"can_read={os.access(path, os.R_OK)} can_write={os.access(path, os.W_OK)}")
        except OSError as exc:
            permissions = f"stat_error={exc}"
        # HID_UNIQ may contain a serial; it is deliberately not written to logs or identifiers.
        logger.info("ASUS interface node=%s path=%s bus=%03x vid=%04x pid=%04x name=%r interface=%s usage_pages=%s report_ids=%s %s parent=%s",
                    node.name, path, bus, vid, pid, name, interface, usage_pages, report_ids, permissions, parent)

        product_name = _known_name(pid, name)
        omni_channel = _omni_keyboard_channel(pid, usage_pages, report_ids)
        direct_azoth = pid in AZOTH_PIDS and interface == 2
        supported = direct_azoth or omni_channel is not None
        if pid in AZOTH_PIDS and "0xff00" in usage_pages.lower().split(",") and "2" in report_ids.split(","):
            oled_nodes[parent] = path
        if direct_azoth:
            device_id = path
            source = "USB" if pid == 0x1A83 else tr("2,4 GHz direkt")
            detail = tr("Einzeltasten-RGB · Aura-TUF direkt · {link}").format(link=AZOTH_PIDS[pid])
        elif omni_channel is not None:
            device_id = f"{path}#report-{omni_channel}"
            product_name = "ROG Azoth"
            source = "Omni Receiver"
            detail = tr("Einzeltasten-RGB · Aura-TUF über Omni Receiver · Report-ID {channel}").format(channel=omni_channel)
            pairing = hid.query_omni_pairing(path)
            if pairing:
                paired_devices[parent] = pairing
                logger.info("Omni paired devices discovered receiver=%s devices=%s", path,
                            [(f"0x{paired_pid:04x}", channel, kind) for paired_pid, channel, kind in pairing])
        elif pid == OMNI_PID:
            device_id = f"{parent}#omni"
            product_name = "ROG Omni Receiver"
            source = "ASUS Omni Receiver"
            detail = tr("Dongle-Schnittstelle {interface} · gekoppelte Geräte werden als HID-Kanäle geführt").format(interface=interface)
        else:
            device_id = f"{parent}#{pid:04x}"
            source = "ASUS HID"
            detail = tr("Erkannt · noch kein nativer Adapter")
        candidates.setdefault((parent, pid), []).append(
            Device(id=device_id, name=product_name, source=source, category=_category(product_name),
                   controllable=supported, detail=detail, product_id=f"0x{pid:04X}",
                   kind="keyboard" if supported else "",
                   # Through the receiver the display shares the key lighting channel (64-byte reports).
                   oled_path=path if omni_channel is not None else "", oled_report=64 if omni_channel is not None else 0,
                   battery_query=(path, omni_channel, 0x01, 6) if omni_channel is not None else ()))
        if omni_channel is not None:
            receiver_nodes[parent] = path

    found: list[Device] = []
    for (parent, pid), interfaces in candidates.items():
        # One physical dongle exposes several HID interfaces; list it once.
        found.append(next((device for device in interfaces if device.controllable), interfaces[0]))
        if pid in AZOTH_PIDS and found[-1].controllable and parent in oled_nodes:
            # Cabled: the display has its own vendor interface with 65-byte reports.
            found[-1].oled_path, found[-1].oled_report = oled_nodes[parent], 65
        logger.info("selected device=%s source=%s interfaces=%d controllable=%s",
                    found[-1].name, found[-1].source, len(interfaces), found[-1].controllable)

    for parent, paired in paired_devices.items():
        for mouse_pid, mouse_channel, mouse_kind in paired:
            # The receiver reports both paired slots. Skip keyboard-family PIDs.
            if mouse_pid in AZOTH_PIDS:
                continue
            mouse_name = "ROG Harpe Ace Extreme" if mouse_pid in (0x1B68, 0x1B69) else tr("ROG Maus ({pid})").format(pid=f"0x{mouse_pid:04X}")
            lamp_path = lamp_arrays.get(parent)
            controllable = lamp_path is not None
            found.append(Device(
                id=f"{lamp_path}#lamp-array" if lamp_path else f"{parent}#paired-{mouse_pid:04x}-{mouse_channel}",
                name=mouse_name, source="Omni Receiver", category="Maus", controllable=controllable,
                product_id=f"0x{mouse_pid:04X}", kind="mouse" if controllable else "",
                battery_query=(receiver_nodes[parent], mouse_channel, 0x07, 5) if parent in receiver_nodes else (),
                detail=(tr("Mausrad-LED · HID LampArray") if controllable else
                        tr("Gekoppeltes Gerät · Report-ID {channel} · keine LampArray-Schnittstelle").format(channel=mouse_channel))))
            logger.info("selected paired mouse=%s pid=0x%04x channel=%d kind=%d lamp_path=%s controllable=%s",
                        mouse_name, mouse_pid, mouse_channel, mouse_kind, lamp_path, controllable)
    logger.info("HID scan complete devices=%d controllable=%d", len(found), sum(device.controllable for device in found))
    return found


def _physical_parent(node: Path) -> str:
    try:
        resolved = (node / "device").resolve()
        for parent in (resolved, *resolved.parents):
            if (parent / "idVendor").exists() and (parent / "idProduct").exists():
                return str(parent)
        return str(resolved)
    except OSError:
        return str(node)


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


def _omni_keyboard_channel(pid: int, usage_pages: str, report_ids: str) -> int | None:
    # Omni vendor collections route keyboard reports on report ID 2. We only
    # select the interface whose descriptor advertises that report ID.
    if pid != OMNI_PID or "0xff00" not in usage_pages.lower().split(",") or "2" not in report_ids.split(","):
        return None
    return 2


def _known_name(pid: int, hid_name: str) -> str:
    known = {0x1A83: "ROG Azoth", 0x1A85: "ROG Azoth", OMNI_PID: "ROG Omni Receiver", 0x19AF: "AURA LED Controller"}
    if pid in known:
        return known[pid]
    return hid_name if "ASUS" in hid_name.upper() or "ROG" in hid_name.upper() else f"ASUS · {hid_name}"


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
