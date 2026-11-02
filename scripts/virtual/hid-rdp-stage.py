"""Actual HID reports through the normal Rampi RDP page to isolated XRDP receipts."""

import json
import re
import urllib.error
import urllib.request


def run(login, user, layout, fixture, reply, visible_nodes, capture, kernel_log, cases):
    helper = "/opt/rampi-source/scripts/virtual/hid-accessible-state.py"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = "http://" + fixture["address"] + ":8000/"

    def fetch(name):
        try:
            with opener.open(base + name, timeout=5) as response:
                return response.read(2_000_000).decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code == 404 and name != ".rampi-nonce":
                return ""
            raise

    if fetch(".rampi-nonce").strip() != fixture["nonce"]:
        raise RuntimeError("Actual isolated RDP receipt origin mismatch")

    def activate(caption):
        login.as_user(user, "python3", helper, "--fixture-activate", caption)

    def names():
        return [row["name"] for row in visible_nodes()]

    def fill(caption, value):
        bounds = json.loads(
            login.as_user(user, "python3", helper, "--fixture-control-bounds", caption).stdout
        )
        login.as_user(user, "wlrctl", "pointer", "move", "-10000", "-10000")
        login.as_user(
            user,
            "wlrctl",
            "pointer",
            "move",
            str(bounds["x"] + bounds["width"] // 2),
            str(bounds["y"] + bounds["height"] // 2),
        )
        login.as_user(user, "wlrctl", "pointer", "click", "left")
        login.as_user(
            user,
            "wtype",
            "-s",
            "100",
            "-M",
            "ctrl",
            "-k",
            "a",
            "-m",
            "ctrl",
            "-k",
            "BackSpace",
        )
        # Even disposable passwords stay out of argv, logs and metadata.
        login.as_user(user, "wtype", "-s", "100", "-", data=value.encode("utf-8"))

    def open_page():
        activate("Remote Desktop")
        login.wait(lambda: "RDP · integrierter Windows-Desktop" in names(), "normal remote menu")
        activate("RDP · integrierter Windows-Desktop")

    def connected():
        return any(name.startswith("Verbunden ·") for name in names())

    def connect():
        fill("Windows-Kennwort · wird nicht gespeichert", fixture["password"])
        activate("Mit Windows verbinden")
        login.wait(connected, "actual normal RDP connection with pinned certificate")

    def lines():
        return fetch(".rampi-input").splitlines()

    def events():
        return [json.loads(line) for line in fetch(".rampi-events.jsonl").splitlines()]

    def dashboard():
        return "Kanban Board" in names()

    open_page()
    login.wait(lambda: "Mit Windows verbinden" in names(), "normal RDP form")
    fill("Zertifikat-Fingerabdruck · unabhängig auf Windows prüfen", fixture["fingerprint"])
    connect()
    first_line = len(lines())
    observed = []
    for case, code in zip(cases, [30, 21, 44, 3, 18], strict=True):
        before = len(lines())
        start = kernel_log.stat().st_size
        reply({"action": "keyboard", "usage": case["usage"], "modifiers": case["modifiers"]})
        modifier = {2: 42, 64: 100}.get(case["modifiers"])

        def delivered(code=code, modifier=modifier, start=start):
            raw = kernel_log.read_bytes()[start:]
            receipts = {
                (int(k), int(v))
                for k, v in re.findall(
                    r"type 1 \(EV_KEY\), code ([0-9]+) \([^)]+\), value ([012])",
                    raw.decode("utf-8", errors="replace"),
                )
            }
            return all(
                {(key, 0), (key, 1)} <= receipts
                for key in [code] + ([modifier] if modifier else [])
            )

        login.wait(delivered, "actual kernel HID key/modifier before remote receipt")
        end = kernel_log.stat().st_size
        reply({"action": "keyboard", "usage": 40, "modifiers": 0})
        login.wait(
            lambda before=before, case=case: (
                len(lines()) == before + 1 and lines()[-1] == case["expected"]
            ),
            "actual server-side HID glyph receipt",
        )
        observed.append(
            {
                "usage": case["usage"],
                "modifiers": case["modifiers"],
                "actual": lines()[-1],
                "expected": case["expected"],
                "kernel_offset_start": start,
                "kernel_offset_end": end,
            }
        )

    mouse_start = len(events())
    login.as_user(user, "wlrctl", "pointer", "move", "-10000", "-10000")
    login.as_user(user, "wlrctl", "pointer", "move", "640", "400")
    reply({"action": "mouse", "dx": 8, "dy": -6})
    login.wait(
        lambda: (
            {"press", "release"}
            <= {event["kind"] for event in events()[mouse_start:] if event.get("button") == 1}
        ),
        "actual remote Bluetooth mouse press/release",
    )
    reply({"action": "keyboard", "usage": 74, "modifiers": 5})
    login.wait(dashboard, "actual HID reserved shortcut back to dashboard")
    open_page()
    login.wait(connected, "same RDP session survives module change")

    def sentinel():
        before = len(lines())
        reply({"action": "keyboard", "usage": 4, "modifiers": 0})
        reply({"action": "keyboard", "usage": 40, "modifiers": 0})
        login.wait(
            lambda: len(lines()) == before + 1 and lines()[-1] == cases[0]["expected"],
            "actual remote HID input resumes",
        )

    sentinel()
    if any(event.get("key") == "Home" for event in events()):
        raise RuntimeError("Reserved Rampi shortcut reached the actual remote server")
    capture(user + "-" + layout + "-rdp-hid-connected")
    activate("Verbindung trennen")
    login.wait(lambda: "Mit Windows verbinden" in names(), "normal RDP disconnect form")
    connect()
    sentinel()
    activate("Verbindung trennen")
    login.wait(lambda: "Mit Windows verbinden" in names(), "normal RDP final disconnect")
    reply({"action": "keyboard", "usage": 74, "modifiers": 5})
    login.wait(dashboard, "return to dashboard after joined input")
    return {
        "keys": observed,
        "actual_mouse": True,
        "reserved_shortcut_suppressed": True,
        "actual_reconnect": True,
        "actual_server_nonce": fixture["nonce"],
        "remote_start_line": first_line,
        "remote_lines": lines(),
        "remote_events": events(),
        "complete_product_acceptance": False,
    }
