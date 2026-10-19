"""Run against Debian's real libnm parser without activating a connection."""

import base64
import os
import tempfile
from pathlib import Path

from rampi.services import wireguard_connection

with tempfile.TemporaryDirectory() as directory:
    filename = Path(directory) / "test.conf"
    # Fresh throwaway material; never stored in Git, logged or used for a real tunnel.
    key = base64.b64encode(os.urandom(32)).decode()
    peer = base64.b64encode(os.urandom(32)).decode()
    filename.write_text(
        f"[Interface]\nPrivateKey={key}\nAddress=10.42.0.2/32\n"
        f"[Peer]\nPublicKey={peer}\nAllowedIPs=10.42.0.0/24\n"
        "Endpoint=127.0.0.1:51820\n"
    )
    connection = wireguard_connection(str(filename), "rampi-test-user")
    setting = connection.get_setting_connection()
    if setting.props.autoconnect or setting.get_num_permissions() != 1:
        raise SystemExit("Unsafe imported profile")
    if list(setting.props.permissions) != ["user:rampi-test-user:"]:
        raise SystemExit("Profile was not restricted to its user")
    properties = connection.to_dbus(0).unpack()
    if properties["connection"]["autoconnect"] is not False:
        raise SystemExit("D-Bus payload lost the autoconnect restriction")
    print("PASS: real libnm import/validation; private user ACL and autoconnect disabled.")
