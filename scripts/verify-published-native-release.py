"""Download and independently audit a source-bound native GitHub release."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "jtracht/rampi-os"


def api(endpoint):
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/{endpoint}"], check=True,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    return json.loads(result.stdout)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(tag, revision, destination):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("A full accepted source revision is required")
    checked_revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()
    if checked_revision != revision:
        raise ValueError("Run frozen validators from the accepted source revision")
    for options in (["diff", "--quiet"], ["diff", "--cached", "--quiet"]):
        subprocess.run(["git", *options], cwd=ROOT, check=True)
    version = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))[
        "workspace"
    ]["package"]["version"]
    regular = re.fullmatch(
        r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version,
    ) is not None
    if tag != "v" + version:
        raise ValueError("Requested tag does not match the frozen source version")
    release = api("releases/tags/" + tag)
    if (release["tag_name"] != tag or release["draft"]
            or release["prerelease"] is not (not regular)):
        raise ValueError("Expected a published release with matching stability status")
    target = api("git/ref/tags/" + tag)["object"]
    for _ in range(4):
        if target["type"] == "commit":
            break
        if target["type"] != "tag":
            raise ValueError("Unexpected tag object")
        target = api("git/tags/" + target["sha"])["object"]
    if target["type"] != "commit" or target["sha"] != revision:
        raise ValueError("Published tag does not match accepted source")
    assets = {}
    for item in release["assets"]:
        name = item["name"]
        if (not name or name in {".", ".."} or "/" in name or "\\" in name
                or Path(name).name != name or name in assets or item["state"] != "uploaded"):
            raise ValueError("Unsafe, duplicate or incomplete GitHub asset")
        assets[name] = item
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ValueError("Use an empty download directory; never mix release attempts")
    subprocess.run([
        "gh", "release", "download", tag, "--repo", REPO,
        "--dir", str(destination),
    ], check=True)
    if {p.name for p in destination.iterdir()} != set(assets):
        raise ValueError("Downloaded assets differ from GitHub release")
    hashes = {name: digest(destination / name) for name in assets}
    server_verified = []
    for name, item in assets.items():
        if (destination / name).stat().st_size != item["size"]:
            raise ValueError("GitHub asset size mismatch: " + name)
        if item.get("digest") is not None:
            if item["digest"] != "sha256:" + hashes[name]:
                raise ValueError("GitHub server digest mismatch: " + name)
            server_verified.append(name)
    checksums = {}
    for line in (destination / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if name in checksums or hashes.get(name) != expected:
            raise ValueError("Invalid or mismatching manifest checksum: " + name)
        checksums[name] = expected
    if set(checksums) != set(assets) - {"SHA256SUMS"}:
        raise ValueError("Checksum manifest does not cover every published asset")
    manifest_name = "native-release.json" if regular else "development-release.json"
    manifest = json.loads((destination / manifest_name).read_text())
    if (manifest["revision"] != revision or manifest["tag"] != tag
            or manifest["kind"] != ("release" if regular else "prerelease")
            or manifest["regular_release"] is not regular
            or manifest["physical_hardware_tests"] is not False
            or hashes[manifest["image"]] != manifest["image_sha256"]):
        raise ValueError("Release manifest/source/image mismatch")
    subprocess.run([
        sys.executable, str(ROOT / "scripts/check-artifacts.py"), str(destination), "--image",
    ], check=True)
    report = {
        "tag": tag, "revision": revision, "release_url": release["html_url"],
        "image": manifest["image"], "image_sha256": manifest["image_sha256"],
        "downloaded_and_verified_assets": hashes,
        "github_server_digest_verified_assets": server_verified,
        "graphical_image_proof_verified": True,
        "regular_release": regular,
    }
    destination.with_suffix(".verified.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    options = parser.parse_args()
    audit(options.tag, options.revision, options.destination.resolve())
