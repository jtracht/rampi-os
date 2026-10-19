# Performance und Messplan

Es wurden bislang keine RAM-/CPU-/Latenzwerte auf Raspberry Pi gemessen.
Architekturentscheidungen sind Hypothesen, keine Benchmarkergebnisse.

Auf Pi 3 B+ nach Boot und Anmeldung jeweils fünf Minuten stabilisieren lassen.
Dashboard, ein einzelnes KI-Terminal, 720p-RDP, Streaming und Browser einzeln
messen. `free -m`, `systemd-cgtop`, `pidstat`, `journalctl --user -u rampi` und
`vcgencmd get_throttled` nutzen. Werkzeuge zuerst erkennen; nur bei Bedarf installieren.
Speicher inklusive Kindprozessen erfassen, Cache von aktiver Belegung trennen.

Für 200 Kachelwechsel Qt-Framezeiten messen; 60-Hz-Ziel bedeutet 16,7 ms pro Frame.
Gleichmäßig große Pfadänderungen laufen nur bei Auswahl. Eingabe-/Remote-Latenz
mit Hochgeschwindigkeitskamera oder geeigneter vorhandener Messhardware ermitteln.
Module werden einmal und erst bei Bedarf gestartet. Chromium kann 1 GB deutlich
belasten; reale moderne Seiten und Downloads müssen mitgemessen werden.

Optimierung erfolgt anhand dieser Daten: Auflösung/Framerate, Browserwahl,
Qt-Backend und Autostarts. Kein ungemessener Anspruch auf hohe Performance.
