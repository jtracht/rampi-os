"""Export verified, unmodified native screenshots; never synthesize UI pictures."""

import argparse
import datetime
import hashlib
import json
import re
import runpy
import shutil
from pathlib import Path

from PIL import Image

CAPTURES = [
    ("einrichtung", "rust-first-run.png", "Einrichtung – zwölf geführte Schritte"),
    ("dashboard", "accessibility-de-dashboard.png", "Dashboard – drei Hauptmodule"),
    ("dashboard-1920", "interaction-dashboard-1920.png", "Dashboard bei 1920 × 1080"),
    ("einstellungen", "accessibility-de-categories.png", "Eine Seite je Kategorie"),
    ("hostprofil", "accessibility-de-host.png", "Persönliches synthetisches Hostprofil"),
    ("wlan", "interaction-settings-wifi.png", "WLAN – native Schalter und integrierte Suche"),
    ("bluetooth", "interaction-settings-bluetooth.png", "Bluetooth – Adapter und native Schalter"),
    ("schalter-ein", "accessibility-de-switches-on.png", "Eingeschaltete Schiebeschalter"),
    ("schalter-aus", "accessibility-de-switches-off.png", "Ausgeschaltete Schiebeschalter"),
    ("rueckmeldung", "accessibility-de-feedback-saved.png", "Sichtbare Erfolgsrückmeldung"),
    ("dashboard-en", "accessibility-en-dashboard.png", "Englische Oberfläche"),
]


def export(captures, output, expected_binary, *, rdp=None, revision=None):
    if not re.fullmatch(r"[0-9a-f]{64}", expected_binary):
        raise ValueError("Actual ELF checksum required")
    if revision is not None and not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid declared source revision")
    if output.exists() or Path(str(output) + ".zip").exists():
        raise FileExistsError("Use a new empty export destination; existing work is preserved")
    scripts = Path(__file__).resolve().parent
    for checker in ["check-accessibility-evidence.py", "check-switch-evidence.py",
                    "check-animation-evidence.py"]:
        runpy.run_path(str(scripts / checker))["check"](captures, expected_binary)
    sources = [(name + ".png", captures / source, caption) for name, source, caption in CAPTURES]
    if rdp is not None:
        proof = json.loads((rdp / "rdp-input.json").read_text(encoding="utf-8"))
        if proof.get("native_elf_sha256") != expected_binary:
            raise ValueError("RDP screenshot came from another or unrecorded executable")
        sources.append(("rdp.png", rdp / "rust-rdp.png",
                        "Echter RDP-Client mit Linux-XRDP-Testserver"))
    records = []
    # Validate every source before creating output; a failed capture cannot
    # quietly produce a partial documentation gallery.
    for name, source, caption in sources:
        if source.is_symlink():
            raise ValueError("Screenshot source must be an actual captured file")
        with Image.open(source) as image:
            if image.format != "PNG" or min(image.size) < 200:
                raise ValueError("Actual full-size PNG screenshot required")
            width, height = image.size
            image.verify()
        records.append({"file": "images/" + name, "caption": caption,
                        "width": width, "height": height,
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    (output / "images").mkdir(parents=True)
    for record, (_, source, _) in zip(records, sources, strict=True):
        destination = output / record["file"]
        shutil.copyfile(source, destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("Screenshot bytes changed during export")
    manifest = {"schema": 1, "capture_kind": "actual native GTK/Wayland local component run",
                "exported_utc": datetime.datetime.now(datetime.UTC).isoformat(),
                "declared_source_revision": revision, "native_elf_sha256": expected_binary,
                "images_modified": False, "release_image_capture": False,
                "complete_product_acceptance": False, "screenshots": records}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)
                                         + "\n", encoding="utf-8")
    text = ("# Screenshots der nativen Entwicklungsoberfläche\n\n"
            "Echte, unveränderte GTK-/Wayland-Aufnahmen; keine Mockups.\n"
            "Die Profile und Server sind synthetische Testdaten, keine Standardzugänge.\n"
            "Funkadapter können in dieser isolierten Umgebung fehlen. Ein vorhandenes\n"
            "RDP-Bild zeigt einen Linux-XRDP-Testserver, keinen persönlichen Windows-PC.\n"
            "Diese Bilder sind keine Image- oder Raspberry-Pi-Hardwareabnahme.\n\n")
    for record in records:
        text += f"## {record['caption']}\n\n![{record['caption']}]({record['file']})\n\n"
    text += "[Herkunft und SHA-256-Prüfsummen](manifest.json)\n"
    (output / "README.md").write_text(text, encoding="utf-8")
    shutil.make_archive(str(output), "zip", root_dir=output)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--rdp", type=Path)
    parser.add_argument("--revision")
    args = parser.parse_args()
    result = export(args.captures, args.output, args.expected_binary,
                    rdp=args.rdp, revision=args.revision)
    print(f"Verified export: {len(result['screenshots'])} unchanged native screenshots")
