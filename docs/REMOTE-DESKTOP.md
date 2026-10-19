# Remote Desktop

RDP verwendet Microsofts Dienst unter Windows 11 Pro und FreeRDP 3 auf dem Pi.
Kennwörter werden interaktiv abgefragt, nie als `/p:`-Argument gespeichert.
`/cert:tofu` prüft eine bekannte Zertifikatsidentität nach dem ersten bewussten
Vertrauen. Die erste Identität unabhängig prüfen. `/cert:ignore` wird nicht verwendet.
`-grab-keyboard` soll verhindern, dass reservierte lokale Kürzel vom Client
abgefangen werden. Der globale Openbox-Kurzbefehl wird softwareseitig unter X11
geprüft; ein laufender RDP-Server ist kein Bestandteil dieses Tests.
Windows 11 Pro bietet keine frei parallelen interaktiven Benutzersitzungen:
eine RDP-Verbindung kann die lokale Sitzung sperren.

Streaming verwendet Sunshine auf Windows mit Moonlight Embedded 2.7.1,
welches laut Releasehinweisen Trixie unterstützt. Das allein beweist weder
Pi-3-Hardwaredecodierung noch konfliktfreien Betrieb im bestehenden Xorg-VT.
Moonlight Qt ist nicht ohne Weiteres austauschbar: anderer Programmname und
andere Optionen. Der Adapter verwendet die Embedded-CLI `moonlight stream`.
Erwartet werden ein bereits gekoppelter Host und Sunshine-Anwendung `Desktop`.
Standard 1280×720, 30 fps, 5 Mbit/s. Rampi startet explizit das SDL-Frontend im
vorhandenen X11 und verhindert die Übernahme reservierter Tastenkürzel. FFmpeg
verwendet verfügbare Decoder einschließlich V4L2 und seinen Software-Fallback.
Reale Decoderleistung, Audio und Latenz sind gemäß geändertem Testumfang
nicht Teil der Abnahme.

Es werden keine Legacy-Grafiktreiber durch Änderungen an `/boot` erzwungen.
Für die Einrichtung Sunshine im Windows-Konto konfigurieren, den Desktop als
Anwendung freigeben und im Rampi-Remote-Modul koppeln. Streaming und RDP sind
separate Startoptionen; keine der beiden ersetzt die andere.

https://github.com/moonlight-stream/moonlight-embedded/releases
https://docs.lizardbyte.dev/projects/sunshine/latest/
