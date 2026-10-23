"""Actual Rust Agent1 screens and replies on a private BlueZ fixture, no radio."""

import os
import subprocess
import tempfile
import time
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Disposable test container required")

import dbus  # noqa: E402
import dbusmock  # noqa: E402

dbusmock.DBusTestCase.start_system_bus()


def configure(obj):
    mock = dbus.Interface(obj, "org.bluez.Mock")
    mock.AddAdapter("hci0", "Virtual pairing fixture")
    mock.AddDevice("hci0", "02:00:00:00:00:01", "Fixture keyboard")
    control = dbus.Interface(obj, dbusmock.MOCK_IFACE)
    control.AddMethod(
        "org.bluez.Mock",
        "CallAgent",
        "ssav",
        "s",
        "peer = self.connection.get_object(args[0], '/org/rampi/PairingAgent', introspect=False); "
        "method = getattr(dbus.Interface(peer, 'org.bluez.Agent1'), args[1]); "
        "values = [dbus.ObjectPath(str(args[2][0]))] if args[2] else []; "
        "values += [(dbus.String(str(args[2][1])) "
        "if args[1] in ['DisplayPinCode', 'AuthorizeService'] "
        "else dbus.UInt32(int(args[2][1])))] if len(args[2]) > 1 else []; "
        "values += [dbus.UInt16(int(args[2][2]))] if len(args[2]) > 2 else []; "
        "ret = str(method(*values, timeout=12))",
    )
    return dbus.Interface(obj, dbusmock.MOCK_IFACE)


process, obj = dbusmock.DBusTestCase.spawn_server_template("bluez5", {}, stdout=subprocess.DEVNULL)
application = None
try:
    bus = dbusmock.DBusTestCase.get_dbus(True)
    configure(obj)
    old_owner = str(bus.get_name_owner("org.bluez"))
    with tempfile.TemporaryDirectory(prefix="rampi-pairing-restart-") as directory:
        application = subprocess.Popen(
            ["/build/target/debug/rampi-native", "--pairing-ui-check"],
            env={**os.environ, "RAMPI_TEST_PAIRING_DIR": directory},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 30
        while not (Path(directory) / "restart-request").exists():
            if application.poll() is not None or time.monotonic() > deadline:
                output, error = application.communicate(timeout=5)
                raise RuntimeError("No restart request: " + output + error)
            time.sleep(0.05)
        process.terminate()
        process.wait(timeout=10)
        process, obj = dbusmock.DBusTestCase.spawn_server_template(
            "bluez5", {}, stdout=subprocess.DEVNULL
        )
        configure(obj)
        assert str(bus.get_name_owner("org.bluez")) != old_owner
        (Path(directory) / "restart-ready").write_text("ready")
        output, error = application.communicate(timeout=20)
        if application.returncode:
            raise RuntimeError(output + error)
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), dbusmock.MOCK_IFACE)
    assert len(manager.GetMethodCalls("RequestDefaultAgent")) == 0
    assert len(manager.GetMethodCalls("RegisterAgent")) >= 1, "Agent not registered after restart"
    print(output.strip())
finally:
    if application is not None and application.poll() is None:
        application.terminate()
        application.wait(timeout=5)
    process.terminate()
    process.wait(timeout=10)
    dbusmock.DBusTestCase.tearDownClass()
print(
    "PASS: Rust Agent1 PIN/passkey, entered count, peer cancel/release, service restart "
    "and spoof rejection; fixture only."
)
