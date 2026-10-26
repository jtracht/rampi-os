# Nativer Sunshine-Verbindungspfad: Komponentenprüfung

Gesamtstand weiterhin 81/100. Diese Entwicklung bleibt im getrennten
Streaming-Entwurfszweig und außerhalb des dev1-Images. Die GTK-Anzeige,
Integration des persönlichen Schlüsselbunds, bestätigte Eingaben und
Windows-Hostabnahme fehlen weiterhin.

Der Rust-Client verwendet die vorhandene Moonlight-Bibliothek für PIN-Kopplung,
Anwendungsabfrage, authentifiziertes Starten/Fortsetzen und Kryptografie.
libcurl übernimmt HTTP und gegenseitiges TLS; nach der Kopplung muss der
Serverschlüssel zum bestätigten Zertifikat passen. OpenSSL erzeugt die
persönlichen Geräteidentitäten. Rampi implementiert kein eigenes
Kopplungs-, Verschlüsselungs- oder Streaming-Protokoll.

Der Client bietet die Identität als Geheimnis für den vorhandenen persönlichen
Secret Service an. Die tatsächliche GTK-/Schlüsselbund-Anbindung ist noch offen.
Im Komponentenlauf wird die Identität kodiert, erneut eingelesen und für
eine neue Verbindung verwendet; dies ist keine Abnahme der PAM-Speicherung.
Unpassende reale private Schlüssel und Zertifikate werden abgewiesen. Eigene
Schlüsselkopien werden beim Verwerfen gelöscht; die internen Kopien verwendeter
Drittanbieterbibliotheken sind davon nicht umfasst. Protokolladressen und
private Schlüssel werden nicht geloggt.

Der lokale C-Verbindungsbesitz wird bereits vor dem HTTPS-Start reserviert.
So sendet ein zweiter lokaler Start keinen Übernahmeaufruf an Sunshine, während
eine andere Verbindung aktiv ist. Der offizielle C-Client erhält seine eigenen
Versionsparameter. Eingehende H.264-/Opus-Daten durchlaufen die vorhandenen
GStreamer-Pipelines; es wird kein externer Videoplayer geöffnet.

Der tatsächliche lokale Test verwendet zwei neue Docker-Container in einem
internen Netzwerk ohne freigegebene Hostports oder Geräte. Beide sind auf
1 GiB ohne Swap und vier CPUs begrenzt. Der vorhandene Sunshine-Testserver
liefert wechselnde rote/blaue Flächen und einen 997-Hz-Ton. Der tatsächliche
Rust-Client koppelt sich, weist ein gültiges, aber abweichendes Serverzertifikat
beim TLS-Handschlag ab und stellt zwei Verbindungen mit wieder eingelesener
Identität her. Geprüft werden die tatsächlich dekodierten Bildpixel und
aufgezeichnetes PCM am tatsächlichen PulseAudio-Ausgang des Clients. Stille
mit angepasster Prüfsumme wurde vom unabhängigen Tonprüfer abgewiesen.

Die Nachweise enthalten das ausgeführte Komponenten-ELF, die C-Bibliothek,
deren vollständigen Quellbaum einschließlich Untermodulen und Lizenzen,
Quellrevisionen, Dateiprüfsummen, Server-/Clientprotokolle und einen tatsächlich
empfangenen PCM-Ausschnitt. Ein Lauf mit uncommittetem Quellbaum wird ausdrücklich
von der endgültigen CI-Abnahme ausgeschlossen. Er kann lokal zur Diagnose
geprüft werden und zählt nicht als Release- oder integrierte Produktabnahme.

Reproduktion aus einem sauberen Checkout:

```sh
docker build -t rampi-rust-dev -f tests/rust/Dockerfile .
docker build -t rampi-stream-media-test -f tests/streaming/Dockerfile.media .
docker build -t rampi-native-sunshine-test -f tests/streaming/Dockerfile.sunshine .
python3 scripts/test-native-streaming.py
python3 scripts/check-stream-evidence.py artifacts/rust/streaming-live
```

Die native CI führt diesen Test auf AMD64 und ARM64 aus. Der erste lokale Lauf
des separaten Server-SDKs scheiterte an einer Docker-Buildkit-Erkennung über
`/.dockerenv`; der Fixture-Installer verlangt jetzt eine ausdrückliche
Build-Kennung und installiert nur in den vorgesehenen Testimages. Der
vorhandene, kompatible Sunshine-Paketstand wird wiederverwendet. Die erneuten
lokalen Tests bestanden. Die vollständige neue CI-Abnahme bleibt erforderlich.

Der Sunshine-Server deaktiviert Eingabegeräte in diesem Test ausdrücklich.
Erfolgreiche Bild-/Tonübertragung belegt deshalb weder bestätigte Tastatur-/
Mauseingaben noch reservierte Kürzel. Es gibt keine Hardware-, Modell- oder
persönlichen Windows-Konfigurationsaufrufe.
