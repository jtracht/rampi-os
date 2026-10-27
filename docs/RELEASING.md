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
`packaging/readiness.json` eintragen. Cargo-, Python-/Client- und Manifest-Version
müssen dieselbe stabile MAJOR.MINOR.PATCH-Version tragen. Der aktuelle reguläre
Workflow erstellt keine Versions-PRs. Die Freigabe des Nutzers zur Veröffentlichung
liegt seit dem 27.10.2026 vor; sie ersetzt keine noch fehlende Softwareabnahme.

Der Imagejob baut genau den geprüften Commit frisch und prüft das tatsächliche
installierte Image mit Erstkonto, PAM, persönlichen Schlüsselbünden, normalem
Neustart und unveränderten Programmdateien. Erst danach stellt der gemeinsame
native Artefaktprüfer Image, ARM64-Paket, Windows-Setup-ZIP, beide Setupskripte,
vollständige Rampi-/Distributions-/Cargo-Quellen, Lizenzen und SHA256SUMS zusammen.
Die öffentliche grafische Belegsammlung enthält ausschließlich die ausdrücklich
erlaubten Dateien, keine temporären Kennwörter oder persönlichen Schlüsselbünde.

Unmittelbar vor Veröffentlichung müssen `main` und die akzeptierte Revision
weiterhin identisch und das neue Tag noch unbenutzt sein. Erst dann wird das
vMAJOR.MINOR.PATCH-Tag erzeugt und ein Draft mit allen geprüften Dateien angelegt.
Nach erfolgreichem Upload wird dieser Draft veröffentlicht. Es gibt keinen
`--clobber`-Pfad. Das GitHub-Environment `release` kann zusätzlich geschützt sein.

Ein fehlgeschlagener Imagebau erzeugt kein Tag. Scheitert ein späterer Upload,
werden Tag oder vorhandene Dateien nicht überschrieben. Vor Wiederaufnahme
Quellrevision, Tag, Draft und vollständige Artefaktversionen abgleichen.
Installierte Endgeräte erhalten keine automatischen Updates.
Die Softwareabnahme vom 20.10.2026 gehört zum historischen Python-/QML-Prototyp
und ersetzt keine Rust-Abnahme. Native Pakete verwenden die Workspace-Version
aus Cargo.toml. `regular_release` bleibt bis zu allen erforderlichen Produkt-
und Release-Nachweisen false.

Nach Veröffentlichung in einem sauberen Checkout der akzeptierten Quellrevision
und mit einem neuen leeren Downloadverzeichnis prüfen:

```sh
python3 scripts/verify-published-native-release.py \
  --tag vMAJOR.MINOR.PATCH --revision ACCEPTED_FULL_COMMIT \
  --destination /absolute/path/to/new-empty-release-download
```

Der Prüfer kontrolliert die wirklichen GitHub-Dateien, Tagrevision, Stabilitätsstatus,
Dateigrößen, vorhandene GitHub-SHA256-Digests, jede ausgelieferte Prüfsumme sowie
Image-, Programm-, Quellen- und grafische Anmeldenachweise. Nur sein erfolgreicher
Bericht bestätigt die unabhängig geprüfte öffentliche Veröffentlichung. Ein
Workflow-Erfolg allein ersetzt diese Download-Prüfung nicht.
