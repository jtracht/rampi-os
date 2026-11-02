"""Require joined real HID/kernel/normal-GTK/RDP input and independent server files."""

import argparse
import hashlib
import json
import re
import runpy
from pathlib import Path


def component(directory, expected_binary):
    base = runpy.run_path(str(Path(__file__).with_name("check-hid-evidence.py")))
    login = runpy.run_path(str(Path(__file__).with_name("check-login-evidence.py")))
    captures = directory / "captures/hid"
    proof = json.loads((captures / "hid-proof.json").read_text())
    sessions = base["validate_proof"](proof, expected_binary)
    base["check_cursor_images"](directory / "captures/hid", proof)
    previous, nonces, reported_events = {}, {}, {}
    for session in sessions:
        remote = session.get("rdp") or {}
        if remote.get("complete_product_acceptance") is not False or any(
            remote.get(name) is not True
            for name in ["actual_mouse", "reserved_shortcut_suppressed", "actual_reconnect"]
        ):
            raise ValueError("Actual complete remote HID stage missing")
        user, layout = session["user"], session["layout"]
        nonce = remote.get("actual_server_nonce", "")
        if not re.fullmatch(r"[0-9a-f]{32}", nonce) or nonces.get(user, nonce) != nonce:
            raise ValueError("Actual remote fixture identity changed")
        nonces[user] = nonce
        start = remote.get("remote_start_line")
        transcript = remote.get("remote_lines")
        earlier = previous.get(user, [])
        wanted = base["GLYPHS"][layout] + [base["GLYPHS"][layout][0]] * 2
        if type(start) is not int or start != len(earlier) or transcript != earlier + wanted:
            raise ValueError("Actual complete remote input transcript mismatch")
        previous[user] = transcript
        keys = remote.get("keys", [])
        if len(keys) != 5:
            raise ValueError("All five actual remote HID cases required")
        trace = (captures / f"{user}-{layout}-kernel-keyboard.txt").read_bytes()
        end_before = session["keys"][-1]["kernel_offset_end"]
        for observed, (usage, mods), code, glyph in zip(
            keys, base["KEYS"], [30, 21, 44, 3, 18], base["GLYPHS"][layout], strict=True
        ):
            if any(
                observed.get(key) != value
                for key, value in [
                    ("usage", usage),
                    ("modifiers", mods),
                    ("actual", glyph),
                    ("expected", glyph),
                ]
            ):
                raise ValueError("Actual remote glyph/modifier case mismatch")
            a, b = observed.get("kernel_offset_start"), observed.get("kernel_offset_end")
            if type(a) is not int or type(b) is not int or not end_before <= a < b <= len(trace):
                raise ValueError("Independent remote kernel receipt interval missing")
            end_before = b
            events = {
                (int(k), int(v))
                for k, v in re.findall(
                    r"type 1 \(EV_KEY\), code ([0-9]+) \([^)]+\), value ([012])",
                    trace[a:b].decode("utf-8", errors="replace"),
                )
            }
            modifier = {2: 42, 64: 100}.get(mods)
            if not all(
                {(k, 0), (k, 1)} <= events for k in [code] + ([modifier] if modifier else [])
            ):
                raise ValueError("Actual remote kernel key/modifier release missing")
        events = remote.get("remote_events", [])
        reported_events[user] = events
        if any(event.get("key") == "Home" for event in events) or not {"press", "release"} <= {
            event.get("kind") for event in events if event.get("button") == 1
        }:
            raise ValueError("Remote mouse receipt or reserved-shortcut isolation failed")
        login["visible_capture"](captures / f"{user}-{layout}-rdp-hid-connected.png")
    if len(set(nonces.values())) != 2:
        raise ValueError("Two independent actual remote fixtures required")
    for user, transcript in previous.items():
        server = directory / "server-receipts" / user
        if (server / ".rampi-input").read_text().splitlines() != transcript:
            raise ValueError("Independent actual server input file differs from guest report")
        if (server / ".rampi-nonce").read_text().strip() != nonces[user]:
            raise ValueError("Independent server nonce differs")
        events = [
            json.loads(line) for line in (server / ".rampi-events.jsonl").read_text().splitlines()
        ]
        if any(event.get("key") == "Home" for event in events):
            raise ValueError("Reserved shortcut leaked in independent server file")
        if events[: len(reported_events[user])] != reported_events[user]:
            raise ValueError("Reported remote mouse/key events differ from independent server file")
    metadata = json.loads((directory / "rdp-fixture-metadata.json").read_text())
    if metadata.get("complete_product_acceptance") is not False:
        raise ValueError("Component proof must not claim whole-product acceptance")
    servers = metadata.get("servers", {})
    if set(servers) != set(nonces) or any(
        record.get("nonce") != nonces[user]
        or record.get("published_ports") is not False
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", record.get("image_id", ""))
        for user, record in servers.items()
    ):
        raise ValueError("Independent server image/origin/port provenance missing")
    expected_source = hashlib.sha256(
        (Path(__file__).resolve().parents[1] / "tests/rust/test-rdp.py").read_bytes()
    ).hexdigest()
    if (
        metadata.get("internal_network") is not True
        or metadata.get("server_source_sha256") != expected_source
    ):
        raise ValueError("Isolated server source/network provenance missing")
    return proof


def check(directory, expected_binary):
    metadata = json.loads((directory / "rdp-fixture-metadata.json").read_text())
    if metadata.get("development_component_only") is not False:
        raise ValueError("Local joined development runs are not fresh acceptance")
    runpy.run_path(str(Path(__file__).with_name("check-hid-evidence.py")))["check"](
        directory, expected_binary
    )
    return component(directory, expected_binary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-binary", required=True)
    options = parser.parse_args()
    check(options.directory, options.expected_binary)
    print(
        "PASS: fresh joined Bluetooth/kernel/normal Rampi/RDP/server input, six layouts, two users."
    )
