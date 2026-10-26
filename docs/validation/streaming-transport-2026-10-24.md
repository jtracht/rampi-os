# Native Streaming-Integration: Transport in Entwicklung

Dieser Stand ergänzt eine notwendige Teilkomponente. Die bestehende Oberfläche
startet Streaming weiterhin extern; eingebettetes Streaming ist damit ausdrücklich
noch nicht implementiert oder abgenommen. Es gibt keinen zusätzlichen Fortschrittspunkt.

## Vorhandene Komponenten

`moonlight-common` ist auf Quellstand
`bf323482e9a2b01c332661d902b7189f70ab5ce8` festgelegt. Verwendet werden dessen
vorhandene HTTP-/PIN-/Host-Schnittstellen mit OpenSSL. Die voreingestellten
HTTP-Clients mit abgeschalteter Serverprüfung werden nicht aktiviert. Die
eigene schlanke `RequestClient`-Anbindung verwendet das installierte libcurl,
gegenseitiges TLS und den öffentlichen Schlüssel des durch PIN-Kopplung
bestätigten Servers als verpflichtenden SPKI-Pin. Ein anderer Schlüssel wird
abgewiesen. Selbstsignierte GameStream-Zertifikate benötigen dadurch weder
eine öffentliche CA noch einen zum Hostnamen passenden Zertifikatsnamen.

Private Schlüssel werden an libcurl als Speicherblobs übergeben. Keine
Kommandozeilenargumente, Debug-Ausgaben oder Transportfehler enthalten diese
Schlüssel oder vollständige Anfrageadressen. Weiterleitungen werden abgewiesen,
Antworten auf 4 MiB und Verbindungs-/Gesamtzeiten begrenzt. Als HTTPS-pflichtig
bezeichnete Anbieter-Endpunkte dürfen nicht per HTTP aufgerufen werden.

Die separate C-Streaming-Anbindung der Community-Bibliothek setzt inzwischen
Rust 1.99 für eine optionale variadische Logfunktion voraus. Sie ist nicht
aktiviert. Stattdessen sind ausschließlich öffentliche Deklarationen des
vorhandenen offiziellen Moonlight-Streamingkerns für die bereits verwendete
Version 2.7.1 generiert. Die ABI-Layouts sind für Linux AMD64/ARM64 festgelegt;
eine unbekannte unversionierte Bibliothek darf später nicht geladen werden.
Der optionale variadische Protokolllogger bleibt unbesetzt. Paketquellen,
Upstream-Revisionen und Lizenzhinweise liegen bei den Headern.

## Tatsächlich geprüft

Rust-Tests innerhalb des Linux-Docker-SDKs verwenden echte lokale TLS-Sockets
und OpenSSL, einschließlich angeforderter Clientzertifikate. Der richtige
Server-Pin empfängt die Anfrage und liefert die erwarteten Bytes. Ein fremder
Pin beendet den Ablauf, bevor der fremde Server eine Anwendungsanfrage erhält.
Fehlende Identität, verbotener Klartext-Endpunkt, HTTP-Weiterleitung und eine
zu große Antwort werden abgewiesen. Clippy mit Warnungen als Fehler besteht.
Auch Formatprüfung, Clippy für die gesamte Workspace und deren Rust-Tests
bestehen zusammen. Der vorhandene Lizenzsammler findet die ursprünglichen Texte
für alle 438 aufgelösten Cargo-Abhängigkeiten. Das ersetzt nicht die spätere
Release-Prüfung einschließlich vollständiger GPL-Quellbeigaben.

Diese Tests sind keine Sunshine-, Video-, Audio-, Eingabe- oder GTK-Abnahme.
Decoderanbindung, private dauerhafte Identitäten, gekoppelte Sitzungssteuerung,
die integrierte Seite und durchgängige tatsächliche Sunshine-Tests bleiben
erforderlich. Es wird kein eigener Netzwerk- oder Verschlüsselungsalgorithmus
entwickelt. Das System verwendet weiterhin die vorhandene stabile Rust-Werkzeugkette.
