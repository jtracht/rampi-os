# Nativer Umfang und Fehlerhilfe

Dies ist der Rust-/Wayland-Entwicklungsstand. v0.5.0 enthält den früheren
Python-/QML-Prototyp. Das native Entwicklungsimage hat eine eigene dokumentierte
Quellrevision und enthält nicht automatisch spätere Änderungen dieses Zweigs.

Die folgende Tabelle beschreibt den aktuellen Entwicklungsstand. Das veröffentlichte
[dev5-Image](https://github.com/jtracht/rampi-os/releases/tag/v0.6.0-dev.5) besteht
einschließlich beider Erstkonto-Wege, normaler Neustarts, persönlicher DE-/EN-Locale
und unabhängig geprüfter öffentlicher Dateien. Es gibt kein Standardpasswort.
[Quellen und Abnahmen](validation/native-dev5-keyboard-release.md).
Die noch nicht vollständig abgenommenen Bereiche bleiben ausdrücklich benannt.

| Bereich | Vorhanden | Abnahmegrenzen und offene Arbeit |
|---|---|---|
| Sitzung/Dashboard | Rust/GTK/labwc, drei abgenommene native Module, Live-Status, Offline-Bedienung | Gesamtprodukt bleibt eine Vorabversion |
| Eingabe/Design | Tastatur, Maus, Cursorwechsel, unabhängige Wellen, Klänge, reduzierte Bewegung | Windows-Remote-Eingabe im neuen Gesamtaufbau |
| Einrichtung | Fortsetzbare 12 Stationen, gemeinsame Einstellungsseiten, persönliche DE-/EN-Sprache und Sitzungs-Locale | Beide Erstkonto-Wege, normale Neustarts und persönliche DE-/EN-Anmeldung im frischen Image bestanden |
| Linux-Konto | Grafischer greetd-/PAM-Login mit Original-Branding, eigenes passwd, Abmeldung, private SSH-Agenten und persönliche Schlüsselbünde | Softwareabnahme einschließlich Streaming-Geheimnissen und erneuter Anmeldung im neuen Image bestanden |
| WLAN | Eigene integrierte Seite; sichtbare/versteckte SSIDs, Adapter, offen/WPA2/WPA3, private Profile; WPA2, sichtbares/verstecktes WPA3, DHCP und Kontentrennung in frischen AMD64-/ARM64-QEMU-Gästen abgenommen | Unternehmensnetze benötigen vorhandenes NM-Profil; physische Funkqualität ausgeschlossen |
| Bluetooth | Eigene Seite, Suche, Codes/PIN/Passkey, Vertrauen/Entfernen, Dienstneustart; Mehradapteroberfläche und tatsächliche virtuelle BlueZ-Bindungen auf AMD64/ARM64 abgenommen | Durchgängige HID-/Remote-Eingabeabnahmen; physischer Funk ausgeschlossen |
| WireGuard/Tailscale | Persönlicher libnm-Import, echte WG-Tunnel; offizieller TS-Dienst, persönliche Anmeldung, privater Kernel-Tunnel mit Rechten/Wiederverbindung softwaregeprüft; manuelle signierte Paketinstallation integriert | Signierte Dienstinstallation und Erhaltung im frischen systemd-Gast sowie getrennte reale Tunnelabnahme bestanden; physische Netze ausgeschlossen |
| Windows-Host | Persönliche Hosts, OpenSSH-Schlüssel/Trust und integriertes RDP; NLA-only gegen vorhandenen FreeRDP-/WinPR-Server mit richtigen/falschen Konten, Domain und Kennwörtern softwaregeprüft | Finale Quellenabnahme bestanden; zusätzliche native Windows-Komponentenprüfung in isolierter GitHub-CI beauftragt; persönliche und externe Testhosts bleiben ausgeschlossen |
| Kanban | JSON und sechs Online-Anbieter einschließlich Gitea, Filter, Spalten, privater Offline-Cache; private Repository-, Organisations- und Benutzerprojekte mit echten Gitea-HTTPS-Prüfungen | Finale Quellenabnahme bestanden; persönliche Anbieterzugänge werden vom jeweiligen Benutzer eingerichtet |
| Browser | WebKit, HTTPS, Navigation, JavaScript, persönliches Profil, Abfragen, Downloads und Datei-/Mehrfachauswahl als Seiten; Mikrofon-/Kamerafreigabe mit realem WebKit und synthetischer Aufnahmequelle geprüft | Finale Quellenabnahme bestanden; synthetische Quelle bestätigt keine physische Kamera oder Mikrofonhardware |
| RDP/Streaming | Integriertes RDW/IronRDP mit Zertifikat-Pin, echten Frames, Tastatur, Wiederverbindung und Abbruchbehandlung; skalierte Maus, beide Scrollachsen und Unicode-Zwischenablage auf AMD64/ARM64 mit tatsächlichen Serverquittungen abgenommen; eingebettetes Moonlight-/GStreamer-Streaming mit privater Kopplung und Dauerlastprüfung; NLA-only-Komponentenprüfung vorhanden | Finale Quellen-/Protokolleingabeabnahme bestanden; physische HID-/Windows-Eingabe nicht behauptet; Pi-Hardwaredecoder softwareseitig angebunden, aber nicht physisch geprüft; Sunshine gibt über die Kopplung seine Host-Sitzung frei |
| Installation | ARM64-Binary, Paketprüfung, manuelle atomare Aktivierung, Reparatur/Rückwechsel | Native Pakete und HTTPS-Bootstrap implementiert; Freigabe des regulären nativen Releases offen |
| Image/Release | Veröffentlichtes v0.6.0-dev.5, vollständige Quellen/Lizenzen, zwei Erstkonto-Verfahren mit normalen Neustarts, grafische PAM-Anmeldung und 28 unabhängig geprüfte öffentliche Dateien | Reguläre Freigabe des Gesamtprodukts nach den übrigen Funktionsarbeiten |

## Fehler eingrenzen

**Host nicht erreichbar:** Aktives Profil, Hostadresse, SSH-Port und VPN prüfen.
Die Anzeige prüft nur TCP. „Erreichbar“ bestätigt weder Windows-Version noch
Benutzeranmeldung. Der Laptop muss eingeschaltet sein.

**SSH lehnt den Host ab:** Den Ed25519-Fingerprint unabhängig auf Windows anzeigen
und vergleichen. Einen geänderten bestehenden Hosteintrag nicht blind löschen;
zuerst die Identität klären. Private Schlüssel gehören nicht in Fehlerberichte.

**Nichtinteraktive Hostprüfung kann den privaten Schlüssel nicht verwenden:**
Das gespeicherte aktive Hostprofil prüfen und unter **Host & SSH** den
**Aktiven SSH-Schlüssel entsperren**. Die Eingabe erfolgt im eingebetteten
OpenSSH-Terminal. Der Agent muss in derselben Linux-Anmeldung erreichbar sein.
Die persönliche SSH-Agent-Sitzung ist in den frischen Anmeldetests abgenommen.

**Vorhandener WLAN-Zugang scheitert:** Das tatsächlich verwendete NM-Profil prüfen.
Eine neue Kennworteingabe ersetzt dessen gespeichertes Geheimnis nicht automatisch.
Für versteckte Netze sind SSID und Sicherheit exakt anzugeben; mehrere passende
Profile werden nicht automatisch priorisiert. Kein zweiter Netzwerkmanager ist nötig.

**Bluetooth-Dienst startet neu:** Auf der Bluetooth-Seite erneut suchen. Alte Anfragen und
PINs werden verworfen; der eigene Agent meldet sich beim neuen Dienst an.
Vertrauen und Entfernen betreffen den gemeinsamen Adapter und brauchen Bestätigung.

**Nach Auflösungswechsel kein Bild:** Ohne Bestätigung wird nach 15 Sekunden der
vorherige angebotene Modus angefordert. Bei inzwischen abgezogenem Monitor kann
dieser fehlen: Monitor wieder anschließen oder über die TTY neu anmelden.
Änderungen gelten bis zur Abmeldung und verändern keine Boot-/Firmwaredateien.

**Tastaturbelegung wirkt nicht:** Im Testfeld prüfen. Der normale Login lädt
`~/.config/rampi/labwc/environment`. In einer fremden vorhandenen Sitzung kann
erst die nächste Rampi-Anmeldung wirksam sein. Fremde Desktopdateien bleiben erhalten.

**HTTPS-Zertifikat abgewiesen:** Datum/Uhrzeit, Hostname und Zertifikatskette prüfen.
Es gibt keinen Zertifikats-Bypass. Downloads warten auf ein ausdrückliches Ziel,
überschreiben nicht und öffnen Dateien nicht automatisch. Ohne Zielentscheidung
werden sie nach einer Minute abgebrochen. Maximal 16 Einträge bleiben bis zum
Leeren der abgeschlossenen Liste erhalten.

**Konfiguration nicht speicherbar:** Das fehlerhafte vorhandene Dokument zuerst
privat sichern und korrigieren. Unbekannte Felder und ungültige Werte werden
abgewiesen; Standardwerte ersetzen nicht die vorhandene Datei.
[Schema und Pfade](CONFIGURATION.md).

**Keine Klickklänge:** Persönliche Einstellung und vorhandenen Pulse-kompatiblen
Audiodienst prüfen. Rampi startet keinen zweiten Audiomanager. Die isolierte
PCM-Abnahme muss wirklichen Ton messen, auch wenn ein anderer Test still läuft.

## Fehlerbericht und Wiederherstellung

Die integrierte Diagnose prüft Konto, Hostanzahl, Programme und Diensterreichbarkeit.
Sie verändert kein Netzwerk und prüft keine Cloudanmeldungen. Ergänzend zeigt
`journalctl --user -u rampi.service` den Verlauf. Vor dem Teilen Benutzernamen,
Hostnamen, Projektpfade und Webadressen prüfen. Keine Kennwörter, Schlüssel,
Hostprofile, Tokens oder echten Kanban-Daten veröffentlichen.

Nenne Programm-/Gitversion, letzten Schritt, genaue Meldung und Testumgebung.
Für Softwareabnahmen Marker und Messdateien angeben; ein Screenshot belegt kein
Protokoll. [Reparatur und Rückwechsel](NATIVE-OPERATIONS.de.md) erhalten persönliche
Daten, setzen deren Schema oder Inhalte aber nicht automatisch zurück.
