"""Check actual Sunshine media/GTK bytes without Windows or hardware claims."""

import hashlib
import json
import math
import re
import runpy
import struct
import sys
import tarfile
from pathlib import Path


def check(directory: Path, *, allow_development=False, require_gtk=False, require_soak=False):
    evidence = json.loads((directory / "evidence.json").read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", evidence["source_revision"]):
        raise ValueError("Streaming source revision missing")
    if evidence["dirty_checkout"] is not False and not allow_development:
        raise ValueError("Uncommitted streaming checkout is not final CI acceptance")
    if (
        # Public upstream Git revisions, not credentials.
        # pragma: allowlist nextline secret
        evidence["embedded_source"] != "775444287305849ebdf4736c75298ad0713e2d5d"
        # pragma: allowlist nextline secret
        or evidence["common_source"] != "b126e481a195fdc7152d211def17190e3434bcce"
        or evidence["sunshine_package_version"] != "2026.914.233613-1+debiantrixie"
    ):
        raise ValueError("Streaming dependency identity differs")
    for name, field in [
        ("client-test", "client_test_sha256"),
        ("libmoonlight-common.so.2.7.1", "moonlight_library_sha256"),
        ("audio-window.raw", "audio_window_sha256"),
        ("moonlight-sources.tar.xz", "moonlight_source_archive_sha256"),
    ]:
        with (directory / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != evidence[field]:
                raise ValueError("Streaming component checksum mismatch: " + name)
    with tarfile.open(directory / "moonlight-sources.tar.xz") as archive:
        for name in [
            "moonlight-source/CMakeLists.txt",
            "moonlight-source/LICENSE",
            "moonlight-source/third_party/moonlight-common-c/src/Connection.c",
            "moonlight-source/third_party/moonlight-common-c/LICENSE.txt",
        ]:
            if not archive.getmember(name).isfile():
                raise ValueError("Moonlight component corresponding source/license missing")
    for name in ["client-test", "libmoonlight-common.so.2.7.1"]:
        with (directory / name).open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise ValueError("Actual streaming ELF missing")
    if (
        evidence["video_connections"] != 2
        or evidence["changed_server_key_rejected"] is not True
        or evidence["restored_identity"] is not True
        or evidence["audio_997hz_verified"] is not True
    ):
        raise ValueError("Streaming connection/identity/audio proof incomplete")
    if any(evidence[field] is not False for field in ["physical_hardware", "windows_host"]):
        raise ValueError("Component proof overclaims hardware or Windows")
    if require_soak and not require_gtk:
        raise ValueError("Soak acceptance requires GTK acceptance")
    if require_gtk and evidence.get("gtk_presentation") is not True:
        raise ValueError("Actual GTK acceptance missing")
    if evidence.get("gtk_presentation") is True:
        check_gtk(directory, evidence)
        if require_soak and evidence.get("gtk_soak") is not True:
            raise ValueError("Sustained actual GTK acceptance missing")
        if evidence.get("gtk_soak") is True:
            check_soak(directory, evidence)
    elif evidence.get("gtk_presentation") is not False:
        raise ValueError("GTK acceptance scope missing")
    if "RAMPI_STREAM_SUNSHINE_VIDEO_OK" not in (directory / "client.log").read_text():
        raise ValueError("Actual Rust video evidence missing")
    if (directory / "sunshine.log").read_text().count("CLIENT CONNECTED") < 2:
        raise ValueError("Independent actual Sunshine connections missing")
    sample = directory / "audio-window.raw"
    verify = runpy.run_path(str(Path(__file__).with_name("test-streaming.py")))["verify_audio"]
    if sample.stat().st_size != 48000 * 4 or not verify(sample):
        raise ValueError("Actual received 997-Hz PCM not verified")
    print(
        "PASS: actual Rust/Sunshine pairing, pinned TLS rejection, two video connections and PCM."
    )
    return evidence


def check_gtk(directory: Path, evidence: dict):
    for name, expected in {
        "rampi-native": evidence["gtk_client_sha256"],
        "sunshine-input.json": evidence["sunshine_input_sha256"],
        **evidence["gtk_screenshot_sha256"],
    }.items():
        if Path(name).name != name:
            raise ValueError("Unsafe GTK evidence path")
        with (directory / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError("Actual GTK evidence checksum mismatch: " + name)
    if set(evidence["gtk_screenshot_sha256"]) != {"gtk-stream-0.png", "gtk-stream-1.png"}:
        raise ValueError("Actual screenshots for both GTK connections required")
    with (directory / "rampi-native").open("rb") as stream:
        header = stream.read(64)
    if (
        (directory / "rampi-native").stat().st_size < 4096
        or len(header) != 64
        or header[:6] != b"\x7fELF\x02\x01"
        or int.from_bytes(header[18:20], "little") not in {62, 183}
    ):
        raise ValueError("Actual executed GTK program missing")
    for name in evidence["gtk_screenshot_sha256"]:
        with (directory / name).open("rb") as stream:
            header = stream.read(24)
        if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Actual GTK screenshot missing")
        width, height = struct.unpack(">II", header[16:24])
        if width < 960 or height < 540:
            raise ValueError("Actual GTK screenshot is smaller than the supported screen")
    log = (directory / "gtk-client.log").read_text(encoding="utf-8")
    for marker in ["RAMPI_STREAM_GTK_PRIVATE_PAIRING_OK", "RAMPI_STREAM_GTK_FRAMES_RECONNECT_OK"]:
        if marker not in log:
            raise ValueError("Actual GTK action missing: " + marker)
    if evidence["input_proof_scope"] != "Sunshine decoded packets; platform injection disabled":
        raise ValueError("Fixture must not claim platform input actuation")
    rows = json.loads((directory / "sunshine-input.json").read_text(encoding="utf-8"))
    keys = [row["fields"] for row in rows if row["kind"] == "keyboard packet"]
    for key in [0x8052, 0x800D]:  # actual physical R and Return, down and up
        for action in [3, 4]:
            if (
                sum(
                    int(row["keyCode"], 16) == key and int(row["keyAction"], 16) == action
                    for row in keys
                )
                < 2
            ):
                raise ValueError(
                    "Actual Sunshine keyboard receipts missing on both GTK connections"
                )
    if any(int(row["keyCode"], 16) == 0x8024 for row in keys):
        raise ValueError("Reserved dashboard Home key reached Sunshine")
    pointer = [row["fields"] for row in rows if row["kind"] == "absolute mouse move packet"]
    if not any(
        int(row["width"]) == 1279
        and int(row["height"]) == 719
        and abs(int(row["x"]) - 640) <= 3
        and abs(int(row["y"]) - 360) <= 3
        for row in pointer
    ):
        raise ValueError("Scaled actual Sunshine pointer receipt missing")
    buttons = [row["fields"] for row in rows if row["kind"] == "mouse button packet"]
    for action in [8, 9]:
        if not any(
            int(row["action"], 16) == action and int(row["button"], 16) == 1 for row in buttons
        ):
            raise ValueError("Actual Sunshine click receipts missing")
    for kind, field, value in [
        ("mouse scroll packet", "scrollAmt1", -120),
        ("mouse hscroll packet", "scrollAmount", 120),
    ]:
        if not any(row["kind"] == kind and int(row["fields"][field]) == value for row in rows):
            raise ValueError("Actual Sunshine scroll receipt missing")
    if (directory / "sunshine.log").read_text().count("CLIENT CONNECTED") < 4:
        raise ValueError("Sunshine did not observe both component and GTK reconnections")


def check_soak(directory: Path, evidence: dict):
    if evidence["client_limits"] != {
        "Memory": 1073741824,
        "MemorySwap": 1073741824,
        "NanoCpus": 4000000000,
    }:
        raise ValueError("Actual sustained streaming resource budget differs")
    data = (directory / "gtk-soak.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != evidence["gtk_soak_sha256"]:
        raise ValueError("Actual sustained stream report checksum differs")
    report = json.loads(data)
    if any(report[key] is not False for key in ["physical_hardware", "windows_host"]):
        raise ValueError("Sustained stream proof overclaims host/hardware")
    for key in [
        "duration_secs",
        "paint_p95_ms",
        "frames",
        "painted_samples",
        "changing_samples",
        "rss_start_kib",
        "rss_end_kib",
        "rss_peak_kib",
    ]:
        if (
            isinstance(report[key], bool)
            or not isinstance(report[key], (int, float))
            or not math.isfinite(report[key])
            or report[key] < 0
        ):
            raise ValueError("Invalid sustained stream measurement: " + key)
    if (
        report["duration_secs"] < 600
        or report["frames"] < 12000
        or report["changing_samples"] < 1000
    ):
        raise ValueError("Sustained actual 720p frames/duration missing")
    if report["painted_samples"] * 10 < report["frames"] * 9 or report["paint_p95_ms"] > 80:
        raise ValueError("Sustained GTK painting budget exceeded")
    if (
        report["rss_peak_kib"] > 512 * 1024
        or report["rss_end_kib"] - report["rss_start_kib"] > 64 * 1024
    ):
        raise ValueError("Sustained stream memory budget exceeded")
    if "RAMPI_STREAM_GTK_SOAK_OK" not in (directory / "gtk-client.log").read_text(encoding="utf-8"):
        raise ValueError("Actual executed GTK soak marker missing")


if __name__ == "__main__":
    check(
        Path(sys.argv[1]),
        require_gtk="--require-gtk" in sys.argv[2:],
        require_soak="--require-soak" in sys.argv[2:],
    )
