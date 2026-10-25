"""Use Cargo vendoring and Git revision checks for the release source archive."""

import argparse
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(*arguments, cwd=None):
    return subprocess.run(
        arguments,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=1800,
    ).stdout


def collect(root, output, archive, revision):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Exact release source revision required")
    if archive.exists():
        raise ValueError("Refusing to overwrite a source archive")
    output.mkdir(parents=True, exist_ok=False)
    configuration = command(
        "cargo",
        "vendor",
        "--manifest-path",
        str(root / "Cargo.toml"),
        "--locked",
        "--versioned-dirs",
        "vendor-sources",
        cwd=output,
    )
    (output / "config.toml").write_text(configuration)
    metadata = json.loads(
        command(
            "cargo",
            "metadata",
            "--manifest-path",
            str(root / "Cargo.toml"),
            "--locked",
            "--format-version=1",
        )
    )
    revisions = []
    for package in metadata["packages"]:
        source = package.get("source") or ""
        if not source.startswith("git+"):
            continue
        expected = source.rsplit("#", 1)[-1]
        actual = command(
            "git", "-C", str(Path(package["manifest_path"]).parent), "rev-parse", "HEAD"
        ).strip()
        if not re.fullmatch(r"[a-f0-9]{40}", expected) or actual != expected:
            raise ValueError("Git dependency checkout differs from locked revision")
        revisions.append(
            {
                "name": package["name"],
                "version": package["version"],
                "source": source,
                "commit": actual,
            }
        )
    (output / "git-source-revisions.json").write_text(json.dumps(revisions, indent=2) + "\n")
    shutil.copyfile(root / "Cargo.lock", output / "Cargo.lock")
    (output / "source-revision.txt").write_text(revision + "\n")
    with tarfile.open(archive, "w:xz") as bundle:
        bundle.add(output, arcname="rust-corresponding-sources")
    print(f"Cargo source archive created; {len(revisions)} locked Git packages verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    options = parser.parse_args()
    collect(ROOT, options.output.resolve(), options.archive.resolve(), options.revision)
