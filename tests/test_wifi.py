import copy

import pytest
from rampi import wifi


class Manager:
    def __init__(self):
        self.calls = []
        self.active_state = 2
        self.root = {"WirelessEnabled": True, "WirelessHardwareEnabled": True}
        self.device = {
            "DeviceType": 2,
            "Managed": True,
            "State": 30,
            "AvailableConnections": ["/saved", "/foreign"],
        }
        self.aps = {
            "/weak": {"Ssid": b"Lab:\\Test", "RsnFlags": 256, "Flags": 1, "Strength": 10},
            "/strong": {"Ssid": b"Lab:\\Test", "RsnFlags": 256, "Flags": 1, "Strength": 90},
            "/open": {"Ssid": b"Guest", "Strength": 40},
            "/hidden": {"Ssid": b"", "Strength": 100},
            "/enterprise": {"Ssid": b"Corp", "RsnFlags": 512, "Flags": 1, "Strength": 80},
        }
        self.profiles = {
            "/saved": {
                "connection": {"permissions": ["user:alice:"]},
                "802-11-wireless": {"ssid": b"Lab:\\Test"},
                "802-11-wireless-security": {"key-mgmt": "wpa-psk"},
            },
            "/foreign": {
                "connection": {"permissions": ["user:bob:"]},
                "802-11-wireless": {"ssid": b"Guest"},
            },
        }

    def properties(self, path, interface):
        if path == wifi.ROOT:
            return self.root
        if path == "/device":
            return self.device if interface.endswith(".Device") else {"ActiveAccessPoint": "/"}
        if path == "/active":
            return {"State": self.active_state}
        return self.aps[path]

    def settings(self, path):
        return self.profiles[path]

    def call(self, path, interface, method, signature=None, values=()):
        self.calls.append((method, values))
        if method == "GetDevices":
            return (["/device"],)
        if method == "GetAllAccessPoints":
            return (list(self.aps),)
        if method == "ActivateConnection":
            return ("/active",)
        if method == "DeactivateConnection":
            return ()
        raise AssertionError(method)


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setattr(wifi, "linux_username", lambda: "alice")
    return Manager()


def test_snapshot_deduplicates_by_raw_ssid_reuses_only_permitted_profiles(manager):
    original = copy.deepcopy(manager.profiles)
    rows = wifi.snapshot(manager=manager)["networks"]
    assert len(rows) == 3
    assert rows[0]["ap"] == "/strong" and rows[0]["saved"]
    assert rows[0]["ssid"] == "Lab:\\Test"
    assert not next(n for n in rows if n["ssid"] == "Guest")["saved"]
    assert not next(n for n in rows if n["ssid"] == "Corp")["supported"]
    assert manager.profiles == original
    assert "GetSecrets" not in [m for m, _ in manager.calls]


def test_saved_profile_activates_without_new_profile_or_password(manager):
    row = wifi.snapshot(manager=manager)["networks"][0]
    assert wifi.connect(row["key"], "", manager=manager) == "WLAN verbunden."
    assert ("ActivateConnection", ("/saved", "/device", "/strong")) in manager.calls


def test_missing_or_unsupported_network_never_activates(manager):
    for key in (
        "missing",
        next(n["key"] for n in wifi.snapshot(manager=manager)["networks"] if not n["supported"]),
    ):
        with pytest.raises(ValueError):
            wifi.connect(key, "", manager=manager)
    assert not any(m.startswith("Activate") for m, _ in manager.calls)


@pytest.mark.parametrize("property_name", ["WirelessEnabled", "WirelessHardwareEnabled"])
def test_radio_off_does_not_scan_or_activate(manager, property_name):
    manager.root[property_name] = False
    result = wifi.snapshot(True, manager=manager)
    assert result["networks"] == [] and result["error"]
    assert not manager.calls


@pytest.mark.parametrize(
    "properties,mode",
    [
        ({"RsnFlags": 256, "Flags": 1}, "wpa-psk"),
        ({"RsnFlags": 1024, "Flags": 1}, "sae"),
        ({"Flags": 1}, "unsupported"),
        ({"WpaFlags": 256, "Flags": 1}, "unsupported"),
        ({}, "open"),
    ],
)
def test_security_never_downgrades_to_open(properties, mode):
    assert wifi.security_mode(properties) == mode


def test_failed_activation_is_not_reported_as_connected(manager):
    manager.active_state = 4
    key = wifi.snapshot(manager=manager)["networks"][0]["key"]
    with pytest.raises(RuntimeError, match="fehlgeschlagen"):
        wifi.connect(key, "", manager=manager)


def test_activation_timeout_stops_only_requested_connection(manager, monkeypatch):
    manager.active_state = 1
    monkeypatch.setattr(wifi.time, "sleep", lambda _: None)
    key = wifi.snapshot(manager=manager)["networks"][0]["key"]
    with pytest.raises(RuntimeError, match="lange"):
        wifi.connect(key, "", manager=manager)
    assert ("DeactivateConnection", ("/active",)) in manager.calls
