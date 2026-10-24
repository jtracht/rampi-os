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
ist bis zum erfolgreichen CI-Lauf offen. Kein Windows-11-Pro-Host und keine
Anbieter-Modellanfrage gehören zu diesen Nachweisen. Der Gesamtstand bleibt bis
zur gesonderten Bewertung unverändert.
