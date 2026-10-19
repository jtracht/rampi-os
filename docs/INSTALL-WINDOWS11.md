# Windows 11 Pro einrichten

Laptop eingeschaltet, geöffnet und im Netz erreichbar halten. Für jeden
Rampi-Benutzer ein eigenes Windows-Konto mit minimalen Rechten verwenden.

1. Vollständigen Quellbaum oder Windows-Host-ZIP entpacken.
2. `./setup.ps1` prüft nur vorhandene Programme, Edition und Build.
3. `./setup.ps1 -Install` installiert den kleinen Adapter nach
   `%LOCALAPPDATA%\Rampi\rampi-session.ps1` mit persönlicher ACL.
4. `-InstallMissing` installiert ausschließlich fehlendes psmux 3.4.0 über
   WinGet-ID `marlocarlo.psmux`. Neue Programme erscheinen gegebenenfalls erst in
   einer neuen Shell im PATH.
5. Bei Bedarf in einer erhöhten PowerShell ausdrücklich `-EnableOpenSsh` wählen.
   Bestehende sshd-Konfiguration wird erhalten; Dienststart und TCP-22-Regel sind
   die transparenten Änderungen. Ohne vorhandene Regel wird nur Profil Private geöffnet.
6. RDP wird ausschließlich mit `-EnableRdp` aktiviert, inklusive NLA und einer
   eigenen TCP-3389-Regel für private Netze. Remote-Firewallzugriff auf das eigene
   VPN weiter einschränken, bevor entfernte Netze verwendet werden.

Windows OpenSSH erwartet normale Benutzerschlüssel in `~/.ssh/authorized_keys`.
Administratorkonten können gemäß bestehender sshd-Konfiguration stattdessen
`%ProgramData%\ssh\administrators_authorized_keys` verwenden. Bestehende Regeln
nicht blind überschreiben; Microsoft-Dokumentation befolgen:
https://learn.microsoft.com/windows-server/administration/openssh/openssh_keymanagement

Pi-Hostschlüsselprüfung: Fingerprint auf Windows lokal ermitteln, unabhängig
abgleichen und erst dann die passende bekannte Hostidentität im persönlichen
Linux-OpenSSH-Profil akzeptieren. Rampi verwendet strikt `StrictHostKeyChecking=yes`.

Anbieter-CLIs aus offiziellen Quellen installieren und im persönlichen Konto
anmelden. Sunshine und VPN werden erkannt, nicht automatisch ersetzt oder geöffnet.
`-WhatIf` zeigt Änderungen. Uninstall entfernt keine Windows-Dienste und beendet
keine bestehenden psmux-Sitzungen. Hostneustarts beenden laufende Prozesse.
