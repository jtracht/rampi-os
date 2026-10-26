"""Enter ephemeral fixture input into the real stock wizard using QEMU QMP."""

import argparse
import json
import socket
import time
from pathlib import Path


def drive(qmp_path, serial, credentials):
    fixture = json.loads(credentials.read_text())
    # The default keyboard layouts agree on lower-case a-f. No shell quoting,
    # text paste, TIOCSTI, guest password reset or custom input driver is used.
    for field in ("user", "password"):
        if not fixture[field] or any(c not in "abcdef" for c in fixture[field]):
            raise ValueError("Fixture requires layout-independent lower-case hex letters")
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    deadline = time.monotonic() + 540
    while True:
        try:
            connection.connect(str(qmp_path))
            break
        except (FileNotFoundError, ConnectionRefusedError):
            if time.monotonic() >= deadline:
                raise TimeoutError("QMP socket did not become ready") from None
            time.sleep(0.3)
    connection.settimeout(15)
    stream = connection.makefile("rwb")
    greeting = json.loads(stream.readline())
    if "QMP" not in greeting:
        raise RuntimeError("Unexpected QMP greeting")

    def execute(name, arguments=None):
        request = {"execute": name}
        if arguments is not None:
            request["arguments"] = arguments
        stream.write(json.dumps(request).encode() + b"\n")
        stream.flush()
        while True:
            response = json.loads(stream.readline())
            if "error" in response:
                # Do not print requests: send-key arguments include credentials.
                raise RuntimeError("QMP input command failed")
            if "return" in response:
                return

    def key(code):
        # Use the standard direct input API, which validates that a handler
        # exists. The legacy send-key may acknowledge silently dropped input
        # and relies on a separate virtual-clock key-release queue.
        for down in (True, False):
            execute("input-send-event", {"events": [{
                "type": "key", "data": {
                    "down": down, "key": {"type": "qcode", "data": code}
                }
            }]})
            time.sleep(0.15)

    execute("qmp_capabilities")
    handled = set()
    try:
        while time.monotonic() < deadline:
            log = serial.read_text(errors="replace") if serial.exists() else ""
            if "RAMPI_PRISTINE_FIRST_USER_PAM_OK" in log:
                return
            if "RAMPI_GUEST_EXIT=" in log:
                raise RuntimeError("Guest stopped before pristine first-user acceptance")
            for line in log.splitlines():
                marker = "RAMPI_FIRST_USER_INPUT="
                if marker not in line:
                    continue
                phase = line.split(marker, 1)[1].strip()
                if phase in handled:
                    continue
                if phase.startswith("keyboard-") and phase[len("keyboard-") :].isdigit():
                    value = ""
                elif phase == "username":
                    value = fixture["user"]
                elif phase in ("password", "confirmation"):
                    value = fixture["password"]
                else:
                    raise RuntimeError("Unknown first-user input phase")
                handled.add(phase)
                for character in value:
                    key(character)
                key("ret")
                print("RAMPI_FIRST_USER_QMP_SENT=" + phase, flush=True)
            time.sleep(0.3)
        raise TimeoutError("Pristine first-user wizard exceeded its input deadline")
    finally:
        stream.close()
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qmp", type=Path, required=True)
    parser.add_argument("--serial", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    arguments = parser.parse_args()
    drive(arguments.qmp, arguments.serial, arguments.credentials)
