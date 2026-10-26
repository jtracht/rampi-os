# Native Streaming- und Image-Abnahme v0.6.0-dev.2

**86/95 = 90,5 %** im vereinbarten Drei-Modul-Umfang. Gegenüber 81/95 erhalten
Linux-Konten, Remote/Streaming, Systemimage, Dokumentation und Performance jeweils
einen belegten Punkt. Nenner und Bewertungsstufen bleiben unverändert.
Das Gesamtprodukt bleibt eine Vorabversion; `regular_release` ist `false`.

Die [Kriterien](native-streaming-ui-2026-10-26.md) wurden vor den Dauerläufen
festgelegt. KI-Module bleiben entfernt. Windows-Testhosts, physische Hardwaretests
und Modellanfragen wurden nicht verwendet.

## Version und öffentliche Dateien

- [Veröffentlichtes Entwicklungsrelease](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.2)
- Quellrevision: `719760b3662864df870091a46593be8e6fe95241`
- [Allgemeine main-CI](https://github.com/jtracht/rampi-os/actions/runs/40320942081)
  und [native main-CI](https://github.com/jtracht/rampi-os/actions/runs/40320942066)
- [Frischer Imagebau, grafische Abnahme und Veröffentlichung](https://github.com/jtracht/rampi-os/actions/runs/40329976709)
- Image: `image_2026-10-26-rampi-os-rpi3bplus-v0.6.0-dev.2.img.xz`
- Image-SHA256: `f50fc7c34f6d9d1c9cd85a2a0a458974c9f36c5745b173c7dfa82f6f0cf617fd`
- Tatsächlich im Image angemeldetes Release-Programm, SHA256:
  `caa587bd20577f816cbeee87d2e8d07a95d131c8e35347da822941d7372d0f2c`

Nach Veröffentlichung wurden alle **28 öffentlichen Dateien** heruntergeladen,
alle Manifest-Prüfsummen und alle **28 GitHub-Server-Digests** verglichen. Tagrevision,
Vorabversionsstatus, Image-, Programm-, Quell- und Anmeldenachweise bestehen.
Enthalten sind Image, ARM64-Paket, beide Installer, Windows-Paket, Rampi-Quellen,
Lizenzen und die vollständigen Abhängigkeitsquellen. Die Debian-Quellen werden in
drei Teilen mit geprüftem Wiederherstellungsskript bereitgestellt. Geprüft sind
Quellen für **646 Distributionspakete**, **501 Cargo-Abhängigkeiten** und die
Moonlight-C-Bibliothek mit **186 inventarisierten Quelldateien**.

Das ältere veröffentlichte dev1-Release bleibt unverändert. Dieser anschließend
eingetragene Dokumentationsnachweis ersetzt weder Tag noch Programm oder Image.

## Tatsächliche Softwareprüfungen

PR- und tatsächlicher Merge-Codebaum stimmen überein. Zusätzlich bestehen die
unabhängig heruntergeladenen endgültigen main-Nachweise beider Architekturen:
native Funktionen, Funkgeräte, grafische PAM-Anmeldung und sieben Paketprüfsummen.
Streaming, PAM-Anmeldung und ARM64-Paket sind an dasselbe ausgeführte Programm
gebunden. Die CI-Messungen unten verwenden das Debug-ELF; das Release-ELF ist
separat an das tatsächlich installierte Image gebunden.

Echte Sunshine-Kopplung, Ablehnung eines geänderten TLS-Schlüssels, persönliche
Secret-Service-Identitäten, zwei GTK-Verbindungen, empfangenes Stereo-PCM und
entschlüsselte Eingabequittungen bestehen. Das Dashboard-Kürzel bleibt lokal.
Die Plattforminjektion im Testserver ist ausgeschaltet; die Paketquittungen werden
nicht als Windows-Eingabeabnahme ausgegeben.

| Architektur | Dauer s | neue Frames | Paint p95 ms | höchster Programm-RSS MiB |
|---|---:|---:|---:|---:|
| AMD64 | 600,51 | 18.008 | 18,48 | 194,0 |
| ARM64 | 600,12 | 15.230 | 17,93 | 188,3 |

Client und Server waren tatsächlich auf jeweils 1 GiB ohne zusätzlichen Swap und
vier CPUs begrenzt. Das sind Softwaremessungen, keine Pi-Timing- oder GPU-Messungen.
Daneben bestehen 600 Modulwechsel, ein separater zehnminütiger Mischlasttest mit
RDP/WebKit/PTYs und die dokumentierte vollständige lokale Reproduktion.

Frische grafische Gäste und das installierte neue Image prüfen zwei Linux-Konten,
ein falsches Kennwort, private Profile, persönliche SSH-Agenten, PAM-Schlüsselbünde
und erneute Anmeldung. Beide Konten speichern und lesen auch über den produktiven
Streaming-Schlüsselbundadapter; eine andere Hostbindung wird zurückgewiesen.
Die installierten Programmdateien einschließlich der Moonlight-C-Bibliothek
bleiben während der Image-Abnahme unverändert.

## Verbleibende neun Punkte

| Bereich mit 4/5 | Noch zu vervollständigen |
|---|---|
| Tastatur und Maus | Windows-spezifische Remote-Eingaben und durchgängige HID-/Layout-Fälle |
| Setup | Integrierter Sprach- und Localewechsel |
| Bluetooth | Durchgängige HID-Eingabe- und Wiederverbindungsfälle |
| VPN | Persönliche Tailscale-Anmeldung/Tunnel und weitere Routingszenarien |
| Windows-Host | NLA und Konten-/Sitzungszuordnung softwareseitig absichern |
| Remote Desktop/Streaming | NLA und Integration des vorhandenen Pi-Decoderpfads |
| Kanban | Weitere Gitea-Projekttypen und Anbieter-Randfälle |
| Sicherheit/Isolation | Übergreifende Sitzungs-, Berechtigungs- und Fehlergrenzen |
| Design/Branding | Einheitlicher Layout-, Fokus- und Bedienungsfeinschliff |

Ausgeschlossene Tests bleiben ausgeschlossen. Das Ziel von 100 % des aktuellen
Produktumfangs ist durch dieses Entwicklungsrelease nicht abgeschlossen.
