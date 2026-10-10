from __future__ import annotations

import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QAction, QFont, QFontDatabase, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .i18n import tr
from .service import DeviceService

PACKAGE_DIR = Path(__file__).parent


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Aura Studio")
    app.setOrganizationName("AuraStudio")
    app.setDesktopFileName("aura-studio")
    icon = QIcon(str(PACKAGE_DIR / "assets" / "aura-studio.svg"))
    app.setWindowIcon(icon)
    for family in ("Inter", "Adwaita Sans"):
        if family in QFontDatabase.families():
            app.setFont(QFont(family))
            break

    service = DeviceService()
    service.loadProfiles()
    service.scan()
    app.aboutToQuit.connect(service.shutdown)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("service", service)
    engine.rootContext().setContextProperty("oled", service.oled)
    engine.rootContext().setContextProperty("trayAvailable", QSystemTrayIcon.isSystemTrayAvailable())
    engine.load(QUrl.fromLocalFile(str(PACKAGE_DIR / "qml" / "Main.qml")))
    if not engine.rootObjects():
        service.shutdown()
        return 1
    window = engine.rootObjects()[0]

    # With "Im Hintergrund weiterlaufen" the window only hides; the tray brings it back.
    tray = QSystemTrayIcon(icon)
    tray.setToolTip("Aura Studio")
    menu = QMenu()
    show_action = QAction(tr("Aura Studio öffnen"))
    quit_action = QAction(tr("Beenden"))
    menu.addAction(show_action)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)

    def show_window() -> None:
        window.show()
        window.raise_()
        window.requestActivate()

    def sync_tray() -> None:
        enabled = bool(service.settings["tray"]) and QSystemTrayIcon.isSystemTrayAvailable()
        app.setQuitOnLastWindowClosed(not enabled)
        tray.setVisible(enabled)

    show_action.triggered.connect(show_window)
    quit_action.triggered.connect(app.quit)
    tray.activated.connect(lambda reason: show_window() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    service.settingsChanged.connect(sync_tray)
    service.languageChanged.connect(lambda: (show_action.setText(tr("Aura Studio öffnen")), quit_action.setText(tr("Beenden"))))
    sync_tray()

    # Ctrl+C / SIGTERM quit cleanly so the devices are handed back to their firmware.
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: app.quit())
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: None)  # lets Python run its signal handlers
    heartbeat.start(250)

    code = app.exec()
    del engine  # before the service, so no binding outlives it
    return code


if __name__ == "__main__":
    raise SystemExit(main())
