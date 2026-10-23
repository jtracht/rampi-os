# Entwicklungsfortschritt

Aktueller Gesamtstand unter der neuen Rust-/Wayland-Vorgabe: **ca. 64 %**.
Rust-Umstellung: **ca. 62 %** (separate Portierungsschätzung).
Der zuvor belegte Python-/QML-Stand lag bei ca. 75 %; Baseline v0.3.0: ca. 69 %.
Das Ziel von mindestens 85 % bleibt offen. Der Architekturwechsel erfordert neue
Implementierungen und Nachweise; frühere QML-/X11-Prüfungen zählen dafür nicht.

| Bereich | Rust-Stand / 5 |
|---|---:|
| Grafische Sitzung und Dashboard | 4 |
| Tastatur und Maus | 3 |
| Setup-Assistent | 3 |
| Linux-Konten und Login | 2 |
| WLAN | 3 |
| Bluetooth | 3 |
| VPN | 3 |
| Windows-Host und Persistenz | 4 |
| Anbieter-CLIs | 3 |
| Remote Desktop und Streaming | 2 |
| Kanban | 3 |
| Browser | 3 |
| Installer und Reparatur | 4 |
| Sicherheit und Isolation | 4 |
| Design und Branding | 3 |
| GitHub und CI/CD | 4 |
| Systemimage | 3 |
| Manuelle Updates | 4 |
| Dokumentation | 3 |
| Performance | 3 |
| **Summe** | **64 / 100** |

Dashboard erreicht vier Punkte durch tatsächliche Dienstzustände, aktuelle Uhrzeit,
Profilwechsel und getrennte Anzeigen für TCP-Erreichbarkeit und ungeprüfte Anmeldung.
Die GTK-Abnahme prüft Live-Änderungen und die direkten Wege zu den Einstellungen.

WLAN erreicht drei Punkte: Neben sichtbaren Netzen sind versteckte SSIDs mit
Adapterauswahl und WPA2/WPA3 beziehungsweise offenem Netz integriert. Passende
Profile werden wiederverwendet; Mehrdeutigkeit und ungültige Eingaben werden
abgewiesen. Die Rust-/GIO-Abnahme prüft die tatsächlichen D-Bus-Aufrufe einschließlich
privater Profilrechte, nicht den Funkverkehr.

Der Assistent erreicht drei Punkte durch integrierte SSH-Einrichtung und persönliche
Tastatur-/Bildschirmeinstellungen. Tastaturänderungen erhalten andere Einstellungen
und verwenden labwc; angebotene Bildschirmmodi verwenden wlr-randr, einschließlich
15-Sekunden-Bestätigung und Rücksetzung. Die tatsächliche Headless-Wayland-Abnahme
prüft diese Abläufe mit dem angebotenen Modus, keine HDMI- oder physische XKB-Eingabe.
Sprachwechsel und weitere Einrichtungsschritte bleiben offen.

Sicherheit und Isolation erreichen vier Punkte durch die eigene SSH-Einrichtung
mit tatsächlichem OpenSSH: passphrasegeschützte Schlüsselerstellung im eingebetteten
Terminal, Wiederaufnahme derselben Erstellung statt paralleler Prozesse und
Hostschlüsselimport nur nach Abgleich eines unabhängig erhaltenen Fingerabdrucks.
Falsche Fingerabdrücke, vorhandene Schlüssel und bestehende Hosteinträge sind
geschützt. Ein tatsächlicher isolierter OpenSSH-Server sowie GTK-/VTE-Abläufe
prüfen diesen Ablauf; die vollständige lokale Abnahme bleibt erfolgreich.

Systemimage erreicht drei Punkte: Ein tatsächliches flashbares Trixie-/ARM64-Image
mit vorgebautem Rust-Programm, Wayland-Sitzung, Paketmanifest und ursprünglichen
Rust-/Distributionslizenzen ist gebaut. Partitionen und Dateisysteme sind geprüft;
QEMU startet den Pi-Kernel mit 1 GiB bis zur Diagnose des nativen Programms.
Das heruntergeladene Image stimmt mit seiner SHA256-Prüfsumme überein.
Die grafische Anmeldung und vollständige native Release-Funktionsgleichheit
bleiben offen; es handelt sich um einen Entwicklungskandidaten, kein reguläres Release.
Nachweis: [Image, Prüfsummen und QEMU-Abnahmen](validation/rust-image-2026-10-23.md).

Installer und Reparatur erreichen vier Punkte: Der tatsächliche ARM64-Installer
ist mit echten Trixie-Paketen, gewöhnlichem Quellbesitz, rootgeschützten
Programmdateien, wiederholter Installation ohne Überschreiben laufender Dateien,
atomarem Versionswechsel, Rückwechsel, abgewiesenen ungültigen/veränderten
Programmen und Deinstallation geprüft. Persönliche Daten bleiben unverändert;
ein fremder Login-Dienst bleibt erhalten. Die vollständige grafische PAM-Anmeldung
und der allgemeine native Release-Bootstrap bleiben offen.
Nachweis: [native CI-Abnahme](validation/rust-native-2026-10-23.md).

Performance erreicht drei Punkte durch einen tatsächlichen Wayland-Lauf mit
600 überprüften Seitenwechseln über mehr als drei Minuten, drei VTE-Terminals,
lokalem WebKit-Inhalt, gezeichneten Frames, Start-/Wechsellatenz, Prozess-CPU,
Speicherverlauf nach der Aufwärmphase und einer Phase mit reduzierter Bewegung.
Die vollständige lokale Abnahme bleibt unter dem Containerlimit von 1 GiB.
Das ist eine Software-Baseline mit labwc/Pixman und Cairo, keine Messung auf
einem physischen Raspberry Pi und keine längere Arbeitslast mit echten KI-/Remote-Sitzungen.

Dokumentation erreicht drei Punkte durch die vollständige Anleitung für die
gegenwärtigen nativen Bedienabläufe und die gesonderte Betriebsanleitung für
Installation, manuelle Updates, Reparatur, Versionswechsel und Deinstallation.
Beide benennen die noch fehlenden Funktionen ausdrücklich:
[Bedienung](NATIVE-USER-GUIDE.de.md), [Betrieb](NATIVE-OPERATIONS.de.md).

Bluetooth erreicht drei Punkte durch die tatsächliche Rust-Agent1-Abnahme für
bewussten Codevergleich, PIN und Passkey, Abbruch mit gelöschter Eingabe sowie
Abweisung fremder D-Bus-Absender. Die Prüfung verwendet einen privaten
BlueZ-Testdienst; Funkkopplung und erneute Agentregistrierung nach einem
Dienstneustart sind damit nicht nachgewiesen.

Der Rust-Assistent speichert den aktuellen Schritt, kann unterbrochen und
fortgesetzt werden und nutzt die vorhandenen Einstellungsseiten. Die tatsächliche
GTK-Abnahme prüft Navigation, Speichern, Überspringen, Abschluss, lokale Diagnose
und mehrere Hostprofile einschließlich Aktivierung, ungültiger Eingaben und
bestätigtem Entfernen. Nicht portierte Einrichtungsschritte sind ausdrücklich
gekennzeichnet; der Assistent erreicht deshalb drei von fünf Punkten.

VPN erhält einen zusätzlichen Punkt für die eigene Rust-WireGuard-Seite mit
persönlicher Profilauswahl, Status, Import, Verbinden und Trennen. Die tatsächliche
GTK-Seite ist gegen eine isolierte NetworkManager-Fixture geprüft. Zusätzlich
importiert und aktiviert derselbe Rust-Adapter zwei echte WireGuard-Gegenstellen
mit NetworkManager: verschlüsselter Verkehr, falscher Schlüssel, Trennen und
Linux-Benutzerisolation sind lokal nachgewiesen. Die vollständige grafische
Tailscale-Einrichtung und weitere VPN-Abläufe bleiben offen.

Kanban erhält einen zusätzlichen Punkt für die lokale Rust-Oberfläche mit
sofortigem Laden, kombinierter Suche und Projekt-/Prioritäts-/Statusfiltern,
konfigurierbarer Spaltenreihenfolge, begrenztem initialem Kartenaufbau mit
Nachladen sowie Erhalt geladener Aufgaben bei Quellfehlern. Der tatsächliche
GTK-Test prüft Filter, erneutes Laden und unveränderte Quelldaten. Die sechs
geforderten Datenquellen sind damit noch nicht vollständig portiert.

Nachweise und Grenzen: [Rust-Migration](RUST-MIGRATION.md).
Die eigene Tailscale-Statusanzeige ist zusätzlich mit offizieller CLI und einem
isolierten Dienst geprüft. Das erhöht den Gesamtwert noch nicht: Kontoanmeldung,
grafische Einrichtung und tatsächlicher Tailscale-Tunnelverkehr bleiben offen.
Die folgenden Tabellen dokumentieren den bisherigen Python-/QML-Stand.

Die Zahl bewertet den gesamten Masterprompt, einschließlich Integration,
Bedienung und Nachweisen. Sie ist eine transparente Planungsschätzung, keine
Messung der verbleibenden Arbeitszeit und keine Aussage, dass ein erfolgreich
veröffentlichter Entwicklungsstand schon sämtliche Anforderungen erfüllt.
Physische Hardwaretests sind auf Nutzerwunsch ausgeschlossen und gehören nicht
zum Nenner. Windows- und Anbieterprüfungen werden dadurch nicht automatisch erfüllt.

20 Bereiche erhalten jeweils bis zu fünf Punkte: 0 = fehlt, 1 = Grundlage,
2 = teilweise implementiert, 3 = wesentliche Funktionen vorhanden, 4 = weitgehend
umgesetzt und softwaregeprüft, 5 = vollständiger vereinbarter Umfang einschließlich
Nachweisen und Dokumentation. Die Summe ergibt den geschätzten Prozentwert.
Punkte steigen durch belegte Funktionen und Prüfungen, nicht durch
Wartezeit, Commits, Testanzahl oder bloßen Release-Erfolg.

| Bereich | Baseline / 5 | Wesentliche verbleibende Arbeit |
|---|---:|---|
| Grafische Sitzung und Dashboard | 4 | Gesamtabnahme aller Module und Offline-Wechsel |
| Tastatur und Maus | 4 | Durchgängige Eingabeprüfung auch in echten Remote-Clients |
| Setup-Assistent | 3 | Einheitliche eigene Einrichtung statt mehrerer Systemdialoge |
| Linux-Konten und Login | 4 | Vollständige grafische Anmelde-/Abmeldeabnahme |
| WLAN | 2 | Eigene Netzwerkauswahl, sichere Kennworteingabe und Dienstprüfung |
| Bluetooth | 2 | Eigene Pairing-Oberfläche und softwareseitige BlueZ-Abnahme |
| VPN | 3 | Grafische persönliche Profilauswahl und Tailscale-Abnahme |
| Windows-Host und Persistenz | 4 | Zusammenhängende Windows-11-Pro-Abnahme |
| Anbieter-CLIs | 3 | Persönliche Anmeldungen, native Anbieterabläufe und Antigravity-Einrichtung |
| Remote Desktop und Streaming | 3 | Streaming-Audio/-Eingabe sowie Windows-NLA/-Aufnahme prüfen |
| Kanban | 3 | Grafische Spaltenkonfiguration, getrennte Filter, echte Anbieterabnahmen |
| Browser | 4 | Moderne Seiten, Downloads und Ressourcenbedarf im Gesamtsystem prüfen |
| Installer und Reparatur | 4 | Weitere Wiederholungs-, Fehler- und Reparaturpfade abnehmen |
| Sicherheit und Isolation | 4 | Abschließende Prüfung über die kombinierten Benutzerabläufe |
| Design und Branding | 4 | Gesamtabgleich aller Ansichten und technischen Logo-Varianten |
| GitHub und CI/CD | 5 | Automatische Prüfungen, Tags und vollständige Releases nachgewiesen |
| Systemimage | 4 | Paketquellen für reproduzierbare Builds festhalten |
| Manuelle Updates | 5 | Versionierte manuelle Installer; keine Geräte-Autoupdates |
| Dokumentation | 3 | Einstellungen, Abläufe und Nachweise vollständig fortschreiben |
| Performance | 1 | Längere Gesamtlast unter 1 GB, CPU-/Start-/Wechsel-/Animationsmessungen |
| **Summe** | **69 / 100** | **Baseline: ca. 69 %** |

Quellen: [vollständige Anforderungen](REQUIREMENTS.de.md),
[Implementierungsstand](STATUS.md), [Tests und Grenzen](TESTING.md),
[vereinbarter Abnahmeumfang](VALIDATION-SCOPE.md).

Belegte Erweiterungen gegenüber der Baseline:

| Bereich | Neuer Punktestand | Nachweis |
|---|---:|---|
| VPN | 4 / 5 | Eigene grafische Auswahl; offizielle D-Bus-Metadaten mit aktivem Zustand; gemeinsame/fremde Profile ausgeschlossen; UID statt Umgebungsvariablen bestimmt das Systemkonto |
| Remote Desktop und Streaming | 4 / 5 | Echter 997-Hz-Testton über Sunshine/PulseAudio, Opus und Moonlight/SDL empfangen; erneute Verbindung; Stille und falscher Ton werden abgewiesen |
| Kanban | 4 / 5 | Spaltenreihenfolge gespeichert; unabhängige Projekt-/Prioritäts-/Statusfilter mit Suche; tatsächliche QML-Tastaturtests und JSON-Neuladen |
| WLAN | 4 / 5 | Eigene Oberfläche; tatsächliche WPA2-Anmeldung, DHCP, IP-Rundlauf, falsches Kennwort und Wiederverbindung mit NetworkManager/hostapd/supplicant auf virtuellen hwsim-Radios; ARM64-Gesamtabnahme noch offen |
| Bluetooth | 3 / 5 | Eigene Geräte- und Kopplungsoberfläche; verifizierter BlueZ-Aufrufer; PIN/Passkey, Bestätigung, Geräteaktionen und Dienstneustart über tatsächliches QML/GIO mit D-Bus-Fixture; echte virtuelle HCI-Kopplung noch offen |

Damit **75 / 100 Punkte**, entsprechend **ca. 75 %**. Lokale Prüfungen sind bestanden;
die Änderungen durchlaufen zusätzlich die vollständige CI und einen frischen
Release-Image-Build. Die verbleibenden Punkte in der Baseline bleiben offen.
