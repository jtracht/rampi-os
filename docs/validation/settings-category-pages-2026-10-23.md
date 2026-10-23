# Einstellungen als Kategorien und einzelne Seiten

Der Gesamtfortschritt bleibt bei **75 %**. Die Tab-Leiste ist durch eine
vertikale Kategorieübersicht ersetzt. Jede Kategorie öffnet ihren eigenen
Seiteninhalt. Zurück/Escape führt zur Übersicht mit wiederhergestelltem Fokus,
anschließend zum Dashboard. Aus der Einrichtung geht es direkt zum aktuellen
Schritt zurück. Direkte Dashboardverknüpfungen bleiben erhalten.

## Lokale Softwareprüfung

- `artifacts/rust-settings-pages`: vollständige native Docker-/Wayland-Abnahme,
  alle erforderlichen Nachweise erfolgreich; zusätzlich fordert der Prüfer nun
  die tatsächliche Aufnahme der Kategorieübersicht.
- Snapshot-SHA256 des Gesamtlaufs:
  `d29bac306c89699f0579b46afc099b49b63a407c6ec26674fa0cdfd22dba34bc`.
  Der Lauf erfasste einen veränderten Arbeitsstand auf Basis von `e992601`.
- 19 Rust-Core-Tests, Format und Clippy ohne Warnungen.
- Tatsächliche Wayland-Eingaben öffnen alle sechs Kategorien und prüfen
  Enter, Escape, Pfeilnavigation, Hostformular und ein einziges Anwendungsfenster.
- Nach der Gesamtabnahme wurden die Rückweg-Beschriftung beim erneuten Öffnen
  und die Prüfung des Pfeiltasten-Umlaufs ergänzt. Dieser finale Stand wurde
  erneut kompiliert, mit Clippy geprüft und im gezielten Wayland-Eingabetest
  ausgeführt (`artifacts/settings-pages/interaction.log`).
- Bestehende Dienst-, TLS-/Schlüsselbund-, PAM-, Browser-, Terminal-, Klang-
  und Animationsprüfungen bleiben Bestandteil des Gesamtlaufs.

600 Modulwechsel im isolierten AMD64-Container; gemessener Prozess-Spitzenwert
212,1 MiB, gesamter Laufzeit-Cgroup-Spitzenwert 479,8 MiB bei einer Grenze von
1 GiB ohne Swap. Diese Messung ist kein Raspberry-Pi-GPU- oder Hardwaretest.
Physische Hardwaretests bleiben gemäß Nutzerauftrag ausgeschlossen.

Die Aufnahmen in `docs/screenshots/settings-categories.png` und
`docs/screenshots/gitea-guided-settings.png` stammen aus der tatsächlichen
Rust-Anwendung unter Wayland; Dienstverfügbarkeit und Gitea-Quelle sind die der
isolierten Aufnahmeumgebung, keine behauptete persönliche Live-Verbindung.
