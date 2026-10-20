"""Small adapter to NetworkManager's public D-Bus API; no radio implementation."""

from __future__ import annotations

import os
import time
import uuid

from .services import linux_username

NM = "org.freedesktop.NetworkManager"
ROOT = "/org/freedesktop/NetworkManager"


class NetworkManager:
    def __init__(self):
        if os.name != "posix":
            raise RuntimeError("WLAN-Einrichtung benötigt NetworkManager unter Linux.")
        from gi.repository import Gio, GLib

        self.gio, self.glib = Gio, GLib
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)

    def call(self, path, interface, method, signature=None, values=()):
        parameters = self.glib.Variant(signature, values) if signature else None
        try:
            return self.bus.call_sync(
                NM,
                path,
                interface,
                method,
                parameters,
                None,
                self.gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION,
                15000,
                None,
            ).unpack()
        except self.glib.Error as exc:
            # Never propagate D-Bus payloads, which may include a credential.
            raise RuntimeError(
                "NetworkManager konnte den WLAN-Auftrag nicht ausführen. "
                "Dienststatus und Berechtigung prüfen."
            ) from exc

    def properties(self, path, interface):
        return self.call(path, "org.freedesktop.DBus.Properties", "GetAll", "(s)", (interface,))[0]

    def settings(self, path):
        return self.call(path, NM + ".Settings.Connection", "GetSettings")[0]


def security_mode(ap: dict) -> str:
    rsn = ap.get("RsnFlags", 0)
    if rsn & 0x100:  # NM_802_11_AP_SEC_KEY_MGMT_PSK
        return "wpa-psk"
    if rsn & 0x400:  # NM_802_11_AP_SEC_KEY_MGMT_SAE
        return "sae"
    if not ap.get("Flags", 0) & 1 and not (rsn or ap.get("WpaFlags", 0)):
        return "open"
    return "unsupported"


def profile_settings(ssid: bytes, mode: str, password: str, username: str) -> dict:
    """Build ordinary NM settings; libnm performs authoritative validation."""
    if not 1 <= len(ssid) <= 32 or mode not in {"open", "wpa-psk", "sae"}:
        raise ValueError("Dieses WLAN benötigt den erweiterten Netzwerkdialog.")
    if mode == "open" and password:
        raise ValueError("Ein offenes WLAN verwendet kein Kennwort.")
    if mode != "open" and (not password or len(password.encode("utf-8")) > 256):
        raise ValueError("Ein gültiges WLAN-Kennwort eingeben.")
    # Imported only on Linux, keeping the native Windows dashboard usable offline.
    import gi

    gi.require_version("NM", "1.0")
    from gi.repository import NM as LibNM
    from gi.repository import GLib

    display = ssid.decode("utf-8", errors="replace")
    values = {
        "connection": {
            "id": GLib.Variant("s", "Rampi · " + display),
            "uuid": GLib.Variant("s", str(uuid.uuid4())),
            "type": GLib.Variant("s", "802-11-wireless"),
            "permissions": GLib.Variant("as", [f"user:{username}:"]),
            # Do not reconnect to a personal network after that user's logout.
            "autoconnect": GLib.Variant("b", False),
        },
        "802-11-wireless": {
            "ssid": GLib.Variant("ay", ssid),
            "mode": GLib.Variant("s", "infrastructure"),
        },
        "ipv4": {"method": GLib.Variant("s", "auto")},
        "ipv6": {"method": GLib.Variant("s", "auto")},
    }
    if mode != "open":
        values["802-11-wireless-security"] = {
            "key-mgmt": GLib.Variant("s", mode),
            "psk": GLib.Variant("s", password),
            "psk-flags": GLib.Variant("u", 0),
            "proto": GLib.Variant("as", ["rsn"]),
        }
    try:
        connection = LibNM.SimpleConnection.new_from_dbus(GLib.Variant("a{sa{sv}}", values))
        connection.verify()
        connection.verify_secrets()
    except GLib.Error as exc:
        raise ValueError("WLAN-Kennwort oder Verbindungseinstellungen sind ungültig.") from exc
    return values


def snapshot(scan: bool = False, *, manager=None) -> dict:
    nm = manager or NetworkManager()
    state = nm.properties(ROOT, NM)
    result: dict = {"networks": [], "enabled": bool(state["WirelessEnabled"]), "error": ""}
    if not state["WirelessHardwareEnabled"]:
        result["error"] = "WLAN ist am Gerät gesperrt."
        return result
    if not result["enabled"]:
        result["error"] = "WLAN ist ausgeschaltet."
        return result
    username = linux_username()
    found: dict[str, dict] = {}
    devices = 0
    for device in nm.call(ROOT, NM, "GetDevices")[0]:
        data = nm.properties(device, NM + ".Device")
        if data["DeviceType"] != 2 or not data.get("Managed", True):
            continue
        devices += 1
        wireless = nm.properties(device, NM + ".Device.Wireless")
        if scan:
            try:
                nm.call(device, NM + ".Device.Wireless", "RequestScan", "(a{sv})", ({},))
                for _ in range(24):
                    time.sleep(0.5)
                    current = nm.properties(device, NM + ".Device.Wireless")
                    if current.get("LastScan", -1) > wireless.get("LastScan", -1):
                        break
                else:
                    result["error"] = "Suche läuft noch; zuletzt bekannte WLANs werden angezeigt."
                wireless = current
            except RuntimeError:
                result["error"] = (
                    "Suche derzeit nicht möglich; zuletzt bekannte WLANs werden angezeigt."
                )
        saved = []
        for path in data.get("AvailableConnections", []):
            try:
                settings = nm.settings(path)
            except RuntimeError:
                continue  # Removed or no longer permitted during snapshot.
            permissions = settings.get("connection", {}).get("permissions", [])
            if permissions and f"user:{username}:" not in permissions:
                continue
            saved.append((path, settings))
        for ap in nm.call(device, NM + ".Device.Wireless", "GetAllAccessPoints")[0]:
            try:
                access = nm.properties(ap, NM + ".AccessPoint")
            except RuntimeError:
                continue  # Access point disappeared during the scan.
            ssid = bytes(access["Ssid"])
            if not ssid or access.get("Mode", 2) != 2:
                continue
            mode = security_mode(access)
            compatible = [
                path
                for path, profile in saved
                if bytes(profile.get("802-11-wireless", {}).get("ssid", [])) == ssid
                and profile.get("802-11-wireless-security", {}).get("key-mgmt", "open") == mode
            ]
            connected = wireless.get("ActiveAccessPoint") == ap and data.get("State") == 100
            label = "".join(c if c.isprintable() else "�" for c in ssid.decode("utf-8", "replace"))
            key = device + ":" + ssid.hex() + ":" + mode
            row = dict(
                key=key,
                ssid=label,
                raw_ssid=ssid.hex(),
                device=device,
                ap=ap,
                mode=mode,
                strength=int(access["Strength"]),
                active=connected,
                saved=bool(compatible),
                profile=compatible[0] if compatible else "",
                supported=mode != "unsupported",
            )
            security = {"open": "Offen", "wpa-psk": "WPA2/3", "sae": "WPA3"}.get(
                mode, "Erweiterte Einrichtung"
            )
            row["label"] = f"{label} · {row['strength']} % · {security}" + (
                " · Verbunden" if connected else " · Gespeichert" if compatible else ""
            )
            if key not in found or (connected, row["strength"]) > (
                found[key]["active"],
                found[key]["strength"],
            ):
                found[key] = row
    result["networks"] = sorted(
        found.values(), key=lambda n: (-n["active"], -n["strength"], n["ssid"])
    )
    if not devices:
        result["error"] = "Kein von NetworkManager verwaltetes WLAN-Gerät gefunden."
    elif not found and not result["error"]:
        result["error"] = (
            "Keine sichtbaren WLANs gefunden. Versteckte Netze im erweiterten Dialog einrichten."
        )
    return result


def connect(key: str, password: str, *, manager=None) -> str:
    nm = manager or NetworkManager()
    row = next((n for n in snapshot(manager=nm)["networks"] if n["key"] == key), None)
    if not row or not row["supported"]:
        raise ValueError("WLAN nicht mehr verfügbar oder nur im erweiterten Dialog einrichtbar.")
    if row["active"]:
        return "WLAN ist bereits verbunden."
    if row["saved"]:
        active = nm.call(
            ROOT, NM, "ActivateConnection", "(ooo)", (row["profile"], row["device"], row["ap"])
        )[0]
    else:
        settings = profile_settings(
            bytes.fromhex(row["raw_ssid"]), row["mode"], password, linux_username()
        )
        active = nm.call(
            ROOT,
            NM,
            "AddAndActivateConnection2",
            "(a{sa{sv}}ooa{sv})",
            (settings, row["device"], row["ap"], {}),
        )[1]
    for _ in range(120):
        state = nm.properties(active, NM + ".Connection.Active")["State"]
        if state == 2:
            return "WLAN verbunden."
        if state == 4:
            raise RuntimeError("WLAN-Verbindung fehlgeschlagen. Kennwort und Netzwerk prüfen.")
        time.sleep(0.5)
    nm.call(ROOT, NM, "DeactivateConnection", "(o)", (active,))
    raise RuntimeError("WLAN-Verbindung hat zu lange gedauert. Netzwerkdialog prüfen.")


def set_enabled(enabled: bool) -> str:
    nm = NetworkManager()
    nm.call(
        ROOT,
        "org.freedesktop.DBus.Properties",
        "Set",
        "(ssv)",
        (NM, "WirelessEnabled", nm.glib.Variant("b", enabled)),
    )
    return "WLAN eingeschaltet." if enabled else "WLAN ausgeschaltet."


def disconnect(key: str, *, manager=None) -> str:
    nm = manager or NetworkManager()
    row = next((n for n in snapshot(manager=nm)["networks"] if n["key"] == key), None)
    if not row or not row["active"]:
        raise ValueError("Das ausgewählte WLAN ist nicht verbunden.")
    nm.call(row["device"], NM + ".Device", "Disconnect")
    return "WLAN getrennt. Das gespeicherte Profil bleibt erhalten."
