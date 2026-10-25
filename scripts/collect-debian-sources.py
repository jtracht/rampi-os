"""Fetch exact installed source packages with APT and verify signed-index SHA256s."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from email.parser import Parser
from pathlib import Path


def source_versions(manifest):
    result = set()
    for line in manifest.splitlines():
        binary, binary_version, package, version = line.split("\t")
        if not binary or not binary_version or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", package):
            raise ValueError("Invalid installed source package identity")
        if not re.fullmatch(r"[0-9][0-9A-Za-z.+:~\-]*", version):
            raise ValueError("Invalid installed source version")
        result.add((package, version))
    if not result:
        raise ValueError("Installed package manifest is empty")
    return sorted(result)


def source_stanzas(text):
    result = []
    for stanza in re.split(r"\n\s*\n", text.strip()):
        fields = Parser().parsestr(stanza)
        types = fields.get("Types", "").split()
        if fields.get("Enabled", "yes").strip().lower() == "no":
            continue
        if "deb" in types and "deb-src" not in types:
            result.append(re.sub(r"^Types:[^\n]*", "Types: deb-src", stanza, flags=re.M))
    return "\n\n".join(result)


def index_files(text, package, version):
    matches = []
    for stanza in re.split(r"\n\s*\n", text.strip()):
        fields = Parser().parsestr(stanza)
        if fields.get("Package") != package or fields.get("Version") != version:
            continue
        entries = []
        for line in fields.get("Checksums-Sha256", "").splitlines():
            if not line.strip():
                continue
            sha, size, name = line.split()
            if (
                not re.fullmatch(r"[a-f0-9]{64}", sha)
                or not size.isdigit()
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+~_%\-]*", name)
                or name in {".", ".."}
            ):
                raise ValueError("Unsafe or incomplete signed source index")
            entries.append({"name": name, "sha256": sha, "size": int(size)})
        if not entries or len({e["name"] for e in entries}) != len(entries):
            raise ValueError("Source checksums missing or duplicated")
        if not any(e["name"].endswith(".dsc") for e in entries):
            raise ValueError("Source descriptor missing")
        matches.append(sorted(entries, key=lambda e: e["name"]))
    if not matches or any(item != matches[0] for item in matches):
        raise ValueError("Exact installed source version missing or ambiguous")
    return matches[0]


def command(*args, cwd=None):
    return subprocess.run(
        args, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8", timeout=1800
    ).stdout


def collect(manifest, output, apt_root, enable_sources):
    packages = source_versions(manifest.read_text())
    output.mkdir(parents=True, exist_ok=False)
    files = output / "files"
    files.mkdir()
    own_lists = []
    try:
        if enable_sources:
            directory = apt_root / "sources.list.d"
            directory.mkdir(exist_ok=True)
            deb822 = "\n\n".join(
                source_stanzas(p.read_text()) for p in sorted(directory.glob("*.sources"))
            )
            legacy = []
            for path in [apt_root / "sources.list", *sorted(directory.glob("*.list"))]:
                if path.is_file():
                    legacy.extend(
                        re.sub(r"^(\s*)deb\s", r"\1deb-src ", line)
                        for line in path.read_text().splitlines()
                        if re.match(r"^\s*deb\s", line)
                    )
            for suffix, content in [(".sources", deb822), (".list", "\n".join(legacy))]:
                if content.strip():
                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        delete=False,
                        dir=directory,
                        prefix="rampi-source-archive-",
                        suffix=suffix,
                    ) as handle:
                        own_lists.append(Path(handle.name))
                        handle.write(content + "\n")
                    own_lists[-1].chmod(0o644)
            command("apt-get", "update", "-qq")
        proof = []
        for package, version in packages:
            entries = index_files(
                command("apt-cache", "showsrc", "--only-source", package), package, version
            )
            with tempfile.TemporaryDirectory(prefix="fetch-", dir=output) as work:
                command(
                    "apt-get",
                    "source",
                    "--download-only",
                    "--only-source",
                    "--yes",
                    package + "=" + version,
                    cwd=work,
                )
                if {p.name for p in Path(work).iterdir()} != {e["name"] for e in entries}:
                    raise ValueError("Downloaded source set differs from signed index: " + package)
                for entry in entries:
                    path = Path(work) / entry["name"]
                    if (
                        path.is_symlink()
                        or not path.is_file()
                        or path.stat().st_size != entry["size"]
                    ):
                        raise ValueError("Invalid downloaded source file")
                    with path.open("rb") as stream:
                        actual = hashlib.file_digest(stream, "sha256").hexdigest()
                    if actual != entry["sha256"]:
                        raise ValueError("Downloaded source SHA256 mismatch")
                    target = files / entry["name"]
                    if target.exists():
                        with target.open("rb") as stream:
                            if hashlib.file_digest(stream, "sha256").hexdigest() != actual:
                                raise ValueError("Source filename collision")
                    else:
                        shutil.copyfile(path, target)
            proof.append({"package": package, "version": version, "files": entries})
            print("Verified exact source: " + package + "=" + version, flush=True)
        shutil.copyfile(manifest, output / "packages-and-sources.tsv")
        (output / "source-archives.json").write_text(
            json.dumps({"schema": 1, "sources": proof}, indent=2) + "\n"
        )
    finally:
        for path in own_lists:
            path.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apt-root", type=Path, default=Path("/etc/apt"))
    parser.add_argument("--enable-sources", action="store_true")
    args = parser.parse_args()
    collect(args.manifest, args.output, args.apt_root, args.enable_sources)
