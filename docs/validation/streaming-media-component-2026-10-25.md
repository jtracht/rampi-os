# GStreamer-Medienadapter: Komponentenprüfung

Dies ist noch keine Abnahme eines eingebetteten Streaming-Moduls. Die Verbindung
zur GTK-Oberfläche und die erfolgreiche Sunshine-Verbindung fehlen weiterhin.
Der Gesamtstand bleibt 81/100; diese Arbeit bleibt außerhalb des dev1-Images.

Der Rust-Adapter verwendet vorhandene GStreamer-Elemente für H.264, Opus,
Farbumwandlung und Audioausgabe. Video endet in einem Appsink für den bestehenden
GTK-/RDW-Renderer, nicht in einem separaten Videofenster. Decodebin wählt einen
vorhandenen Decoder; dieser Test belegt keine Raspberry-Pi-Hardwaredecodierung.
Eingangsqueues sind nach Bytes und Anzahl begrenzt. Es bleibt höchstens ein
fertiges Bild für den Renderer. Ein überlasteter Videoeingang meldet einen Fehler,
den die Moonlight-Laufzeitanbindung als Schlüsselbild-Anforderung behandelt.
Der neue Laufzeitadapter ist separat beschrieben; der tatsächliche erfolgreiche
Netzwerkpfad ist noch offen.

Im tatsächlichen Docker-Medien-SDK mit 1 GiB ohne Swap und vier CPUs kodiert
FFmpeg rote, blaue und grüne Bilder als H.264. Der Produktionsadapter muss deren
Pixel, Größe und Alphakanal korrekt dekodieren und nach Zerstören/Neuanlegen
weiterarbeiten. Ein zunächst fehlgeschlagener Test zeigte, dass vollständige
Access Units gegenüber H.264-Parse ausdrücklich mit `alignment=au` bezeichnet
werden müssen; nach dieser Korrektur bestanden alle Farben und der Neustart.

Ein tatsächlicher GStreamer-Opusencoder liefert einen 997-Hz-Stereoton. Derselbe
Produktionsdecoder wird im Test an einen PCM-Appsink angeschlossen. Gemessen
wurden 1005,4 Hz bei RMS 0,563 innerhalb der festgelegten Toleranz. Das prüft
Dekodierung und Datenfluss, keinen Lautsprecher oder Sunshine-Netzwerkpfad.
Leere und übergroße Medienpakete werden abgewiesen. Es erfolgen keine Modell-
oder Hardwareanfragen.

Die vorbereitete native CI führt diese explizite Komponentenprüfung auf AMD64
und ARM64 aus und verlangt ihren tatsächlichen Erfolgsmarker in `stream-media.log`.
Der Medienstand `5c7d57ab7cf347da4377da6bb223eb50ece60bcd` hat inzwischen native
CI `40209060876` auf beiden Architekturen bestanden. Unabhängig heruntergeladene
Nachweise wurden mit den Prüfern genau dieses Quellstands geprüft, einschließlich
der sieben ARM64-Paketprüfsummen und des tatsächlichen Programmhashes. Das
belegt den Medienstand, nicht die danach entwickelte C-Laufzeitanbindung.
Weitere Pflicht-
abnahmen bleiben: authentifiziertes Pairing und private Identitäten, Sunshine-
Video/Audio, sichtbare GTK-Fläche, bestätigte Eingaben, reservierte Kürzel,
Wiederverbindung und Serverabbruch. Keine davon wird durch diesen Test ersetzt.

Referenzen: vorhandene GStreamer-Schnittstellen
[Appsrc](https://gstreamer.freedesktop.org/documentation/app/appsrc.html),
[Appsink](https://gstreamer.freedesktop.org/documentation/app/appsink.html) und
[Decodebin](https://gstreamer.freedesktop.org/documentation/playback/decodebin.html).
