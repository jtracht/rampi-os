# Entwicklungsfortschritt

Der Produktumfang wurde am 26.10.2026 ausdrücklich verkleinert: Codex, Claude
Code und Gemini/Antigravity samt direkter CLI- und Sitzungsintegration entfallen.
Es bleiben drei Hauptmodule: Kanban, Remote Desktop und Browser.

Die bisher abgenommenen **81/100** sind deshalb nicht direkt mit dem neuen
Prozentwert vergleichbar. Nach Abzug der früheren drei Anbieter-CLI-Punkte
beträgt die vergleichbare Basis **78/95 = 82,1 %**. Die entfernten fünf möglichen
Punkte werden nicht auf andere Bereiche verteilt.

Der belegte Stand beträgt jetzt **86/95 = 90,5 %**. Das veröffentlichte
[v0.6.0-dev.3](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.3)
besteht einschließlich tatsächlicher erster Kontoeinrichtung, normalen Neustarts,
grafischer PAM-Anmeldung, privaten Schlüsselbünden und unabhängiger Kontrolle
aller 28 öffentlichen Dateien. Nur der zurückgenommene Image-Punkt wird
wiederhergestellt: [Erststart-Abnahme](validation/native-first-account-dev3-release.md).
Das fehlerhafte ältere dev2 bleibt unverändert; es gibt kein Standardpasswort.

| Bereich | Basis / 5 | Aktuell abgenommen / 5 |
|---|---:|---:|
| Grafische Sitzung und Dashboard | 4 | 5 |
| Tastatur und Maus | 4 | 4 |
| Setup-Assistent | 4 | 4 |
| Linux-Konten und Login | 4 | 5 |
| WLAN | 5 | 5 |
| Bluetooth | 4 | 4 |
| VPN | 4 | 4 |
| Windows-Host | 4 | 4 |
| Remote Desktop und Streaming | 3 | 4 |
| Kanban | 4 | 4 |
| Browser | 5 | 5 |
| Installer und Reparatur | 4 | 5 |
| Sicherheit und Isolation | 4 | 4 |
| Design und Branding | 4 | 4 |
| GitHub und CI/CD | 4 | 5 |
| Systemimage | 4 | 5 |
| Manuelle Updates | 5 | 5 |
| Dokumentation | 4 | 5 |
| Performance | 4 | 5 |
| **Summe** | **78 / 95** | **86 / 95** |

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

Das dev3-Release bleibt ausdrücklich unvollständig. Direkte KI-Integrationen
bleiben entfernt. Hardwaretests, Windows-Testhosts und Modellanfragen sind
ausgeschlossen. Nenner und bisherige Bewertungsstufen bleiben unverändert.

## Weiterarbeit bis mindestens 95 Prozent

Der Folgestand dev4 ergänzt Sprach- und Validierungsfehlertexte, gemeinsame
konfigurationserhaltende Locale-Installation und echte Anmelde-/Neuanmeldeprüfungen
für Deutsch und Englisch. Die zu kurze dreisekündige Frist des kalten Sprachabrufs
wurde anhand einer tatsächlichen 6,7-Sekunden-Messung im emulierten Gast korrigiert.
Die endgültige Quelle muss weiterhin auf beiden Architekturen vollständig
bestehen. Diagnosegäste, neue Tests und Quellcode allein geben keine Punkte.

Danach sind insbesondere Einrichtung, VPN, RDP/Streaming, Kanban und übergreifende
Berechtigungs-/Sitzungsgrenzen anhand derselben Skala erneut abzunehmen. Noch
nicht frisch abgenommene Bereiche behalten ihren Tabellenwert. Bluetooth-HID,
Tastatur-/Layoutfälle, Windows-Host-Randfälle und Fokus-/Bedienungsfeinschliff
bleiben offen. Das volle 100-Prozent-Ziel ist nicht abgeschlossen.
`regular_release` bleibt `false`.

[Frühere 81-Punkte-Abnahme](validation/rust-native-81-2026-10-24.md),
[historische dev2-Abnahme](validation/native-streaming-dev2-release.md),
[gemeinsamer Entwicklungsstand](validation/complete-native-development-2026-10-26.md),
[Bedienung](NATIVE-USER-GUIDE.de.md), [Betrieb](NATIVE-OPERATIONS.de.md),
[Umfang und Fehlerhilfe](NATIVE-SUPPORT.de.md).
