# Native Architektur

Die verbindliche Anwendung ist Rust/GTK 4 unter Wayland mit labwc. `native/`
enthält Anwendung und Oberfläche. `client/` enthält den historischen Prototyp
und die weiterverwendeten Grafik-/Klangdateien. Frühere X11-Prüfungen zählen
nicht als Nachweise der neuen Laufzeit.

GTK übernimmt Formulare, Fokus, Eingabe und Layout. Cairo zeichnet ausschließlich
die Rampi-Kachelflächen; VTE und WebKitGTK liefern vorhandene Terminal- und
Browser-Engines. labwc übernimmt Displayserver, Fensterverwaltung und globale
Tastenkombinationen. Eine vollständige Desktopumgebung wird nicht installiert.
Die gemessene Softwarebaseline verwendet Cairo/Pixman, keine physische Pi-GPU.

## Zuständigkeiten und Vertrauensgrenzen

| Komponente | Rampi-Aufgabe | Verbindliche Systemautorität |
|---|---|---|
| `native/core` | Konfiguration, Validierung, Kanban, Startargumente, Bewegungsparameter | Dateirechte und aufgerufene Programme |
| `native/ui` | Eine GTK-Anwendung, Seitenwechsel, Status, Fehleranzeige | GTK/GLib und vorhandene Dienste |
| WLAN-Adapter | Netze, persönliche neue Profile, vorhandene Profile verwenden | NetworkManager und polkit |
| Bluetooth-Agent | Bewusster Vergleich, PIN/Passkey, Suchfreigabe | BlueZ und aktuelle eindeutige D-Bus-Dienstidentität |
| VPN-Adapter | libnm-Import und persönliche Auswahl; Tailscale-Status | NetworkManager/WireGuard beziehungsweise offizielle Tailscale-Software |
| SSH-Einrichtung | Schlüssel erzeugen und unabhängig geprüfte Fingerprints vergleichen | OpenSSH und Linux-Dateirechte |
| System-Einstellungen | Persönliche XKB-Datei und angebotene Bildschirmmodi | labwc und wlr-randr |
| Kontoaktionen | Eigenes Kennwort und bestätigte Abmeldung | passwd/PAM und systemd-Sitzungsaufsicht |
| Browserseiten | Webseitenabfragen, Downloadziel, Fortschritt und Abbruch | WebKitGTK, TLS-Prüfung und Benutzerentscheidung |
| Remote Desktop | Integrierte RDW-/IronRDP-Fläche, Zertifikat-Pin, Eingaben und Zwischenablage | Windows-Konto, TLS/RDP und unabhängiger Zertifikatsvergleich |

Rampi implementiert keine eigene Kontendatenbank, Kryptografie, Netzwerkprotokolle,
Terminal-/Browser-Engine oder allgemeine Dienstverwaltung. Das Dashboard öffnet
keine Listener. Seine kurze TCP-Prüfung bestätigt keine Windows-Anmeldung.

## Sitzung und Lebensdauer

Bei einem neuen Login startet greetd den vorhandenen Wayland-Greeter mit PAM auf
VT7. `rampi-session` startet anschließend labwc. In einer bereits vorhandenen
Wayland-Sitzung wird diese verwendet. `rampi-wayland-start` übernimmt die Umgebung
in den systemd-Benutzermanager und wartet auf `rampi.service`. Normales Beenden
beendet den Sitzungslauf; Fehler können über `Restart=on-failure` neu starten.
Linux-TTYs bleiben erhalten. Ein fremder Login-Dienst wird nicht ersetzt.
Grafischer greetd-/PAM-Durchlauf und persönliche Schlüsselbünde sind auf beiden Architekturen abgenommen.

Ein GTK-Stack enthält Dashboard, Einstellungen, Assistent, Kanban, Browser,
Terminals und Bestätigungsseiten. VTE und WebKit starten bei Bedarf. Seitenwechsel
beenden laufende Terminalprozesse nicht. RDP ist mit RDW/IronRDP in denselben GTK-Stack eingebettet. Die vollständige
Die Streaming-Seite integriert Moonlight-C und GStreamer in dasselbe GTK-Fenster;
persönliche Kopplungen verwenden den vorhandenen Secret Service. Alle blockierenden
Kopplungs-/Verbindungsoperationen laufen auf Arbeitsthreads. Direkte KI-Sitzungen sind entfernt.

Strg+Alt+Pos1 wird von labwc abgefangen. Der Starter aktiviert die einzelne
GTK-Anwendung und kehrt zum Dashboard zurück. Der reservierte Tastendruck
erreicht keine untergeordnete PTY. Escape bleibt in Terminal und Browser für
deren eigene Bedienung verfügbar; auf Rampi-Seiten ruft es die Abbruchaktion auf.

## Asynchronität und Isolation

GIO-D-Bus, Prozess-Pipes und Socketprüfungen verwenden GLib-Futures. Kanban-Dateien
werden außerhalb des GTK-Hauptthreads gelesen. Prozesse haben Zeit- und
Ausgabelimits; Aufrufe verwenden Argumentlisten statt Shellinterpolation.
Dashboard-Antworten prüfen das aktive Profil erneut. Eine verlassene SSH-Seite
wird durch eine späte Scanantwort nicht wieder geöffnet.

Eine eigene D-Bus-Verbindung besitzt die Bluetooth-Suche. Bei Seitenwechsel wird
sie freigegeben. Agent1 akzeptiert ausschließlich den aktuellen BlueZ-Absender.
Dienstwechsel verwerfen alte Anfragen samt PIN. Die begrenzte Wiederanmeldung
ist an die neue Dienstidentität gebunden und überbrückt deren Startphase.
Eine BlueZ-Abbruchmeldung löst keine Abbruchaktion gegen einen Nachfolgedienst aus.

Rampi läuft als gewöhnlicher Linux-Benutzer. Persönliche Konfigurationen erhalten
0700-Verzeichnisse und 0600-Dateien. Fehlerhafte bestehende Konfigurationen werden
nicht durch Standardwerte überschrieben. Neue WLAN-Profile erhalten eine
Benutzer-ACL; WireGuard verwendet nur eindeutig persönliche Profile. Routing,
Funkgeräte und Bluetooth bleiben dennoch Systemzustände, keine privaten Geräte.
Windows-Berechtigungen gelten davon unabhängig.

OpenSSH erzeugt Schlüssel und berechnet Fingerprints. Passphrasen bleiben in
seiner Terminalabfrage. Empfangenes Hostvertrauen verlangt einen unabhängig
erhaltenen SHA256-Wert; vorhandene Hosteinträge werden nicht ersetzt. WebKit
verwendet ein persönliches Profil, reguläre TLS-Prüfung und seine eingeschaltete
Sandbox. Downloads warten auf eine Zielentscheidung, erlauben kein Überschreiben
und öffnen Dateien nicht automatisch. Zusätzliche Geräteberechtigungen werden
in diesem Entwicklungsstand abgewiesen.

## Auslieferung

Installer bereiten Programm und Assets gemeinsam vor und aktivieren `current`
atomar. Rückwechsel prüfen Besitz, Rechte und Programmhash. Geräte führen keine
automatischen Updates aus. CI baut amd64/ARM64; der festgehaltene pi-gen-Weg
enthält Quellrevision, Programmhash, Paketmanifest und ursprüngliche Lizenzen.
QEMU prüft Boot und Diagnose, keine grafische Anmeldung oder GPU-Decodierung.
Reguläre Releases bleiben während der Portierung gesperrt.

[Entwicklung und Tests](NATIVE-DEVELOPMENT.de.md),
[Umfang und Fehlerhilfe](NATIVE-SUPPORT.de.md), [Konfiguration](CONFIGURATION.md),
[Betrieb](NATIVE-OPERATIONS.de.md), [Fortschrittsmaßstab](PROGRESS.md).

Die XKB-Einrichtung folgt der [labwc-Dokumentation](https://labwc.github.io/getting-started.html).
Downloads berücksichtigen die [WebKitGTK-6.0-Dateipfade](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/gtk/migrating-to-webkitgtk-6.0.md).

## Historische Architektur des Python-/QML-Prototyps

Die folgenden Entscheidungen beschreiben ausschließlich den früheren Stand.

Raspberry Pi OS Lite Trixie arm64 ist laut offizieller Kompatibilitätsliste für
Pi 3 B+ geeignet. Der 64-Bit-Stack vereinfacht die Verwendung gepflegter Qt-Pakete.
Die Entscheidung ist keine RAM-Messung. Die 1-GB-Zielgröße muss real geprüft werden.

LightDM übernimmt PAM, Linux-Konten, Xorg und die virtuelle Konsole. Openbox führt
Fensterwechsel und globale Tastenkombinationen aus. Rampi startet weder einen
eigenen Displayserver noch eine zweite Desktopumgebung. X11 wurde für den ersten
Stand wegen der vorhandenen FreeRDP-/VTE-/Chromium-Integration gewählt. Wayland
mit labwc bleibt eine mögliche Alternative nach Messung der Decoder- und
Shortcut-Kompatibilität. SDL wäre für ein reines Dashboard geeignet, würde aber
mehr eigene Formular-/Fokusintegration erfordern. GTK/VTE ist eine Alternative;
Qt Quick vereint portable Entwicklung und vorhandene Pfadanimationen.

Das unprivilegierte Python-Backend verwendet einen auf drei Threads begrenzten
Qt-Workerpool. Zeitbegrenzte Systemaufrufe und HTTP-Zugriffe blockieren keine
Animationen. Es gibt keinen lokalen HTTP-Server und keinen neuen Netzwerkport.
Qt Quick rendert die Oberfläche; native externe Anwendungen übernehmen die
ressourcenintensiven Module. xfce4-terminal verwendet die etablierte VTE-Engine.
Der aktuelle Stand steuert externe Fenster; er bettet sie nicht in Qt ein.

OpenSSH authentifiziert das persönliche Windows-Konto. Ein winziger
PowerShell-Adapter startet die offiziellen CLIs in einem vorhandenen nativen
psmux-Server mit ConPTY. Ein Rampi-eigener Sitzungsserver ist nicht notwendig.
Die Windows-Berechtigungen gelten weiterhin. Reattach verwendet denselben
Sitzungsnamen pro Anbieter und Benutzer; Projektwechsel für eine vorhandene
Sitzung erfordern bewusstes Beenden dieser Sitzung.

Quellen, geprüft 19.10.2026:
- https://www.raspberrypi.com/software/operating-systems/
- https://packages.debian.org/trixie/python3-pyside6.qtquick
- https://github.com/psmux/psmux
- https://github.com/RPi-Distro/pi-gen/tree/arm64
