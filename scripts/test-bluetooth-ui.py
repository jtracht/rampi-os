"""Actual QML/BlueZ-agent contract on an isolated python-dbusmock bus, no radio."""

import os
import subprocess
import tempfile
import threading
from pathlib import Path

if not Path("/.dockerenv").exists() or os.environ.get("RAMPI_TEST_CONTAINER") != "1":
    raise SystemExit("Run only in the designated disposable container")

import dbus  # noqa: E402
import dbusmock  # noqa: E402
from gi.repository import Gio  # noqa: E402
from PySide6.QtCore import QEvent, QEventLoop, QMetaObject, QObject, Qt, QTimer, QUrl  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402, F401
from PySide6.QtTest import QTest  # noqa: E402
from rampi.app import create_application  # noqa: E402
from rampi.backend import Backend  # noqa: E402
from rampi.bluetooth import AGENT, BLUEZ  # noqa: E402
from rampi.config import Settings  # noqa: E402


def require(value, message):
    if not value:
        raise RuntimeError(message)


def wait_until(condition):
    for _ in range(600):
        if condition():
            return
        loop = QEventLoop()
        QTimer.singleShot(25, loop.quit)
        loop.exec()
    raise RuntimeError("Bluetooth fixture UI operation timed out")


dbusmock.DBusTestCase.start_system_bus()
process, obj = dbusmock.DBusTestCase.spawn_server_template("bluez5", {}, stdout=subprocess.DEVNULL)
backend = None
try:
    bus = dbusmock.DBusTestCase.get_dbus(True)
    mock = dbus.Interface(obj, "org.bluez.Mock")
    adapter = mock.AddAdapter("hci0", "Test Bluetooth")
    device = mock.AddDevice("hci0", "02:00:00:00:00:01", "Test Keyboard")
    device_mock = dbus.Interface(bus.get_object(BLUEZ, device), dbusmock.MOCK_IFACE)
    # The template emits connection changes but older Debian versions leave
    # GetManagedObjects stale. Keep its methods and synchronize the advertised state.
    for method, value in (("Connect", True), ("Disconnect", False)):
        device_mock.AddMethod(
            BLUEZ + ".Device1",
            method,
            "",
            "",
            f"from dbusmock.templates.bluez5 import {method}; {method}(self); "
            f"self.Set('org.bluez.Device1', 'Connected', dbus.Boolean({value}))",
        )
    root_mock = dbus.Interface(obj, dbusmock.MOCK_IFACE)
    root_mock.AddMethod(
        "org.bluez.Mock",
        "CallAgent",
        "ssav",
        "s",
        "peer = self.connection.get_object(args[0], '" + AGENT + "', introspect=False); "
        "method = getattr(dbus.Interface(peer, 'org.bluez.Agent1'), args[1]); "
        "values = [dbus.ObjectPath(str(args[2][0]))] if args[2] else []; "
        "values += [(dbus.String(str(args[2][1])) "
        "if args[1] in ['DisplayPinCode', 'AuthorizeService'] "
        "else dbus.UInt32(int(args[2][1])))] if len(args[2]) > 1 else []; "
        "values += [dbus.UInt16(int(args[2][2]))] if len(args[2]) > 2 else []; "
        "ret = str(method(*values, timeout=12))",
    )
    with tempfile.TemporaryDirectory(prefix="rampi-bluetooth-ui-") as directory:
        os.environ["XDG_CONFIG_HOME"] = directory
        os.environ["XDG_CACHE_HOME"] = directory
        app = create_application()
        backend = Backend(Settings(setup_complete=True))
        messages = []
        backend.message.connect(messages.append)
        backend.timer.stop()
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
        window.findChild(QObject, "settingsTabs").setProperty("currentIndex", 3)
        QMetaObject.invokeMethod(dialog, "open")
        wait_until(lambda: dialog.property("visible") and bool(backend.bluetooth["devices"]))
        picker = window.findChild(QObject, "bluetoothDevice")
        picker.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Down)
        require(
            picker.property("currentValue") == device,
            "Keyboard did not select the Bluetooth device",
        )
        destination = Gio.bus_get_sync(Gio.BusType.SYSTEM, None).get_unique_name()
        # A process with the same Unix user still may not impersonate bluetoothd.
        peer = bus.get_object(destination, AGENT, introspect=False)
        try:
            dbus.Interface(peer, BLUEZ + ".Agent1").RequestConfirmation(
                dbus.ObjectPath(device), dbus.UInt32(123456)
            )
        except dbus.exceptions.DBusException as error:
            require(
                error.get_dbus_name() == BLUEZ + ".Error.Rejected",
                "Unexpected spoofed-caller error",
            )
        else:
            raise RuntimeError("The agent accepted a caller other than the BlueZ owner")
        require(not backend.bluetoothChallenge, "Foreign caller opened a pairing prompt")

        def challenge(method, parameters):
            result = []

            def invoke():
                try:
                    result.append(
                        mock.CallAgent(destination, method, dbus.Array(parameters, signature="v"))
                    )
                except Exception as error:
                    result.append(error)

            thread = threading.Thread(target=invoke, daemon=True)
            thread.start()
            wait_until(lambda: bool(backend.bluetoothChallenge) or bool(result))
            require(bool(backend.bluetoothChallenge), "Agent invocation failed: " + repr(result))
            return thread, result

        thread, result = challenge(
            "RequestConfirmation", [dbus.ObjectPath(device), dbus.UInt32(123456)]
        )
        pairing = window.findChild(QObject, "bluetoothPairingDialog")
        wait_until(lambda: pairing.property("visible"))
        accept = window.findChild(QObject, "bluetoothPairingAccept")
        require(not accept.property("enabled"), "A code was confirmed without conscious comparison")
        require(
            window.findChild(QObject, "bluetoothPairingCode").property("text") == "123456",
            "The actual confirmation code was not displayed",
        )
        reviewed = window.findChild(QObject, "bluetoothPairingReviewed")
        reviewed.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        accept.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Return)
        wait_until(lambda: bool(result))
        thread.join(timeout=2)
        require(not isinstance(result[0], Exception), "BlueZ did not receive confirmation")
        require(not backend.bluetoothChallenge, "Completed confirmation remained visible")
        for kind, expected in (("RequestPasskey", "000042"), ("RequestPinCode", "12ab")):
            thread, result = challenge(kind, [dbus.ObjectPath(device)])
            wait_until(lambda: pairing.property("visible"))
            field = window.findChild(QObject, "bluetoothPairingPin")
            field.forceActiveFocus()
            for character in expected:
                QTest.keyClick(
                    window,
                    Qt.Key(ord(character.upper())),
                )
            backend.changed.emit()
            require(field.property("text") == expected, "A status update erased pairing input")
            QTest.keyClick(window, Qt.Key.Key_Return)
            wait_until(lambda result=result: bool(result))
            thread.join(timeout=2)
            require(
                str(result[0]) == (str(int(expected)) if kind == "RequestPasskey" else expected),
                "PIN/passkey D-Bus reply lost the actual test input: " + repr(result),
            )
            require(not field.property("text"), "Pairing input was retained")
        thread, result = challenge("RequestAuthorization", [dbus.ObjectPath(device)])
        wait_until(lambda: pairing.property("visible"))
        QTest.keyClick(window, Qt.Key.Key_Escape)
        wait_until(lambda: bool(result))
        thread.join(timeout=2)
        require(isinstance(result[0], Exception), "Escape did not reject pairing")
        require(dialog.property("visible"), "Rejecting pairing also closed the settings dialog")
        for method, values, displayed in (
            ("DisplayPinCode", [dbus.ObjectPath(device), dbus.String("123456")], "123456"),
            (
                "DisplayPasskey",
                [dbus.ObjectPath(device), dbus.UInt32(42), dbus.UInt16(2)],
                "000042",
            ),
        ):
            mock.CallAgent(destination, method, dbus.Array(values, signature="v"))
            wait_until(lambda: pairing.property("visible"))
            require(
                window.findChild(QObject, "bluetoothPairingCode").property("text") == displayed,
                "Keyboard pairing code was not displayed correctly",
            )
            mock.CallAgent(destination, "Cancel", dbus.Array([], signature="v"))
            wait_until(lambda: not backend.bluetoothChallenge)

        def press(name):
            wait_until(lambda: not backend.bluetooth["busy"])
            button = window.findChild(QObject, name)
            require(button.property("enabled"), "Actual Bluetooth action is disabled: " + name)
            button.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_Return)

        def dismiss_message():
            notice = window.findChild(QObject, "notificationDialog")
            if notice.property("visible"):
                QTest.keyClick(window, Qt.Key.Key_Escape)
                wait_until(lambda: not notice.property("visible"))

        press("bluetoothScan")
        wait_until(lambda: bool(messages))
        require(messages[-1] == "Gerätesuche gestartet.", "Discovery failed: " + repr(messages))
        wait_until(lambda: bool(backend.bluetooth["adapters"][0]["own_scan"]))
        dismiss_message()
        press("bluetoothPair")
        wait_until(lambda: backend.bluetooth["devices"][0]["paired"])
        dismiss_message()
        press("bluetoothConnect")
        wait_until(lambda: backend.bluetooth["devices"][0]["connected"])
        dismiss_message()
        press("bluetoothTrust")
        confirmation = window.findChild(QObject, "bluetoothActionConfirmation")
        wait_until(lambda: confirmation.property("visible"))
        QTest.keyClick(window, Qt.Key.Key_Escape)
        require(
            not backend.bluetooth["devices"][0]["trusted"], "Cancelled trust action was applied"
        )
        press("bluetoothTrust")
        wait_until(lambda: confirmation.property("visible"))
        press("bluetoothConfirmYes")
        wait_until(lambda: backend.bluetooth["devices"][0]["trusted"])
        dismiss_message()
        press("bluetoothConnect")
        wait_until(lambda: not backend.bluetooth["devices"][0]["connected"])
        dismiss_message()
        press("bluetoothRemove")
        wait_until(lambda: confirmation.property("visible"))
        press("bluetoothConfirmYes")
        wait_until(lambda: not backend.bluetooth["devices"])
        dismiss_message()
        window.findChild(QObject, "settingsTabs").setProperty("currentIndex", 0)
        wait_until(lambda: not backend.bluetooth["adapters"][0]["own_scan"])
        old_thread = backend.bt_agent.worker_thread
        process.terminate()
        process.wait(timeout=10)
        wait_until(lambda: not old_thread.is_alive())
        wait_until(lambda: not backend.bluetooth["adapters"])
        process, obj = dbusmock.DBusTestCase.spawn_server_template(
            "bluez5", {}, stdout=subprocess.DEVNULL
        )
        replacement = dbus.Interface(obj, "org.bluez.Mock")
        replacement.AddAdapter("hci1", "Restarted Bluetooth")
        backend.refreshBluetooth()
        wait_until(lambda: bool(backend.bluetooth["adapters"]))
        require(
            backend.bluetooth["adapters"][0]["path"] == "/org/bluez/hci1",
            "BlueZ restart retained an obsolete adapter",
        )
        backend.jobs.pool.waitForDone(20000)
        backend.bt_agent.close()
        require(not warnings, "QML emitted warnings during Bluetooth pairing")
        engine.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
finally:
    if backend:
        backend.bt_agent.close()
    process.terminate()
    process.wait(timeout=10)
    dbusmock.DBusTestCase.tearDownClass()
print(
    "PASS: real QML keyboard, BlueZ caller authentication, explicit code comparison, "
    "typed PIN/passkey replies and Escape rejection; isolated D-Bus fixture only."
)
