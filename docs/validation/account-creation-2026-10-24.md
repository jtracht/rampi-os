# Native Einrichtung zusätzlicher Linux-Konten

Die Rust-Seite verwendet vorhandenes sudo, useradd und passwd innerhalb eines
VTE-Terminals. Es gibt keinen eigenen Kontenspeicher, PAM-Ersatz, Root-Dienst,
Polkit-Dialog oder geänderte sudoers-Regeln im installierten Produkt.

Ein neuer Name wird streng validiert und als einzelnes Argument hinter `--`
übergeben. useradd erstellt ein gewöhnliches Konto mit eigener Gruppe,
`/bin/bash` und UMASK 077. Die Seite prüft die tatsächliche NSS-Identität über
getent sowie UID, Home-Besitz, Nicht-Symlink und Modus 0700. Vor passwd wird
dieselbe Identität erneut geprüft. Ein bestehendes Konto kann nicht für eine
Kennwortänderung übernommen werden. Teilfehler bleiben sichtbar; vorhandene
Konten oder Verzeichnisse werden nicht automatisch repariert oder gelöscht.

## Lokale tatsächliche Softwareprüfung

Der gesamte Ablauf läuft mit UID 1000 in einer neuen Docker-Umgebung unter
Wayland mit 1 GiB Limit. Zuerst fehlen administrative Rechte: sudo fragt nach
dem vorhandenen Benutzerkennwort und weist die Aktion ab; es entsteht kein Konto.
Nur die Wegwerf-Testumgebung erhält anschließend eine sudoers-Freigabe für die
beiden offiziellen Werkzeuge. Das Produkt installiert keine solche Freigabe.

Die echte GTK-Seite prüft ungültige Namen, Bestätigung/Abbruch, Zurückweisung
eines vorhandenen Kontos, erfolgreiche Erstellung und tatsächliches passwd.
Eine vorhandene rootgehörige Home-Struktur und ein verlinktes Home führen trotz
erfolgreichem useradd nicht zur Kennwortfreigabe. Die Strukturen bleiben
unverändert und die beiden Konten bleiben gesperrt. Das gültige neue Konto
besitzt sein Home mit Modus 0700, erhält keine sudo-Gruppe und authentifiziert
sich anschließend tatsächlich über PAM. Das Kennwort des bisherigen Kontos
bleibt unverändert; Kennwörter erscheinen nicht in Ausgaben oder Aufnahmen.

Der frische grafische greetd-/PAM-Durchlauf mit zwei isolierten Konten ist
zusätzlich im [80-Prozent-Nachweis](rust-native-80-2026-10-24.md) dokumentiert.
Die erweiterte [native Gesamt-CI 40093153025](https://github.com/jtracht/rampi-os/actions/runs/40093153025)
auf AMD64 und ARM64 und die [allgemeine CI 40093152982](https://github.com/jtracht/rampi-os/actions/runs/40093152982)
bestehen. Beide heruntergeladenen nativen Nachweise, die frischen grafischen
Anmeldungen und die sieben Paketprüfsummen wurden unabhängig erneut geprüft.
[PR 34](https://github.com/jtracht/rampi-os/pull/34) ist mit dem identischen geprüften
Git-Baum `770fb0a0dc7a2b370f959f862e6912c0087876eb` zusammengeführt.
Der Gesamtstand bleibt bis zur gesonderten Bewertung bei 80/100.
