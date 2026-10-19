# Sicherheitsmodell

Siehe die zentrale [Sicherheitsdokumentation](../SECURITY.md).
Installationsrechte sind von Laufzeitrechten getrennt. Die systemd-Benutzerunit
setzt NoNewPrivileges und UMask=0077; privilegierte Systemänderungen laufen über
vorhandene polkit-Dialoge. Netzwerkprogramme verwenden die regulären
Systemberechtigungen. Die Openbox-Sitzung bewahrt den normalen TTY-Zugang.

Offene Abnahmen: Windows-Serverendpunkt zwischen zwei Benutzern, persönliche
WireGuard-Importrechte, Secret-Service-Entsperrung unter PAM und globale
Tastenkürzel während RDP/Streaming. Keine dieser Prüfungen wird aus einem
erfolgreichen Build abgeleitet.
