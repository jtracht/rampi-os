# Entwicklungsfortschritt

Aktueller Entwicklungsstand: **ca. 72 %**. Baseline v0.3.0: ca. 69 %.

Die Zahl bewertet den gesamten Masterprompt, einschließlich Integration,
Bedienung und Nachweisen. Sie ist eine transparente Planungsschätzung, keine
Messung der verbleibenden Arbeitszeit und keine Aussage, dass ein erfolgreich
veröffentlichter Entwicklungsstand schon sämtliche Anforderungen erfüllt.
Physische Hardwaretests sind auf Nutzerwunsch ausgeschlossen und gehören nicht
zum Nenner. Windows- und Anbieterprüfungen werden dadurch nicht automatisch erfüllt.

20 Bereiche erhalten jeweils bis zu fünf Punkte: 0 = fehlt, 1 = Grundlage,
2 = teilweise implementiert, 3 = wesentliche Funktionen vorhanden, 4 = weitgehend
umgesetzt und softwaregeprüft, 5 = vollständiger vereinbarter Umfang einschließlich
Nachweisen und Dokumentation. Die Summe ergibt den geschätzten Prozentwert.
Punkte steigen durch belegte Funktionen und Prüfungen, nicht durch
Wartezeit, Commits, Testanzahl oder bloßen Release-Erfolg.

| Bereich | Baseline / 5 | Wesentliche verbleibende Arbeit |
|---|---:|---|
| Grafische Sitzung und Dashboard | 4 | Gesamtabnahme aller Module und Offline-Wechsel |
| Tastatur und Maus | 4 | Durchgängige Eingabeprüfung auch in echten Remote-Clients |
| Setup-Assistent | 3 | Einheitliche eigene Einrichtung statt mehrerer Systemdialoge |
| Linux-Konten und Login | 4 | Vollständige grafische Anmelde-/Abmeldeabnahme |
| WLAN | 2 | Eigene Netzwerkauswahl, sichere Kennworteingabe und Dienstprüfung |
| Bluetooth | 2 | Eigene Pairing-Oberfläche und softwareseitige BlueZ-Abnahme |
| VPN | 3 | Grafische persönliche Profilauswahl und Tailscale-Abnahme |
| Windows-Host und Persistenz | 4 | Zusammenhängende Windows-11-Pro-Abnahme |
| Anbieter-CLIs | 3 | Persönliche Anmeldungen, native Anbieterabläufe und Antigravity-Einrichtung |
| Remote Desktop und Streaming | 3 | Streaming-Audio/-Eingabe sowie Windows-NLA/-Aufnahme prüfen |
| Kanban | 3 | Grafische Spaltenkonfiguration, getrennte Filter, echte Anbieterabnahmen |
| Browser | 4 | Moderne Seiten, Downloads und Ressourcenbedarf im Gesamtsystem prüfen |
| Installer und Reparatur | 4 | Weitere Wiederholungs-, Fehler- und Reparaturpfade abnehmen |
| Sicherheit und Isolation | 4 | Abschließende Prüfung über die kombinierten Benutzerabläufe |
| Design und Branding | 4 | Gesamtabgleich aller Ansichten und technischen Logo-Varianten |
| GitHub und CI/CD | 5 | Automatische Prüfungen, Tags und vollständige Releases nachgewiesen |
| Systemimage | 4 | Paketquellen für reproduzierbare Builds festhalten |
| Manuelle Updates | 5 | Versionierte manuelle Installer; keine Geräte-Autoupdates |
| Dokumentation | 3 | Einstellungen, Abläufe und Nachweise vollständig fortschreiben |
| Performance | 1 | Längere Gesamtlast unter 1 GB, CPU-/Start-/Wechsel-/Animationsmessungen |
| **Summe** | **69 / 100** | **Baseline: ca. 69 %** |

Quellen: [vollständige Anforderungen](REQUIREMENTS.de.md),
[Implementierungsstand](STATUS.md), [Tests und Grenzen](TESTING.md),
[vereinbarter Abnahmeumfang](VALIDATION-SCOPE.md).

Belegte Erweiterungen gegenüber der Baseline:

| Bereich | Neuer Punktestand | Nachweis |
|---|---:|---|
| VPN | 4 / 5 | Eigene grafische Auswahl; echte libnm-Metadaten mit aktivem Zustand; gemeinsame/fremde Profile ausgeschlossen; UID statt Umgebungsvariablen bestimmt das Systemkonto |
| Remote Desktop und Streaming | 4 / 5 | Echter 997-Hz-Testton über Sunshine/PulseAudio, Opus und Moonlight/SDL empfangen; erneute Verbindung; Stille und falscher Ton werden abgewiesen |
| Kanban | 4 / 5 | Spaltenreihenfolge gespeichert; unabhängige Projekt-/Prioritäts-/Statusfilter mit Suche; tatsächliche QML-Tastaturtests und JSON-Neuladen |

Damit **72 / 100 Punkte**, entsprechend **ca. 72 %**. Lokale Prüfungen sind bestanden;
die Änderungen durchlaufen zusätzlich die vollständige CI und einen frischen
Release-Image-Build. Die verbleibenden Punkte in der Baseline bleiben offen.
