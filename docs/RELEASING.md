# Releases

Conventional Commits auf Feature-Branches, Pull Requests nach main.
Reguläre Releases sind gesperrt, solange `regular_release` false ist oder
Software-/Funktionsnachweise fehlen. Physische Hardwaretests sind ausgenommen.
Die Sperre nicht allein zur Veröffentlichung
eines erfolgreichen Builds entfernen.

Nach Abschluss der vereinbarten Softwareabnahme konkrete Nachweisdateien in
`packaging/readiness.json` eintragen. Release Please erstellt einen Versions-PR,
aktualisiert Changelog/Version und erzeugt nach Merge ein vMAJOR.MINOR.PATCH-Tag
mit einem zunächst unveröffentlichten Draft. Der Imagejob und die Paketierung
müssen vollständig erfolgreich sein. Erst dann lädt der Publishjob Quellpaket,
Windows-Host-ZIP, setup.sh, setup.ps1, Lizenzinformationen, Image und SHA256SUMS
hoch und veröffentlicht den Draft. Das GitHub-Environment `release` kann im
Repository zusätzlich mit menschlicher Freigabe geschützt werden.

Ein fehlgeschlagener Build lässt den Draft unveröffentlicht. Es wird kein
zweites Versions-Tag erfunden. Vor Wiederholung Tag, Commit und Artefaktversionen
abgleichen. Installierte Endgeräte erhalten keine automatischen Updates.
Die Softwareabnahme vom 20.10.2026 ist dokumentiert und in readiness.json
eingetragen. Jeder neue Release muss seinen eigenen Image-/QML-/QEMU- und
vollständigen Artefakttest bestehen. Der Versionsstand steht in pyproject.toml.
Die CI weist Abweichungen zwischen Paketversion, Clientversion und
Release-Manifest zurück. Der zusätzliche Client-Versionsmarker wird als
expliziter Generic-Updater mit reinen SemVer-Versionen gepflegt.
