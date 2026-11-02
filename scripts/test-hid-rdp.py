"""Run existing isolated XRDP servers and the normal QEMU/PAM/HID guest together."""

import argparse
import hashlib
import json
import secrets
import subprocess
import time
import uuid
from pathlib import Path


def command(*args, data=None, check=True, timeout=120):
    return subprocess.run(args, input=data, capture_output=True, check=check, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-image", default="rampi-rdp-fixture")
    parser.add_argument("--virtual-image", default="rampi-virtual-tools")
    parser.add_argument("--sdk-image", default="rampi-rust-dev")
    parser.add_argument("--build-volume", default="rampi-rust-build")
    parser.add_argument("--timeout", type=int, default=6000)
    parser.add_argument("--artifacts", type=Path, help="New directory inside workspace artifacts")
    parser.add_argument(
        "--development", action="store_true", help="Component checks only; never fresh acceptance"
    )
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    suffix = uuid.uuid4().hex[:12]
    network = "rampi-hid-rdp-" + suffix
    guest = network + "-guest"
    output = root / "artifacts" / ("hid-rdp-" + suffix)
    if options.artifacts:
        output = (root / options.artifacts).resolve()
    if not output.is_relative_to(root / "artifacts") or output.exists():
        parser.error("The evidence directory must be new and inside workspace artifacts")
    relative = output.relative_to(root).as_posix()
    private = root / "artifacts" / (".hid-rdp-private-" + suffix + ".json")
    print("Joined input evidence: " + str(output), flush=True)
    created, servers, accounts, identities = False, {}, {}, {}
    try:
        command(
            "docker", "network", "create", "--internal", "--label", "rampi.test=hid-rdp", network
        )
        created = True
        info = json.loads(command("docker", "network", "inspect", network).stdout)[0]
        if info["Internal"] is not True:
            raise RuntimeError("The designated fixture network is not internal")
        for index, user in enumerate(["rampi-hid-one", "rampi-hid-two"]):
            name = network + "-server-" + str(index)
            servers[user] = name
            command(
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--network",
                network,
                "--user",
                "root",
                "--label",
                "rampi.test=hid-rdp",
                "-v",
                str(root) + ":/src:ro",
                "-e",
                "RAMPI_TEST_CONTAINER=1",
                options.server_image,
                "python3",
                "/src/tests/rust/test-rdp.py",
                "--server",
                "--joined-hid",
            )
            for _ in range(100):
                if (
                    command(
                        "docker",
                        "exec",
                        name,
                        "test",
                        "-f",
                        "/run/rampi-rdp-server-ready",
                        check=False,
                    ).returncode
                    == 0
                ):
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("Own XRDP fixture did not become ready")
            password = secrets.token_urlsafe(24)
            command(
                "docker",
                "exec",
                "-i",
                name,
                "chpasswd",
                data=("rdpuser:" + password + "\n").encode(),
            )
            der = command(
                "docker",
                "exec",
                name,
                "openssl",
                "x509",
                "-in",
                "/etc/xrdp/cert.pem",
                "-outform",
                "DER",
            ).stdout
            nonce = (
                command("docker", "exec", name, "cat", "/run/rampi-rdp-probe")
                .stdout.decode()
                .strip()
            )
            info = json.loads(command("docker", "inspect", name).stdout)[0]
            if info["HostConfig"]["PortBindings"]:
                raise RuntimeError("Own fixture unexpectedly published a host port")
            address = info["NetworkSettings"]["Networks"][network]["IPAddress"]
            accounts[user] = {
                "address": address,
                "password": password,
                "fingerprint": hashlib.sha256(der).hexdigest(),
                "nonce": nonce,
            }
            identities[user] = {"image_id": info["Image"], "nonce": nonce, "published_ports": False}
        private.write_text(
            json.dumps(
                {"scope": "rampi-isolated-hid-rdp", "internal_network": True, "accounts": accounts}
            )
        )
        private.chmod(0o600)
        command(
            "docker",
            "create",
            "--name",
            guest,
            "--network",
            "bridge",
            "--memory",
            "3g",
            "--memory-swap",
            "3g",
            "--cpus",
            "4",
            "--label",
            "rampi.test=hid-rdp",
            "-v",
            str(root) + ":/app",
            "-v",
            options.build_volume + ":/build:ro",
            "-v",
            str(private) + ":/run/rdp-fixtures.json:ro",
            options.virtual_image,
            "python3",
            "scripts/test-virtual-linux.py",
            "--native-session-binary",
            "/build/target/debug/rampi-native",
            "--rdp-fixtures",
            "/run/rdp-fixtures.json",
            "--output-directory",
            "/app/" + relative,
            "--timeout",
            str(options.timeout),
        )
        command("docker", "network", "connect", "--gw-priority", "-1", network, guest)
        # Do not buffer credentials or entire cloud-init logs in a public proof.
        with (root / "artifacts" / ("hid-rdp-" + suffix + ".log")).open("wb") as log:
            result = subprocess.run(
                ["docker", "start", "--attach", guest],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=options.timeout + 300,
            )
        state = json.loads(command("docker", "inspect", guest).stdout)[0]["State"]
        for user, name in servers.items():
            destination = output / "server-receipts" / user
            destination.mkdir(parents=True)
            for filename in [".rampi-input", ".rampi-events.jsonl", ".rampi-nonce"]:
                command(
                    "docker",
                    "cp",
                    name + ":/home/rdpuser/.rampi-hid-receipts/" + filename,
                    str(destination / filename),
                    check=False,
                )
            for filename, source_path in {
                "xrdp.log": "/var/log/xrdp.log",
                "xrdp-sesman.log": "/var/log/xrdp-sesman.log",
                "desktop.log": "/home/rdpuser/desktop.log",
            }.items():
                command(
                    "docker",
                    "cp",
                    name + ":" + source_path,
                    str(destination / filename),
                    check=False,
                )
        public_text = [output / "serial.log"] + list((output / "captures").rglob("*.json"))
        public_text.extend((output / "server-receipts").rglob("*.log"))
        public_text.append(root / "artifacts" / ("hid-rdp-" + suffix + ".log"))
        for filename in public_text:
            if filename.is_file() and any(
                account["password"].encode() in filename.read_bytes()
                for account in accounts.values()
            ):
                raise RuntimeError("Generated fixture password appeared in public test evidence")
        metadata = {
            "internal_network": True,
            "servers": identities,
            "server_source_sha256": hashlib.sha256(
                (root / "tests/rust/test-rdp.py").read_bytes()
            ).hexdigest(),
            "complete_product_acceptance": False,
            "development_component_only": options.development,
        }
        (output / "rdp-fixture-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        if result.returncode or state["ExitCode"]:
            raise RuntimeError("Joined input guest failed; inspect " + relative + "/serial.log")
        digest = (
            command(
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "-v",
                options.build_volume + ":/build:ro",
                options.sdk_image,
                "sha256sum",
                "/build/target/debug/rampi-native",
            )
            .stdout.decode()
            .split()[0]
        )
        if options.development:
            code = (
                "import runpy; from pathlib import Path; "
                "runpy.run_path('scripts/check-hid-rdp-evidence.py')['component'](Path("
                + repr(relative)
                + "),"
                + repr(digest)
                + "); print('LOCAL_JOINED_COMPONENT_OK_NOT_FRESH_ACCEPTANCE')"
            )
            checks = ["python3", "-c", code]
        else:
            checks = [
                "python3",
                "scripts/check-hid-rdp-evidence.py",
                relative,
                "--expected-binary",
                digest,
            ]
        checked = command(
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            str(root) + ":/src:ro",
            "-w",
            "/src",
            options.sdk_image,
            *checks,
        )
        print(checked.stdout.decode())
        print("Evidence: " + str(output))
    finally:
        command("docker", "rm", "-f", guest, check=False)
        for name in servers.values():
            command("docker", "rm", "-f", name, check=False)
        if created:
            command("docker", "network", "rm", network, check=False)
        private.unlink(missing_ok=True)
        for filename in ["user-data", "seed.img"]:
            (output / filename).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
