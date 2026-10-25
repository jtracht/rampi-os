# Moonlight-Laufzeitadapter: begrenzte Komponentenabnahme

Diese Erweiterung bleibt außerhalb des Entwicklungsimages. Der Gesamtstand
bleibt 81/100. Eine erfolgreiche Sunshine-Verbindung, die GTK-Anzeige und
authentifizierte Wiederverbindung sind damit noch nicht abgenommen.

Der Rust-Adapter verbindet die vorhandene offizielle Moonlight-C-Bibliothek
mit den vorhandenen GStreamer-Decodern. Das GameStream-Protokoll, RTSP,
Medienübertragung und Eingabeverschlüsselung verbleiben bei Moonlight.
Es werden ausschließlich die generierten Schnittstellen der vorhandenen
Moonlight-Embedded-Version 2.7.1 geladen. Die zugehörigen Quellen sind festgelegt:

- Moonlight Embedded: `775444287305849ebdf4736c75298ad0713e2d5d`
- moonlight-common-c: `b126e481a195fdc7152d211def17190e3434bcce`

Das Test-SDK verwendet den vorhandenen upstream-CMake-Target `moonlight-common`.
Es installiert ausschließlich diese Bibliothek und erhält den vollständigen
Quellcheckout im SDK. Kein eigener Netzwerkclient oder zusätzlicher Player
wird dafür implementiert. Eine spätere Aufnahme ins Systemimage benötigt
weiterhin vollständige Drittanbieterquellen und deren Release-Prüfung.

Der Verbindungsstart und das Aufräumen laufen auf einem Arbeiterthread.
Der klonbare Bedienendpunkt fragt Bilder ab, übergibt typisierte Eingaben und
fordert einen Abbruch an. Ein prozessbezogener Besitz verhindert konkurrierende
C-Verbindungen. Alte Bedienendpunkte dürfen nach dem Aufräumen keine neue
Verbindung unterbrechen. Eigene Kopien von Eingabeschlüsseln werden auch bei
ungültigen Parametern, aufgegebenem Start und frühem Abbruch gelöscht.
C-Rückrufe behalten keine geliehenen Medienzeiger; begrenzte Kopien werden an
GStreamer übergeben. Fehlender Platz für Videodaten fordert über Moonlight
ein neues Schlüsselbild an. Rust-Paniken verlassen keine C-Rückrufgrenze.

Der echte lokale Test lädt die tatsächliche versionierte Bibliothek. Ein
Loopback-TCP-Endpunkt beantwortet die RTSP-Anfrage absichtlich nicht. Moonlight
muss seine echte RTSP-Startphase erreichen, der Bedienendpunkt muss den Abbruch
innerhalb einer Sekunde übergeben und der Arbeiter danach innerhalb von
20 Sekunden aufräumen. Der beobachtete native Empfangstimeout dauert etwa
15 Sekunden. Das Aufräumen gibt den Verbindungsbesitz wieder frei. Zusätzlich
werden ein veralteter Endpunkt gegenüber einem neuen vorbereiteten Start,
Abbruch vor dem C-Aufruf, aufgegebene Vorbereitung und ungültiger Zieltext
geprüft. Das ist ausdrücklich kein erfolgreicher Video-/Audiostream.

Ein erster Lauf im frisch gebauten SDK zeigte einen tatsächlichen Suchpfadfehler:
`ldconfig` indexiert den upstream-SONAME `.so.4`, nicht automatisch den exakten
Dateinamen. Der Adapter verwendet deshalb zusätzlich die regulären absoluten
Installationspfade, weiterhin ausschließlich mit der exakten Version 2.7.1.
Danach bestanden beide tatsächlichen Medien-/Laufzeittests ohne besondere
Suchpfad-Umgebungsvariable sowie Workspace-Fmt/Clippy und drei TLS-Tests.
Das SDK baut die echte Bibliothek aus den oben genannten Quellen selbst.

Die native CI verlangt beide tatsächlichen Erfolgsmarker in `stream-media.log`:
`RAMPI_STREAM_GSTREAMER_MEDIA_OK` und `RAMPI_STREAM_NATIVE_C_LIFECYCLE_OK`.
Diese Erweiterung hat lokal bestanden; ihre neue CI-Abnahme steht noch aus.
Die CI des vorherigen Medienstands prüft diesen neuen Laufzeitadapter nicht. Die verbleibenden
Ende-zu-Ende-Nachweise umfassen Pairing mit privaten Identitäten, Serverbindung,
Sunshine-Video/Audio, sichtbare GTK-Bilder, bestätigte Eingaben, reservierte
Tastenkürzel, Wiederverbindung und Serverabbruch. Hardware- oder Modellanfragen
werden nicht ausgeführt.
