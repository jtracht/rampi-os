"""Collect the actual license texts from locked Cargo source dependencies."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
compiler = subprocess.check_output(["rustc", "-vV"], text=True)
target_triple = next(
    line.removeprefix("host: ") for line in compiler.splitlines() if line.startswith("host: ")
)
metadata = json.loads(
    subprocess.check_output(
        ["cargo", "metadata", "--locked", "--format-version=1", "--filter-platform", target_triple]
    )
)
workspace = set(metadata["workspace_members"])
resolved = {node["id"] for node in metadata["resolve"]["nodes"]}
packages = []
missing = []
for package in metadata["packages"]:
    if package["id"] in workspace or package["id"] not in resolved:
        continue
    directory = Path(package["manifest_path"]).parent
    texts = {
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.name.lower().startswith(("license", "licence", "copying", "notice", "copyright"))
    }
    if package.get("license_file"):
        texts.add(directory / package["license_file"])
    for folder in ["LICENSES", "licenses"]:
        if (directory / folder).is_dir():
            texts.update(path for path in (directory / folder).rglob("*") if path.is_file())
    if package["name"] in ["webkit6", "webkit6-sys", "javascriptcore6", "javascriptcore6-sys"]:
        texts.add(Path(__file__).resolve().parents[1] / "assets/licenses/rust/webkit6-rs-LICENSE")
    if not texts:
        missing.append(f"{package['name']} {package['version']}")
        continue
    target = output / f"{package['name']}-{package['version']}"
    target.mkdir()
    for index, text in enumerate(sorted(texts)):
        shutil.copyfile(text, target / f"{index:02d}-{text.name}")
    packages.append(
        {
            "name": package["name"],
            "version": package["version"],
            "license": package.get("license"),
            "source": package.get("source"),
            "texts": len(texts),
        }
    )
if missing:
    raise SystemExit("Review dependencies with missing license texts: " + ", ".join(missing))
(output / "packages.json").write_text(json.dumps(packages, indent=2) + "\n", encoding="utf-8")
toolchain = Path(subprocess.check_output(["rustc", "--print", "sysroot"], text=True).strip())
library_notices = toolchain / "share/doc/rust/COPYRIGHT-library.html"
if not library_notices.is_file():
    raise SystemExit("Rust standard-library notices missing from the build toolchain")
shutil.copyfile(library_notices, output / "Rust-standard-library-COPYRIGHT.html")
shutil.copytree(toolchain / "share/doc/rust/licenses", output / "Rust-license-texts")
print(f"Collected original license texts for {len(packages)} locked Cargo dependencies.")
