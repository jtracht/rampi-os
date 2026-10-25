"""Check actual native Sunshine component bytes; no GTK/Windows acceptance claim."""

import hashlib
import json
import re
import runpy
import sys
import tarfile
from pathlib import Path


def check(directory: Path, *, allow_development=False):
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
    if any(
        evidence[field] is not False
        for field in ["physical_hardware", "windows_host", "gtk_presentation"]
    ):
        raise ValueError("Component proof overclaims hardware, Windows or GTK")
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


if __name__ == "__main__":
    check(Path(sys.argv[1]))
