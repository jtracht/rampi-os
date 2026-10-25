# PAM und persönlicher Schlüsselbund: Startreihenfolge

Stand 26.10.2026: Die Implementierung hat die frische grafische AMD64-/ARM64-
Abnahme auf dem bisherigen PR-Kopf bestanden. Allgemeine CI 40177935066 und
native CI 40177934983 sind erfolgreich; ihre heruntergeladenen Nachweise wurden
unabhängig geprüft. Beide Konten haben mit dem tatsächlichen Rust-Adapter
gespeichert und nach erneuter PAM-Anmeldung ihre eigenen Geheimnisse gelesen.
Der getestete Merge-Stand war `64c926cd8926e04adffbda3a92bb175674b3761e`;
der ARM64-Programmhash war
`ad10f082dcfde99391da8217a91ae3a7a0fe43b6bf6a2dfd9d421586a220c3f9`.

Das native Entwicklungsrelease v0.6.0-dev.1 ist inzwischen veröffentlicht und
unabhängig geprüft. Es enthält diese Änderung noch nicht. Für die Integration
wird PR 46 mit dessen endgültigem Hauptstand
`cb5cebcc9fb958cca2652d799e531cb8243e0fb3` zusammengeführt und erneut geprüft.
Die früheren Nachweise ersetzen diese Prüfung und eine neue Image-Abnahme
nicht. Der belegte Gesamtstand bleibt 81/100, Linux-Konten/Login bei vier Punkten.
Die erfolgreiche Diagnose in einem wiederverwendeten Gast ist ausdrücklich
kein frischer Abnahmenachweis. Ein Windows-Testhost wird nicht verwendet.

Bei GNOME Keyring 48.0-1 kann der socketaktivierte Dienst seine Secret-Service-
Objekte bereits initialisieren, bevor PAM den ersten Login-Schlüsselbund erstellt.
Im untersuchten Fall lieferte ReadAlias danach einen gültigen Backend-Pfad,
Properties.Get scheiterte aber mit UnknownMethod, weil das D-Bus-Objekt fehlte.
Die exakt installierten Debian-Quellen wurden über APT heruntergeladen und gegen
den signierten Index geprüft. Der Dienst registriert seine vorhandenen
Sammlungen bei der Initialisierung des Secret Service.

Rampi verwendet weiterhin denselben vorhandenen GNOME-Dienst, seinen Socket
und PAM. Ein persönliches Standardprofil startet zunächst dessen pkcs11-Komponente;
die bestehende Rampi-Sitzung startet secrets nach der PAM-Anmeldung. Ein bereits
erreichbarer persönlicher systemd-/D-Bus wird wiederverwendet.

Der Installer erkennt nur die bekannte unveränderte systemweite Dienstkonfiguration.
Globale Anpassungen, persönliche Units/Drop-ins, Symlinks und vorhandene
Schlüsselbünde werden erhalten. Neue Konten erhalten das Standardprofil über
`/etc/skel`. Für kompatible vorhandene Konten erfolgen persönliche Schreibzugriffe
als deren UID; ein privater Checkout wird dabei nicht für andere Benutzer geöffnet.
Bei Deinstallation werden nur bytegleiche Rampi-Profile entfernt, keine Schlüsselbünde.

Die Container-Prüfung `tests/rust/test-keyring-profile.py` führt die tatsächlichen
Installer-Helfer mit gewöhnlichen Linux-Rechten aus. Sie prüft Eigentümer,
Wiederholung, private Checkout-Pfade, angepasste Profile, vorhandene Daten,
Symlinks und globale Overrides. Ihre synthetische Schlüsselbunddatei ist nur eine
Dateierhaltungsprüfung und kein Verschlüsselungsnachweis.

Der frische grafische Test muss mit dem tatsächlichen Rust-Adapter für beide
Benutzer speichern, fremde Dateizugriffe abweisen, sich jeweils abmelden und
nach erneuter PAM-Anmeldung die eigenen persistenten Geheimnisse wieder lesen.
Manuelle Entsperrung und Übergabe eines Schlüsselbundkennworts sind ausgeschlossen.
Der Prüfer verlangt die jeweiligen Kontonachweise und verwirft vorbereitete oder
wiederverwendete Gäste. Die Image-Prüfung verwendet die wirklich installierte
Vorlage und kontrolliert deren unveränderte Dateien.
