# Sicherheit

Bitte Schwachstellen nicht mit Zugangsdaten in öffentlichen Issues posten.
Im GitHub-Repository Security → Advisories → Report a vulnerability verwenden,
sofern Private Vulnerability Reporting für das Repository aktiviert ist.
Alternativ zuerst ohne technische Geheimnisse um einen privaten Kontakt bitten.

Dieser Entwicklungsstand hat noch keine Produktionsfreigabe. Offene
Sicherheitsabnahmen stehen in `packaging/readiness.json` und `docs/STATUS.md`.

Keine Rampi-eigene Passwortdatenbank, Kryptografie oder öffentlich lauschender
Broker. Linux-Prozesse laufen als angemeldeter Benutzer. SSH-Hostprüfung bleibt
aktiv, FreeRDP deaktiviert Zertifikatsprüfung nicht. Provider-Tokens gehören in
den persönlichen Secret Service. HTTP-Redirects werden nicht verfolgt, damit
Authorization nicht an fremde Hosts weitergereicht wird. Prozessstarts verwenden
Argumentlisten; Windows-Projektpfade sind literale, kodierte PowerShell-Werte.

Windows-Änderungen an SSH/RDP verlangen ausdrückliche Installationsoptionen.
Der Host-Adapter lehnt SYSTEM ab und verwendet die bestehenden Benutzerrechte.
psmux-Benutzerisolation muss zusätzlich mit zwei echten Konten geprüft werden.
Ein erfolgreiches Persistenzexperiment ist kein Isolationsnachweis.

Öffentliche HTTP-APIs erhalten nur manuell eingerichtete Lesetokens. Persönliche
Kanban-Caches können vertrauliche Projektdaten enthalten. Browserprofile,
SSH-Schlüssel und Konfigurationen dürfen nicht zwischen Konten geteilt werden.
