from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine

from .backend import DeviceService


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Aura Studio")
    app.setOrganizationName("AuraStudio")
    app.setDesktopFileName("aura-studio")
    engine = QQmlApplicationEngine()
    service = DeviceService()
    app.aboutToQuit.connect(service.releaseControls)
    engine.rootContext().setContextProperty("deviceService", service)
    qml = Path(__file__).parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        return 1
    service.loadProfiles()
    service.scan()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
