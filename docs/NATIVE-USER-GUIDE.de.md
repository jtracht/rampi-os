# Rampi mit Rust und Wayland bedienen

Diese Anleitung gilt für den Entwicklungszweig mit `rampi-native`. Das veröffentlichte native
Entwicklungsrelease v0.6.0-dev.3 liegt diesem Zweig vorausgehend zugrunde. Neuere
Änderungen sind erst nach einem weiteren Release in dessen Image enthalten. Physische Hardwaretests sind auf Wunsch ausgeschlossen.

## Erster Start und Anmeldung

Die Sitzung verwendet labwc unter Wayland. Der System-Login übernimmt die
Authentifizierung über greetd und PAM; Rampi speichert kein eigenes Linux-Kennwort.
Grafische Anmeldung und erneute persönliche Schlüsselbund-Entsperrung sind
auf AMD64 und ARM64 mit zwei Konten softwareseitig abgenommen.
Der reguläre TTY-Zugang bleibt vorhanden.

Beim ersten Start erscheint die Einrichtung. **Weiter / Schritt überspringen**
speichert den aktuellen Schritt. **Später fortsetzen** öffnet das Dashboard,
ohne die Einrichtung als abgeschlossen zu markieren. Über **Einrichtung fortsetzen**
im Dashboard gelangst du zurück. **Einrichtung abschließen** ist am letzten Schritt
möglich und bestätigt deinen Durchlauf; Verbindungen werden dadurch nicht als
erfolgreich geprüft markiert.

Die zwölf Stationen zeigen auch fehlende Funktionen ausdrücklich an. Auf der
Systemseite kannst du Deutsch oder Englisch persönlich speichern. Die Oberfläche
übernimmt die Sprache nach erneutem Öffnen; die Sitzungs-Locale gilt ab der nächsten
Anmeldung. Die Kontenverwaltung verwendet Linux-Systemkonten.

## Dashboard und Navigation

Pfeil links/rechts wechselt zwischen den drei Hauptkacheln (Kanban, Remote Desktop und Browser), Enter öffnet das
Modul. Tab bewegt den Fokus zwischen Bedienelementen. Escape führt von einer
Bestätigungsseite zurück beziehungsweise zum Dashboard; aus einem während der
Einrichtung geöffneten Einstellungsbereich geht es zurück zur Einrichtung.
Strg+Alt+Pos1 ist für die Rückkehr zu Rampi reserviert und wird nicht an die
Terminal-PTY weitergegeben. Im Terminal und Browser bleibt Escape für deren eigene
Bedienung verfügbar; verwende dort Strg+Alt+Pos1 für das Dashboard.

WLAN und Bluetooth erscheinen jeweils einmal oben im Dashboard. Ein Klick führt
zur zugehörigen Einstellungsseite. Suche, Kennworteingabe, Kopplung und Bestätigungen bleiben
innerhalb desselben Rampi-Fensters. Bei Tastaturbedienung verschwindet der
Mauszeiger; Mausbewegung zeigt ihn wieder.

**Einstellungen** öffnet eine vertikale Kategorieübersicht im Stil eines
Konsolenmenüs. Pfeil hoch/runter wählt eine Kategorie, Enter öffnet ihre eigene
Seite. Es gibt keine Einstellungs-Tabs. **← Einstellungen** oder Escape führt
zur Übersicht zurück und merkt sich die zuletzt gewählte Kategorie; ein weiteres
Escape öffnet das Dashboard. Während der Ersteinrichtung führt Zurück direkt
zum aktuellen Einrichtungsschritt. Alle Bereiche bleiben im selben Fenster.

![Kategorieübersicht der nativen Rust-Anwendung](screenshots/settings-categories.png)

Tatsächliche Wayland-Aufnahme aus der isolierten Softwareprüfung. Die dort
fehlenden Bluetooth-Dienste betreffen nur diese Aufnahmeumgebung.

Unter **System** kannst du Bewegung reduzieren und Klickklänge abschalten.
Speichere die persönlichen Einstellungen mit der entsprechenden Schaltfläche.
Unter **Eigenes Linux-Kennwort ändern** fragt das offizielle passwd im eingebetteten
Terminal nach altem und neuem Kennwort. Rampi speichert diese Eingaben nicht.
**Weiteres Linux-Konto einrichten** führt durch Anlegen, Kennwort und erneute
Anmeldung. Gib einen neuen Namen ein und bestätige. Das vorhandene `sudo`
entscheidet anhand deiner bisherigen Rechte und fragt gegebenenfalls im
eingebetteten Terminal nach deinem Administratorkennwort. Rampi verändert keine
sudo-Regeln. Ohne diese Rechte scheitert die Aktion sichtbar.

`useradd` legt ein gewöhnliches Konto mit privatem Home-Verzeichnis an. Es erhält
keine Administratorrechte und zunächst kein nutzbares Kennwort. Erst nach Prüfung
von Systemidentität, Home-Besitz und Modus 0700 wird **Kennwort für das neue Konto
setzen** verfügbar. Das offizielle `passwd` fragt zweimal nach dem neuen Kennwort.
Vor dem Setzen werden Identität und Home-Rechte erneut geprüft. Vorhandene Konten,
fremde oder verlinkte Home-Verzeichnisse werden nicht übernommen oder umgeschrieben.
Bei einem teilweisen Systemfehler muss ein Administrator das gesperrte Konto über
die Systemkonsole prüfen. Es erfolgt keine automatische Löschung oder Rechteänderung.
Nach Erfolg kannst du weitere Konten vorbereiten oder dich regulär abmelden und
mit dem neuen Konto anmelden. Das Terminal bleibt mit seinem Ergebnis sichtbar;
ein Modulwechsel startet keinen zweiten Vorgang.

**Von Rampi abmelden** öffnet eine Bestätigungsseite. Lokale Anwendungen und
Verbindungen werden geschlossen; die Windows-Anmeldung wird dadurch nicht beendet.
Die Klangwiedergabe verwendet den vorhandenen Pulse-kompatiblen Audiodienst.

Auf derselben Systemseite eine persönliche Tastaturbelegung wählen und anwenden. Andere
persönliche Compositor-Einstellungen bleiben erhalten. Das Eingabefeld dient zum
sofortigen Prüfen; bei einer fremden Sitzung gilt die Datei gegebenenfalls erst
nach der nächsten Rampi-Anmeldung. Die Oberfläche bleibt derzeit deutsch.
**Bildschirme und Auflösungen anzeigen** zeigt die vom laufenden Wayland-System
angebotenen Modi. Eine Änderung muss innerhalb von 15 Sekunden bestätigt werden;
sonst erfolgt die Rücksetzung. Die Auflösung gilt bis zur Abmeldung.

## Persönliche Windows-Hosts

Unter **Host & SSH** kannst du mehrere Profile anlegen. Wähle einen vorhandenen
Eintrag oder **Neues Hostprofil**. Trage Profilname, Hostname/VPN-IP,
Windows-Benutzername, SSH-Port, den Pfad eines vorhandenen persönlichen
SSH-Schlüssels und die Streaming-Auflösung ein. Alte Projektwerte bleiben im Profil erhalten.

**Hostprofil speichern** validiert und speichert. **Ausgewählten Host verwenden**
setzt den Host für anschließend gestartete Verbindungen. Ein Wechsel der Auswahl
verwirft ungespeicherte Formularänderungen. Bereits laufende Terminals behalten
ihre bestehende Verbindung. **Entfernen vorbereiten** verlangt anschließend eine
Bestätigung; dabei werden weder Schlüsseldateien noch Daten auf Windows gelöscht.

Windows benötigt die bestehende Integration aus
[INSTALL-WINDOWS11.md](INSTALL-WINDOWS11.md). OpenSSH muss deinen persönlichen
Schlüssel akzeptieren. Der verifizierte Windows-Hostschlüssel muss bereits in
deiner persönlichen OpenSSH-Konfiguration bekannt sein. Rampi akzeptiert unbekannte
Hostschlüssel nicht automatisch.

Unterhalb der Hostprofile kannst du einen persönlichen Rampi-Schlüssel mit
OpenSSH erstellen. Die Passphrase wird im eingebetteten Terminal eingegeben.
Über **Schlüsselerstellung fortsetzen** kehrst du zum selben Prozess zurück;
vorhandene Schlüssel werden nicht überschrieben. **Rampi-Schlüssel in Formular
übernehmen** trägt den Pfad ein; anschließend das Hostprofil speichern.
Danach **Aktiven SSH-Schlüssel entsperren** wählen. OpenSSH fragt die Passphrase
im eingebetteten Terminal ab. **SSH-Entsperren fortsetzen** kehrt zum laufenden
Vorgang zurück. Nach Erfolg können auch die nichtinteraktiven Hostprüfungen den
Schlüssel verwenden. Die Sitzung verwendet einen erreichbaren persönlichen
OpenSSH-Agent weiter oder startet genau einen Agenten für diese Anmeldung.
Beim Abmelden endet ein von Rampi gestarteter Agent; ein zuvor vorhandener
Agent bleibt bestehen. Die Schlüsseldatei und ihre Passphrase werden dabei
nicht verändert. Nach einer neuen Anmeldung gegebenenfalls erneut entsperren.
**Öffentlichen Rampi-Schlüssel anzeigen** zeigt nur die öffentliche Datei zur
Übertragung in das persönliche Windows-Konto.

**Hostschlüssel des aktiven Profils prüfen** liest den Ed25519-Schlüssel mit
OpenSSH. Vergleiche den SHA256-Fingerabdruck direkt am Windows-Host oder über
einen anderen vertrauenswürdigen Kanal und gib diesen unabhängig geprüften
Wert ein. Rampi speichert nur bei Übereinstimmung. Ein bereits bekannter Host
wird nicht automatisch ersetzt. Dies ersetzt keine Windows-Anmeldung; die
Übertragung des öffentlichen Benutzerschlüssels bleibt ein ausdrücklicher Schritt.

Direkte KI-Module gehören seit der Produktänderung vom 26.10.2026 nicht mehr
zu Rampi. Es werden keine Anbieterprogramme installiert, gestartet oder verwaltet.

## WLAN und Bluetooth

Auf der WLAN-Seite sucht **WLANs suchen** über NetworkManager nach verfügbaren Netzen.
Wähle das Netz, trage bei Bedarf das Kennwort ein und verbinde dich.
Bestehende Profile werden wiederverwendet. Neue Profile werden deinem
Linux-Konto zugeordnet. Unternehmensnetze benötigen ein vorhandenes geeignetes
NetworkManager-Profil. Unter **Verstecktes WLAN verbinden** die verfügbaren Adapter
anzeigen, den Adapter wählen und die exakte SSID sowie WPA2 Personal, WPA3 Personal
oder ein offenes Netz angeben. Passende vorhandene Profile werden verwendet; bei
mehreren passenden Profilen verlangt Rampi zuerst eine Bereinigung.

Auf der Bluetooth-Seite wählst du Adapter und Gerät, startest die Suche und koppelst.
Die Suche wird beim Verlassen der Seite freigegeben. Ein Codevergleich verlangt
eine bewusste Bestätigung. PIN und Passkey werden verdeckt eingegeben und nach
Bestätigung oder Abbruch geleert. Vertrauen und entfernte Kopplungen wirken
geräteweit; beachte die Bestätigungsseite. Bei einem Dienstneustart verwirft Rampi
alte Kopplungsanfragen samt Eingaben und meldet seinen Agenten erneut an.

Die bisherigen Rust-Prüfungen verwenden isolierte D-Bus-Testdienste. Sie belegen
Bedienabläufe und Schnittstellen, keine tatsächliche Funkkopplung.

## VPN

WireGuard-Profile werden über die vorhandene libnm-Bibliothek importiert und
von NetworkManager gespeichert. Die Seite zeigt ausschließlich persönliche,
eindeutig deinem Konto zugeordnete Profile. Importierte Profile verbinden sich
nicht automatisch. Wähle das Profil und verbinde beziehungsweise trenne es.
Die ursprüngliche Konfigurationsdatei bleibt erhalten.

Tailscale bleibt im selben Einstellungsbereich: Status prüfen, **Tailscale verbinden**
wählen und die systemweite Änderung auf der Bestätigungsseite freigeben. Wenn
Anmeldung erforderlich ist, **Tailscale-Anmeldung öffnen** wählen. Die offizielle
Anmeldung erscheint in einer eigenen Rampi-Seite mit temporärem Browserprofil.
**Zurück zu VPN** verwirft diese Ansicht; anschließend den Status aktualisieren.
Eine angezeigte Anmeldeseite bestätigt noch keinen erfolgreichen Tunnel.

Ein Administrator muss das tatsächlich verwendete Linux-Konto einmalig als
Tailscale-Operator freigeben, beispielsweise bewusst mit
`sudo tailscale set --operator=BENUTZER`. Rampi erweitert diese Rechte nicht selbst
und setzt bestehende Tailscale-Optionen nicht zurück. Tailscale und seine Routen
wirken systemweit. Benutzerkonten des Anbieters werden von dessen Anmeldung geprüft.
Headscale und eigene Login-Server sind in diesem Anmeldeweg nicht vorgesehen.

## Kanban, Browser und Remote Desktop

Unter **Kanban & Browser** führt die Einrichtung durch **Quelle → Zugang → Prüfung**.
Eine lokale JSON-Datei sowie GitHub, Gitea, Trello, Jira, Asana oder Notion sind
verfügbar. [Quellenformate und Zugang einrichten](KANBAN-NATIVE.de.md).
Das Kanban-Modul bleibt schreibgeschützt. Suche sowie Projekt-, Prioritäts- und
Statusfilter lassen sich kombinieren. **Aufgaben neu laden** aktualisiert die
Quelle. Bei Fehlern erscheint der passende private Offline-Cache mit sichtbarem
Hinweis; ein Profilwechsel übernimmt keine Daten des vorherigen Boards.

Der Browser verwendet WebKitGTK mit persönlichem Profil. Er unterstützt
Adresszeile, zurück, vorwärts und neu laden. Unterstützte Webseitenabfragen
erscheinen als Rampi-Seite. HTTPS-Zertifikatsfehler werden abgewiesen. Navigationen verwenden HTTPS.
**Downloads** öffnet die integrierte Liste. Prüfe den vollständigen Zielpfad und
wähle **Download speichern** oder **Download abbrechen**. Vorhandene Dateien werden
nicht überschrieben und Dateien nicht automatisch geöffnet. Ohne Zielentscheidung
wird nach einer Minute abgebrochen; nach Abschluss lässt sich die Liste leeren.
Weitere moderne Webseiten und Geräteberechtigungen bleiben zu prüfen.

Beim Hochladen öffnet sich eine eigene **Dateien für die Webseite auswählen**-Seite.
Öffne Ordner mit Enter oder einem Doppelklick; über den Ordnerpfad kannst du
direkt wechseln. Markiere die gewünschten Dateien und bestätige **Auswählen**.
Wenn die Webseite mehrere Dateien erlaubt, funktioniert auch Strg+A in der Liste.
Der Dateitypfilter stammt von der Webseite; **Alle Dateitypen anzeigen** hebt ihn
für diese Auswahl auf. Versteckte Einträge bleiben ausgeblendet.
**Abbrechen**, Escape, Verlassen der Auswahl oder eine neue Navigation im Browser
verwerfen die ausstehende Anfrage. Ohne ausdrückliche Bestätigung bekommt die
Webseite keine neue Datei. Höchstens 128 lesbare lokale Dateien werden gemeinsam
übernommen; Ordner und Spezialdateien werden abgewiesen.

**Remote Desktop → RDP** öffnet die integrierte Windows-Desktop-Seite. Host und
Windows-Konto stammen aus dem aktiven persönlichen Profil. Gib den RDP-Port,
den unabhängig auf Windows geprüften SHA-256-Zertifikatfingerabdruck und dein
Windows-Kennwort ein. Der Fingerabdruck muss 64 Hex-Zeichen enthalten; Doppelpunkte
und Leerzeichen sind erlaubt. Das Kennwort wird nach dem Start aus dem Eingabefeld
entfernt und weder gespeichert noch als Prozessargument übergeben.

Der Fingerabdruck bezieht sich auf das tatsächliche RDP-Serverzertifikat,
**nicht auf den SSH-Hostschlüssel**. Auf Windows kann eine administrative
PowerShell den aktiven Zertifikatsbezug und dessen SHA-256 anzeigen:

```powershell
$rdp = Get-CimInstance -Namespace root/cimv2/TerminalServices -ClassName Win32_TSGeneralSetting -Filter "TerminalName='RDP-tcp'"
$certificate = Get-ChildItem 'Cert:\LocalMachine\Remote Desktop', 'Cert:\LocalMachine\My' |
    Where-Object Thumbprint -eq $rdp.SSLCertificateSHA1Hash | Select-Object -First 1
if (-not $certificate) { throw 'Aktives RDP-Zertifikat nicht gefunden.' }
$sha256 = [Security.Cryptography.SHA256]::Create()
try { ([BitConverter]::ToString($sha256.ComputeHash($certificate.RawData))).Replace('-', '').ToLowerInvariant() }
finally { $sha256.Dispose() }
```

Vergleiche diesen Wert über einen bereits vertrauenswürdigen Weg. Eine Abweichung
verhindert die Anmeldung; der angezeigte neue Wert wird nicht automatisch akzeptiert.
**← Dashboard** oder **Strg+Alt+Pos1** wechseln zurück und erhalten die Verbindung.
**Verbindung trennen** trennt RDP, ohne Windows abzumelden. Nach einem Netzabbruch
wird die Anmeldung wieder angeboten. Escape bleibt innerhalb der Desktopfläche
für den entfernten Rechner verfügbar. RDW stellt Maus und Tastatur bereit.
Textkopien aus Rampi und vom Host werden über die Zwischenablage in beide
Richtungen übertragen. Die Auflösung bleibt beim Verbinden fest; die Fläche wird lokal skaliert.

Die Softwareabnahme verwendet einen echten XRDP-Testserver. Eine native Windows-
11-Pro-/NLA-Abnahme ist noch offen; ein Windows-Testhost wird auf Nutzerwunsch nicht verwendet.

## Desktop-Streaming mit Sunshine

Im Remote-Modul **Desktop-Streaming · integriert** öffnen. Auf dem aktiven Host
muss Sunshine erreichbar sein. **Host neu koppeln** zeigt einen PIN direkt auf
der Rampi-Seite; diesen im Sunshine-Host bestätigen. Die bestätigte Identität
liegt im persönlichen Linux-Schlüsselbund, getrennt nach Host und Windows-Konto.
Eine andere Linux-Anmeldung verwendet ihren eigenen Schlüsselbund. Die Windowskennung
trennt die gespeicherten Profile. Sunshine gibt mit der bestätigten Kopplung seine
Host-Sitzung frei. Für eine gesonderte Windows-Kontoanmeldung steht RDP zur Verfügung. Private
Schlüssel werden nicht in die normale Konfiguration oder Befehlszeile geschrieben.

**Kopplung laden / Anwendungen aktualisieren** verwendet eine gespeicherte
Kopplung. Eine angebotene Anwendung in der eingebetteten Liste wählen und starten.
Das Bild bleibt im vorhandenen Rampi-Fenster; die Einrichtungsfelder werden während
der Verbindung ausgeblendet. Das aktuelle Profil verwendet H.264, 30 Bilder pro Sekunde und Stereo. Die
Auflösung stammt aus dem aktiven Hostprofil; unterstützt werden gerade Größen bis
1920×1080. Der Standard 1280×720 ist die im Ressourcenlauf geprüfte Variante. GStreamer wählt vorhandene Decoder. Mauspositionen
berücksichtigen die lokale Skalierung und Bildränder; beide Scrollachsen und
Tastaturereignisse werden über Moonlight übertragen.

**Stream trennen** stoppt die Verbindung und zeigt die Auswahl erneut. Sunshine
und die entfernte Anwendung werden dadurch nicht beendet. **Strg+Alt+Pos1**
kehrt zum Dashboard zurück und beendet den Stream. Escape und Tab bleiben bei
fokussierter Desktopfläche für den entfernten Rechner verfügbar. Nach einem
Netzabbruch die Kopplung erneut laden und verbinden. Rampi akzeptiert keinen
geänderten gespeicherten Sunshine-Schlüssel stillschweigend; gegebenenfalls den
Host unabhängig prüfen und ausdrücklich neu koppeln.

Ist der persönliche Schlüsselbund gesperrt, mit der normalen PAM-Anmeldung
entsperren; Rampi öffnet keinen zusätzlichen Entsperrdialog. Eine fehlende oder
inkompatible Moonlight-C-Bibliothek wird als Fehler angezeigt. Der native Installer
verwendet vorhandene kompatible Bibliotheken oder baut nur die offizielle
Bibliothek; ein zusätzlicher Player oder Display-Server ist nicht nötig.
Softwareprüfungen verwenden einen isolierten Sunshine-Server. Windows-NLA,
physische Funk-/Videoeigenschaften und der Decoderpfad eines echten Pi sind damit
nicht nachgewiesen.

## Diagnose und persönliche Daten

Im Browser fokussiert **Strg+L** die Adressleiste, **F5** lädt die Seite neu.
**Vollbild · F11** oder **F11** blenden die Browserleiste aus; **Escape** bringt
sie zurück. Auch das Vollbild einer Webseite bleibt im vorhandenen Rampi-Fenster.
Beim Verlassen bleibt die Rampi-Sitzung selbst im Vollbild.
Cookies mit Ablaufdatum, lokale Seitendaten und IndexedDB-Daten bleiben nach
einem Neustart im persönlichen Browserprofil erhalten. Ein anderes Linux-Konto
erhält ein eigenes, leeres Profil und kann die privaten Profildateien nicht lesen.

**Diagnose** prüft lokal das Linux-Konto, Hostprofile, verfügbare Programme und
die Erreichbarkeit der Systemdienste. Sie verändert keine Netzwerkeinstellungen
und prüft keine Windows-Anmeldung oder Anbieterzugänge.

Persönliche Einstellungen liegen unter `~/.config/rampi/settings.json`, mit
privatem Verzeichnis und Dateirechten. Der Browser verwendet ein separates
persönliches Profil. Kennwörter gehören nicht in Hostprofile oder Kanban-Dateien.
Installer und Versionswechsel übernehmen keine fremden Benutzerprofile.

Installation und Wiederherstellung: [NATIVE-OPERATIONS.de.md](NATIVE-OPERATIONS.de.md).
