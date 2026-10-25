"""Lossless release transport for full source archives above GitHub's file limit."""

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

LIMIT = 2 * 1024**3  # Every uploaded file must be strictly smaller than 2 GiB.
PART_BYTES = 1024**3
SOURCE = "dependency-sources.tar.xz"
INDEX = "dependency-sources.parts.json"


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular source asset: " + path.name)
    return path


def digest(path):
    with regular(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def parts(directory):
    index_path = regular(directory / INDEX)
    if index_path.stat().st_size > 1024 * 1024:
        raise ValueError("Source parts index is too large")
    index = json.loads(index_path.read_text())
    if (
        not isinstance(index, dict)
        or set(index) != {"schema", "name", "size", "sha256", "parts"}
        or type(index["schema"]) is not int
        or index["schema"] != 1
        or index["name"] != SOURCE
        or type(index["size"]) is not int
        or index["size"] <= 0
        or not isinstance(index["sha256"], str)
        or not re.fullmatch(r"[a-f0-9]{64}", index["sha256"])
        or not isinstance(index["parts"], list)
        or not 1 <= len(index["parts"]) <= 999
    ):
        raise ValueError("Invalid source parts index")
    total = 0
    for number, item in enumerate(index["parts"], 1):
        if (
            not isinstance(item, dict)
            or set(item) != {"name", "size", "sha256"}
            or item["name"] != f"{SOURCE}.part{number:03d}"
            or type(item["size"]) is not int
            or not 0 < item["size"] < LIMIT
            or not isinstance(item["sha256"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"])
        ):
            raise ValueError("Unsafe, reordered or invalid source part")
        if regular(directory / item["name"]).stat().st_size != item["size"]:
            raise ValueError("Source part size mismatch")
        total += item["size"]
    if total != index["size"]:
        raise ValueError("Source part totals differ from original archive")
    if {p.name for p in directory.glob(SOURCE + ".part*")} != {
        item["name"] for item in index["parts"]
    }:
        raise ValueError("Unexpected or missing source parts")
    return index


def copy_parts(directory, index, output):
    combined = hashlib.sha256()
    for item in index["parts"]:
        sha = hashlib.sha256()
        count = 0
        with regular(directory / item["name"]).open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                count += len(chunk)
                if count > item["size"]:
                    raise ValueError("Source part grew during verification")
                sha.update(chunk)
                combined.update(chunk)
                if output is not None:
                    output.write(chunk)
        if count != item["size"] or sha.hexdigest() != item["sha256"]:
            raise ValueError("Source part checksum mismatch: " + item["name"])
    if combined.hexdigest() != index["sha256"]:
        raise ValueError("Reconstructed original source archive checksum mismatch")


def source_assets(directory):
    if (directory / INDEX).exists():
        if (directory / SOURCE).exists():
            raise ValueError("Ambiguous single and multipart source archive")
        return {INDEX, *(item["name"] for item in parts(directory)["parts"])}
    regular(directory / SOURCE)
    if any(directory.glob(SOURCE + ".part*")):
        raise ValueError("Source part index missing")
    return {SOURCE}


@contextmanager
def source_archive(directory):
    source_assets(directory)
    if not (directory / INDEX).exists():
        yield directory / SOURCE
        return
    index = parts(directory)
    # The temporary tree is explicitly contained in the artifact's parent.
    parent = directory.resolve().parent
    with tempfile.TemporaryDirectory(prefix="rampi-release-source-", dir=parent) as temporary:
        temporary = Path(temporary).resolve()
        temporary.relative_to(parent)
        restored = temporary / SOURCE
        with restored.open("xb") as stream:
            copy_parts(directory, index, stream)
        yield restored


def split_sources(directory, *, threshold=LIMIT, part_bytes=PART_BYTES):
    if not 0 < part_bytes < threshold <= LIMIT:
        raise ValueError("Invalid source transport limits")
    source = regular(directory / SOURCE)
    if source.stat().st_size < threshold:
        return False
    if (directory / INDEX).exists() or any(directory.glob(SOURCE + ".part*")):
        raise ValueError("Refusing to overwrite existing source parts")
    created = []
    entries = []
    combined = hashlib.sha256()
    total = 0
    try:
        with source.open("rb") as original:
            while True:
                first = original.read(min(1024 * 1024, part_bytes))
                if not first:
                    break
                if len(entries) == 999:
                    raise ValueError("Too many source parts")
                path = directory / f"{SOURCE}.part{len(entries) + 1:03d}"
                sha = hashlib.sha256()
                count = 0
                with path.open("xb") as stream:
                    created.append(path)
                    chunk = first
                    while chunk:
                        stream.write(chunk)
                        sha.update(chunk)
                        combined.update(chunk)
                        count += len(chunk)
                        if count == part_bytes:
                            break
                        chunk = original.read(min(1024 * 1024, part_bytes - count))
                total += count
                entries.append({"name": path.name, "size": count, "sha256": sha.hexdigest()})
        if total != source.stat().st_size:
            raise ValueError("Original source archive changed during splitting")
        index = {
            "schema": 1,
            "name": SOURCE,
            "size": total,
            "sha256": combined.hexdigest(),
            "parts": entries,
        }
        # Reread the bytes actually written before removing the original file.
        copy_parts(directory, index, None)
        index_path = directory / INDEX
        with index_path.open("x") as stream:
            created.append(index_path)
            json.dump(index, stream, indent=2)
            stream.write("\n")
        source.unlink()
        return True
    except BaseException:
        if source.exists():
            for path in reversed(created):
                path.unlink(missing_ok=True)
        raise


def check_limits(directory):
    for path in directory.iterdir():
        if regular(path).stat().st_size >= LIMIT:
            raise ValueError("Release file exceeds GitHub's per-file limit: " + path.name)


def restore(directory, output):
    with source_archive(directory) as source:
        # Exclusive creation preserves every existing destination.
        with output.open("xb") as destination, source.open("rb") as stream:
            shutil.copyfileobj(stream, destination, 1024 * 1024)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", type=Path, required=True, metavar="DIRECTORY")
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    restore(options.restore, options.output)
