# Persönlicher OpenSSH-Agent · 24.10.2026

Der bisher erzeugte Schlüssel besitzt eine Passphrase. Ohne verfügbaren Agenten
konnte die nichtinteraktive KI-Hostprüfung ihn nicht verwenden. Rampi verwendet
jetzt den vorhandenen OpenSSH-Agent und `ssh-add`, mit Passphraseeingabe im
eingebetteten VTE-Terminal. Es gibt keinen eigenen Schlüsselspeicher.

## Lokale Nachweise

- Tatsächliches OpenSSH in einem isolierten Docker-Container: kein Agent und
  verwaister Socket führen jeweils zu einem erreichbaren, leeren Sitzungsagenten.
  Er endet mit der Sitzung. Ein vorhandener erreichbarer Agent wird wiederverwendet
  und bleibt nach Sitzungsende bestehen. Nur der abschließende Compositor-Aufruf
  ist in diesem Test durch einen wartenden Übergabeprozess ersetzt.
- Tatsächliches GTK/VTE unter Wayland: `ssh-keygen` erzeugt ein mit zufälliger
  Passphrase geschütztes Schlüsselpaar. Der Entsperrknopf öffnet `ssh-add` im
  vorhandenen Fenster. Modulwechsel und erneutes Betätigen kehren zum selben
  Prozess zurück. `ssh-add -L` weist genau den erzeugten öffentlichen Schlüssel
  im echten Agenten nach. Die Passphrase erscheint nicht in den Terminalausgaben.
- Private Schlüssel müssen dem angemeldeten Linux-Konto gehören und dürfen
  keine Gruppen- oder Fremdrechte besitzen. Externes Askpass wird für diesen
  Aufruf durch `SSH_ASKPASS_REQUIRE=never` unterbunden.

Die grafische QEMU-Abnahme prüft zusätzlich den tatsächlichen Agent-Socket in der
Umgebung des über systemd gestarteten Rampi-Prozesses, getrennten Zugriff zweier
Linux-Konten und das Ende des Sitzungsagenten nach Abmeldung. Diese neue Abnahme
ist auf beiden Architekturen akzeptiert. Kein Windows-11-Pro-Host und keine
Anbieter-Modellanfrage gehören zu diesen Nachweisen. Die Erweiterung allein
erhöht den Gesamtstand nicht.

Die [native CI 40110647246](https://github.com/jtracht/rampi-os/actions/runs/40110647246)
und [allgemeine CI 40110647303](https://github.com/jtracht/rampi-os/actions/runs/40110647303)
sind vollständig erfolgreich. Heruntergeladene Laufzeit-, Funk- und Login-Nachweise
sowie sieben Paketprüfsummen bestehen zusätzlich die eingefrorenen Prüfer.

* PR-Quellstand: `1db51b61bc44befa64fb4d648d8af1ea6ae4c429`.
* Gebauter kombinierter Stand: `bc5dfaf48067ff8d7918f7047df728fb4d2e7af0`.
* [PR #36](https://github.com/jtracht/rampi-os/pull/36), zusammengeführt als
  `659a09784dde5cc6e34369fa09ed6f62f3a32d26`.
* Getesteter und zusammengeführter Tree:
  `e0a901caca51a2318bb1350f8352f52a9011e7d1`.
* ARM64-Paketprogramm, gegen beide tatsächlichen Login-Sitzungen geprüft:
  `75c50e606597c08284479c54010b1c6a3938fc0435e71b3d80339a3a4bfccf45`.
