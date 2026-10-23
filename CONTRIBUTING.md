# Mitwirken

Feature-/Fix-Branch erstellen, Änderungen mit Conventional Commits beschreiben
und Pull Request nach main öffnen. Bestehende Systemdienste wiederverwenden.
Keine eigenen Protokolle, Passwortdatenbanken oder Browser-/Terminalengines.
Rampi-spezifische Adapter klein und unprivilegiert halten.

Die neue Anwendung liegt unter `native/` und verwendet Rust/GTK 4/Wayland.
Vor einem nativen PR `python scripts/test-native.py` ausführen: gesperrter Build,
Format, Core-Tests, Clippy, echte Wayland-Laufzeit und verpflichtende Nachweise.
Anleitung und Grenzen: [native Entwicklung](docs/NATIVE-DEVELOPMENT.de.md).
Die CI wiederholt amd64/ARM64 und prüft den Installer zusätzlich auf ARM64.
Cargo-Abhängigkeitsänderungen benötigen neue ursprüngliche Lizenztexte und
Abgleich des Image-Lizenzsammlers. Änderungen am Dienst-/Sitzungsaufbau müssen
bestehende Login-, Netzwerk- und Benutzerkonfigurationen berücksichtigen.

Die historische Regression bleibt zusätzlich: pytest, Ruff, mypy und betroffene
Windows-/Paketierungsprüfungen. QML-Nachweise ersetzen keine Rust-Abnahme.
Implementierung von tatsächlichen Hardwaretests trennen. Keine persönlichen
Schlüssel, Token, Hostprofile oder reale Projektcaches committen. Änderungen an
Releasebereitschaft benötigen nachvollziehbare Testnachweise.
