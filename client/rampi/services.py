"""Adapters for established operating-system tools; polkit decides authorization."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

from .process import command


def inventory() -> dict[str, object]:
    names = [
        "nmcli",
        "bluetoothctl",
        "tailscale",
        "wg",
        "ssh",
        "xfreerdp3",
        "xfreerdp",
        "moonlight",
        "chromium",
        "firefox-esr",
        "xfce4-terminal",
        "systemctl",
    ]
    return {"platform": os.name, "programs": {name: shutil.which(name) or "" for name in names}}


def network_status() -> str:
    if os.name != "posix":
        raise RuntimeError("NetworkManager ist auf diesem System nicht verfügbar.")
    from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusVariant

    bus = QDBusConnection.systemBus()
    interface = QDBusInterface(
        "org.freedesktop.NetworkManager",
        "/org/freedesktop/NetworkManager",
        "org.freedesktop.DBus.Properties",
        bus,
    )
    if not interface.isValid():
        raise RuntimeError("NetworkManager-D-Bus ist nicht erreichbar.")
    reply = interface.call("Get", "org.freedesktop.NetworkManager", "State")
    if reply.errorMessage():
        raise RuntimeError(reply.errorMessage())
    state = reply.arguments()[0]
    if isinstance(state, QDBusVariant):
        state = state.variant()
    return {
        70: "Verbunden",
        60: "Standortnetz",
        50: "Lokales Netz",
        40: "Verbinde …",
        30: "Trenne …",
        20: "Getrennt",
        10: "Schlafmodus",
    }.get(state, "Unbekannt")


def wifi_list() -> list[dict[str, str]]:
    # Escaped SSIDs must not be parsed with split(':').
    output = command(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"])
    result = []
    for line in output.splitlines():
        fields = re.split(r"(?<!\\):", line)
        if len(fields) == 3 and fields[0]:
            result.append(
                dict(
                    zip(
                        ("ssid", "signal", "security"),
                        [f.replace(r"\:", ":").replace(r"\\", "\\") for f in fields],
                        strict=True,
                    )
                )
            )
    return result


def bluetooth_status() -> str:
    return command(["bluetoothctl", "show"])


def tailscale_status() -> str:
    data = json.loads(command(["tailscale", "status", "--json"]))
    return str(data.get("BackendState", "Unknown"))


def tailscale_action(action: str) -> str:
    if action not in {"up", "down"}:
        raise ValueError("Unbekannte Tailscale-Aktion.")
    program = shutil.which("tailscale")
    if not program:
        raise RuntimeError("Tailscale ist nicht installiert.")
    path = Path(program).resolve()
    if os.name != "posix" or path.stat().st_uid != 0:
        raise RuntimeError(
            "Privilegierte VPN-Aktionen benötigen eine root-eigene Linux-Installation."
        )
    args = ["pkexec", str(path), action]
    if action == "up":
        args += ["--timeout=30s"]
    return command(args, timeout=90)


def wireguard_profiles() -> str:
    return command(["nmcli", "-t", "-f", "UUID,NAME,TYPE,ACTIVE", "connection", "show"])


def linux_username() -> str:
    if os.name != "posix":
        raise RuntimeError("Linux-Systemkonto benötigt.")
    import pwd

    return pwd.getpwuid(os.getuid()).pw_name  # type: ignore[attr-defined]


def personal_wireguard_profiles() -> list[dict[str, object]]:
    """Read libnm metadata only. Shared and other users' profiles are excluded."""
    if os.name != "posix":
        raise RuntimeError("NetworkManager-Profile sind nur unter Linux verfügbar.")
    import gi

    gi.require_version("NM", "1.0")
    from gi.repository import NM

    client = NM.Client.new(None)
    if not client.get_nm_running():
        raise RuntimeError("NetworkManager ist nicht erreichbar.")
    active = {connection.get_uuid() for connection in client.get_active_connections()}
    permissions = [f"user:{linux_username()}:"]
    profiles = []
    for connection in client.get_connections():
        setting = connection.get_setting_connection()
        if (
            setting is None
            or setting.get_connection_type() != "wireguard"
            or list(setting.props.permissions) != permissions
        ):
            continue
        identifier = setting.get_uuid()
        name = setting.get_id()
        connected = identifier in active
        profiles.append(
            {
                "uuid": identifier,
                "name": name,
                "active": connected,
                "label": name + (" · Verbunden" if connected else " · Getrennt"),
            }
        )
    return sorted(profiles, key=lambda item: str(item["name"]).casefold())


def wireguard_connection(filename: str, username: str):
    path = Path(filename).expanduser().resolve(strict=True)
    if path.suffix != ".conf" or path.stat().st_size > 65536:
        raise ValueError("Eine WireGuard-Konfiguration (.conf, höchstens 64 KiB) auswählen.")
    # libnm parses WireGuard; set permissions BEFORE adding it to the system service.
    # No shared transient profile and no auto-connect/routing race during import.
    import gi

    gi.require_version("NM", "1.0")
    from gi.repository import NM, GLib

    try:
        connection = NM.conn_wireguard_import(str(path))
    except GLib.Error as exc:
        raise ValueError("WireGuard-Konfiguration konnte nicht sicher importiert werden.") from exc
    setting = connection.get_setting_connection()
    setting.props.autoconnect = False
    setting.add_permission("user", username, None)
    connection.verify()
    return connection


def wireguard_import(filename: str) -> str:
    connection = wireguard_connection(filename, linux_username())
    from gi.repository import NM, Gio, GLib

    setting = connection.get_setting_connection()
    properties = connection.to_dbus(NM.ConnectionSerializationFlags.ALL)
    parameters = GLib.Variant.new_tuple(properties, GLib.Variant("u", 1), GLib.Variant("a{sv}", {}))
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    bus.call_sync(
        "org.freedesktop.NetworkManager",
        "/org/freedesktop/NetworkManager/Settings",
        "org.freedesktop.NetworkManager.Settings",
        "AddConnection2",
        parameters,
        GLib.VariantType.new("(oa{sv})"),
        Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION,
        30000,
        None,
    )
    return f"Persönliches WireGuard-Profil importiert, Autostart aus. UUID: {setting.get_uuid()}"


def network_action(action: str, value: str = "") -> str:
    if action == "status":
        return wireguard_profiles()
    if action == "import":
        return wireguard_import(value)
    if action not in {"up", "down"}:
        raise ValueError("Unbekannte Netzwerkaktion.")
    if not value or len(value) > 200 or "\x00" in value:
        raise ValueError("Ein gültiges Verbindungsprofil auswählen.")
    # UUID prevents interpreting a profile name as a switch.
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        raise ValueError("Bitte die UUID des NetworkManager-Profils verwenden.")
    return command(["nmcli", "connection", action, "uuid", value], timeout=60)
