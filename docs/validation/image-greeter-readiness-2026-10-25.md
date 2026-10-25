# Kalter Image-Start: sichtbare Anmeldefläche abwarten

Der frische Imagebau aus `e8944c3` und dessen Kernelboot sind gelungen.
Die unabhängige Quellenprüfung bestätigte 537 Distributionspakete und
479 Cargo-Abhängigkeiten. Die grafische Prüfung im ursprünglichen installierten
Image scheiterte anschließend vor der ersten Anmeldung: Der erlaubte Rust-
Branding-Prozess lief, seine Fläche war bei der einmaligen Abfrage noch nicht
in der Toplevel-Liste.

Der vorhandene reine Diagnosemodus wurde mit demselben unveränderten Image
ausgeführt. Er gibt absichtlich keine Anmeldedaten ein und endet ohne erfolgreiche
Abnahme. Sein tatsächliches Wayland-/labwc-Protokoll zeigt `set_app_id` für
`org.rampi.LoginBranding` und die erste zugehörige Bildzuordnung nach etwa
31 Sekunden Compositor-Laufzeit. Die Bereitschaft des schneller sichtbaren
wlgreet-Fensters genügt deshalb nicht für die Bereitschaft der GTK-Brandingfläche.

Die Prüfung wartet nun mit derselben vorhandenen 90-Sekunden-Grenze auf die
tatsächlich zugeordnete Branding-Fläche und die sichtbaren Original-Logo-Pixel.
Eine sichtbare Workstation führt weiterhin sofort zum Fehler. Die Prüfung des
einzigen Branding-Prozesses samt erlaubter Argumente bleibt erhalten; schwarzes
Bild, fehlendes Logo und ein Ablauf der Grenze bleiben Fehler. Es wird keine
feste längere Schlafzeit eingeführt und kein installiertes Produktprogramm ersetzt.
Das letzte Toplevel-Ergebnis wird vor jeder Anmeldung zur Diagnose gespeichert.

Noch erforderlich sind die erneute vollständige grafische Image-Abnahme mit
zwei Konten, falschem Kennwort, privaten Profilen und unveränderten installierten
Dateien sowie ein frischer Release-Bau nach erfolgreicher CI. Der Gesamtstand
bleibt 81/100; der Diagnosemodus ist kein erfolgreicher Login-Nachweis.

Nachweise: [ursprünglicher Lauf](https://github.com/jtracht/rampi-os/actions/runs/40203007032)
und [reiner Diagnoselauf](https://github.com/jtracht/rampi-os/actions/runs/40208281245).
