# Entwicklungsfortschritt

Der Produktumfang wurde am 26.10.2026 ausdrücklich verkleinert: Codex, Claude
Code und Gemini/Antigravity samt direkter CLI- und Sitzungsintegration entfallen.
Es bleiben drei Hauptmodule: Kanban, Remote Desktop und Browser.

Die bisher abgenommenen **81/100** sind deshalb nicht direkt mit dem neuen
Prozentwert vergleichbar. Nach Abzug der früheren drei Anbieter-CLI-Punkte
beträgt die vergleichbare Basis **78/95 = 82,1 %**. Die entfernten fünf möglichen
Punkte werden nicht auf andere Bereiche verteilt.

Der belegte Stand beträgt jetzt **91/95 = 95,8 %**.
Das veröffentlichte [v0.6.0-dev.4](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.4)
besteht die endgültige native Abnahme beider Architekturen, den frischen Imagebau,
beide Erstkonto-Verfahren mit normalen Neustarts und die unabhängige Kontrolle
der wirklich veröffentlichten Dateien. Die fünf zusätzlichen Softwareabschlüsse
sind einzeln [begründet und zugeordnet](validation/native-dev4-software-acceptance.md).

| Bereich | Basis / 5 | Aktuell abgenommen / 5 |
|---|---:|---:|
| Grafische Sitzung und Dashboard | 4 | 5 |
| Tastatur und Maus | 4 | 4 |
| Setup-Assistent | 4 | 5 |
| Linux-Konten und Login | 4 | 5 |
| WLAN | 5 | 5 |
| Bluetooth | 4 | 4 |
| VPN | 4 | 5 |
| Windows-Host | 4 | 4 |
| Remote Desktop und Streaming | 3 | 5 |
| Kanban | 4 | 5 |
| Browser | 5 | 5 |
| Installer und Reparatur | 4 | 5 |
| Sicherheit und Isolation | 4 | 5 |
| Design und Branding | 4 | 4 |
| GitHub und CI/CD | 4 | 5 |
| Systemimage | 4 | 5 |
| Manuelle Updates | 5 | 5 |
| Dokumentation | 4 | 5 |
| Performance | 4 | 5 |
| **Summe** | **78 / 95** | **91 / 95** |

Die Bewertungsstufen bleiben unverändert: 0 fehlt, 1 Grundlage, 2 teilweise,
3 wesentliche Funktionen, 4 weitgehend umgesetzt und softwaregeprüft,
5 vollständiger vereinbarter Umfang des jeweiligen Bereichs samt Nachweisen.
Testanzahl, Wartezeit und gelöschte Funktionen ergeben keine Punkte.

Dashboard erhält den zusätzlichen Punkt nur für die tatsächlichen Hin- und
Rückwege aller drei verbleibenden eingebetteten Module ohne Netzwerkzugang.
Es bleibt genau ein Fenster; RDP, Kanban/Gitea und Browser behalten ihre echten
Protokoll- und Profilabnahmen. Installer/Reparatur ergänzt die inzwischen
vorhandene native Bootstrap-/Rückwechselabnahme um die tatsächlichen PAM- und
Erhaltungsprüfungen für zwei Konten und vorhandene angepasste Dienste.
GitHub/CI/CD ergänzt den erfolgreich veröffentlichten nativen Entwicklungsrelease
mit frischem Image und vollständig unabhängig geprüften öffentlichen Downloads.
Die genauen Grenzen und Artefaktzuordnungen stehen im verlinkten Nachweis.

Das dev4-Release bleibt ausdrücklich eine Vorabversion. Der ältere Imagefehler
ist bereits in dev3 behoben; beide Veröffentlichungen bleiben unverändert.
Es gibt kein Standardpasswort. Die kalte persönliche Sprache und ihre erneute
PAM-Anmeldung sind nun zusätzlich an die endgültige dev4-Quelle gebunden.

Das zusätzliche [dev5-Release](validation/native-dev5-keyboard-release.md)
korrigiert die persönliche Tastatur-Dateiauswertung und besteht erneut vollständige
Quell-/Image-/Downloadprüfungen. Der einzelne Randfall erhöht den Punktestand nicht.
Der Nutzer hat die Weiterarbeit bis 100 % und Windows-Komponentenprüfungen in
isolierter GitHub-CI ausdrücklich beauftragt. Persönliche Rechner und externe
Windows-Testhosts bleiben ausgeschlossen. Weitere Punkte benötigen neue Nachweise.

## Verbleibende Arbeit

Tastatur-/Layout-Randfälle, durchgängige Bluetooth-HID-/Remote-Eingabe,
tatsächliche Windows-Host-Randfälle und Fokus-/Bedienungsfeinschliff behalten
jeweils 4/5. Das vollständige 100-Prozent-Ziel ist nicht abgeschlossen.
`regular_release` bleibt `false`. Hardwaretests, persönliche Rechner, externe
Windows-Testhosts und Modellanfragen bleiben ausgeschlossen. Isolierte
Windows-Komponentenprüfungen in GitHub-CI sind ausdrücklich beauftragt.

[Dev4-Abnahme](validation/native-dev4-software-acceptance.md),
[Dev3-Erststart-Abnahme](validation/native-first-account-dev3-release.md),
[historische dev2-Abnahme](validation/native-streaming-dev2-release.md),
[Bedienung](NATIVE-USER-GUIDE.de.md), [Betrieb](NATIVE-OPERATIONS.de.md),
[Umfang und Fehlerhilfe](NATIVE-SUPPORT.de.md).
