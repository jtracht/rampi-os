"""BlueZ metadata/actions and its official asynchronous pairing-agent interface."""

from __future__ import annotations

import os
import re
import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal

BLUEZ = "org.bluez"
AGENT = "/org/rampi/PairingAgent"
DEVICE = re.compile(r"/org/bluez/hci[0-9]+/dev_(?:[0-9A-Fa-f]{2}_){5}[0-9A-Fa-f]{2}\Z")
ADAPTER = re.compile(r"/org/bluez/hci[0-9]+\Z")
_discovery: set[str] = set()
_discovery_lock = threading.Lock()
AGENT_XML = """<node><interface name="org.bluez.Agent1">
<method name="Release"/>
<method name="Cancel"/>
<method name="RequestPinCode"><arg type="o" direction="in"/><arg type="s" direction="out"/></method>
<method name="RequestPasskey"><arg type="o" direction="in"/><arg type="u" direction="out"/></method>
<method name="DisplayPinCode"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
<method name="DisplayPasskey"><arg type="o" direction="in"/>
<arg type="u" direction="in"/><arg type="q" direction="in"/></method>
<method name="RequestConfirmation"><arg type="o" direction="in"/>
<arg type="u" direction="in"/></method>
<method name="RequestAuthorization"><arg type="o" direction="in"/></method>
<method name="AuthorizeService"><arg type="o" direction="in"/>
<arg type="s" direction="in"/></method>
</interface></node>"""


def libraries():
    if os.name != "posix":
        raise RuntimeError("Bluetooth-Einrichtung benötigt BlueZ unter Linux.")
    from gi.repository import Gio, GLib

    return Gio, GLib


def call(path, interface, method, signature=None, values=(), timeout=15000):
    Gio, GLib = libraries()
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    try:
        return bus.call_sync(
            BLUEZ,
            path,
            interface,
            method,
            GLib.Variant(signature, values) if signature else None,
            None,
            Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION,
            timeout,
            None,
        ).unpack()
    except GLib.Error as exc:
        raise RuntimeError(
            "BlueZ konnte den Auftrag nicht ausführen. Gerät, Dienst und Berechtigung prüfen."
        ) from exc


def snapshot() -> dict:
    objects = call("/", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects")[0]
    adapters, devices = [], []
    for path, interfaces in objects.items():
        if "org.bluez.Adapter1" in interfaces and ADAPTER.fullmatch(path):
            data = interfaces["org.bluez.Adapter1"]
            adapters.append(
                dict(
                    path=path,
                    name=data.get("Alias", data.get("Address", "Bluetooth")),
                    powered=bool(data.get("Powered")),
                    discovering=bool(data.get("Discovering")),
                    own_scan=path in _discovery,
                )
            )
        if "org.bluez.Device1" in interfaces and DEVICE.fullmatch(path):
            data = interfaces["org.bluez.Device1"]
            name = data.get("Alias", data.get("Name", data["Address"]))
            name = "".join(c if c.isprintable() else "�" for c in name)
            paired = bool(data.get("Paired"))
            connected = bool(data.get("Connected"))
            devices.append(
                dict(
                    path=path,
                    adapter=str(data["Adapter"]),
                    name=name,
                    address=data["Address"],
                    paired=paired,
                    connected=connected,
                    trusted=bool(data.get("Trusted")),
                    label=name
                    + " · "
                    + data["Address"]
                    + (" · Verbunden" if connected else " · Gekoppelt" if paired else ""),
                )
            )
    return dict(
        adapters=sorted(adapters, key=lambda a: a["path"]),
        devices=sorted(devices, key=lambda d: (-d["connected"], -d["paired"], d["name"])),
        error="" if adapters else "Kein Bluetooth-Adapter gefunden.",
    )


def action(operation: str, path: str, enabled: bool = False) -> str:
    state = snapshot()
    if ADAPTER.fullmatch(path) and path in {a["path"] for a in state["adapters"]}:
        if operation in {"scan", "stop-scan"}:
            if operation == "scan":
                _, GLib = libraries()
                call(
                    path,
                    BLUEZ + ".Adapter1",
                    "SetDiscoveryFilter",
                    "(a{sv})",
                    (
                        {
                            "Transport": GLib.Variant("s", "auto"),
                            "DuplicateData": GLib.Variant("b", False),
                        },
                    ),
                )
            call(
                path,
                BLUEZ + ".Adapter1",
                "StartDiscovery" if operation == "scan" else "StopDiscovery",
            )
            with _discovery_lock:
                if operation == "scan":
                    _discovery.add(path)
                else:
                    _discovery.discard(path)
            return (
                "Gerätesuche gestartet." if operation == "scan" else "Eigene Gerätesuche beendet."
            )
        if operation == "power":
            _, GLib = libraries()
            call(
                path,
                "org.freedesktop.DBus.Properties",
                "Set",
                "(ssv)",
                (BLUEZ + ".Adapter1", "Powered", GLib.Variant("b", enabled)),
            )
            if not enabled:
                with _discovery_lock:
                    _discovery.discard(path)
            return "Bluetooth eingeschaltet." if enabled else "Bluetooth ausgeschaltet."
    row = next((d for d in state["devices"] if d["path"] == path), None)
    if not row:
        raise ValueError("Das ausgewählte Bluetooth-Gerät ist nicht mehr verfügbar.")
    methods = {
        "pair": "Pair",
        "cancel-pair": "CancelPairing",
        "connect": "Connect",
        "disconnect": "Disconnect",
    }
    if operation in methods:
        call(
            path,
            BLUEZ + ".Device1",
            methods[operation],
            timeout=90000 if operation == "pair" else 20000,
        )
        return {
            "pair": "Gerät gekoppelt. Bei Bedarf Verbinden wählen.",
            "cancel-pair": "Kopplung abgebrochen.",
            "connect": "Gerät verbunden.",
            "disconnect": "Gerät getrennt.",
        }[operation]
    if operation == "remove":
        call(row["adapter"], BLUEZ + ".Adapter1", "RemoveDevice", "(o)", (path,))
        return "Bluetooth-Kopplung entfernt."
    if operation == "trust":
        _, GLib = libraries()
        call(
            path,
            "org.freedesktop.DBus.Properties",
            "Set",
            "(ssv)",
            (BLUEZ + ".Device1", "Trusted", GLib.Variant("b", enabled)),
        )
        return "Vertrauen gespeichert." if enabled else "Vertrauen entfernt."
    raise ValueError("Unbekannte Bluetooth-Aktion.")


def stop_discovery():
    with _discovery_lock:
        paths = list(_discovery)
    for path in paths:
        try:
            call(path, BLUEZ + ".Adapter1", "StopDiscovery")
        finally:
            with _discovery_lock:
                _discovery.discard(path)
    return "Eigene Bluetooth-Suche beendet."


def has_discovery() -> bool:
    with _discovery_lock:
        return bool(_discovery)


def response(kind: str, value: str):
    if kind == "RequestPinCode":
        if not 1 <= len(value) <= 16 or not value.isascii() or not value.isalnum():
            raise ValueError("PIN: 1–16 Buchstaben oder Ziffern eingeben.")
        return "(s)", (value,)
    if kind == "RequestPasskey":
        if not value.isascii() or not value.isdecimal() or len(value) > 6:
            raise ValueError("Passkey: höchstens sechs Ziffern eingeben.")
        return "(u)", (int(value),)
    return "()", ()


class PairingAgent(QObject):
    requested = Signal(object)
    removed = Signal(int)
    updated = Signal()
    unavailable = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.stopping = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.loop = None
        self.error = ""
        self.pending: dict[int, tuple] = {}
        self.serial = 0
        self.timeout = QTimer(self)
        self.timeout.setInterval(1000)
        self.timeout.timeout.connect(self.expire)
        self.timeout.start()

    def ensure(self):
        libraries()
        with self.lock:
            if self.worker_thread is None or not self.worker_thread.is_alive():
                self.ready.clear()
                self.stopping.clear()
                self.error = ""
                self.worker_thread = threading.Thread(
                    target=self._serve, name="rampi-bluez-agent", daemon=True
                )
                self.worker_thread.start()
        if not self.ready.wait(6) or self.error:
            raise RuntimeError(self.error or "Bluetooth-Kopplungsdialog startet noch.")

    def _serve(self):
        Gio, GLib = libraries()
        context = GLib.MainContext.new()
        context.push_thread_default()
        registration = 0
        subscriptions = []
        bus = None
        try:
            loop = GLib.MainLoop.new(context, False)
            self.loop = loop
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            owner = bus.call_sync(
                "org.freedesktop.DBus",
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "GetNameOwner",
                GLib.Variant("(s)", (BLUEZ,)),
                None,
                Gio.DBusCallFlags.NONE,
                5000,
                None,
            ).unpack()[0]

            def received(connection, sender, path, interface, method, parameters, invocation):
                if sender != owner:
                    invocation.return_dbus_error(BLUEZ + ".Error.Rejected", "BlueZ caller required")
                    return
                values = parameters.unpack()
                if method in {"Release", "Cancel"}:
                    self.cancel_all()
                    invocation.return_value(GLib.Variant("()", ()))
                    if method == "Release":
                        loop.quit()
                    return
                device = values[0]
                if not DEVICE.fullmatch(device):
                    invocation.return_dbus_error(BLUEZ + ".Error.Rejected", "Unknown device")
                    return
                display = method.startswith("Display")
                code = (
                    str(values[1]).zfill(6)
                    if method in {"DisplayPasskey", "RequestConfirmation"}
                    else str(values[1])
                    if method == "DisplayPinCode"
                    else ""
                )
                with self.lock:
                    self.serial += 1
                    identifier = self.serial
                    if not display:
                        self.pending[identifier] = (method, invocation, time.monotonic() + 60)
                self.requested.emit(
                    dict(
                        id=identifier,
                        kind=method,
                        device=device,
                        code=code,
                        entered=int(values[2]) if method == "DisplayPasskey" else 0,
                        service=str(values[1]) if method == "AuthorizeService" else "",
                        display=display,
                    )
                )
                if display:
                    invocation.return_value(GLib.Variant("()", ()))

            info = Gio.DBusNodeInfo.new_for_xml(AGENT_XML).interfaces[0]
            registration = bus.register_object(AGENT, info, received, None, None)
            bus.call_sync(
                BLUEZ,
                "/org/bluez",
                BLUEZ + ".AgentManager1",
                "RegisterAgent",
                GLib.Variant("(os)", (AGENT, "KeyboardDisplay")),
                None,
                Gio.DBusCallFlags.NONE,
                5000,
                None,
            )

            def changed(*_args):
                self.updated.emit()

            subscriptions.append(
                bus.signal_subscribe(
                    BLUEZ,
                    None,
                    None,
                    None,
                    None,
                    Gio.DBusSignalFlags.NONE,
                    changed,
                )
            )

            def owner_changed(_bus, _sender, _path, _interface, _signal, values):
                if values.unpack()[2] != owner:
                    with _discovery_lock:
                        _discovery.clear()
                    self.error = "BlueZ wurde neu gestartet. Geräte erneut aktualisieren."
                    self.unavailable.emit(self.error)
                    loop.quit()

            subscriptions.append(
                bus.signal_subscribe(
                    "org.freedesktop.DBus",
                    "org.freedesktop.DBus",
                    "NameOwnerChanged",
                    "/org/freedesktop/DBus",
                    BLUEZ,
                    Gio.DBusSignalFlags.NONE,
                    owner_changed,
                )
            )
            self.ready.set()
            if not self.stopping.is_set():
                loop.run()
        except Exception:
            self.error = "BlueZ-Kopplungsdialog nicht verfügbar. Dienst und Berechtigung prüfen."
            self.ready.set()
            self.unavailable.emit(self.error)
        finally:
            self.cancel_all()
            if bus:
                for identifier in subscriptions:
                    bus.signal_unsubscribe(identifier)
                if registration:
                    try:
                        bus.call_sync(
                            BLUEZ,
                            "/org/bluez",
                            BLUEZ + ".AgentManager1",
                            "UnregisterAgent",
                            GLib.Variant("(o)", (AGENT,)),
                            None,
                            Gio.DBusCallFlags.NONE,
                            3000,
                            None,
                        )
                    except GLib.Error:
                        pass
                    bus.unregister_object(registration)
            context.pop_thread_default()

    def answer(self, identifier: int, accept: bool, value: str = ""):
        _, GLib = libraries()
        with self.lock:
            item = self.pending.get(identifier)
            if item is None:
                raise ValueError("Diese Bluetooth-Anfrage ist nicht mehr gültig.")
            kind, invocation, deadline = item
            signature, values = response(kind, value) if accept else ("()", ())
            self.pending.pop(identifier)
        if accept and time.monotonic() < deadline:
            invocation.return_value(GLib.Variant(signature, values))
        else:
            invocation.return_dbus_error(
                BLUEZ + ".Error.Rejected", "User rejected or request expired"
            )
        self.removed.emit(identifier)

    def cancel_all(self):
        with self.lock:
            items = list(self.pending.items())
            self.pending.clear()
        for identifier, (_, invocation, _) in items:
            invocation.return_dbus_error(BLUEZ + ".Error.Canceled", "Pairing cancelled")
            self.removed.emit(identifier)
        self.removed.emit(0)  # Clears transient displayed passkeys too.

    def expire(self):
        with self.lock:
            expired = [key for key, item in self.pending.items() if time.monotonic() >= item[2]]
        for identifier in expired:
            try:
                self.answer(identifier, False)
            except ValueError:
                pass

    def close(self):
        self.stopping.set()
        self.timeout.stop()
        self.cancel_all()
        if self.loop:
            self.loop.quit()
        if self.worker_thread:
            self.worker_thread.join(timeout=4)
