from pathlib import Path

root = Path(__file__).resolve().parents[1]
for filename in ["LICENSE", "NOTICE", "docs/LICENSES.md", "assets/references/RIGHTS.md"]:
    if not (root / filename).is_file():
        raise SystemExit(f"Required license documentation missing: {filename}")
if "Apache License" not in (root / "LICENSE").read_text():
    raise SystemExit("Apache license missing")
print("License and provenance documentation present; see LICENSES.md for component obligations.")
