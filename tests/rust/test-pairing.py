"""Actual Rust Agent1 screens and replies on a private BlueZ fixture, no radio."""

import os
import subprocess
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Disposable test container required")

import dbus  # noqa: E402
import dbusmock  # noqa: E402

dbusmock.DBusTestCase.start_system_bus()
process, obj = dbusmock.DBusTestCase.spawn_server_template("bluez5", {}, stdout=subprocess.DEVNULL)
try:
    bus = dbusmock.DBusTestCase.get_dbus(True)
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
    result = subprocess.run(
        ["/build/target/debug/rampi-native", "--pairing-ui-check"],
        capture_output=True,
        text=True,
        timeout=40,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), dbusmock.MOCK_IFACE)
    assert len(manager.GetMethodCalls("RequestDefaultAgent")) == 0
    print(result.stdout.strip())
finally:
    process.terminate()
    process.wait(timeout=10)
    dbusmock.DBusTestCase.tearDownClass()
print(
    "PASS: Rust Agent1 confirmation, PIN, passkey, cancellation and spoof rejection; fixture only."
)
