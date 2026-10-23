# Bindung der Release-Freigabe an allgemeine und native CI

Gesamtstand weiterhin **75 / 100**; kein neuer regulärer nativer Release.
Die Release-Pipeline benötigte bisher nur den erfolgreichen Workflow `CI`.
Der neue Prüfer verlangt zusätzlich beide Architekturen des nativen Workflows
`Rust and Wayland`, jeweils für denselben Hauptbranch-Push und dieselbe Revision.
Er prüft die tatsächlichen Jobs, akzeptiert keinen älteren grünen Lauf statt
eines neueren unvollständigen/fehlgeschlagenen Laufs und weist unvollständige
API-Ergebnisse ab. Die Veröffentlichung prüft erneut live und liefert eine
quellgebundene `release-ci.json` mit Prüfsumme aus.

## Ausgeführt

- `pytest`: **108 Tests erfolgreich**, einschließlich 21 neuer Release-CI-Fälle.
- Ruff für Skripte und Tests erfolgreich.
- Quellarchiv und Windows-Hostpaket aus einem sauberen, temporären Checkout
  tatsächlich erzeugt; Archivvollständigkeit und alle sechs SHA256-Werte geprüft.
  Das ist keine Image- oder reguläre Release-Abnahme.
- Tatsächliche GitHub-API-Abfrage akzeptiert Revision
  `45dd1996bd86a3e74acd09c7601ee4b69bd3085e`:
  [allgemeine CI](https://github.com/jtracht/rampi-os/actions/runs/39950195755),
  [native AMD64-/ARM64-CI und QEMU-WLAN](https://github.com/jtracht/rampi-os/actions/runs/39950195748).
  Die lokalen JSON-Nachweise liegen in `artifacts/release-ci-45dd199.json`.
- Die tatsächliche Abfrage für `e9926012334d86ec6f8ef42287eec765231c8a31`
  weist trotz erfolgreicher allgemeiner CI die Freigabe ab, weil für diesen
  Dokumentations-Commit keine native Push-Abnahme existiert.
- Explizite API-Fixtures prüfen fremde Revisionen/Repositories/Branches,
  PR-Ereignisse, fehlende oder fehlgeschlagene Jobs, abgebrochene/übersprungene
  Läufe, neuere ausstehende Läufe, unvollständige Seiten und manipulierte
  Offline-Nachweise. Diese Fixtures ersetzen nicht die obigen Live-Abfragen.

## Noch offen

Das Gate ist eine Voraussetzung, kein Beleg eines veröffentlichten Releases.
Native Versionspflege, aktuelle Image-Funktionsgleichheit, grafischer Login und
die übrigen Produktanforderungen bleiben offen. Die bestehende Produktsperre
wird nicht aufgehoben. Physische Hardwaretests bleiben ausgeschlossen.

Schnittstellen:
[GitHub workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run),
[GitHub REST Workflow Runs](https://docs.github.com/en/rest/actions/workflow-runs).
