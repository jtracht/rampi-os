"""Authoritative dashboard state on private NM/BlueZ fixtures plus an actual TCP listener."""

import os
import socket
import subprocess
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Disposable test container required")

import dbus  # noqa: E402
import dbusmock  # noqa: E402

dbusmock.DBusTestCase.start_system_bus()
network, nm = dbusmock.DBusTestCase.spawn_server_template(
    "networkmanager", {}, stdout=subprocess.DEVNULL
)
bluetooth, bluez = dbusmock.DBusTestCase.spawn_server_template(
    "bluez5", {}, stdout=subprocess.DEVNULL
)
listener = socket.socket()
try:
    listener.bind(("127.0.0.1", 22223))
    listener.listen(8)
    mock = dbus.Interface(nm, dbusmock.MOCK_IFACE)
    device = mock.AddWiFiDevice("dashboard", "wlan_dashboard", 100)
    ap = mock.AddAccessPoint(
        device, "dashboard", "Dashboard fixture", "02:00:00:00:00:01", 2, 2412, 54000, 80, 0
    )
    connection = mock.AddWiFiConnection(device, "dashboard", "Dashboard fixture", "")
    mock.AddActiveConnection([device], connection, ap, "dashboard", 2)
    mock.AddProperties("org.freedesktop.NetworkManager", {"WirelessEnabled": dbus.Boolean(True)})
    control = dbus.Interface(bluez, "org.bluez.Mock")
    adapter = control.AddAdapter("hci0", "Dashboard fixture")
    bt_device = control.AddDevice("hci0", "02:00:00:00:00:01", "Dashboard keyboard")
    bus = dbusmock.DBusTestCase.get_dbus(True)
    dbus.Interface(bus.get_object("org.bluez", bt_device), dbusmock.MOCK_IFACE).UpdateProperties(
        "org.bluez.Device1", {"Connected": dbus.Boolean(True)}
    )
    result = subprocess.run(
        ["/build/target/debug/rampi-native", "--dashboard-check"],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    assert not mock.GetMethodCalls("ActivateConnection")
    assert not mock.GetMethodCalls("AddAndActivateConnection2")
    assert not dbus.Interface(
        bus.get_object("org.bluez", adapter), dbusmock.MOCK_IFACE
    ).GetMethodCalls("StartDiscovery")
    print(result.stdout.strip())
finally:
    listener.close()
    for process in [bluetooth, network]:
        process.terminate()
        process.wait(timeout=10)
    dbusmock.DBusTestCase.tearDownClass()
print("PASS: dashboard state, routing, profile refresh and offline handling; no radio/login proof.")
