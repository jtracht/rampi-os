# Entwicklungsfortschritt

Der Produktumfang wurde am 26.10.2026 ausdrücklich verkleinert: Codex, Claude
Code und Gemini/Antigravity samt direkter CLI- und Sitzungsintegration entfallen.
Es bleiben drei Hauptmodule: Kanban, Remote Desktop und Browser.

Die bisher abgenommenen **81/100** sind deshalb nicht direkt mit dem neuen
Prozentwert vergleichbar. Nach Abzug der früheren drei Anbieter-CLI-Punkte
beträgt die vergleichbare Basis **78/95 = 82,1 %**. Die entfernten fünf möglichen
Punkte werden nicht auf andere Bereiche verteilt.

Die neue Zielabnahme umfasst **81/95 = 85,3 %**. Sie gilt erst, wenn beide neuen
nativen CI-Läufe und die unabhängige Prüfung ihrer tatsächlich heruntergeladenen
Programm-, Login-, Radio- und Paketnachweise bestehen. Bis dahin ist 85,3 % ein
Zielwert. [Umfang, Kriterien und Nachweise](validation/three-module-scope-2026-10-26.md).

| Bereich | Basis / 5 | Nach bestandener Zielabnahme / 5 |
|---|---:|---:|
| Grafische Sitzung und Dashboard | 4 | 5 |
| Tastatur und Maus | 4 | 4 |
| Setup-Assistent | 4 | 4 |
| Linux-Konten und Login | 4 | 4 |
| WLAN | 5 | 5 |
| Bluetooth | 4 | 4 |
| VPN | 4 | 4 |
| Windows-Host | 4 | 4 |
| Remote Desktop und Streaming | 3 | 3 |
| Kanban | 4 | 4 |
| Browser | 5 | 5 |
| Installer und Reparatur | 4 | 5 |
| Sicherheit und Isolation | 4 | 4 |
| Design und Branding | 4 | 4 |
| GitHub und CI/CD | 4 | 5 |
| Systemimage | 4 | 4 |
| Manuelle Updates | 5 | 5 |
| Dokumentation | 4 | 4 |
| Performance | 4 | 4 |
| **Summe** | **78 / 95** | **81 / 95** |

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

Das veröffentlichte [v0.6.0-dev.1](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.1)
ist eine ausdrücklich unvollständige Vorabversion und enthält die spätere
Schlüsselbundintegration und KI-Entfernung noch nicht. Ein bestehendes Image
wird niemals still durch neueren Code ersetzt. Reguläre Release-Funktionsgleichheit,
eingebettetes Streaming, Sprachwechsel und Windows-NLA bleiben offen.
Physische Hardwaretests und Windows-Testhosts sind auf Nutzerwunsch ausgeschlossen.
Es werden keine Modellanfragen ausgelöst.

[Frühere 81-Punkte-Abnahme](validation/rust-native-81-2026-10-24.md),
[grafische Image-Abnahme](validation/image-graphical-2026-10-24.md),
[Bedienung](NATIVE-USER-GUIDE.de.md), [Betrieb und manuelle Updates](NATIVE-OPERATIONS.de.md),
[Entwicklung](NATIVE-DEVELOPMENT.de.md), [Umfang und Fehlerhilfe](NATIVE-SUPPORT.de.md).
