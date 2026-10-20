"""Actual QML/GIO contract test on python-dbusmock's isolated NM fixture, not radio."""

import os
import subprocess
import tempfile
import uuid
from pathlib import Path

if not Path("/.dockerenv").exists() or os.environ.get("RAMPI_TEST_CONTAINER") != "1":
    raise SystemExit("The WLAN fixture requires its designated disposable container")

import dbus  # noqa: E402
import dbusmock  # noqa: E402
from PySide6.QtCore import QEvent, QEventLoop, QMetaObject, QObject, Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402, F401
from PySide6.QtTest import QTest  # noqa: E402
from rampi.app import create_application  # noqa: E402
from rampi.backend import Backend  # noqa: E402
from rampi.config import Settings  # noqa: E402
from rampi.services import linux_username  # noqa: E402
from rampi.wifi import NM, ROOT  # noqa: E402


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def wait_until(condition):
    for _ in range(400):
        if condition():
            return
        loop = QEventLoop()
        QTimer.singleShot(25, loop.quit)
        loop.exec()
    raise RuntimeError("WLAN fixture UI operation did not complete")


dbusmock.DBusTestCase.start_system_bus()
process, obj = dbusmock.DBusTestCase.spawn_server_template(
    "networkmanager", {}, stdout=subprocess.DEVNULL
)
try:
    bus = dbusmock.DBusTestCase.get_dbus(True)
    mock = dbus.Interface(obj, dbusmock.MOCK_IFACE)
    manager = bus.get_object(NM, ROOT)
    controls = dbus.Interface(manager, dbusmock.MOCK_IFACE)
    device = mock.AddWiFiDevice("rampi_test", "wlan_test", 30)
    access = mock.AddAccessPoint(
        device, "rampi_ap", "Lab:\\Rampi", "02:00:00:00:00:01", 2, 2412, 54000, 82, 256
    )
    dev = dbus.Interface(bus.get_object(NM, device), dbusmock.MOCK_IFACE)
    dev.AddProperties(
        NM + ".Device.Wireless",
        {
            "ActiveAccessPoint": dbus.ObjectPath("/"),
            "LastScan": dbus.Int64(0),
        },
    )
    dev.AddMethod(
        NM + ".Device",
        "Disconnect",
        "",
        "",
        f"self.Set('{NM}.Device', 'State', dbus.UInt32(30)); "
        f"self.Set('{NM}.Device.Wireless', 'ActiveAccessPoint', dbus.ObjectPath('/'))",
    )
    dev.AddMethod(
        NM + ".Device.Wireless",
        "RequestScan",
        "a{sv}",
        "",
        f"self.Set('{NM}.Device.Wireless', 'LastScan', "
        f"dbus.Int64(self.Get('{NM}.Device.Wireless', 'LastScan') + 1))",
    )
    # Extend the established fixture's older API with the current method signature.
    # Its fake activation is deliberate: only the client/API contract is under test.
    controls.AddMethod(
        NM,
        "AddAndActivateConnection2",
        "a{sa{sv}}ooa{sv}",
        "ooa{sv}",
        "pair = self.add_and_activate_connection(self, args[0], args[1], args[2]); "
        f"objects[args[1]].Set('{NM}.Device.Wireless', 'ActiveAccessPoint', args[2]); "
        "ret = (pair[0], pair[1], {})",
    )
    with tempfile.TemporaryDirectory(prefix="rampi-wifi-ui-") as directory:
        os.environ["XDG_CONFIG_HOME"] = directory
        os.environ["XDG_CACHE_HOME"] = directory
        app = create_application()
        backend = Backend(Settings(setup_complete=True))
        backend.timer.stop()
        messages = []
        backend.message.connect(messages.append)
        engine = QQmlApplicationEngine()
        warnings = []
        engine.warnings.connect(lambda values: warnings.extend(str(v) for v in values))
        engine.rootContext().setContextProperty("rampi", backend)
        engine.rootContext().setContextProperty("windowed", True)
        engine.rootContext().setContextProperty("showSetup", False)
        engine.load(
            QUrl.fromLocalFile(
                str(Path(__file__).resolve().parents[1] / "client/rampi/qml/Main.qml")
            )
        )
        window = engine.rootObjects()[0]
        window.requestActivate()
        dialog = window.findChild(QObject, "settingsDialog")
        window.findChild(QObject, "settingsTabs").setProperty("currentIndex", 1)
        QMetaObject.invokeMethod(dialog, "open")
        wait_until(lambda: dialog.property("opened"))
        require(window.activeFocusItem().property("visible"), "Dialog focused hidden content")
        wait_until(lambda: bool(backend.wifi["networks"]))
        picker = window.findChild(QObject, "wifiPicker")
        picker.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Down)
        require(picker.property("currentIndex") == 0, "Keyboard did not select fixture WLAN")
        require("Lab:\\Rampi" in picker.property("currentText"), "SSID was parsed incorrectly")
        secret = uuid.uuid4().hex
        field = window.findChild(QObject, "wifiPassword")
        field.forceActiveFocus()
        for character in secret:
            QTest.keyClick(window, Qt.Key(ord(character.upper())))
        require(field.property("text") == secret, "Keyboard did not enter the WLAN password")
        require(field.property("displayText") != secret, "WLAN password is not masked")
        QTest.keyClick(window, Qt.Key.Key_Return)
        require(not field.property("text"), "Submitted password remains in the UI")
        wait_until(lambda: any(n["active"] for n in backend.wifi["networks"]))
        calls = controls.GetMethodCalls("AddAndActivateConnection2")
        require(len(calls) == 1, "The UI did not create exactly one profile")
        settings = calls[0][1][0]
        require(
            list(settings["connection"]["permissions"]) == [f"user:{linux_username()}:"],
            "New WLAN profile lost its user ACL",
        )
        require(
            settings["802-11-wireless-security"]["psk"] == secret,
            "D-Bus lost the submitted WLAN credential",
        )
        require(all(secret not in text for text in messages), "Credential leaked into messages")
        require(secret not in repr(backend.wifi), "Credential leaked into UI metadata")
        require(
            not any(
                secret.encode() in p.read_bytes() for p in Path(directory).rglob("*") if p.is_file()
            ),
            "Credential leaked into Rampi configuration or cache",
        )
        disconnect = window.findChild(QObject, "wifiDisconnect")
        disconnect.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Return)
        wait_until(lambda: not backend.wifi["busy"])
        require(not backend.wifi["networks"][0]["active"], "Disconnect left WLAN active")
        require(len(dev.GetMethodCalls("Disconnect")) == 1, "Disconnect did not reach D-Bus")
        # A refresh preserves selection; the existing profile is reused on reconnect.
        backend.refreshWifi(False)
        wait_until(lambda: not backend.wifi["busy"])
        require(picker.property("currentIndex") == 0, "Refresh lost WLAN selection")
        backend.connectWifi(backend.wifi["networks"][0]["key"], "")
        wait_until(lambda: not backend.wifi["busy"])
        require(
            len(controls.GetMethodCalls("ActivateConnection")) == 1, "Saved profile was not reused"
        )
        require(
            len(controls.GetMethodCalls("AddAndActivateConnection2")) == 1,
            "Reconnect created a duplicate profile",
        )
        scan = window.findChild(QObject, "wifiScan")
        scan.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Return)
        wait_until(lambda: not backend.wifi["busy"])
        require(len(dev.GetMethodCalls("RequestScan")) == 1, "Scan did not reach D-Bus")
        radio = window.findChild(QObject, "wifiRadio")
        radio.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Return)
        wait_until(lambda: not backend.wifi["busy"])
        require(
            not backend.wifi["enabled"] and not backend.wifi["networks"],
            "Radio disable did not update the UI",
        )
        QTest.keyClick(window, Qt.Key.Key_Return)
        wait_until(lambda: not backend.wifi["busy"])
        require(
            backend.wifi["enabled"] and backend.wifi["networks"],
            "Radio enable did not restore the WLAN list",
        )
        require(not warnings, "QML emitted warnings")
        backend.jobs.pool.waitForDone(25000)
        engine.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
finally:
    process.terminate()
    process.wait(timeout=10)
    dbusmock.DBusTestCase.tearDownClass()
print(
    "PASS: actual QML keyboard, masked password, private D-Bus settings, profile reuse; "
    "isolated NetworkManager fixture only, no radio or wireless authentication test."
)
