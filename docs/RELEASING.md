# Releases

Conventional Commits auf Feature-Branches, Pull Requests nach main.
Reguläre Releases sind gesperrt, solange `regular_release` false ist oder
Software-/Funktionsnachweise fehlen. Physische Hardwaretests sind ausgenommen.
Die Sperre nicht allein zur Veröffentlichung
eines erfolgreichen Builds entfernen.

Die Freigabe benötigt zusätzlich erfolgreiche **CI**- und **Rust and Wayland**-
Push-Läufe für exakt denselben `main`-Commit. Beide Workflow-Abschlüsse können
die Freigabeprüfung auslösen; ein zuerst fertig gewordener Lauf reicht nicht aus.
`scripts/check-release-ci.py` liest die tatsächlichen GitHub-Läufe und Jobs.
PR-/Fork-Läufe, fremde Revisionen, fehlende Architekturen, übersprungene Jobs und
ein älterer Erfolg bei neuerem fehlgeschlagenem Lauf geben keinen Release frei.
Während ein Lauf noch arbeitet oder GitHub-Nachweise nicht erreichbar sind,
bleibt die Veröffentlichung gesperrt.

Vor dem Veröffentlichen wird diese Abfrage erneut für den Release-Commit
ausgeführt. `release-ci.json` hält Repository, Revision, Workflow-/Job-IDs und
Ergebnisse fest, wird mit ausgeliefert und ist Teil von SHA256SUMS. Der
Artefaktprüfer verlangt beide Workflow-Nachweise für dieselbe Quellrevision wie
Quellarchiv und ARM64-Paket. Der frische Image-/QEMU-Job bleibt zusätzlich Pflicht.
[Prüfung des nativen CI-Gates](validation/native-release-ci-gate-2026-10-23.md).

Nach Abschluss der vereinbarten Softwareabnahme konkrete Nachweisdateien in
`packaging/readiness.json` eintragen. Release Please erstellt einen Versions-PR,
aktualisiert Changelog/Version und erzeugt nach Merge ein vMAJOR.MINOR.PATCH-Tag
mit einem zunächst unveröffentlichten Draft.
Die Option `force-tag-creation` setzt das Tag bereits beim Anlegen des Drafts,
damit weitere Versions-PRs während des Imagebuilds den richtigen Ausgangspunkt haben.
Der Imagejob und die Paketierung müssen vollständig erfolgreich sein. Erst dann lädt der Publishjob Quellpaket,
Windows-Host-ZIP, setup.sh, setup.ps1, Lizenzinformationen, Image und SHA256SUMS
hoch und veröffentlicht den Draft. Das GitHub-Environment `release` kann im
Repository zusätzlich mit menschlicher Freigabe geschützt werden.

Ein fehlgeschlagener Build lässt den Draft unveröffentlicht. Es wird kein
zweites Versions-Tag erfunden. Vor Wiederholung Tag, Commit und Artefaktversionen
abgleichen. Installierte Endgeräte erhalten keine automatischen Updates.
Die Softwareabnahme vom 20.10.2026 gehört zum historischen Python-/QML-Prototyp
und ersetzt keine Rust-Abnahme. Native Pakete verwenden die Workspace-Version
aus Cargo.toml. Die bestehende Release-Please-Versionspflege und der ältere
Versionsprüfer verwenden noch Python-/Client-/Manifest-Versionen; diese Migration
muss vor einem regulären nativen Release abgeschlossen werden. `regular_release`
bleibt bis zu allen erforderlichen Produkt- und Release-Nachweisen false.
