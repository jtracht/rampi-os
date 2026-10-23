"""Actual Rust/GIO calls against the established private NM fixture, not WiFi radio."""

import os
import pwd
import subprocess
import tempfile
import uuid
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Use only the designated disposable test container")

import dbus  # noqa: E402
import dbusmock  # noqa: E402

NM = "org.freedesktop.NetworkManager"
ROOT = "/org/freedesktop/NetworkManager"
dbusmock.DBusTestCase.start_system_bus()
process, obj = dbusmock.DBusTestCase.spawn_server_template(
    "networkmanager", {}, stdout=subprocess.DEVNULL
)
try:
    bus = dbusmock.DBusTestCase.get_dbus(True)
    mock = dbus.Interface(obj, dbusmock.MOCK_IFACE)
    controls = dbus.Interface(bus.get_object(NM, ROOT), dbusmock.MOCK_IFACE)
    device = mock.AddWiFiDevice("rust_test", "wlan_rust", 30)
    mock.AddAccessPoint(
        device, "rust_ap", "Rust\\Lab:Private", "02:00:00:00:00:01", 2, 2412, 54000, 82, 256
    )
    dev = dbus.Interface(bus.get_object(NM, device), dbusmock.MOCK_IFACE)
    dev.UpdateProperties(NM + ".Device", {"Managed": dbus.Boolean(True)})
    dev.AddProperties(
        NM + ".Device.Wireless",
        {"ActiveAccessPoint": dbus.ObjectPath("/"), "LastScan": dbus.Int64(0)},
    )
    dev.AddMethod(
        NM + ".Device",
        "Disconnect",
        "",
        "",
        f"self.Set('{NM}.Device', 'State', dbus.UInt32(30)); "
        f"self.Set('{NM}.Device.Wireless', 'ActiveAccessPoint', dbus.ObjectPath('/'))",
    )
    dev.AddMethod(NM + ".Device.Wireless", "RequestScan", "a{sv}", "", "")
    controls.AddMethod(
        NM,
        "AddAndActivateConnection2",
        "a{sa{sv}}ooa{sv}",
        "ooa{sv}",
        "ap = args[2] if str(args[2]) != '/' else objects[args[1]].access_points[0]; "
        "pair = self.add_and_activate_connection(self, args[0], args[1], ap); "
        "objects[pair[0]].settings = args[0]; "
        + f"objects[args[1]].Set('{NM}.Device.Wireless', 'ActiveAccessPoint', args[2]); "
        + "ret = (pair[0], pair[1], {})",
    )
    with tempfile.TemporaryDirectory(prefix="rampi-rust-nm-") as directory:
        secret = uuid.uuid4().hex
        key = Path(directory) / "key"
        key.write_text(secret)
        key.chmod(0o600)
        env = {
            **os.environ,
            "RAMPI_TEST_SECRET_FILE": str(key),
            "XDG_CONFIG_HOME": directory,
            "XDG_CACHE_HOME": directory,
        }
        result = subprocess.run(
            ["/build/target/debug/rampi-native", "--service-check"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        calls = controls.GetMethodCalls("AddAndActivateConnection2")
        assert len(calls) == 2, "Rust created duplicate WLAN profiles"
        profile = calls[0][1][0]
        assert list(profile["connection"]["permissions"]) == [
            f"user:{pwd.getpwuid(os.getuid()).pw_name}:"
        ]
        assert profile["802-11-wireless-security"]["psk"] == secret
        assert len(controls.GetMethodCalls("ActivateConnection")) == 2
        hidden = calls[1][1]
        assert str(hidden[2]) == "/"
        assert hidden[0]["802-11-wireless"]["hidden"]
        assert hidden[0]["802-11-wireless-security"]["key-mgmt"] == "sae"
        assert list(hidden[0]["connection"]["permissions"]) == [
            f"user:{pwd.getpwuid(os.getuid()).pw_name}:"
        ]
        assert secret not in result.stdout + result.stderr
        assert not any(
            secret.encode() in p.read_bytes()
            for p in Path(directory).rglob("*")
            if p.is_file() and p != key
        )
        print(result.stdout.strip())
finally:
    process.terminate()
    process.wait(timeout=10)
    dbusmock.DBusTestCase.tearDownClass()
print(
    "PASS: Rust scan, private profile/password, saved-profile reuse, "
    "disconnect and radio state; fixture only."
)
