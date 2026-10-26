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
Die vollständige Bedienabnahme dieses Einrichtungsschritts und die Abnahme des
endgültigen Programmstands auf beiden Architekturen stehen noch aus. Daher kein
zusätzlicher Fortschrittspunkt. Die regulären nativen Prüfungen verlangen nun
auch den tatsächlichen privaten Tunnelbeleg mit identischem Programmhash.

## Noch vor der Komplettversion

1. Den unveränderten Erststart im frisch gebauten Image und den folgenden
   normalen Neustart sowie den offiziell vorab eingerichteten Kontoablauf prüfen.
2. Die vollständige deutsch-/englische Oberfläche fertigstellen. Fluent,
   persönliche Sprachauswahl, Sitzungs-Locale, Dashboardnavigation und
   Einrichtungsbeschreibungen sind integriert; weitere Seiten und Fehlermeldungen
   sind noch nicht vollständig übersetzt.
3. Echte virtuelle Bluetooth-Tastatur und -Maus einschließlich Wiederverbindung
   sowie Tailscale-Anmeldung, Tunnelverkehr und Rechte-/Routengrenzen abnehmen.
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
