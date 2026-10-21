"""Actual libnm import and Rust/GIO contracts; isolated NM fixture, no tunnel."""

import os
import pwd
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

if os.environ.get("RAMPI_TEST_CONTAINER") != "1" or not Path("/.dockerenv").exists():
    raise SystemExit("Requires the disposable test container")

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
    settings = dbus.Interface(bus.get_object(NM, ROOT + "/Settings"), NM + ".Settings")
    controls = dbus.Interface(bus.get_object(NM, ROOT + "/Settings"), dbusmock.MOCK_IFACE)
    controls.AddMethod(
        NM + ".Settings",
        "AddConnection2",
        "a{sa{sv}}ua{sv}",
        "oa{sv}",
        "ret = (self.SettingsAddConnection(args[0]), {})",
    )
    manager = dbus.Interface(bus.get_object(NM, ROOT), dbusmock.MOCK_IFACE)
    # The template's default deactivation only handles device-backed connections.
    manager.AddMethod(
        NM,
        "DeactivateConnection",
        "o",
        "",
        f"remaining = [p for p in self.Get('{NM}', 'ActiveConnections') if p != args[0]]; "
        f"self.Set('{NM}', 'ActiveConnections', dbus.Array(remaining, signature='o'))",
    )
    user = pwd.getpwuid(os.getuid()).pw_name
    denied = []
    for name, permissions, kind in [
        ("Personal: VPN\\Lab", [f"user:{user}:"], "wireguard"),
        ("Shared", [], "wireguard"),
        ("Foreign", ["user:rampi-other:"], "wireguard"),
        ("Shared with another", [f"user:{user}:", "user:rampi-other:"], "wireguard"),
        ("Other type", [f"user:{user}:"], "802-3-ethernet"),
    ]:
        identifier = str(uuid.uuid4())
        settings.AddConnection(
            {
                "connection": {
                    "id": name,
                    "type": kind,
                    "uuid": identifier,
                    "permissions": dbus.Array(permissions, signature="s"),
                    "autoconnect": dbus.Boolean(False),
                }
            }
        )
        if name != "Personal: VPN\\Lab":
            denied.append(identifier)
    with tempfile.TemporaryDirectory(prefix="rampi-rust-wg-") as directory:
        path = Path(directory) / "rampi-test.conf"
        key = subprocess.check_output(["wg", "genkey"], text=True).strip()
        peer = subprocess.run(
            ["wg", "pubkey"], input=key + "\n", capture_output=True, text=True, check=True
        ).stdout.strip()
        content = (
            f"[Interface]\nPrivateKey={key}\nAddress=198.18.99.1/32\n"
            f"[Peer]\nPublicKey={peer}\nAllowedIPs=198.18.99.2/32\n"
        )
        path.write_text(content)
        path.chmod(0o600)
        bad = Path(directory) / "bad.conf"
        bad.write_text("[Interface]\nPrivateKey=invalid-private-key-value\n")
        bad.chmod(0o600)
        ui = "--ui" in sys.argv
        result = subprocess.run(
            ["/build/target/debug/rampi-native", "--vpn-ui-check" if ui else "--wireguard-check"],
            env={
                **os.environ,
                "USER": "rampi-other",
                "LOGNAME": "rampi-other",
                "RAMPI_TEST_WG_FILE": str(path),
                "RAMPI_TEST_WG_INVALID": str(bad),
                "RAMPI_TEST_WG_DENY_UUIDS": ",".join(denied),
            },
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        calls = controls.GetMethodCalls("AddConnection2")
        assert len(calls) == 1
        profile, flags, args = calls[0][1]
        assert profile["connection"]["permissions"] == [f"user:{user}:"]
        assert not profile["connection"]["autoconnect"]
        assert flags == 1 and not args
        assert profile["wireguard"]["private-key"] == key
        assert len(manager.GetMethodCalls("ActivateConnection")) == 1
        assert len(manager.GetMethodCalls("DeactivateConnection")) == 1
        assert key not in result.stdout + result.stderr
        assert path.read_text() == content
        print(result.stdout.strip())
finally:
    process.terminate()
    process.wait(timeout=10)
    dbusmock.DBusTestCase.tearDownClass()
print(
    "PASS: real libnm parsing, private ACL before storage, manual activation "
    "and Rust/GIO contract; fixture only."
)
