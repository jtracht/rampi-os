# Virtuelle Linux-Abnahme · 20. Oktober 2026

Lokaler Entwicklungsnachweis, noch keine abschließende ARM64-CI-Freigabe:

- Offizielles Debian-13-Generic-Image `20261017-2634`, amd64, festgelegte SHA512;
  QEMU/TCG mit 1 GiB und vier CPUs im Docker-Werkzeugcontainer. Keine Weitergabe
  von Hostgeräten, Hostnetzwerk, privaten Schlüsseln oder Benutzerverzeichnissen.
- Originaler Debian-Kernel `6.12.113+deb13-amd64`, tatsächliches systemd,
  NetworkManager, wpa_supplicant, hostapd und dnsmasq.
- Linux `mac80211_hwsim` erzeugt zwei WLAN-Radios. Der Zugangspunkt liegt in
  einem getrennten Netzwerk-Namensraum, der Client bleibt bei NetworkManager.
- Ein normaler Linux-Benutzer verwendet den unveränderten Rampi-WLAN-Adapter.
  Die Test-Richtlinie erlaubt ausschließlich dessen NetworkManager-Aktionen;
  reale Desktop-Freigaben bleiben eine gesonderte Policy-/Login-Prüfung.
- Tatsächlich bestanden: WPA2-Anmeldung, DHCP-Adresse, IP-Rundlauf über WLAN,
  Trennen, Ablehnung eines falschen Kennworts und erneute Anmeldung mit korrektem
  Kennwort. Marker `RAMPI_WIFI_LIVE_OK`, abschließend `RAMPI_GUEST_EXIT=0`.
- Zwei Bluetooth-HCI-Controller durch den echten Linux-Treiber `hci_vhci` und
  BlueZ `btvirt` ebenfalls nachgewiesen; vollständige Kopplung noch offen.

Die lokalen Nachweise liegen unter `artifacts/virtual-wifi-local/`. Die Harness
steht in `scripts/test-virtual-linux.py` und `scripts/virtual/`. Der optionale
vorbereitete OS-Cache dient ausschließlich lokalen Entwicklungsdurchläufen;
eine CI-Abnahme muss vom festgelegten Originalimage neu starten. VM-Disks und
Cloud-Init-Dateien werden nicht öffentlich als Testartefakte hochgeladen.

Dies belegt echte Softwareprotokolle auf virtuellen Geräten. Physische Funk-,
Pi-GPU- und Pi-Latenzwerte werden dadurch nicht nachgewiesen. Die Gesamtziele
bis mindestens 85 % sind weiterhin aktiv; dieser Nachweis ersetzt sie nicht.
