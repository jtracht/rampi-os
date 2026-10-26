# Entwicklungsfortschritt

Der Produktumfang wurde am 26.10.2026 ausdrücklich verkleinert: Codex, Claude
Code und Gemini/Antigravity samt direkter CLI- und Sitzungsintegration entfallen.
Es bleiben drei Hauptmodule: Kanban, Remote Desktop und Browser.

Die bisher abgenommenen **81/100** sind deshalb nicht direkt mit dem neuen
Prozentwert vergleichbar. Nach Abzug der früheren drei Anbieter-CLI-Punkte
beträgt die vergleichbare Basis **78/95 = 82,1 %**. Die entfernten fünf möglichen
Punkte werden nicht auf andere Bereiche verteilt.

Der belegte Stand wird wegen des nachträglich festgestellten Erststartfehlers auf
**85/95 = 89,5 %** korrigiert. Das veröffentlichte
[v0.6.0-dev.2](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.2)
enthält den integrierten Drei-Modul-Stand mit eingebettetem Streaming. Allgemeine
und native main-CI, unabhängige Programm-/Konten-/Paketprüfungen, frischer Imagebau,
grafische Image-Anmeldung und Kontrolle aller öffentlichen Downloads bestehen.
[Bisherige Abnahme](validation/native-streaming-dev2-release.md). Diese prüfte bereits
vorbereitete Konten und übersah den unveränderten Erststart: `pi` bleibt gesperrt,
während greetd bereits die Anmeldung zeigt. Es gibt kein Standardpasswort.
Die Korrektur im Komplettversionszweig ist noch nicht frisch abgenommen.

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
| Systemimage | 4 | 4 |
| Manuelle Updates | 5 | 5 |
| Dokumentation | 4 | 5 |
| Performance | 4 | 5 |
| **Summe** | **78 / 95** | **85 / 95** |

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

Das veröffentlichte dev2-Release bleibt eine ausdrücklich unvollständige Vorabversion.
Das frühere dev1-Release bleibt unverändert. Streaming, PAM-Schlüsselbünde und
die Entfernung der KI-Module sind jetzt im neuen Image enthalten. Sprachwechsel,
Windows-NLA und die weiteren dokumentierten Funktionsdetails bleiben offen.
Physische Hardwaretests und Windows-Testhosts sind auf Nutzerwunsch ausgeschlossen.
Es werden keine Modellanfragen ausgelöst.

[Frühere 81-Punkte-Abnahme](validation/rust-native-81-2026-10-24.md),
[grafische Image-Abnahme](validation/image-graphical-2026-10-24.md),
[Bedienung](NATIVE-USER-GUIDE.de.md), [Betrieb und manuelle Updates](NATIVE-OPERATIONS.de.md),
[Entwicklung](NATIVE-DEVELOPMENT.de.md), [Umfang und Fehlerhilfe](NATIVE-SUPPORT.de.md).


## Korrigierte Image-Abnahme

Der Nenner bleibt unverändert bei 95 Punkten. Die frühere Bewertung von 90,5 %
wird wegen der fehlenden Erstbenutzereinrichtung auf 89,5 % zurückgenommen.
Vor dem nächsten Release muss ein frischer unveränderter Gast den vorhandenen
Raspberry-Pi-Benutzerassistenten tatsächlich durchlaufen und danach die normale
grafische PAM-Anmeldung erreichen. Eine vorherige Testkontenerstellung ersetzt
diesen Nachweis nicht. Es wird kein Standardpasswort eingeführt.

| Bereich | Vor der Erweiterung / 5 | Jetzt abgenommen / 5 |
|---|---:|---:|
| Linux-Konten und Login | 4 | 5 |
| Remote Desktop und Streaming | 3 | 4 |
| Systemimage | 4 | 4 |
| Dokumentation | 4 | 5 |
| Performance | 4 | 5 |

Alle übrigen Bereiche behalten ihre bestehende Bewertung. Frische PAM-Anmeldungen,
erneute Anmeldung und persönliche Streaming-Geheimnisse beider Konten bestehen.
Die tatsächliche eingebettete Bild-/Eingabe-/Kopplungsabnahme und der vorab definierte
zehnminütige bewegte Stream unter 1 GiB/vier CPUs bestehen auf beiden Architekturen.
Bedienung, Installation, Rückwechsel und Grenzen der drei Module sind dokumentiert.
Der neue native Versionsstand wurde mit vollständigen Quellen veröffentlicht und
anschließend tatsächlich heruntergeladen und unabhängig geprüft. Die detaillierten
Nachweise und die verbleibenden neun Punkte stehen in der
[Release-Abnahme](validation/native-streaming-dev2-release.md).
`regular_release` bleibt für das unvollständige Gesamtprodukt ausdrücklich `false`.

[Kriterien für die Erweiterung](validation/native-streaming-ui-2026-10-26.md).
Eine lokale Komponentenprüfung, Testanzahl oder Wartezeit allein gibt keinen
zusätzlichen Punkt frei. Der neue Komplettversionszweig enthält inzwischen reale
Linux-NLA- und zusätzliche Gitea-Projekt-Komponentennachweise. Vollständiger
Sprachwechsel, Erststart-Image-Abnahme und weitere Funktionsdetails bleiben offen:
[gemeinsamer Entwicklungsstand](validation/complete-native-development-2026-10-26.md).
Keine Hardwaretests, Windows-Testhosts oder Modellanfragen.
