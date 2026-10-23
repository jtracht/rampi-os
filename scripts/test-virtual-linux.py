"""Boot an isolated Debian/QEMU acceptance VM; never use host radio devices."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import yaml

VERSION = "20261017-2634"
DIGESTS = {
    "amd64": "62aa92aeff32cbf3fe6c01f410fef4035b1603a512f073c9f8889072168de9e49fa361ba48621359fc7608ad91225e823ea233feb33f612eb39e50aaf21957fe",  # noqa: E501 # pragma: allowlist secret
    "arm64": "e578f7ddf4033ff24f27b3daf27225831ba2824b72165425eb4a0dbfe918fc1e7a6c9adb18b2440dfae41781303aa754f18886cd1574576cda567aa24bf9221d",  # noqa: E501 # pragma: allowlist secret
}


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=60).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument(
        "--native-binary", type=Path, help="Built Rust NetworkManager acceptance executable"
    )
    parser.add_argument(
        "--native-session-binary",
        type=Path,
        help="Test graphical greetd/PAM login and the actual native session",
    )
    parser.add_argument(
        "--prepared", action="store_true", help="Local development only: reuse a prepared OS cache"
    )
    parser.add_argument("--prepare-cache", action="store_true")
    parser.add_argument(
        "--resume-development",
        action="store_true",
        help="Debug only: reuse the existing login guest, never release evidence",
    )
    options = parser.parse_args()
    if options.resume_development and not options.native_session_binary:
        raise SystemExit("Only the designated graphical login development guest may be resumed")
    if options.native_session_binary and (
        options.probe or options.native_binary or options.prepare_cache
    ):
        raise SystemExit("Graphical login is a separate full acceptance run")
    if options.prepare_cache and not options.probe:
        raise SystemExit("Only an OS probe, without test users or credentials, may become a cache")
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if not arch:
        raise SystemExit("Run on Linux amd64 or arm64 with QEMU and cloud-image-utils installed")
    root = Path(__file__).resolve().parents[1]
    cache = root / ".tools/virtual-cloud"
    output = root / (
        "artifacts/virtual-login" if options.native_session_binary else "artifacts/virtual-linux"
    )
    cache.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    if options.native_session_binary:
        captures = output / "captures"
        captures.mkdir(exist_ok=True)
        for generated in ["greeter.png", "rampi-login.png", "rampi-other.png", "login-proof.json"]:
            (captures / generated).unlink(missing_ok=True)
    image = cache / f"debian-{VERSION}-{arch}.qcow2"
    if not image.exists():
        url = (
            f"https://cloud.debian.org/images/cloud/trixie/{VERSION}/"
            f"debian-13-generic-{arch}-{VERSION}.qcow2"
        )
        print("Downloading pinned official Debian generic image", flush=True)
        with urllib.request.urlopen(url, timeout=90) as response, image.open("wb") as stream:
            shutil.copyfileobj(response, stream)
    with image.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha512").hexdigest()
    if digest != DIGESTS[arch]:
        raise SystemExit(
            "Debian cloud image checksum mismatch; cached image retained for inspection"
        )
    backing = cache / f"prepared-{arch}.qcow2" if options.prepared else image
    if not backing.exists():
        raise SystemExit("Prepared development cache is missing")
    source = output / "source"
    source.mkdir(exist_ok=True)
    # Share a dedicated source-only copy, never .git, host HOME or ignored tools/keys.
    for name in ("client", "scripts", "installer", "system", "docs", "assets", "image"):
        shutil.copytree(
            root / name,
            source / name,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for name in ("setup.sh", "LICENSE", "NOTICE", "pyproject.toml"):
        shutil.copy2(root / name, source / name)
    native_digest = None
    if options.native_binary:
        if options.probe or not options.native_binary.is_file():
            raise SystemExit("Native acceptance requires a built executable and a full guest run")
        native_target = source / "rampi-network-acceptance"
        shutil.copy2(options.native_binary, native_target)
        native_target.chmod(0o755)
        native_digest = hashlib.sha256(native_target.read_bytes()).hexdigest()
    elif (source / "rampi-network-acceptance").exists():
        (source / "rampi-network-acceptance").unlink()
    if options.native_session_binary:
        native_target = source / "rampi-native"
        if options.native_session_binary.resolve() != native_target.resolve():
            shutil.copy2(options.native_session_binary, native_target)
        native_target.chmod(0o755)
        native_digest = hashlib.sha256(native_target.read_bytes()).hexdigest()
    config = {
        "hostname": "rampi-acceptance",
        "manage_etc_hosts": True,
        "package_update": True,
        "packages": [
            "bluez",
            "bluez-test-tools",
            "network-manager",
            "wpasupplicant",
            "hostapd",
            "dnsmasq-base",
            "iw",
            "iputils-ping",
            "python3-gi",
            "gir1.2-nm-1.0",
            "python3-pyside6.qtcore",
            "polkitd",
            "rfkill",
        ],
        "write_files": [{"path": "/etc/rampi-acceptance-vm", "content": "isolated-qemu\n"}],
        "runcmd": [
            [
                "bash",
                "-c",
                "mkdir -p /opt/rampi-source; "
                "mount -t 9p -o trans=virtio,version=9p2000.L,ro rampisource /opt/rampi-source "
                "&& bash /opt/rampi-source/scripts/virtual/guest-run.sh "
                + ("--probe" if options.probe else "")
                + "; result=$?; echo RAMPI_GUEST_EXIT=$result; exit $result",
            ]
        ],
        "power_state": {"mode": "poweroff", "delay": "now", "timeout": 30},
    }
    if options.native_session_binary:
        config["packages"] += [
            "greetd",
            "wlgreet",
            "labwc",
            "wtype",
            "grim",
            "wlrctl",
            "dbus-user-session",
            "libgtk-4-1",
            "libvte-2.91-gtk4-0",
            "libwebkitgtk-6.0-4",
            "libnm0",
            "libcanberra0",
            "libgstreamer-plugins-base1.0-0",
            "libssl3t64",
            "libgtk-4-media-gstreamer",
            "librsvg2-common",
            "gnome-keyring",
            "fonts-dejavu-core",
        ]
        config["runcmd"][0][2] = (
            "mkdir -p /opt/rampi-source /opt/rampi-captures; "
            "mount -t 9p -o trans=virtio,version=9p2000.L,ro rampisource /opt/rampi-source && "
            "mount -t 9p -o trans=virtio,version=9p2000.L rampicaptures /opt/rampi-captures && "
            "python3 /opt/rampi-source/scripts/virtual/test-login-guest.py; "
            "result=$?; echo RAMPI_GUEST_EXIT=$result; exit $result"
        )
    (output / "user-data").write_text("#cloud-config\n" + yaml.safe_dump(config), encoding="utf-8")
    (output / "meta-data").write_text(f"instance-id: rampi-{time.time_ns()}\n", encoding="utf-8")
    seed = output / "seed.img"
    if seed.exists():
        seed.unlink()
    run("cloud-localds", str(seed), str(output / "user-data"), str(output / "meta-data"))
    overlay = output / "guest.qcow2"
    if options.resume_development and not overlay.is_file():
        raise SystemExit("No existing development guest to resume")
    if overlay.exists() and not options.resume_development:
        overlay.unlink()
    if not options.resume_development:
        run("qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", str(backing), str(overlay))
        run("qemu-img", "resize", str(overlay), "10G")
    qemu = "qemu-system-aarch64" if arch == "arm64" else "qemu-system-x86_64"
    args = [
        qemu,
        "-machine",
        "virt" if arch == "arm64" else "q35",
        "-accel",
        "tcg,thread=multi",
        "-cpu",
        "cortex-a72" if arch == "arm64" else "max",
        "-m",
        "1024",
        "-smp",
        "4",
        "-nographic",
        "-monitor",
        "none",
        "-no-reboot",
        "-drive",
        f"file={overlay},format=qcow2,if=virtio",
        "-drive",
        f"file={seed},format=raw,if=virtio,readonly=on",
        "-nic",
        "user,model=virtio-net-pci",
        "-virtfs",
        f"local,path={source},mount_tag=rampisource,security_model=none,readonly=on",
    ]
    if arch == "arm64":
        args += ["-bios", "/usr/share/qemu-efi-aarch64/QEMU_EFI.fd"]
    if options.native_session_binary:
        captures = output / "captures"
        captures.mkdir(exist_ok=True)
        args += ["-virtfs", f"local,path={captures},mount_tag=rampicaptures,security_model=none"]
        args += [
            "-device",
            "qemu-xhci,id=rampi-usb",
            "-device",
            "usb-kbd,bus=rampi-usb.0",
            "-device",
            "usb-tablet,bus=rampi-usb.0",
        ]
    (output / "environment.json").write_text(
        json.dumps(
            {
                "architecture": arch,
                "image_version": VERSION,
                "image_sha512": digest,
                "memory_mib": 1024,
                "cpus": 4,
                "physical_devices": False,
                "native_binary_sha256": native_digest,
                "prepared_development_cache": options.prepared,
                "resumed_development_guest": options.resume_development,
                "graphical_login": bool(options.native_session_binary),
                "qemu": run(qemu, "--version").splitlines()[0],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        "Booting 1-GiB guest with "
        + (
            "graphical login and emulated input"
            if options.native_session_binary
            else "virtual radios"
        )
        + "; no host devices forwarded",
        flush=True,
    )
    with (output / "serial.log").open("wb") as log:
        with subprocess.Popen(args, stdout=log, stderr=log) as process:
            try:
                process.wait(timeout=options.timeout)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=15)
                raise SystemExit(
                    "Virtual Linux acceptance timed out; inspect artifacts/virtual-linux"
                ) from None
    text = (output / "serial.log").read_text(errors="replace")
    for line in text.splitlines():
        if "RAMPI_" in line:
            print(line[line.index("RAMPI_") :])
    marker = "RAMPI_VIRTUAL_PROBE_OK" if options.probe else "RAMPI_VIRTUAL_ACCEPTANCE_OK"
    if options.native_session_binary:
        marker = "RAMPI_GRAPHICAL_LOGIN_OK"
    if options.native_binary and not all(
        m in text for m in ["RAMPI_RUST_WIFI_LIVE_OK", "RAMPI_RUST_WIFI_OTHER_USER_OK"]
    ):
        raise SystemExit("Native virtual WLAN evidence missing; inspect serial.log")
    if marker not in text or "RAMPI_GUEST_EXIT=0" not in text:
        raise SystemExit(f"Virtual Linux acceptance failed; inspect {output}/serial.log")
    if options.prepare_cache:
        prepared_next = cache / f"prepared-next-{arch}.qcow2"
        run("qemu-img", "convert", "-O", "qcow2", str(overlay), str(prepared_next))
        prepared_next.replace(cache / f"prepared-{arch}.qcow2")


if __name__ == "__main__":
    main()
