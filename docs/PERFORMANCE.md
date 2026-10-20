# Softwaremessung und Performancegrenzen

Physische Hardwaretests sind auf Nutzerwunsch ausgeschlossen. Im nativen
ARM64-Trixie-Container mit 1 GB RAM und vier CPUs erreichte der kurze tatsächliche
QML-Starttest am 19.10.2026 eine maximale Prozessbelegung von 112876 KiB
(etwa 110 MiB), 0,36 s Benutzer- und 0,07 s System-CPU-Zeit bei 1,82 s Laufzeit.
Nachweis: CI-Lauf 39335885373, Job trixie-arm64, erfolgreicher Docker-Testschritt.
Der getrennte X11-Schritt dieses Laufs scheiterte an seinem damaligen Testaufbau.
Diese Werte messen nur den Clientstart, nicht das Gesamtsystem oder Pi-Leistung.

Optionale spätere Hardwaremessung außerhalb des Abnahmeumfangs:
Nach Boot und Anmeldung jeweils fünf Minuten stabilisieren lassen.
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
