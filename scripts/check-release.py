"""Require documented software acceptance before the fresh release checks."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--configuration-only", action="store_true")
args = parser.parse_args()
readiness = json.loads((ROOT / "packaging/readiness.json").read_text())
if readiness["schema"] != 1 or len(readiness["evidence"]) < 10:
    raise SystemExit("Invalid readiness schema")
if json.loads((ROOT / "release-please-config.json").read_text())["draft"] is not True:
    raise SystemExit("Releases must initially be drafts")
if not args.configuration_only:
    failures = [
        name
        for name, evidence in readiness["evidence"].items()
        if not isinstance(evidence, str) or not (ROOT / evidence).is_file()
    ]
    if not readiness["regular_release"] or failures:
        raise SystemExit("Release withheld. Missing evidence: " + ", ".join(failures))
print("Release configuration valid.")
