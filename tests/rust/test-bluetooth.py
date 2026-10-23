"""Exercise the production Rust/GIO BlueZ adapter on a private fixture bus.

This validates D-Bus contracts and discovery-client cleanup, not radio pairing,
Agent1 PIN/passkey screens or a physical Bluetooth controller.
"""

import os
import subprocess
import sys
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Use only the designated disposable test container")

import dbus  # noqa: E402
import dbusmock  # noqa: E402

dbusmock.DBusTestCase.start_system_bus()
process, obj = dbusmock.DBusTestCase.spawn_server_template("bluez5", {}, stdout=subprocess.DEVNULL)
try:
    bus = dbusmock.DBusTestCase.get_dbus(True)
    control = dbus.Interface(obj, "org.bluez.Mock")
    adapter = control.AddAdapter("hci0", "Rust test adapter")
    # Debian's template reads its optional DiscoveryFilter from StartDiscovery
    # without initializing it. Initialize through its existing official method.
    dbus.Interface(bus.get_object("org.bluez", adapter), "org.bluez.Adapter1").SetDiscoveryFilter(
        dbus.Dictionary({}, signature="sv")
    )
    device = control.AddDevice("hci0", "02:00:00:00:00:01", "Rust test keyboard")
    # The distro template emits Connected but omits the corresponding stored
    # property update. Keep ObjectManager/GetAll consistent with that signal.
    device_mock = dbus.Interface(bus.get_object("org.bluez", device), dbusmock.MOCK_IFACE)
    for method, connected in [("Connect", True), ("Disconnect", False)]:
        device_mock.AddMethod(
            "org.bluez.Device1",
            method,
            "",
            "",
            f"self.connected = {connected}; "
            f"self.Set('org.bluez.Device1', 'Connected', dbus.Boolean({connected}))",
        )
    ui = "--ui" in sys.argv
    result = subprocess.run(
        ["/build/target/debug/rampi-native", "--bluetooth-ui-check" if ui else "--bluetooth-check"],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ},
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    methods = dbus.Interface(bus.get_object("org.bluez", adapter), dbusmock.MOCK_IFACE)
    assert len(methods.GetMethodCalls("StartDiscovery")) == (1 if ui else 2)
    assert len(methods.GetMethodCalls("StopDiscovery")) == (0 if ui else 1)
    assert len(methods.GetMethodCalls("RemoveDevice")) == (0 if ui else 1)
    print(result.stdout.strip())
finally:
    process.terminate()
    process.wait(timeout=10)
    dbusmock.DBusTestCase.tearDownClass()
print("PASS: Rust BlueZ operations and private discovery lifetime; fixture only.")
