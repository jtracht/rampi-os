"""Reproduce native software acceptance in disposable Linux Docker containers.

Snapshots tracked/nonignored source, builds it once and freezes the binary for
runtime checks. Does not mount host devices, host services or personal profiles.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command, *, timeout=600):
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def require(result):
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def acceptance(options):
    if require(run(["docker", "info", "--format", "{{.OSType}}"])).strip() != "linux":
        raise RuntimeError("Docker must run Linux containers")
    volume = options.build_volume or "rampi-native-test-" + uuid.uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", volume):
        raise ValueError("Invalid Docker build volume name")
    output = options.artifacts.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (
        tempfile.TemporaryDirectory(prefix="rampi-native-source-") as temporary,
        tempfile.TemporaryDirectory(prefix="rampi-native-captures-", dir=output) as captured,
    ):
        source = Path(temporary)
        # The ordinary container user must traverse this source-only snapshot
        # even when the host developer uses a different UID.
        source.chmod(0o755)
        captures = Path(captured)
        if (
            source.resolve().parent != Path(tempfile.gettempdir()).resolve()
            or captures.resolve().parent != output
        ):
            raise RuntimeError("Unexpected temporary directory")
        # Only this new disposable capture folder is writable by container UID 1000.
        os.chmod(captures, 0o777)  # noqa: S103 - generated screenshots, never personal profiles
        files = require(run(["git", "ls-files", "-c", "--others", "--exclude-standard", "-z"]))
        digest = hashlib.sha256()
        for name in sorted(set(files.split("\0")) - {""}):
            original = ROOT / name
            if not original.is_file():
                continue
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
            digest.update(name.encode() + b"\0" + hashlib.sha256(target.read_bytes()).digest())
        revision = require(run(["git", "rev-parse", "HEAD"])).strip()
        dirty = bool(require(run(["git", "status", "--porcelain"])).strip())
        (output / "source-state.json").write_text(
            json.dumps(
                {
                    "revision": revision,
                    "working_tree_changes": dirty,
                    "snapshot_sha256": digest.hexdigest(),
                    "hardware_tests": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if not options.skip_image_build:
            print("Building the pinned native test environment …", flush=True)
            require(
                run(
                    [
                        "docker",
                        "build",
                        "-t",
                        options.image,
                        "-f",
                        str(source / "tests/rust/Dockerfile"),
                        str(source),
                    ],
                    timeout=1200,
                )
            )
        base = [
            "docker",
            "run",
            "--rm",
            "--mount",
            f"type=bind,source={source},target=/src,readonly",
        ]
        build = ["--mount", f"type=volume,source={volume},target=/build"]
        frozen = ["--mount", f"type=volume,source={volume},target=/build,readonly"]
        guarded = ["--network", "none", "-e", "RAMPI_TEST_CONTAINER=1"]
        user = ["--user", "1000:1000"]
        budget = ["--memory=1g", "--memory-swap=1g", "--cpus=4"]
        # Needed by WebKit's own Bubblewrap sandbox on disposable Docker only.
        sandbox = [
            "--security-opt",
            "seccomp=unconfined",
            "--security-opt",
            "apparmor=unconfined",
            "--security-opt",
            "systempaths=unconfined",
        ]
        try:
            print("Checking and compiling the frozen source …", flush=True)
            result = run(
                base
                + build
                + [
                    "-e",
                    "CARGO_HOME=/build/cargo",
                    options.image,
                    "bash",
                    "-ec",
                    "cargo fmt --all --check; cargo test --locked -p rampi-core; "
                    "cargo test --locked -p rampi-stream -j1; "
                    "cargo clippy --locked --workspace --all-targets -j1 -- -D warnings; "
                    "cargo build --locked --workspace -j1",
                ],
                timeout=1200,
            )
            (output / "build.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            require(result)
            require(
                run(
                    [
                        "docker",
                        "build",
                        "--build-arg",
                        "BASE_IMAGE=" + options.image,
                        "-f",
                        str(source / "tests/remote/Dockerfile"),
                        "-t",
                        "rampi-native-rdp-fixture",
                        str(source),
                    ],
                    timeout=600,
                )
            )
            stages = [
                (
                    "rdp-acceptance.log",
                    [
                        sys.executable,
                        str(source / "tests/rust/test-rdp.py"),
                        "--image",
                        options.image,
                        "--server-image",
                        "rampi-native-rdp-fixture",
                        "--build-volume",
                        volume,
                        "--artifacts",
                        str(captures),
                    ],
                ),
                (
                    "bootstrap-tls.log",
                    base
                    + frozen
                    + guarded
                    + budget
                    + [options.image, "python3", "tests/rust/test-bootstrap.py"],
                ),
                (
                    "cloud-kanban.log",
                    base
                    + frozen
                    + guarded
                    + budget
                    + [options.image, "python3", "tests/rust/test-cloud-kanban.py"],
                ),
                (
                    "wayland.log",
                    base
                    + frozen
                    + guarded
                    + user
                    + budget
                    + sandbox
                    + [
                        "--mount",
                        f"type=bind,source={captures},target=/artifacts",
                        "-e",
                        "RAMPI_TEST_ARTIFACTS=/artifacts",
                        options.image,
                        "dbus-run-session",
                        "--",
                        "bash",
                        "tests/rust/run-wayland.sh",
                    ],
                ),
                (
                    "network-contract.log",
                    base
                    + frozen
                    + guarded
                    + user
                    + [options.image, "python3", "tests/rust/test-services.py"],
                ),
                (
                    "bluetooth-contract.log",
                    base
                    + frozen
                    + guarded
                    + user
                    + [options.image, "python3", "tests/rust/test-bluetooth.py"],
                ),
                (
                    "wireguard-contract.log",
                    base
                    + frozen
                    + guarded
                    + user
                    + [options.image, "python3", "tests/rust/test-wireguard.py"],
                ),
                (
                    "wireguard-peers.log",
                    [
                        sys.executable,
                        str(source / "scripts/test-native-wireguard.py"),
                        "--image",
                        options.image,
                        "--build-volume",
                        volume,
                    ],
                ),
                (
                    "tailscale-status.log",
                    base
                    + frozen
                    + guarded
                    + user
                    + [options.image, "python3", "tests/rust/test-tailscale.py"],
                ),
                (
                    "account-pam.log",
                    base
                    + frozen
                    + guarded
                    + budget
                    + [options.image, "python3", "tests/rust/test-accounts.py"],
                ),
                (
                    "browser-https.log",
                    base
                    + frozen
                    + guarded
                    + budget
                    + sandbox
                    + [options.image, "python3", "tests/rust/test-browser.py"],
                ),
            ]
            for name, command in stages:
                print("Running " + name + " …", flush=True)
                result = run(command)
                (output / name).write_text(result.stdout + result.stderr, encoding="utf-8")
                if name == "wayland.log":
                    for item in captures.iterdir():
                        if item.is_file():
                            shutil.copy2(item, output / item.name)
                require(result)
            print("Running actual private Gitea HTTPS/GTK acceptance …", flush=True)
            require(
                run(
                    [
                        sys.executable,
                        str(source / "tests/rust/test-gitea-live.py"),
                        "--image",
                        options.image,
                        "--build-volume",
                        volume,
                        "--artifacts",
                        str(output / "gitea-live"),
                    ]
                )
            )
            soak = output / "mixed-soak"
            soak.mkdir()
            # Runtime UID 1000 writes only nonsecret test captures here; the
            # invoking CI user also needs to collect receipts and logs.
            soak.chmod(0o777)
            print("Running ten-minute mixed RDP/WebKit/PTY workload …", flush=True)
            result = run(
                [
                    sys.executable,
                    str(source / "tests/rust/test-rdp.py"),
                    "--soak",
                    "--image",
                    options.image,
                    "--server-image",
                    "rampi-native-rdp-fixture",
                    "--build-volume",
                    volume,
                    "--artifacts",
                    str(soak),
                ],
                timeout=900,
            )
            (soak / "acceptance.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            require(result)
            require(
                run(
                    base
                    + [
                        options.image,
                        "shellcheck",
                        "installer/raspberrypi/setup.sh",
                        "system/rampi",
                        "system/rampi-session",
                        "system/rampi-wayland-start",
                        "system/rampi-health",
                        "system/rampi-greeter",
                        "installer/raspberrypi/greeter-profile.sh",
                        "tests/rust/run-wayland.sh",
                    ]
                )
            )
            if options.installer:
                result = run(
                    base
                    + frozen
                    + guarded
                    + [options.image, "bash", "tests/rust/test-installer.sh"]
                )
                (output / "installer-lifecycle.log").write_text(
                    result.stdout + result.stderr, encoding="utf-8"
                )
                require(result)
            result = run(
                [sys.executable, str(source / "scripts/check-native-evidence.py"), str(output)]
                + (["--require-installer"] if options.installer else [])
            )
            print(require(result).strip())
            print("Artifacts: " + str(output))
        finally:
            if not options.build_volume:
                run(["docker", "volume", "rm", volume])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="rampi-rust-dev")
    parser.add_argument(
        "--skip-image-build",
        action="store_true",
        help="Use the existing image; Rust sources are still rebuilt and checked",
    )
    parser.add_argument(
        "--build-volume", help="Explicit reusable build cache; do not use it concurrently"
    )
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts/rust-local")
    parser.add_argument(
        "--installer",
        action="store_true",
        help="Only on native ARM64: also run the real installer lifecycle",
    )
    acceptance(parser.parse_args())
