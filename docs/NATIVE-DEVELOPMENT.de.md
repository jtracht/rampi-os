# Rust entwickeln und Softwareabnahme wiederholen

Die Oberfläche ist Linux-Software. Windows kann `rampi-core` und die bestehende
Windows-Hostintegration prüfen; GTK-/Wayland-Abläufe laufen in Linux-Docker.
Physische Hardwaretests sind auf Nutzerwunsch ausgeschlossen.

GitHub startet die native Abnahme für Pull Requests und für Pushes auf `main`.
Damit gibt es für einen Feature-Commit mit offenem PR keinen zusätzlichen,
gleichzeitig abbrechenden Push-Lauf. Andere Branches lassen sich bei Bedarf
über den vorhandenen manuellen Workflow-Start prüfen.

## Gesamtlauf

Benötigt werden Git, Python 3 und ein erreichbarer Linux-Docker-Dienst.
Aus dem Checkout:

```sh
python scripts/test-native.py
```

Der Ablauf baut die festgehaltene Testumgebung, erfasst den nicht ignorierten
Quellstand in einem temporären Snapshot und kompiliert ihn einmal. Laufende
Prüfungen sehen keine nachträglichen Änderungen des Arbeitsverzeichnisses.
`artifacts/rust-local/source-state.json` enthält Git-Revision, Hinweis auf lokale
Änderungen und Snapshot-Hash. Ein veränderter Arbeitsstand ist kein Nachweis
eines unveränderten Git-Commits.

Standardmäßig wird ein eigenes Buildvolume anschließend entfernt. Logs, echte
Compositor-PNGs, Messwerte und Abnahme-JSON bleiben im Ausgabeordner. Nur ein neu
erzeugter temporärer Aufnahmeordner erhält die nötigen Container-Schreibrechte;
bestehende Verzeichnisrechte werden nicht gelockert. Für wiederholte Entwicklung:

```sh
python scripts/test-native.py --skip-image-build --build-volume rampi-rust-build --artifacts artifacts/rust
```

Das überspringt nur den Docker-Imagebau. Format, Rust-Tests, Clippy und Kompilierung
laufen weiterhin. Dasselbe Buildvolume darf nicht gleichzeitig von einem zweiten
Build oder Test verändert werden. Nach Dockerfile-Änderungen das Image neu bauen.
Auf nativem ARM64 ergänzt `--installer` die tatsächliche Installer-/Reparatur-/
Rückwechsel-/Deinstallationsprüfung; auf amd64 ist dieser Zusatz nicht vorgesehen.
Die GitHub-Matrix verwendet dafür einen nativen ARM64-Runner.

## Nachweisarten

| Ausgabe | Tatsächlich geprüft | Grenze |
|---|---|---|
| `build.log` | Gesperrte Cargo-Auflösung, Format, Core-Tests, Clippy, Linux-Build | Keine Windows-GUI |
| `wayland.log` | GTK-Seiten, Assistent, SSH, VTE, WebKit, Klickton und 600 Seitenwechsel | Pixman/Cairo statt Pi-GPU |
| `interaction-*.png`, `visual-acceptance.json` | Reale Wayland-Eingabe, vier Kanten bei Start/Hover/Fokus, reduzierte Bewegung, 1280×720 und 1600×900 | Keine physischen Eingabegeräte oder HDMI-Messung |
| `cloud-kanban.log` | Tatsächliches GTK, curl/TLS und verschlüsselter Schlüsselbund, sechs Anbieter-Verträge, Offline-/Quellen-/Token-Trennung | Keine persönlichen Cloudkonten |
| `gitea-live/` | Offizieller isolierter Gitea-Server über HTTPS; echte GTK-/Schlüsselbund-Seite, Lesezugang, Paginierung, serverseitige Änderung und Abschaltung | Repository-Projekte in Gitea 28.2.0; auf AMD64/ARM64 akzeptiert, weitere Projekttypen und persönliche Anbieterzugänge offen |
| `bootstrap-tls.log` | Reales curl/HTTPS, Quellen-/Binary-Abgleich, manipulierte Archive, Prüfsummen und Pfadschutz | Installer-Stub; echte ARM64-Lifecycle-Abnahme separat |
| `network-contract.log` | Rust/GIO, versteckte SSIDs, ACL, Profilwiederverwendung | Private NM-Fixture, kein Funk/DHCP |
| `bluetooth-contract.log` und Agent-Marker | Suche, PIN/Passkey, eingegebene Stellen, fremder Absender, Cancel/Release, echter Fixture-Prozesswechsel | Private BlueZ-Fixture, keine Funkkopplung |
| `account-pam.log` | Unprivilegiertes passwd im VTE, altes/falsches/neues Kennwort gegen PAM, zweites Linux-Konto | Kein grafischer greetd-Durchlauf |
| `browser-https.log` | Lokaler TLS-Server, temporäre CA, Zertifikatsfehler, Navigation, JavaScript-Abfragen, WebKit-Dateitransfer | Keine persönlichen Internetkonten oder komplette Seitensammlung |
| `wireguard-contract.log` | Echter libnm-Import plus private D-Bus-Fixture | Kein Tunnel in dieser Einzelstufe |
| `wireguard-peers.log` | Echte NM-/WireGuard-Gegenstellen, verschlüsselter Verkehr, falscher Schlüssel, Kontentrennung, Trennen | Private Containervernetzung |
| `tailscale-status.log` | Offizielle CLI, isolierter Dienst und begrenzte Fehler-Fixtures | Keine Anmeldung und kein Tailscale-Tunnel |
| `performance.json`, `memory-peak-bytes.txt` | Beobachtete Frames, CPU, RSS und Containerpeak unter 1 GiB | Keine Pi-Geschwindigkeit oder echte KI-/Remote-Dauerlast |
| `native-acceptance.json` | Alle verpflichtenden Marker und Leistungsbudgets | Kein Ersatz für fehlende Einzelbelege |

SSH verwendet einen wirklichen kurzlebigen OpenSSH-Server und OpenSSH-Testschlüssel.
Die zufällige Passphrase wird im VTE eingegeben und nicht ausgegeben. Geprüft sind
Schlüsselaustausch und bewusste Hostvertrauensnahme, keine Windows-Anmeldung.
Die HTTPS-CA wird ausschließlich im Wegwerfcontainer installiert, niemals im
Trust Store des Hosts oder Geräts.

Konten-, PAM- und Diensttests verweigern die Ausführung außerhalb ihres Containers.
Host-Eingabegeräte, GPU-Geräte, Systembusse und persönliche Profile werden nicht
eingebunden. Nur die privaten WireGuard-Gegenstellen erhalten NET_ADMIN/NET_RAW.
Die WebKit-Sandbox bleibt eingeschaltet. Die dokumentierten Docker-Ausnahmen
für Seccomp, AppArmor und maskierte Systempfade gelten ausschließlich im Test.
GitHub sichert und restauriert zusätzliche Namespace-Einstellungen seiner
kurzlebigen VM; der lokale Prüflauf verändert sie nicht. Bei Namespacefehlern
eine geeignete Testmaschine verwenden, statt die WebKit-Sandbox abzuschalten.

## Einzelentwicklung und Beiträge

Unter Linux mit den Paketen aus `tests/rust/Dockerfile`:

```sh
cargo test --locked -p rampi-core
cargo fmt --all --check
cargo clippy --locked --workspace --all-targets -- -D warnings
RAMPI_ASSETS="$PWD/client/rampi" cargo run --locked -p rampi-ui -- --windowed
```

Ohne Systemdienste zeigt die Anwendung deren Nichtverfügbarkeit; das ist kein
Demo-Modus. `--*-check`-Funktionen sind für isolierte Testumgebungen bestimmt.
Neue Pflichtstufen in `scripts/check-native-evidence.py` aufnehmen. Ein grüner
Build allein reicht nicht. Nach Cargo-Abhängigkeitsänderungen müssen der
Linux-Abhängigkeitsgraph, ursprüngliche Lizenztexte und Image-Lizenzsammler
erneut geprüft werden. Die historische Python-Suite bleibt eine zusätzliche
Regression und ersetzt keine Rust-GUI-Abnahme.

## Virtuelle WLAN-Geräte

Die native QEMU-Stufe baut das Prüfprogramm aus demselben produktiven `bus.rs`.
Sie prüft WPA2, DHCP, echten IP-Verkehr, falsches Kennwort, Wiederverbindung und
einen zweiten Linux-Benutzer. [Nachweis und Wiederholung](validation/rust-wlan-qemu-2026-10-23.md).
Die CI verwendet einen frischen offiziellen Debian-Gast; der lokale optionale
`--prepared`-Cache ist ausschließlich für Entwicklung und wird im Nachweis markiert.


Die vollständige lokale Archivabnahme mit `scripts/test-native.py` setzt einen
eingecheckten, während des Laufs unveränderten Quellstand voraus. Sie friert das
Programm ein und bindet nun auch die wirklichen Moonlight-/GTK-/Dauerlastbelege
an diesen Stand. Für den normalen Bearbeitungszyklus bleiben Cargo-Tests und
Clippy einzeln nutzbar. Ein nicht eingecheckter Komponentenlauf ist kein
veröffentlichungsfähiger Nachweis.
