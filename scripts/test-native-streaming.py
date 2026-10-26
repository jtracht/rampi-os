"""Actual Rust/Moonlight/GStreamer against the existing isolated Sunshine fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
import subprocess
import time
import uuid
from pathlib import Path


def main(server_image: str, client_image: str, output: Path, gtk: bool = False, soak: bool = False):
    root = Path(__file__).resolve().parents[1]
    fixture = runpy.run_path(str(root / "scripts/test-streaming.py"))
    run = fixture["run"]
    output.mkdir(parents=True, exist_ok=False)
    suffix = uuid.uuid4().hex[:12]
    network = ""
    containers = []

    def execute(container, *args, **kwargs):
        return run("docker", "exec", "-i", container, *args, **kwargs)

    try:
        network = run(
            "docker", "network", "create", "--internal", f"rampi-native-stream-{suffix}"
        ).stdout.strip()
        for role, image, destination in [
            ("server", server_image, "/app"),
            ("client", client_image, "/src"),
        ]:
            args = [
                "docker",
                "run",
                "-d",
                "--rm",
                "--network",
                network,
                "--name",
                f"rampi-native-stream-{suffix}-{role}",
                "--memory=1g",
                "--memory-swap=1g",
                "--cpus=4",
                "-v",
                f"{root}:{destination}:ro",
                "-e",
                "RAMPI_TEST_CONTAINER=1",
            ]
            args += (
                [
                    "-e",
                    "DISPLAY=:99",
                    "-e",
                    f"RAMPI_TEST_INPUT_RECEIPTS={int(gtk)}",
                    "-e",
                    f"RAMPI_TEST_STREAM_SOAK={int(soak)}",
                ]
                if role == "server"
                else [
                    "-v",
                    "rampi-rust-build:/build",
                    "-e",
                    "CARGO_HOME=/build/cargo",
                    "-e",
                    "XDG_RUNTIME_DIR=/tmp/rampi-client-runtime",  # pragma: allowlist secret
                ]
            )
            containers.append(run(*args, image, "sleep", "infinity").stdout.strip())
        server, client = containers
        limits = json.loads(run("docker", "inspect", client).stdout)[0]["HostConfig"]
        client_limits = {key: limits[key] for key in ["Memory", "MemorySwap", "NanoCpus"]}
        if client_limits != {
            "Memory": 1073741824,
            "MemorySwap": 1073741824,
            "NanoCpus": 4000000000,
        }:
            raise RuntimeError("Actual native streaming resource limits differ")
        run(
            "docker",
            "exec",
            "-d",
            server,
            "Xvfb",
            ":99",
            "-screen",
            "0",
            "1280x720x24",
            "-nolisten",
            "tcp",
        )
        time.sleep(1)
        run("docker", "exec", "-d", server, "python3", "scripts/test-streaming.py", "--server")
        address = next(
            iter(
                json.loads(run("docker", "inspect", server).stdout)[0]["NetworkSettings"][
                    "Networks"
                ].values()
            )
        )["IPAddress"]
        for _ in range(120):
            if ":47989" in execute(server, "ss", "-ltn").stdout:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("Actual Sunshine fixture did not listen")
        execute(
            client,
            "bash",
            "-ec",
            "mkdir -p /tmp/rampi-client-runtime; chmod 700 /tmp/rampi-client-runtime; "
            "pulseaudio --start --exit-idle-time=-1",
        )
        build = execute(
            client,
            "cargo",
            "test",
            "--locked",
            "-p",
            "rampi-stream",
            "--lib",
            "--no-run",
            "--message-format=json",
        )
        artifacts = [json.loads(line) for line in build.stdout.splitlines() if line.startswith("{")]
        binary = next(
            item["executable"]
            for item in artifacts
            if item.get("reason") == "compiler-artifact"
            and item.get("target", {}).get("name") == "rampi_stream"
            and item.get("profile", {}).get("test")
            and item.get("executable")
        )
        binary_sha = execute(client, "sha256sum", binary).stdout.split()[0]
        library = "/usr/local/lib/libmoonlight-common.so.2.7.1"
        library_sha = execute(client, "sha256sum", library).stdout.split()[0]
        embedded = execute(
            client, "git", "-C", "/opt/moonlight-source", "rev-parse", "HEAD"
        ).stdout.strip()
        common = execute(
            client,
            "git",
            "-C",
            "/opt/moonlight-source/third_party/moonlight-common-c",
            "rev-parse",
            "HEAD",
        ).stdout.strip()
        if (
            # Public upstream Git revisions, not credentials.
            # pragma: allowlist nextline secret
            embedded != "775444287305849ebdf4736c75298ad0713e2d5d"
            # pragma: allowlist nextline secret
            or common != "b126e481a195fdc7152d211def17190e3434bcce"
        ):
            raise RuntimeError("Unexpected Moonlight runtime source")
        run(
            "docker",
            "exec",
            "-d",
            client,
            "bash",
            "-ec",
            "parec --format=s16le --rate=48000 --channels=2 --device=@DEFAULT_MONITOR@ "
            "> /tmp/rampi-received-audio.raw",
        )
        with (output / "client.log").open("wb") as log:
            process = subprocess.Popen(
                [
                    "docker",
                    "exec",
                    "-e",
                    f"RAMPI_TEST_SUNSHINE={address}",
                    client,
                    binary,
                    "client::tests::actual_sunshine_pair_restore_and_video",
                    "--ignored",
                    "--nocapture",
                ],
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(160):
                    pin = execute(
                        client, "cat", "/run/rampi-acceptance/pairing-pin", check=False
                    ).stdout.strip()
                    if re.fullmatch(r"\d{4}", pin):
                        break
                    if process.poll() is not None:
                        raise RuntimeError("Rust client ended before requesting pairing approval")
                    time.sleep(0.25)
                else:
                    raise RuntimeError("Actual client pairing PIN missing")
                execute(server, "sh", "-c", "cat > /home/rampi/sunshine-pin", input_text=pin + "\n")
                if process.wait(timeout=190) != 0:
                    raise RuntimeError("Actual Rust Sunshine test failed; see client.log")
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
        if gtk:
            if soak:
                execute(server, "touch", "/home/rampi/stream-soak-start")
            execute(client, "cargo", "build", "--locked", "-p", "rampi-ui", "--bin", "rampi-native")
            execute(client, "rm", "-f", "/run/rampi-acceptance/pairing-pin")
            with (output / "gtk-client.log").open("wb") as log:
                process = subprocess.Popen(
                    [
                        "docker",
                        "exec",
                        "-e",
                        f"RAMPI_TEST_SUNSHINE={address}",
                        "-e",
                        f"RAMPI_TEST_STREAM_SOAK={int(soak)}",
                        client,
                        "dbus-run-session",
                        "--",
                        "bash",
                        "tests/streaming/run-gtk.sh",
                    ],
                    stdout=log,
                    stderr=log,
                )
                try:
                    for _ in range(240):
                        pin = execute(
                            client, "cat", "/run/rampi-acceptance/pairing-pin", check=False
                        ).stdout.strip()
                        if re.fullmatch(r"\d{4}", pin):
                            break
                        if process.poll() is not None:
                            raise RuntimeError(
                                "Actual GTK client ended before pairing PIN; see gtk-client.log"
                            )
                        time.sleep(0.25)
                    else:
                        raise RuntimeError("Actual GTK pairing PIN missing")
                    execute(
                        server, "sh", "-c", "cat > /home/rampi/sunshine-pin", input_text=pin + "\n"
                    )
                    if process.wait(timeout=1000 if soak else 240) != 0:
                        raise RuntimeError("Actual GTK stream failed; see gtk-client.log")
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=10)
            for index in range(2):
                run(
                    "docker",
                    "cp",
                    f"{client}:/run/rampi-acceptance/gtk-stream-{index}.png",
                    str(output / f"gtk-stream-{index}.png"),
                )
            run(
                "docker",
                "cp",
                f"{client}:/build/target/debug/rampi-native",
                str(output / "rampi-native"),
            )
        run(
            "docker",
            "cp",
            f"{client}:/tmp/rampi-received-audio.raw",
            str(output / "received-audio.raw"),
        )
        audio = (output / "received-audio.raw").read_bytes()
        sample = output / "audio-window.raw"
        window = 48000 * 4
        for offset in range(0, len(audio) - window + 1, window // 2):
            sample.write_bytes(audio[offset : offset + window])
            if fixture["verify_audio"](sample):
                break
        else:
            raise RuntimeError("Actual received PulseAudio PCM lacks the remote 997-Hz tone")
        if "RAMPI_STREAM_SUNSHINE_VIDEO_OK" not in (output / "client.log").read_text():
            raise RuntimeError("Actual Rust video/identity proof missing")
        # Export the executed component ELF and C library for independent hashes.
        run("docker", "cp", f"{client}:{binary}", str(output / "client-test"))
        run("docker", "cp", f"{client}:{library}", str(output / "libmoonlight-common.so.2.7.1"))
        execute(
            client,
            "tar",
            "--exclude=.git",
            "-cJf",
            "/run/rampi-acceptance/moonlight-sources.tar.xz",
            "-C",
            "/opt",
            "moonlight-source",
        )
        sources = output / "moonlight-sources.tar.xz"
        run(
            "docker", "cp", f"{client}:/run/rampi-acceptance/moonlight-sources.tar.xz", str(sources)
        )
        evidence = {
            "client_limits": client_limits,
            "source_revision": run("git", "rev-parse", "HEAD").stdout.strip(),
            "dirty_checkout": bool(run("git", "status", "--porcelain").stdout.strip()),
            "client_test_sha256": binary_sha,
            "moonlight_library_sha256": library_sha,
            "moonlight_source_archive_sha256": hashlib.sha256(sources.read_bytes()).hexdigest(),
            "embedded_source": embedded,
            "common_source": common,
            "video_connections": 2,
            "changed_server_key_rejected": True,
            "restored_identity": True,
            "audio_997hz_verified": True,
            "audio_window_sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
            "physical_hardware": False,
            "windows_host": False,
            "gtk_presentation": gtk,
            "sunshine_package_version": execute(
                server, "dpkg-query", "-W", "-f=${Version}", "sunshine"
            ).stdout.strip(),
        }
        if gtk:
            evidence["gtk_soak"] = soak
            if soak:
                run(
                    "docker",
                    "cp",
                    f"{client}:/run/rampi-acceptance/gtk-soak.json",
                    str(output / "gtk-soak.json"),
                )
                evidence["gtk_soak_sha256"] = hashlib.sha256(
                    (output / "gtk-soak.json").read_bytes()
                ).hexdigest()
            evidence["gtk_client_sha256"] = hashlib.sha256(
                (output / "rampi-native").read_bytes()
            ).hexdigest()
            evidence["gtk_screenshot_sha256"] = {
                f"gtk-stream-{index}.png": hashlib.sha256(
                    (output / f"gtk-stream-{index}.png").read_bytes()
                ).hexdigest()
                for index in range(2)
            }
            raw_log = execute(server, "cat", "/home/rampi/sunshine.log").stdout
            packets = re.findall(
                r"--begin ((?:keyboard|(?:absolute|relative) mouse move|"
                r"mouse (?:button|scroll|hscroll)) packet)--(.*?)--end \1--",
                raw_log,
                re.S,
            )
            receipts = [
                {
                    "kind": kind,
                    "fields": dict(re.findall(r"([A-Za-z0-9]+)\s*\[([0-9A-Fa-f -]+)\]", body)),
                }
                for kind, body in packets
            ]
            (output / "sunshine-input.json").write_text(json.dumps(receipts, indent=2) + "\n")
            evidence["sunshine_input_sha256"] = hashlib.sha256(
                (output / "sunshine-input.json").read_bytes()
            ).hexdigest()
            evidence["input_proof_scope"] = "Sunshine decoded packets; platform injection disabled"
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(
            "RAMPI_STREAM_SUNSHINE_AUDIO_VIDEO_OK: actual Rust pairing, pinned TLS rejection, "
            "two changing video connections and remote 997-Hz PCM"
        )
    finally:
        for container in containers:
            run(
                "docker",
                "cp",
                f"{container}:/home/rampi/sunshine.log",
                str(output / "sunshine.log"),
                check=False,
            )
            run(
                "docker",
                "cp",
                f"{container}:/tmp/rampi-received-audio.raw",
                str(output / "received-audio.raw"),
                check=False,
            )
            run("docker", "rm", "--force", container, check=False)
        if gtk and (output / "sunshine.log").is_file():
            text = (output / "sunshine.log").read_text(encoding="utf-8", errors="replace")
            if not (output / "sunshine-input.json").exists():
                packets = re.findall(
                    r"--begin ((?:keyboard|(?:absolute|relative) mouse move|"
                    r"mouse (?:button|scroll|hscroll)) packet)--(.*?)--end \1--",
                    text,
                    re.S,
                )
                rows = [
                    {
                        "kind": kind,
                        "fields": dict(re.findall(r"([A-Za-z0-9]+)\s*\[([0-9A-Fa-f -]+)\]", body)),
                    }
                    for kind, body in packets
                ]
                (output / "sunshine-input.json").write_text(json.dumps(rows, indent=2) + "\n")
            safe = [
                line
                for line in text.splitlines()
                if re.search(r"\]: (?:Info|Warning|Error|Fatal):", line)
            ]
            (output / "sunshine.log").write_text("\n".join(safe) + "\n", encoding="utf-8")
        if network:
            run("docker", "network", "rm", network, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-image", default="rampi-native-sunshine-test")
    parser.add_argument("--client-image", default="rampi-stream-media-test")
    parser.add_argument("--output", type=Path, default=Path("artifacts/rust/streaming-live"))
    parser.add_argument(
        "--gtk",
        action="store_true",
        help="Also exercise the actual embedded GTK page and private keyring",
    )
    parser.add_argument(
        "--soak",
        action="store_true",
        help="Also require 600 seconds of real animated GTK streaming",
    )
    args = parser.parse_args()
    if args.soak and not args.gtk:
        parser.error("--soak requires --gtk")
    main(args.server_image, args.client_image, args.output, args.gtk, args.soak)
