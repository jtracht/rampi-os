# Lizenzen und Herkunft

Eigenentwickelter Rampi-Code: Apache License 2.0 (`LICENSE`).
Drittanbieter behalten ihre Bedingungen. Paketinstallation ist keine
Umlizenzierung. Mit einem Systemimage entstehen zusätzliche
Weitergabepflichten, insbesondere Copyright-/Lizenztexte und gegebenenfalls
korrespondierende Quellen für GPL-Komponenten. Vor einem regulären Release
Manifest, Debian-Copyrightdateien und Source-Angebote zum exakten Paketstand
vollständig archivieren. Die aktuelle Dokumentprüfung ersetzt das nicht.

| Komponente | Lizenzfamilie / Herkunft |
|---|---|
| Qt/PySide6 | LGPLv3/GPLv3 bzw. kommerziell; dynamische Debian-Bibliotheken |
| Python | PSF |
| Openbox | GPLv2 |
| LightDM | GPLv3 |
| systemd | LGPLv2.1+ und Komponentenlizenzen |
| NetworkManager | GPLv2+ |
| libnm, einschließlich WireGuard-Importer | LGPLv2.1+; dynamische Systembibliothek |
| BlueZ | GPLv2/LGPL je Komponente |
| FreeRDP | Apache-2.0 |
| xfce4-terminal/VTE | GPL/LGPL je Paket |
| Chromium | BSD und zahlreiche Drittkomponenten |
| OpenSSH | BSD-artige Einzelkomponentenlizenzen |
| psmux 3.4.0 | MIT, nicht in Rampi umgelabelt |
| Moonlight Embedded | GPLv3 |
| Sunshine | GPLv3 |
| Tailscale | BSD-3-Clause für Open-Source-Teile; Dienstbedingungen separat |
| WireGuard | GPLv2 / tools GPLv2 je Paket |
| pi-gen | BSD-3-Clause |
| Lucide-SVG-Icons | ISC und zugehörige Feather-MIT-Hinweise; vollständige Datei in client/rampi/icons/LICENSE |

Maßgeblich sind jeweils die Copyrightdateien der tatsächlich verwendeten Version.
Offizielle KI-CLIs werden nicht im Pi-Image oder Rampi-Quellcode gebündelt.
Anbieterbedingungen und persönliche Anmeldung bleiben erhalten.

Grafiken: siehe `assets/references/RIGHTS.md`. Keine Lizenz an Drittanbieter-
Marken wird durch Apache-2.0 erteilt. Systemschriften werden aus dem jeweiligen
Betriebssystem verwendet; Windows-Schriftdateien werden nicht weitergegeben.
# Rust-/Wayland-Entwicklungsstand

Der native Image-Bau sammelt die ursprünglichen Lizenztexte aller für den
Linux-Zielbau aufgelösten Cargo-Abhängigkeiten aus deren festgehaltenen Quellen.
Die Liste mit Versionen und SPDX-Angaben liegt im Image unter
`/usr/share/doc/rampi/rust-licenses/packages.json`. Die Standardbibliothek erhält
ihre ursprünglichen Rust-Notices und Lizenztexte aus dem verwendeten Toolchain.
Die Erfassung ergänzt die separat gesammelten Lizenzinformationen der
Distributionspakete; sie ersetzt deren Bedingungen nicht.

Vier WebKit-/JavaScriptCore-Rust-Crates liefern den übergeordneten MIT-Lizenztext
nicht im Crate-Archiv mit. Die unveränderte Datei stammt aus genau der in ihren
Quellmetadaten angegebenen Upstream-Revisionen, deren Lizenzdateien identisch sind; Herkunft siehe
`assets/licenses/rust/README.md`. Ein fehlender Original-Lizenztext bricht die
Sammlung ab. Die bisherigen Release-Angaben weiter unten beziehen sich auf den
historischen Python-/QML-Stand, soweit nicht ausdrücklich anders angegeben.

