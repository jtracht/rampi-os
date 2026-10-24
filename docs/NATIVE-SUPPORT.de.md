# Nativer Umfang und Fehlerhilfe

Dies ist der Rust-/Wayland-Entwicklungsstand. v0.5.0 enthält den früheren
Python-/QML-Prototyp. Das native Entwicklungsimage hat eine eigene dokumentierte
Quellrevision und enthält nicht automatisch spätere Änderungen dieses Zweigs.

| Bereich | Vorhanden | Wesentliche offene Arbeit |
|---|---|---|
| Sitzung/Dashboard | Rust/GTK/labwc, sechs Module, Live-Status, Offline-Bedienung | Gesamtabnahme aller externen Module |
| Eingabe/Design | Tastatur, Maus, Cursorwechsel, unabhängige Wellen, Klänge, reduzierte Bewegung | Windows-Remote-Eingabe im neuen Gesamtaufbau |
| Einrichtung | Fortsetzbare 15 Stationen und gemeinsame Einstellungen | Vollständige Anbieter-Einrichtung, Sprachwechsel |
| Linux-Konto | PAM/passwd, eigenes Kennwort, bestätigte Abmeldung | Weitere Konten und grafischer Greeter-Durchlauf |
| WLAN | Sichtbare/versteckte SSIDs, Adapter, offen/WPA2/WPA3, private neue Profile | Unternehmensnetze benötigen vorhandenes NM-Profil; WPA2/DHCP und Kontentrennung in QEMU belegt; WPA3-/ARM64-Funkabnahme offen |
| Bluetooth | Eigene Seite, Suche, Codes/PIN/Passkey, Vertrauen/Entfernen, Dienstneustart | Zusätzliche virtuelle Controller-Abnahme; physischer Funk ist ausgeschlossen |
| WireGuard/Tailscale | Persönlicher libnm-Import und echte WG-Tunnel; offizieller TS-Status, eigene Aktionen und eingebettete Anmeldung | Persönliche TS-Anmeldung, TS-Tunnel und weitere Routing-Szenarien |
| Windows/KI | Persönliche Hosts, OpenSSH-Schlüssel/Trust, bestehender nativer psmux-/ConPTY-Adapter | Zusammenhängende Windows-11-Pro-Abnahme mit neuer Oberfläche und Anbieteranmeldungen |
| Antigravity | Offizielle Windows-CLI `agy`, eigene Einrichtungs-/Sitzungsseite und Installationsprüfung | Persönliche Installation, Anmeldung und tatsächliche Anbieteranfrage |
| Kanban | JSON und sechs Online-Anbieter einschließlich Gitea, Filter, Spalten, privater Offline-Cache | Persönliche Anbieterzugänge; weitere Gitea-Projekttypen |
| Browser | WebKit, HTTPS, Navigation, JavaScript, persönliches Profil, Abfragen, Downloads und Datei-/Mehrfachauswahl als Seiten | Weitere moderne Seiten-/Geräteberechtigungsabnahmen |
| RDP/Streaming | Integriertes RDW/IronRDP mit Zertifikat-Pin, echten Frames, Tastatur, Wiederverbindung und Abbruchbehandlung in Docker; Moonlight-Aufruf | Windows-NLA, zusätzliche Maus-/Clipboard-Abnahme, integriertes Streaming und Pi-Decoderpfad |
| Installation | ARM64-Binary, Paketprüfung, manuelle atomare Aktivierung, Reparatur/Rückwechsel | Native Pakete und HTTPS-Bootstrap implementiert; Freigabe des regulären nativen Releases offen |
| Image/Release | Gebauter nativer Kandidat, Lizenzen/Provenienz, QEMU-Boot und grafische PAM-Anmeldung mit zwei Konten | Reguläre native Release-Funktionsgleichheit |

## Fehler eingrenzen

**Host nicht erreichbar:** Aktives Profil, Hostadresse, SSH-Port und VPN prüfen.
Die Anzeige prüft nur TCP. „Erreichbar“ bestätigt weder Windows-Version noch
Benutzeranmeldung oder Anbieter-CLI. Der Laptop muss eingeschaltet sein.

**SSH lehnt den Host ab:** Den Ed25519-Fingerprint unabhängig auf Windows anzeigen
und vergleichen. Einen geänderten bestehenden Hosteintrag nicht blind löschen;
zuerst die Identität klären. Private Schlüssel gehören nicht in Fehlerberichte.

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
