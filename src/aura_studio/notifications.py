"""Desktop notifications through the freedesktop notification service."""
from __future__ import annotations

import subprocess

from PySide6.QtDBus import QDBusConnection, QDBusInterface

from . import hid


def send(title: str, body: str) -> None:
    try:
        interface = QDBusInterface("org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                                   "org.freedesktop.Notifications", QDBusConnection.sessionBus())
        if interface.isValid():
            # app name, replaces id, icon, summary, body, actions, hints, timeout (ms)
            reply = interface.call("Notify", "Aura Studio", 0, "aura-studio", title, body, [], {}, 12000)
            if not reply.errorMessage():
                return
        subprocess.Popen(["notify-send", "-a", "Aura Studio", "-i", "aura-studio", title, body])
    except (OSError, RuntimeError):
        hid.app_logger().warning("Could not show notification: %s", title)
