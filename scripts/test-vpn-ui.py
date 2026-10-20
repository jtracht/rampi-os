"""Activate the actual private fixture VPN through its QML picker and keyboard."""

import argparse
import os
import tempfile
from pathlib import Path

if not Path("/.dockerenv").exists() or os.environ.get("RAMPI_TEST_CONTAINER") != "1":
    raise SystemExit("VPN mutation requires the designated disposable container")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--uuid", required=True)
expected = parser.parse_args().uuid
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QEvent, QEventLoop, QMetaObject, QObject, Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402, F401
from PySide6.QtTest import QTest  # noqa: E402
from rampi.app import create_application  # noqa: E402
from rampi.backend import Backend  # noqa: E402
from rampi.config import Settings  # noqa: E402


def wait_until(condition):
    for _ in range(400):
        if condition():
            return
        # Run the same event loop as the application, releasing the Python GIL
        # so QRunnable jobs can execute with Debian's PySide6 bindings too.
        loop = QEventLoop()
        QTimer.singleShot(50, loop.quit)
        loop.exec()
    raise RuntimeError(
        "VPN UI timeout: " + repr(backend.vpnProfiles) + "; pending=" + repr(backend.jobs.pending)
    )


with tempfile.TemporaryDirectory(prefix="rampi-vpn-ui-") as directory:
    os.environ["XDG_CONFIG_HOME"] = directory
    os.environ["XDG_CACHE_HOME"] = directory
    app = create_application()
    backend = Backend(Settings(setup_complete=True))
    backend.timer.stop()
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(str(v) for v in values))
    engine.rootContext().setContextProperty("rampi", backend)
    engine.rootContext().setContextProperty("windowed", True)
    engine.rootContext().setContextProperty("showSetup", False)
    engine.load(
        QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / "client/rampi/qml/Main.qml"))
    )
    window = engine.rootObjects()[0]
    window.requestActivate()
    dialog = window.findChild(QObject, "settingsDialog")
    QMetaObject.invokeMethod(dialog, "open")
    wait_until(lambda: dialog.property("opened"))
    window.findChild(QObject, "settingsTabs").setProperty("currentIndex", 2)
    wait_until(lambda: bool(backend.vpnProfiles["profiles"]))
    assert len(backend.vpnProfiles["profiles"]) == 1  # noqa: S101
    assert not backend.vpnProfiles["profiles"][0]["active"]  # noqa: S101
    picker = window.findChild(QObject, "vpnPicker")
    picker.forceActiveFocus()
    QTest.keyClick(window, Qt.Key.Key_Down)
    if picker.property("currentValue") != expected:
        raise SystemExit("Keyboard did not select the actual private connection UUID")
    backend.refreshVpnProfiles()
    wait_until(lambda: not any(name.startswith("vpn-profiles-") for name in backend.jobs.pending))
    if picker.property("currentValue") != expected:
        raise SystemExit("Metadata refresh lost the selected private connection")
    connect = window.findChild(QObject, "connectWireGuard")
    connect.forceActiveFocus()
    generation = backend._vpn_generation
    QTest.keyClick(window, Qt.Key.Key_Return)
    QTest.qWait(150)
    if backend._vpn_generation == generation:
        raise RuntimeError(
            "Enter did not activate the focused VPN button: "
            + repr({key: connect.property(key) for key in ("activeFocus", "enabled", "visible")})
        )
    wait_until(
        lambda: any(p["uuid"] == expected and p["active"] for p in backend.vpnProfiles["profiles"])
    )
    if warnings:
        raise SystemExit("QML warnings: " + "\n".join(warnings))
    backend.jobs.pool.waitForDone(25000)
    engine.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
print("PASS: actual QML keyboard selected the private VPN, kept its UUID and activated the tunnel.")
