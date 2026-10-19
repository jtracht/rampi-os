# Remote Desktop

RDP verwendet Microsofts Dienst unter Windows 11 Pro und FreeRDP 3 auf dem Pi.
Kennwörter werden interaktiv abgefragt, nie als `/p:`-Argument gespeichert.
`/cert:tofu` prüft eine bekannte Zertifikatsidentität nach dem ersten bewussten
Vertrauen. Die erste Identität unabhängig prüfen. `/cert:ignore` wird nicht verwendet.
`-grab-keyboard` soll verhindern, dass reservierte lokale Kürzel vom Client
abgefangen werden. Das Verhalten ist auf Zielhardware noch abzunehmen.
Windows 11 Pro bietet keine frei parallelen interaktiven Benutzersitzungen:
eine RDP-Verbindung kann die lokale Sitzung sperren.

Streamingkandidat ist Sunshine auf Windows mit Moonlight Embedded ab 2.7.1,
welches laut Releasehinweisen Trixie unterstützt. Das allein beweist weder
Pi-3-Hardwaredecodierung noch konfliktfreien Betrieb im bestehenden Xorg-VT.
Moonlight Qt ist nicht ohne Weiteres austauschbar: anderer Programmname und
andere Optionen. Der Adapter verwendet die Embedded-CLI `moonlight stream`.
Erwartet werden ein bereits gekoppelter Host und Sunshine-Anwendung `Desktop`.
Standard 1280×720, 30 fps, 5 Mbit/s. Pairing/Decoder/Audio und eine verlässliche
Integration in dieselbe grafische Sitzung fehlen noch als Hardwareabnahme.

Es werden keine Legacy-Grafiktreiber durch Änderungen an `/boot` erzwungen.
Falls der Trixie-Decoder auf Pi 3 nicht zuverlässig arbeitet, muss vor Freigabe
eine gepflegte vorhandene Streamingalternative real evaluiert werden. RDP allein
erfüllt die verbindliche doppelte Remote-Anforderung nicht.

https://github.com/moonlight-stream/moonlight-embedded/releases
https://docs.lizardbyte.dev/projects/sunshine/latest/
