"""Require documented software acceptance before the fresh release checks."""

import argparse
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
versions = {
    "project": tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"],
    "client": re.search(
        r'__version__ = "([^"]+)"', (ROOT / "client/rampi/__init__.py").read_text()
    ).group(1),
    "manifest": json.loads((ROOT / ".release-please-manifest.json").read_text())["."],
}
if len(set(versions.values())) != 1:
    raise SystemExit(f"Release version mismatch: {versions}")
parser = argparse.ArgumentParser()
parser.add_argument("--configuration-only", action="store_true")
args = parser.parse_args()
readiness = json.loads((ROOT / "packaging/readiness.json").read_text())
if readiness["schema"] != 1 or len(readiness["evidence"]) < 10:
    raise SystemExit("Invalid readiness schema")
if json.loads((ROOT / "release-please-config.json").read_text())["draft"] is not True:
    raise SystemExit("Releases must initially be drafts")
if not args.configuration_only:
    native_version = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))[
        "workspace"
    ]["package"]["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", native_version) or native_version != versions[
        "manifest"
    ]:
        raise SystemExit("Release version mismatch: native Rust version must match the stable tag")
    failures = [
        name
        for name, evidence in readiness["evidence"].items()
        if not isinstance(evidence, str) or not (ROOT / evidence).is_file()
    ]
    if not readiness["regular_release"] or failures:
        raise SystemExit("Release withheld. Missing evidence: " + ", ".join(failures))
print("Release configuration valid.")
