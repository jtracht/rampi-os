# Softwareabnahme am 20. Oktober 2026

Physische Hardwaretests sind ausdrücklich ausgeschlossen. Diese Abnahme bestätigt
den dokumentierten Softwareumfang, keine Funk-, HDMI-, GPU- oder Latenzmessungen.

CI: [vollständig erfolgreich](https://github.com/jtracht/rampi-os/actions/runs/39376526903), Quellrevision
`6e3062eacac0a8ea81c12c536fccb15343d272eb`.
Image: offizieller pi-gen-Build aus `a1f3373012b7086fc712b60ae86bc7c61ac40fb6`,
Workflow 39335603836, erfolgreicher Producer-Job. Dessen damaliger Validator
verwendete noch eine ungeeignete serielle Konsole; er ist kein erfolgreicher
Gesamtlauf. Dasselbe unveränderte Artefakt bestand anschließend die
[separate Imageprüfung](https://github.com/jtracht/rampi-os/actions/runs/39376146264) mit Validatorrevision
`babfe7140b963a587aa0a7caa924f86c50bf39a1`.

| Freigabekriterium | Tatsächlicher Nachweis |
|---|---|
| native_qml_and_keyboard | Reale QML-Oberfläche unter Linux/Windows und ARM64; sechs Fokuswechsel, Enter/Escape; Openbox/X11 fängt den reservierten Home-Tastendruck ab |
| docker_networkmanager_import | Echtes Trixie-libnm importiert und validiert WireGuard; persönliche Benutzer-ACL vor Speicherung, Autostart aus |
| windows_native_persistence | Nativer ConPTY-/psmux-Prozess; echter interaktiver SSH-Client abrupt beendet, danach weitere Ausgaben und Reattach; zweites Windows-Konto kann fremde Sitzung nicht öffnen |
| configuration_and_secret_isolation | Private atomare Konfiguration und Cache; Hostschlüsselrotation verweigert; echtes GNOME-Keyring-Schreiben/Lesen, verschlüsselte Datei mit persönlichen Rechten; keine Tokens in argv |
| kanban_contracts_and_cache | 36 Python-Tests insgesamt, darunter Anbieter-Verträge/Paginierung, lesende Adapter, Such-/Cache- und Redirect-Verhalten; keine behaupteten persönlichen Cloudanmeldungen |
| installer_script_validation | ShellCheck, PowerShell-Analyse; tatsächlicher Windows-Installer-ACL-/Datenbewahrungstest; Linux-Installer im echten pi-gen-Rootfs ausgeführt; AccountsService/PAM mit richtigem und falschem Passwort |
| ci_security_and_packages | Alle sechs CI-Jobs erfolgreich; Ruff, mypy, pip-audit, Secret-Scan, Lizenz-/Herkunftsdokumente, Python-Build und unveränderliches Git-Quellarchiv |
| image_partitions_and_filesystems | FAT/ext4 readonly geprüft, Partitionen und Bootdateien vorhanden; Paketmanifest und Lizenzarchiv exportiert |
| qemu_software_boot | Originaler Pi-Kernel 6.18.50 und originales initramfs auf raspi3b mit 1 GiB/vier CPUs; echter systemd-Healthcheck meldet Rampi 0.1.0.dev0 und RAMPI_BOOT_OK bei Gastsekunde 186 |
| release_artifact_completeness | CI prüft tatsächlich Quell-/Windows-Archive und alle sechs Komponentenprüfsummen; Image und Validierungsmetadaten liegen als erzeugte Artefakte vor. Der Publishjob prüft zusätzlich zwingend den vollständigen versionsgleichen Satz einschließlich Image, Lizenzarchiv und Bootlog vor Veröffentlichung |

QEMU verwendet eine temporäre DTB ohne den fehlerhaft emulierten Watchdog,
die originale serielle Aliaszuordnung ttyAMA1 und einen beschreibbaren
Laufzeit-Snapshot. Das veröffentlichte Pi-Image wird dabei nicht angepasst.
Die Probe wird mit systemd.wants ausdrücklich gestartet. Details stehen in
qemu-environment.txt und dem vollständigen qemu-boot.log des verlinkten Laufs.

Diese Baseline gibt keinen ungeprüften zukünftigen Build frei. Jeder Release
muss seinen eigenen neuen Image-Build, Rootfs-QML-Starttest, QEMU-Healthcheck
und vollständigen Artefakt-/Prüfsummentest bestehen. Der neue Healthcheck
rendert zusätzlich die tatsächliche Oberfläche ohne Display und behandelt
QML-Warnungen als Fehler. Er startet auf Endgeräten ausschließlich bei Diagnose.

Grenzen: persönliche Anbieter-/VPN-/RDP-/Sunshine-Verbindungen sind nicht live
geprüft; Sunshine streamt die aktive Konsole und bietet keine zusätzliche
Windows-Kontoanmeldung. Siehe SECURITY.md und STATUS.md. Die Quellenrevision
und das Paketmanifest sind nachvollziehbar; bewegliche Paketspiegel verhindern
bislang eine Zusage bitweise identischer Images.

