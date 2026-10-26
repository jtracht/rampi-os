"""Check exact distro and Cargo source coverage before publishing an image."""

import argparse
import hashlib
import json
import re
import runpy
import tarfile
import tomllib
from email.parser import Parser
from pathlib import Path, PurePosixPath


def inventory(path, prefix):
    result = {}
    with tarfile.open(path, "r|xz") as archive:
        for item in archive:
            if item.name == prefix and item.isdir():
                continue
            if not item.name.startswith(prefix + "/"):
                raise ValueError("Unexpected source archive root")
            name = item.name[len(prefix) + 1 :]
            if "\\" in name or ".." in PurePosixPath(name).parts:
                raise ValueError("Unsafe source archive path")
            if item.isdir():
                continue
            if not item.isfile() or name in result:
                raise ValueError("Source archive link, special file or duplicate")
            metadata = name in {
                "Cargo.lock",
                "config.toml",
                "source-revision.txt",
                "source-archives.json",
                "packages-and-sources.tsv",
                "git-source-revisions.json",
            } or name.endswith(("/.cargo-checksum.json", ".dsc"))
            stream = archive.extractfile(item)
            if metadata:
                if item.size > 16 * 1024**2:
                    raise ValueError("Source metadata too large")
                data = stream.read()
                sha = hashlib.sha256(data).hexdigest()
            else:
                data = None
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            result[name] = {"size": item.size, "sha256": sha, "data": data}
    return result


def check_rust(entries, lock, revision):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Exact source revision required")
    if entries["Cargo.lock"]["data"] != lock:
        raise ValueError("Cargo sources use a different lockfile")
    if entries["source-revision.txt"]["data"].decode().strip() != revision:
        raise ValueError("Cargo sources use a different source revision")
    configuration = tomllib.loads(entries["config.toml"]["data"].decode())["source"]
    if (
        configuration["crates-io"]["replace-with"] != "vendored-sources"
        or configuration["vendored-sources"]["directory"] != "vendor-sources"
    ):
        raise ValueError("Cargo source configuration is not portable")
    required = {"Cargo.lock", "config.toml", "source-revision.txt", "git-source-revisions.json"}
    git_records = json.loads(entries["git-source-revisions.json"]["data"])
    git_proof = {(p["name"], p["version"], p["source"]): p["commit"] for p in git_records}
    if len(git_proof) != len(git_records):
        raise ValueError("Duplicate Git source provenance")
    expected_git = set()
    count = 0
    for package in tomllib.loads(lock.decode())["package"]:
        source = package.get("source")
        if source is None:
            continue  # These local sources are in the source checkout archive.
        if source.startswith("git+"):
            identity = (package["name"], package["version"], source)
            expected_git.add(identity)
            if (
                not re.fullmatch(r"[a-f0-9]{40}", source.rsplit("#", 1)[-1])
                or git_proof.get(identity) != source.rsplit("#", 1)[-1]
                or configuration[source.split("#", 1)[0]]["replace-with"] != "vendored-sources"
            ):
                raise ValueError("Git source provenance differs from locked commit")
        elif not source.startswith("registry+"):
            raise ValueError("Unsupported dependency source")
        prefix = f"vendor-sources/{package['name']}-{package['version']}/"
        checksum_path = prefix + ".cargo-checksum.json"
        checksums = json.loads(entries[checksum_path]["data"])
        if checksums["package"] != package.get("checksum"):
            raise ValueError("Cargo registry checksum differs from lockfile")
        required.add(checksum_path)
        for name, expected in checksums["files"].items():
            path = prefix + name
            if ".." in PurePosixPath(name).parts or name.startswith("/") or "\\" in name:
                raise ValueError("Unsafe Cargo source path")
            if entries[path]["sha256"] != expected:
                raise ValueError("Cargo source file checksum mismatch")
            required.add(path)
        count += 1
    if not count or set(entries) != required or set(git_proof) != expected_git:
        raise ValueError("Cargo dependency source set incomplete or contains unexpected files")
    return count


def check_descriptor(package, entries):
    files = package["files"]
    descriptors = [f for f in files if f["name"].endswith(".dsc")]
    if len(descriptors) != 1 or len({f["name"] for f in files}) != len(files):
        raise ValueError("Exactly one source descriptor and unique files required")
    payload = entries["files/" + descriptors[0]["name"]]["data"].decode()
    if payload.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
        payload = payload.split("\n\n", 1)[1].split("-----BEGIN PGP SIGNATURE-----", 1)[0]
    fields = Parser().parsestr(payload)
    if fields.get("Source") != package["package"] or fields.get("Version") != package["version"]:
        raise ValueError("Source descriptor has a different package/version")
    referenced = {}
    for line in fields.get("Checksums-Sha256", "").splitlines():
        if line.strip():
            sha, size, name = line.split()
            if name in referenced:
                raise ValueError("Duplicate source descriptor reference")
            referenced[name] = (sha, int(size))
    provided = {
        f["name"]: (f["sha256"], f["size"]) for f in files if not f["name"].endswith(".dsc")
    }
    if not referenced or referenced != provided:
        raise ValueError("Source archives referenced by descriptor are missing or different")


def check(directory, revision, lock):
    source_versions = runpy.run_path(str(Path(__file__).with_name("collect-debian-sources.py")))[
        "source_versions"
    ]
    with tarfile.open(directory / "dependency-licenses.tar.xz") as archive:
        manifest = archive.extractfile("dependency-licenses/packages-and-sources.tsv").read()
    binaries = {
        (line.split("\t")[0].split(":")[0], line.split("\t")[1])
        for line in manifest.decode().splitlines()
    }
    image_packages = {
        (line.split("\t")[0], line.split("\t")[1])
        for line in (directory / "package-manifest.tsv").read_text().splitlines()
    }
    if binaries != image_packages:
        raise ValueError("Distro source inventory differs from installed image packages")
    source_archive = runpy.run_path(str(Path(__file__).with_name("release-assets.py")))[
        "source_archive"
    ]
    with source_archive(directory) as source:
        entries = inventory(source, "opt/rampi-corresponding-sources")
    if entries["packages-and-sources.tsv"]["data"] != manifest:
        raise ValueError("Distro source archive uses a different package manifest")
    proof = json.loads(entries["source-archives.json"]["data"])
    if proof != json.loads((directory / "debian-source-archives.json").read_text()):
        raise ValueError("External distro source manifest differs from archive")
    packages = [(item["package"], item["version"]) for item in proof["sources"]]
    if (
        proof.get("schema") != 1
        or len(packages) != len(set(packages))
        or set(packages) != set(source_versions(manifest.decode()))
    ):
        raise ValueError("Exact installed source package coverage missing")
    required = {"packages-and-sources.tsv", "source-archives.json"}
    for package in proof["sources"]:
        check_descriptor(package, entries)
        for item in package["files"]:
            path = "files/" + item["name"]
            if entries[path]["size"] != item["size"] or entries[path]["sha256"] != item["sha256"]:
                raise ValueError("Distro source archive checksum mismatch")
            required.add(path)
    if set(entries) != required:
        raise ValueError("Unexpected distro source archive content")
    rust = check_rust(
        inventory(directory / "rust-dependency-sources.tar.xz", "rust-corresponding-sources"),
        lock,
        revision,
    )
    print(f"PASS: exact sources for {len(packages)} distro packages and {rust} Cargo dependencies.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--lockfile", type=Path, required=True)
    options = parser.parse_args()
    check(options.directory, options.revision, options.lockfile.read_bytes())
