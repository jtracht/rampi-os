"""Verify actual GTK accessibility captures against their program and sources."""

import argparse
import hashlib
import json
import runpy
from pathlib import Path


def check(directory, expected_binary):
    a11y = json.loads((directory / "accessibility-proof.json").read_text(encoding="utf-8"))
    if a11y.get("schema") != 1 or a11y.get("complete_product_acceptance") is not False:
        raise ValueError("Actual accessibility component provenance missing")
    sessions = a11y.get("sessions", [])
    if (
        len(sessions) != 2
        or {s.get("language") for s in sessions} != {"de", "en"}
        or len({s.get("pid") for s in sessions}) != 2
        or any(
            type(s.get("pid")) is not int
            or s["pid"] <= 1
            or type(s.get("uid")) is not int
            or s["uid"] < 1000
            or s.get("native_elf_sha256") != expected_binary
            for s in sessions
        )
    ):
        raise ValueError("Actual two-language accessibility processes/program mismatch")
    for name in ["tests/rust/test-accessibility.py", "scripts/virtual/hid-accessible-state.py"]:
        if (
            a11y.get("source_hashes", {}).get(name)
            != hashlib.sha256((Path(__file__).resolve().parents[1] / name).read_bytes()).hexdigest()
        ):
            raise ValueError("Accessibility source mismatch: " + name)
    visible_capture = runpy.run_path(str(Path(__file__).with_name("check-login-evidence.py")))[
        "visible_capture"
    ]
    for language in ["de", "en"]:
        for page in ["dashboard", "categories", "host"]:
            stem = directory / f"accessibility-{language}-{page}"
            rows = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
            names = [r.get("name", "") for r in rows if r.get("role") == "button"]
            if not names or any(not name.strip() for name in names):
                raise ValueError("Actual accessible button caption missing")
            if page == "dashboard" and not (
                any(n.startswith("WLAN" if language == "de" else "Wi-Fi") for n in names)
                and any(n.startswith("Bluetooth") for n in names)
            ):
                raise ValueError("Actual dashboard radio captions missing")
            if page == "categories" and "Host & SSH" not in names:
                raise ValueError("Actual category caption missing")
            fields = [r.get("name", "") for r in rows if r.get("role") in {"entry", "text"}]
            if page == "host" and (
                len(fields) != 6
                or any(not name.strip() for name in fields)
                or ("Profilname" if language == "de" else "Profile name") not in fields
            ):
                raise ValueError("Actual personal host form captions missing")
            visible_capture(stem.with_suffix(".png"))
    return a11y


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expected-binary", required=True)
    options = parser.parse_args()
    check(options.directory, options.expected_binary)
    print("PASS: actual GTK accessibility, two languages, program and source binding.")
