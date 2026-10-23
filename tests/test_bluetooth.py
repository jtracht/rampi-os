import pytest
from rampi import bluetooth


@pytest.mark.parametrize(
    "kind,value,expected",
    [
        ("RequestPinCode", "1234", ("(s)", ("1234",))),
        ("RequestPinCode", "Aa901", ("(s)", ("Aa901",))),
        ("RequestPasskey", "000001", ("(u)", (1,))),
        ("RequestPasskey", "999999", ("(u)", (999999,))),
        ("RequestConfirmation", "", ("()", ())),
    ],
)
def test_agent_response_uses_official_dbus_types(kind, value, expected):
    assert bluetooth.response(kind, value) == expected


@pytest.mark.parametrize(
    "kind,value",
    [
        ("RequestPinCode", ""),
        ("RequestPinCode", "a" * 17),
        ("RequestPinCode", "é"),
        ("RequestPasskey", ""),
        ("RequestPasskey", "1000000"),
        ("RequestPasskey", "-1"),
        ("RequestPasskey", "١٢٣"),
    ],
)
def test_invalid_pairing_input_never_becomes_a_dbus_reply(kind, value):
    with pytest.raises(ValueError):
        bluetooth.response(kind, value)


def test_unknown_device_and_action_never_call_mutating_methods(monkeypatch):
    calls = []
    monkeypatch.setattr(bluetooth, "snapshot", lambda: {"adapters": [], "devices": []})
    monkeypatch.setattr(bluetooth, "call", lambda *args, **kwargs: calls.append(args))
    for path in ("/other/service", "/org/bluez/hci0", "/org/bluez/hci0/dev_00_11_22_33_44_55"):
        with pytest.raises(ValueError):
            bluetooth.action("pair", path)
    assert not calls
