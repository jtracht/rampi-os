# Testnachweise und Abnahme

Physische Hardwaretests sind auf Nutzerwunsch ausgeschlossen. Verbindlicher
Ersatzumfang: [VALIDATION-SCOPE.md](VALIDATION-SCOPE.md).

Am 19./20.10.2026 tatsächlich ausgeführt:

- 36 Python-Tests auf Windows, Linux und nativem ARM64-Trixie: private
  Konfiguration, sichere Argumente, Zertifikatsoptionen, Anbieter-Verträge,
  Cachetrennung, Redirect-Schutz, Hostschlüsselrotation und Secret-Übergabe.
- Tatsächliches QML geladen, sechs Fokuswechsel, Enter und Escape geprüft;
  gerenderter Screenshot, kein HTML-Ersatz.
- ARM64-Docker unter 1 GB RAM und vier CPUs: echte libnm-Importvalidierung,
  Benutzer-ACL vor Speicherung, Autostart deaktiviert.
- AccountsService/PAM im wegwerfbaren ARM64-Container: normales Konto angelegt,
  richtiges Passwort akzeptiert, falsches abgewiesen.
- Tatsächlicher GNOME-Keyring-/Secret-Service-Rundlauf in isoliertem D-Bus:
  Token gespeichert und gelesen, verschlüsselte Datei und persönliche Rechte
  bestätigt (CI 39338203802).
- Virtuelles X11 mit Openbox/Qt: Ctrl+Alt+Home wechselt vom zweiten Fenster
  zum Dashboard. Der Home-Tastendruck erreicht das andere Fenster nicht.
  X11 kann nach Ende des Grabs ein alleinstehendes KeyRelease liefern;
  dieses löst keine Home-Aktion aus.
- Offizielles psmux 3.4.0 per SHA256 geprüft, native Prozesspersistenz lokal
  unter Windows 11 Pro und in Windows-CI bestätigt.
- Windows-CI: isolierter OpenSSH-Server, zwei temporäre normale Konten,
  echten interaktiven SSH-Client abrupt beendet, erneut verbunden und
  fortlaufende Ausgabe bestätigt; fremdes Konto kann Sitzung nicht öffnen.
- Windows-Installer in CI ausgeführt: unsichere Alt-ACL ersetzt, nur Benutzer
  und SYSTEM zugelassen; persönliche Daten erhalten.
- Ruff, mypy, ShellCheck, PowerShell-Analyse, pip-audit, Secret-Scan,
  Lizenzdokumente, vollständige Quell-/Windows-Archive und Prüfsummen.

Windows-Integrationstests laufen auf GitHub-Windows-Runnern, nicht auf einem
virtuellen Windows-11-Pro-Desktop. Lokale Persistenz und Bestandsaufnahme liefen
auf dem vorhandenen Windows 11 Pro. CI verändert keine persönlichen Konten
oder bestehenden Hostdienste.

Imageworkflow: offizieller pi-gen-Build, readonly FAT-/ext4-Prüfungen,
Partitionslayout, Bootdateien, Paketmanifest und Lizenzarchiv. QEMU muss den
echten systemd-Healthcheck RAMPI_BOOT_OK erreichen; ein Build allein ist kein
Bootnachweis. Aktuelle Ergebnisse: [GitHub Actions](https://github.com/jtracht/rampi-os/actions).
Fehlgeschlagene Prüfungen werden vor Freigabe behoben, nicht als bestanden gewertet.

Keine erfolgreichen persönlichen Cloudanmeldungen, VPN-Netze, RDP-Desktops
oder Sunshine-Streams werden behauptet. Funk, HDMI, GPU-Leistung und echte
Eingabe-/Streaminglatenz sind außerhalb des vereinbarten Testumfangs.

Reproduzieren: pytest -q, python scripts/test-ui.py und die Docker-Aufrufe
in .github/workflows/ci.yml. Windows-SSH-/Installer-Tests verweigern Ausführung
außerhalb von GitHub CI. Imageprotokolle werden als Artefakte aufbewahrt.
