"""Validate personal WLAN profile storage on real NM, without a radio device."""

import argparse
import os
import uuid
from pathlib import Path

from rampi.services import linux_username
from rampi.wifi import NM, ROOT, NetworkManager, profile_settings

if not Path("/.dockerenv").exists() or os.environ.get("RAMPI_TEST_CONTAINER") != "1":
    raise SystemExit("This test requires the designated disposable NetworkManager container")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--deny-secrets")
options = parser.parse_args()
nm = NetworkManager()
if options.deny_secrets:
    try:
        nm.call(
            options.deny_secrets,
            NM + ".Settings.Connection",
            "GetSecrets",
            "(s)",
            ("802-11-wireless-security",),
        )
    except RuntimeError as exc:
        from gi.repository import Gio

        remote = Gio.DBusError.get_remote_error(exc.__cause__) or ""
        if not remote.endswith((".PermissionDenied", ".AccessDenied")):
            raise RuntimeError("Unexpected error instead of WLAN secret access denial") from None
    else:
        raise RuntimeError("A different Linux user could retrieve the WLAN credential")
else:
    secret = uuid.uuid4().hex
    settings = profile_settings(b"Rampi private WLAN test", "wpa-psk", secret, linux_username())
    path = nm.call(
        ROOT + "/Settings",
        NM + ".Settings",
        "AddConnection2",
        "(a{sa{sv}}ua{sv})",
        (settings, 1, {}),
    )[0]
    metadata = nm.settings(path)
    if metadata["connection"]["permissions"] != [f"user:{linux_username()}:"]:
        raise RuntimeError("Real NetworkManager did not preserve the personal WLAN ACL")
    if metadata["connection"]["autoconnect"] or secret in repr(metadata):
        raise RuntimeError("WLAN metadata has an unsafe autoconnect or credential leak")
    secrets = nm.call(
        path, NM + ".Settings.Connection", "GetSecrets", "(s)", ("802-11-wireless-security",)
    )[0]
    if secrets["802-11-wireless-security"]["psk"] != secret:
        raise RuntimeError("Real NetworkManager did not store the submitted WLAN credential")
    for mode, password in (("open", ""), ("sae", uuid.uuid4().hex)):
        profile_settings(b"Validation only", mode, password, linux_username())
    try:
        profile_settings(b"Invalid password", "wpa-psk", "short", linux_username())
    except ValueError:
        pass
    else:
        raise RuntimeError("libnm accepted an invalid WPA2 password")
    # Only the public object path is returned; no test credentials are logged.
    print(path)
