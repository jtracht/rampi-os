# Gemeinsamer Entwicklungsstand für die Komplettversion

Arbeitszweig: `codex/complete-native-release`, Ausgangspunkt `abade32`.
Dies ist eine Entwicklungsnotiz und keine Freigabe oder Abnahme eines neuen
Releases. Der belegte Gesamtstand bleibt **85/95 = 89,5 %**. Die beiden
veröffentlichten Entwicklungsreleases werden nicht überschrieben.

## Implementiert und lokal als Komponente geprüft

- RDP übernimmt die persönliche Auflösung und XKB-Tastaturbelegung. Ein
  `DOMÄNE\Benutzer` wird an die bestehenden IronRDP-/SSPI-Schnittstellen übergeben.
  TLS, geprüfter Zertifikatsfingerabdruck und CredSSP bleiben verpflichtend.
- Die tatsächliche Rampi-Verbindungsseite hat gegen den bestehenden
  FreeRDP-/WinPR-Server im isolierten Linux-Container mit ausschließlich NLA
  bestanden: falsches Zertifikat, falsches Kennwort und unbekanntes Konto werden
  abgewiesen; das gültige Domänenkonto liefert 1280 × 720 Bildpunkte und nach
  beiden Anmeldungen tatsächlich am Server empfangene Tastatureingaben.
  Kein Windows-Testhost wurde verwendet.
- Gitea-Organisationsprojekte und persönliche Projekte ergänzen Repository-
  Projekte. Die echte Gitea-Version 28.2.0 hat alle drei Bereiche mit privaten
  Projekten, nur lesendem Token, erhaltenen leeren Spalten, persönlichem
  Schlüsselbund, Aktualisierung und Offline-Cache bestanden. Schreibversuche
  des Lesetokens werden mit HTTP 403 abgewiesen.
- GStreamer liefert den Namen seines tatsächlich verwendeten H.264-Decoders.
  Der echte H.264-/Opus-Rundlauf samt Abbau und Neuerstellung prüft diese Angabe.
  Das ist kein Nachweis einer physischen Pi-Videobeschleunigung.

Die NLA- und Gitea-Komponentenprüfungen sind an denselben ausgeführten
Programmprüfwert `61537fb597d65ecb27a4c6f56a4368732e1bdb4eea521a7500b277be96095197`
gebunden. Sie stammen aus dem noch bearbeiteten Entwicklungsstand und ersetzen
keine erneute Abnahme der endgültigen Quellrevision.

Weitere lokale Prüfungen: 292 Python-Tests bestanden, elf umgebungsabhängige
Tests übersprungen; 21 Rust-Kerntests, nativer Build, Clippy für alle Ziele und
ShellCheck bestanden. Frühere fehlgeschlagene NLA-/Gitea-Testaufbauten bleiben
als lokale Diagnose erhalten und zählen nicht als erfolgreiche Abnahme.

## Erststart: Korrektur eingebaut, echte Image-Abnahme noch offen

Das Image bootet zunächst in die originale Raspberry-Pi-Benutzereinrichtung.
Ein kleiner systemd-Abschlussdienst schaltet die grafische Anmeldung erst frei,
wenn der originale Dienst beendet und das erste Konto mit eigenem Kennwort
anmeldbar ist. Es wird kein Standardkennwort eingeführt. Der Installer auf
bereits eingerichteten Geräten ändert diesen Ablauf nicht.

Die Image-Prüfung startet ohne vorbereitete Konten. QEMU tippt ausschließlich
kurzlebige Testdaten in den originalen Konsolendialog. Danach muss genau dieses
Kennwort über greetd/PAM eine sichtbare native Sitzung unter UID 1000 öffnen.
Erst anschließend folgen die vorhandenen Zwei-Konten-/Schlüsselbundtests.
Programmdateien müssen unverändert bleiben. Vorbereitete Konten allein werden
vom strengeren Prüfer ausdrücklich zurückgewiesen. Dieser neue vollständige
Image-Durchlauf wurde inzwischen ausgeführt: Der frische ARM64/pi-gen-Bau auf
`c52c6f75d1ffad4f9aa018df4e9e1f5a9eff3684` war erfolgreich, die grafische
Erststartprüfung blieb nach der ersten Tastaturfrage stehen. Das ist ausdrücklich
keine Image-Abnahme. Der unveränderte komprimierte Kandidat hat SHA256
`7c30d47509abed139e4fabaf69351b335846a73041e1255754fe86b67e5b12db`, sein
Programm SHA256 `34ab0a711a824552d34d982dc1bbb62783b490f5627bb945a3da5a39c9d3afba`.
Ein separater Prüflauf verwendet ausschließlich eine Wegwerfkopie dieses Images
und protokolliert Konsolendaten nur vor jeder Anforderung von Zugangsdaten.
Der endgültige Release benötigt weiterhin einen neuen vollständigen Imagebau.

Der vorherige Bau stoppte korrekt an fehlenden Lizenzdateien zweier Fluent-
Abhängigkeiten. Die unveränderten Apache-/MIT-Lizenztexte stammen jetzt aus den
exakten, in den Crates dokumentierten Upstream-Revisionen; der reguläre Sammler
prüft ihre Herkunft. Die vollständige lokale Sammlung für 450 Linux-Abhängigkeiten
besteht. Es wurde keine Lizenzprüfung ausgenommen.

Zusätzlich haben zwei offizielle Tailscale-Daemons in einer isolierten Docker-
Umgebung über einen echten Kernel-Tunnel in beide Richtungen ICMP-Pakete
übertragen. Der Test verwendet einen privaten Headscale-Koordinator und beweist
keine öffentliche Anbieteranmeldung. Trennen, Wiederverbinden, Zugriffssperre für
eine fremde UID, unveränderte Hauptrouten sowie unveränderte DNS-, Hostnamen-,
Operator- und Routingpräferenzen sind inzwischen lokal bestanden. Tatsächlich
getestetes Programm: `3b2d7d595fb7f126bb7c8c3034fd2923e6f31be4d8f64a848522e94a885741ff`;
Komponentenbeleg unter `artifacts/complete-tailscale-receipts`; der strenge Prüfer
hat auch die tatsächlichen Ping-Ausgaben vor/nach Trennung und die explizite
Zugriffsverweigerung des offiziellen Daemons bestätigt.
Der Test fand einen echten Fehler: `tailscale up` mit zusätzlichen JSON-/Timeout-
Optionen verlangt vorhandene Sondereinstellungen erneut. Der vorhandene,
parameterlose Wiederverbindungsaufruf erhält sie, während Rampi weiterhin eine
Prozessfrist erzwingt. Erste Anmeldung und neue Profile benötigen die persönliche
Operatorfreigabe am tatsächlich angemeldeten Profil; ein eingebetteter Terminal-
Schritt verwendet dafür die vorhandene sudo-Authentifizierung.
Die lokale Bedienabnahme dieses Einrichtungsschritts besteht inzwischen ebenfalls:
Der originale sudo-Prozess im tatsächlichen VTE-Terminal weist ein falsches
Kennwort ab, nimmt erst an seiner zweiten Abfrage das richtige entgegen und setzt
die Operatorfreigabe im echten angemeldeten Profil. Das Kennwort erscheint nicht
im Terminal; die Anwendung kehrt in demselben Fenster zur Einstellungsseite
zurück. Anschließend bestehen fremde UID-Sperre, Verkehr, Trennung und
Wiederverbindung weiterhin. Beleg: `artifacts/complete-tailscale-operator-pam-ready`,
Programm `892e28a7a5a3eaf9c044ba6bc636eee5ae8eafc14c3b1c97c5b9815af86149a7`.
Der Prüfer verlangt beide tatsächlichen sudo-/PAM-Quittungen zusätzlich zu den
Netzwerkbelegen und gleichem Programmhash. Die Abnahme des endgültigen
Programmstands auf beiden Architekturen steht noch aus. Daher kein zusätzlicher
Fortschrittspunkt.

Die Tailscale-Seite einschließlich Zustandsmeldungen, Anmeldeseite, Operator-
Einrichtung und allgemeiner Bestätigungsaktionen verwendet jetzt beide Fluent-
Kataloge. Der tatsächliche englische GTK-Test öffnet die Berechtigungsseite und
bricht sie wieder ab; es bleibt bei einem Fenster. Der bisherige deutsche Test
prüft weiterhin Status, Bestätigung, eingebettete Anmeldung und Trennung.
Nachweis: `artifacts/complete-vpn-language-ui-fixed.log`. Dieser Sprachtest ist
keine Anbieteranmeldung; die tatsächliche sudo-Kennworteingabe ist separat im
oben genannten privaten Tunneltest abgenommen.

Die erste vollständige native CI dieses Entwicklungszweigs (`40413505616`,
Quelle `8a04e51`) ist noch fehlgeschlagen: AMD64 verglich den Bluetooth-Zähler
ohne die unsichtbaren Fluent-Isolationszeichen. Der korrigierte Vergleich erhält
die Zeichen in der Oberfläche und besteht lokal. ARM64 bestand den tatsächlichen
zehnminütigen Bild-/Ton-Dauerlauf, aber die erforderlichen R-Tastenquittungen
fehlten auf dem Sunshine-Server. Der lokale Gegentest empfängt und überträgt R
und Enter auf beiden Verbindungen; das ist keine ARM64-Abnahme. Zusätzliche
GTK-Tastencodes und öffentliche serverseitige Tastenanzahlen werden deshalb
als Diagnose aufgezeichnet. Die unveränderten Ende-zu-Ende-Eingabegates bleiben
verbindlich.

Der zweite Erststart-Diagnoselauf (`40415182410`) hat gezeigt, dass der bisherige
QMP-Befehl quittiert wurde, aber evtest im Linux-Gast keinerlei Tastendruck sah.
Der Test verwendet nun die regulären direkten QMP-Tastenereignisse mit getrenntem
Drücken und Loslassen. Das ist noch kein erfolgreicher Erststartnachweis.
Der originale Systemdialog, PAM und alle installierten Programmdateien bleiben
unverändert; die Eingabediagnose endet vor jeder Zugangsdatenanforderung.

Die Erstkontoprüfung wurde zusätzlich auf den tatsächlichen Rust-Schlüsselbund-
Adapter und eine zweite echte PAM-Anmeldung erweitert. Das ursprüngliche Konto
existiert bereits vor der Installation der Vorlagen unter `/etc/skel`; deshalb
genügen die zwei später angelegten Konten hierfür nicht. Diese strengere
Erstkontoabnahme ist noch offen. Der Eingabeprüfer wartet nun außerdem auf die
tatsächliche Bereitschaft von evtest, bevor er den ersten Tastendruck anfordert.

Die Release-Verpackung übernimmt jetzt ausdrücklich Erstkonto-JSON und sichtbares
Erstkonto-PNG in das Belegarchiv. Ein gemeinsamer Prüfer verlangt genau die neun
freigegebenen regulären Dateien, begrenzte Größen, keine zusätzlichen privaten
Dateien oder Verweise und prüft die entpackten Nachweise erneut gegen Quelle,
Image und Programm. Die sieben zusätzlichen Archivtests verwenden synthetische
Dateien ausschließlich als Format-/Ablehnungsfälle und zählen nicht als Anmeldung.

Die vollständige native CI `40419411752` der Quelle
`22a0b266feab4611f86d962c9618bee9f0eba5dc` besteht auf AMD64 und ARM64.
Heruntergeladene native, grafische Login-, Funkgeräte- und Paketnachweise wurden
mit den Prüfern genau dieser Quelle unabhängig kontrolliert, einschließlich aller
sieben Paketprüfsummen. Lokaler Nachweis:
`artifacts/complete-native-22a/accepted.json`. Das ist keine frische Image-Abnahme
und keine Freigabe der Komplettversion.

Auch der direkte QMP-Eingabelauf `40419408169` hat die Ersteinrichtung nicht
bestanden. Der nächste Test verwendet deshalb das bestehende Debian-Werkzeug
ydotool und das vorhandene Linux-uinput-Modul ausschließlich in der wegwerfbaren
Gastkopie. Der originale Benutzerassistent, PAM und die installierten Rampi-
Programme bleiben erhalten. Das Werkzeug wird aus dem signierten Debian-
Backports-Repository ergänzt; vorhandene Paketversionen dürfen sich nicht ändern.
Es ist weder eine Produktinstallation noch ein Nachweis des USB-Tastaturwegs.
Der Nachweis bezeichnet den Eingabeweg ausdrücklich als Kernel-uinput und USB
als ungeprüft. evtest muss echte Enter-Drück-/Loslassereignisse empfangen und
vor jeder Zugangsdaten-Eingabe beendet werden. Nur dieses öffentliche,
zugangsdatenfreie Eingabeprotokoll ergänzt das Belegarchiv als neunte Datei.
Die Erstkonto-Anmeldung und dessen persönlicher Schlüsselbund nach erneuter
PAM-Anmeldung bleiben verpflichtend und sind weiterhin offen.

## Noch vor der Komplettversion

1. Den unveränderten Erststart im frisch gebauten Image und den folgenden
   normalen Neustart sowie den offiziell vorab eingerichteten Kontoablauf prüfen.
2. Die vollständige deutsch-/englische Oberfläche fertigstellen. Fluent,
   persönliche Sprachauswahl, Sitzungs-Locale, Dashboardnavigation und
   Einrichtungsbeschreibungen sind integriert; weitere Seiten und Fehlermeldungen
   sind noch nicht vollständig übersetzt.
3. Echte virtuelle Bluetooth-Tastatur und -Maus einschließlich Wiederverbindung
   abnehmen. Die lokale private Tailscale-Tunnel-/PAM-Abnahme muss auf der
   endgültigen Quelle beider Architekturen bestehen. Ein integrierter manueller
   Installationspfad für eine fehlende offizielle Tailscale-Installation ist
   ebenfalls noch nötig; das aktuelle native Image enthält diesen Dienst nicht.
4. Die übrigen Decoder-, Eingabe-, Isolations- und Bedienungsgrenzen der
   unveränderten Fortschrittsskala schließen und dokumentieren.
5. Auf der endgültigen Quelle sämtliche AMD64-/ARM64-Prüfungen, grafischen
   Kontentests und Dauerläufe durchführen, Fehler beheben und anschließend das
   frische Image einschließlich sämtlicher Quellen, Lizenzen und Prüfsummen
   veröffentlichen und unabhängig herunterladen/prüfen. Die Veröffentlichungs-
   prüfer müssen dabei auch den neuen NLA-Prüfer einfrieren und ausführen.

Direkte KI-Integrationen bleiben entfernt. Hardwaretests, Modellanfragen und
Windows-Testhosts bleiben ausgeschlossen. Es werden keine zusätzlichen Chats,
Aufgaben oder Fortsetzungsautomationen angelegt.
