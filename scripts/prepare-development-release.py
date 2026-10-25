"""Assemble a verified native prerelease without claiming regular-product readiness."""

import argparse
import hashlib
import json
import re
import runpy
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def development_tag(version):
    if not re.fullmatch(
        r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-"
        r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*",
        version,
    ):
        raise ValueError("Development publication requires an explicit SemVer prerelease version")
    if any(
        part.isdigit() and len(part) > 1 and part.startswith("0")
        for part in version.split("-", 1)[1].split(".")
    ):
        raise ValueError("Numeric prerelease identifiers cannot have leading zeroes")
    return "v" + version


def check_remote_tag(root, tag):
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--tags", "origin", "refs/tags/" + tag],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode == 0:
        raise ValueError("Release tag already exists; refusing to replace it: " + tag)
    if result.returncode != 2 or result.stdout.strip():
        raise ValueError("Remote tag state could not be verified")


def regular_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular release artifact: " + path.name)
    return path


def assemble(root, image_dir, version, revision):
    tag = development_tag(version)
    output = root / "artifacts/release"
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Invalid immutable release source")
    readiness = json.loads((root / "packaging/readiness.json").read_text(encoding="utf-8"))
    if readiness.get("regular_release") is not False:
        raise ValueError("This publisher is specifically for an unfinished development product")
    if json.loads(regular_file(image_dir / "readiness.json").read_text()) != readiness:
        raise ValueError("Image readiness and release source differ")
    images = list(image_dir.glob("*.img.xz"))
    if len(images) != 1:
        raise ValueError("Exactly one fresh flashable image is required")
    image = regular_file(images[0])
    with image.open("rb") as stream:
        image_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    # This rechecks visible native frames, both PAM identities, unchanged installed
    # files, the image digest and its actual source; a successful build alone fails.
    checker = runpy.run_path(str(root / "scripts/check-image-login-evidence.py"))["check"]
    proof = checker(image_dir / "graphical-login", revision, image_sha)
    runpy.run_path(str(root / "scripts/check-source-archives.py"))["check"](
        image_dir, revision, (root / "Cargo.lock").read_bytes()
    )
    required = [
        image.name,
        f"rampi-linux-arm64-{version}.tar.xz",
        "package-manifest.tsv",
        "dependency-licenses.tar.xz",
        "dependency-sources.tar.xz",
        "debian-source-archives.json",
        "rust-dependency-sources.tar.xz",
        "qemu-boot.log",
        "qemu-environment.txt",
        "partitions.json",
        "pi-gen-revision.txt",
        "readiness.json",
        "native-image-provenance.txt",
    ]
    for name in required:
        regular_file(image_dir / name)
        if (output / name).exists():
            raise ValueError("Refusing to overwrite an assembled artifact: " + name)
    with tarfile.open(image_dir / f"rampi-linux-arm64-{version}.tar.xz") as archive:
        binary_sha = archive.extractfile("bin/binary-sha256.txt").read().decode().strip()
        source = archive.extractfile("bin/source-revision.txt").read().decode().strip()
    if source != revision or binary_sha != proof["native_binary_sha256"]:
        raise ValueError("Image acceptance and release program identity differ")
    for name in required:
        shutil.copyfile(image_dir / name, output / name)
    # Explicitly copy only nonsecret image acceptance outputs into a flat asset.
    evidence = output / "graphical-login-evidence.tar.xz"
    if evidence.exists():
        raise ValueError("Image evidence asset already exists")
    names = [
        "environment.json",
        "serial.log",
        "captures/login-proof.json",
        "captures/greeter.png",
        "captures/rampi-login.png",
        "captures/rampi-other.png",
    ]
    with tarfile.open(evidence, "w:xz") as archive:
        for name in names:
            source = regular_file(image_dir / "graphical-login" / name)
            archive.add(source, arcname="graphical-login/" + name, recursive=False)
    manifest = {
        "schema": 1,
        "kind": "prerelease",
        "tag": tag,
        "version": version,
        "revision": revision,
        "regular_release": False,
        "image": image.name,
        "image_sha256": image_sha,
        "native_binary_sha256": binary_sha,
        "physical_hardware_tests": False,
    }
    (output / "development-release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    checksums = []
    for item in sorted(output.iterdir()):
        if item.name == "SHA256SUMS":
            continue
        regular_file(item)
        with item.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        checksums.append(f"{digest}  {item.name}")
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    notes = (
        f"Native Rust/GTK4/Wayland development release {tag}.\n\n"
        "This is an unfinished development version, not a regular completed product. "
        "The release uses the exact source revision " + revision + ".\n\n"
        "Includes a freshly built ARM64 Raspberry Pi 3 B+ image, source, native package, "
        "setup.sh, setup.ps1, Windows host package, checksums, licenses and QEMU evidence. "
        "Graphical image login, two Linux accounts and unchanged installed program files "
        "were checked in software. Physical hardware testing is excluded.\n\n"
        "Known gaps include fully embedded desktop streaming, language selection, "
        "end-to-end PAM/keyring acceptance and personal Windows/provider acceptance. "
        "No model requests were performed. See docs/NATIVE-SUPPORT.de.md in the source. "
        "Device updates remain manual.\n"
    )
    (root / "artifacts/development-release-notes.md").write_text(notes, encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag-only", action="store_true")
    parser.add_argument("--check-remote-tag", action="store_true")
    parser.add_argument("--image-dir", type=Path, default=ROOT / "artifacts/image")
    args = parser.parse_args()
    version = tomllib.loads((ROOT / "Cargo.toml").read_text())["workspace"]["package"]["version"]
    if args.check_remote_tag:
        check_remote_tag(ROOT, development_tag(version))
    if args.tag_only:
        print("tag=" + development_tag(version))
        return
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = assemble(ROOT, args.image_dir.resolve(), version, revision)
    print("PASS: development artifacts and installed-image proof assembled for " + manifest["tag"])


if __name__ == "__main__":
    main()
