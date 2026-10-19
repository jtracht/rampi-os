# Sicherheitsmodell

Siehe die zentrale [Sicherheitsdokumentation](../SECURITY.md).
Installationsrechte sind von Laufzeitrechten getrennt. Die systemd-Benutzerunit
setzt UMask=0077 und läuft als angemeldeter Benutzer. Privilegierte Systemänderungen laufen über
vorhandene polkit-Dialoge; Rampi wird nicht als root gestartet. NoNewPrivileges
wird nur beim schreibgeschützten System-Healthcheck gesetzt, da es im Benutzer-
Client reguläre PAM-/pkexec-Anmeldungen aus dessen Konsole verhindern würde.
Netzwerkprogramme verwenden die regulären
Systemberechtigungen. Die Openbox-Sitzung bewahrt den normalen TTY-Zugang.

Offene Abnahmen: Windows-Serverendpunkt zwischen zwei Benutzern, persönliche
Secret-Service-Entsperrung unter PAM und globale
Tastenkürzel während RDP/Streaming. Keine dieser Prüfungen wird aus einem
erfolgreichen Build abgeleitet. WireGuard-Importrechte und echte Linux-PAM-
Authentifizierung wurden bereits gegen Trixie-Komponenten im Container geprüft.
