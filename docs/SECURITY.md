# Sicherheitsmodell

Siehe die zentrale [Sicherheitsdokumentation](../SECURITY.md).
Installationsrechte sind von Laufzeitrechten getrennt. Die systemd-Benutzerunit
setzt UMask=0077 und läuft als angemeldeter Benutzer. Privilegierte Systemänderungen laufen über
vorhandene polkit-Dialoge; Rampi wird nicht als root gestartet. NoNewPrivileges
wird nur beim schreibgeschützten System-Healthcheck gesetzt, da es im Benutzer-
Client reguläre PAM-/pkexec-Anmeldungen aus dessen Konsole verhindern würde.
Netzwerkprogramme verwenden die regulären
Systemberechtigungen. Die Openbox-Sitzung bewahrt den normalen TTY-Zugang.

Zwei getrennte Windows-Konten und ein echter SSH-Abbruch/Reattach sind in CI
geprüft. GNOME Keyring wurde in einem isolierten D-Bus tatsächlich entsperrt,
beschrieben und gelesen; verschlüsselte Dateien und persönliche Rechte wurden
bestätigt. Der grafische LightDM/PAM-Entsperrablauf wird damit nicht als live
geprüft behauptet. WireGuard-Importrechte und Linux-PAM-Authentifizierung wurden
gegen echte Trixie-Komponenten geprüft.

Das globale X11-Kürzel wird unter Openbox abgefangen; FreeRDP und Moonlight
starten mit deaktivierter Tastaturübernahme. Ein laufender RDP-/Streaminghost
war nicht Bestandteil dieses Tests.

Sunshine autorisiert gekoppelte Clients und überträgt den aktiven Windows-
Konsolendesktop. Das ist keine zusätzliche Windows-Kontoanmeldung. Streaming
setzt daher einen persönlich zugeordneten Host und das eigene aktive Windows-
Konto voraus; eine getrennte Streamingfreigabe mehrerer Windows-Konten auf
demselben Host ist im aktuellen Stand nicht implementiert. SSH und RDP behalten
ihre tatsächliche Windows-Kontoauthentifizierung. Diese Einschränkung darf
nicht als umfassende Mehrbenutzerisolation beim Streaming ausgegeben werden.
