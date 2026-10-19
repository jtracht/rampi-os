import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
  id: dialog
  title: rampi.configuration.setup_complete ? "Einstellungen · persönliches Profil" : "Willkommen bei Rampi · Einrichtung"
  modal: true
  standardButtons: Dialog.Close
  property var host: rampi.configuration.hosts.length ? rampi.configuration.hosts[rampi.configuration.active_host] : ({})
  function showPage(index) { tabs.currentIndex = index; open(); }
  onOpened: address.forceActiveFocus()
  contentItem: ColumnLayout {
    spacing: 12
    TabBar {
      id: tabs; Layout.fillWidth: true
      TabButton { text: "Host & SSH" }
      TabButton { text: "System" }
      TabButton { text: "VPN" }
      TabButton { text: "Kanban & Browser" }
    }
    StackLayout {
      currentIndex: tabs.currentIndex
      Layout.fillWidth: true; Layout.fillHeight: true
      ScrollView {
        clip: true
        ColumnLayout {
          width: parent.width - 20; spacing: 12
          Label { text: "Windows 11 Pro · persönliche Verbindung"; font.pixelSize: 23; font.bold: true }
          Label { text: "Vor dem Verbinden den SSH-Hostschlüssel über einen unabhängigen Kanal prüfen und in known_hosts übernehmen."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          Label { text: "Hostname / VPN-IP" }
          TextField { id: address; text: dialog.host.address || ""; placeholderText: "workstation.tailnet.ts.net"; Layout.fillWidth: true }
          Label { text: "Windows-Benutzername" }
          TextField { id: username; text: dialog.host.username || ""; Layout.fillWidth: true }
          Label { text: "SSH-Port" }
          SpinBox { id: port; from: 1; to: 65535; value: dialog.host.port || 22; editable: true }
          Label { text: "Persönlicher privater SSH-Schlüssel · nur Dateipfad" }
          TextField { id: identity; text: dialog.host.identity || ""; placeholderText: "~/.ssh/id_ed25519"; Layout.fillWidth: true }
          Button { text: "SSH-Schlüssel mit OpenSSH erzeugen"; onClicked: rampi.action("ssh-key", "") }
          Label { text: "Projektverzeichnis auf Windows" }
          TextField { id: project; text: dialog.host.project || ""; placeholderText: "C:\\Projects\\MeinProjekt"; Layout.fillWidth: true }
          Label { text: "Die offiziellen CLIs und psmux müssen im Windows-Benutzerkonto eingerichtet sein. Anmeldungen erfolgen in den jeweiligen offiziellen Programmen."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
      }
      ScrollView {
        ColumnLayout {
          width: parent.width - 20; spacing: 16
          Label { text: "Vorhandene Systemdienste"; font.pixelSize: 23; font.bold: true }
          Label { text: "Die Systemdialoge verwenden NetworkManager, BlueZ und polkit. Linux-Konten und Login bleiben unter PAM-Verwaltung."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          Button { text: "WLANs suchen"; onClicked: rampi.action("wifi-scan", "") }
          Button { text: "Netzwerkverbindungen einrichten"; onClicked: rampi.action("wifi-connect", "") }
          Button { text: "Bluetooth · Geräte koppeln"; onClicked: rampi.action("bluetooth", "") }
          Button { text: "HDMI · Anzeige einstellen"; onClicked: rampi.action("display", "") }
          Button { text: "Tastatur und Maus"; onClicked: rampi.action("keyboard", "") }
          Button { text: "Linux-Systemkonsole öffnen"; onClicked: rampi.launch("console") }
          Button { text: "Abschlussdiagnose / installierte Programme"; onClicked: rampi.action("diagnostics", "") }
          CheckBox { id: reducedMotion; text: "Bewegung reduzieren"; checked: rampi.configuration.reduce_motion }
          Label { text: "Benutzeranlage und Sprache: siehe Installationsanleitung.\nStrg+Alt+F2 öffnet den regulären TTY-Zugang."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
      }
      ScrollView {
        ColumnLayout {
          width: parent.width - 20; spacing: 16
          Label { text: "Tailscale & WireGuard"; font.pixelSize: 23; font.bold: true }
          Label { text: "VPN-Verbindungen verändern das systemweite Routing. polkit beziehungsweise der vorhandene Dienst entscheidet über Berechtigungen."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          RowLayout {
            Button { text: "Tailscale verbinden"; onClicked: rampi.action("tailscale-up", "") }
            Button { text: "Trennen"; onClicked: rampi.action("tailscale-down", "") }
            Button { text: "Status"; onClicked: rampi.action("tailscale-status", "") }
          }
          Label { text: "WireGuard-Konfigurationsdatei" }
          TextField { id: wgFile; placeholderText: "/home/user/VPN.conf"; Layout.fillWidth: true }
          Button { text: "In NetworkManager importieren"; onClicked: rampi.action("wg-import", wgFile.text) }
          Button { text: "Profile anzeigen"; onClicked: rampi.action("wg-status", "") }
          TextField { id: wgUuid; placeholderText: "UUID des NetworkManager-Profils"; Layout.fillWidth: true }
          RowLayout {
            Button { text: "WireGuard verbinden"; onClicked: rampi.action("wg-up", wgUuid.text) }
            Button { text: "Trennen"; onClicked: rampi.action("wg-down", wgUuid.text) }
          }
          Label { text: "Persönliche VPN-Profile vor der Verwendung in NetworkManager auf den eigenen Linux-Benutzer beschränken. Tailscale hat eine systemweite Geräteidentität."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
      }
      ScrollView {
        ColumnLayout {
          width: parent.width - 20; spacing: 12
          Label { text: "Kanban · ausschließlich Lesezugriff"; font.pixelSize: 23; font.bold: true }
          ComboBox { id: boardKind; model: ["json", "github", "trello", "jira", "asana", "notion"]; currentIndex: Math.max(0, model.indexOf(rampi.configuration.board_kind)) }
          Label { text: "Datenquelle · Datei oder Anbieter-Projekt-ID (Format siehe Dokumentation)" }
          TextField { id: boardSource; text: rampi.configuration.board_source; Layout.fillWidth: true }
          Label { text: "Secret-Service-Profilname · kein Token im Konfigurationsfeld" }
          TextField { id: tokenKey; text: rampi.configuration.board_token_key; Layout.fillWidth: true }
          Label { text: "Cloud-Connectoren sind implementiert, aber noch nicht gegen persönliche Anbieter-Konten validiert. Lokale JSON-Dateien benötigen kein Token."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          Label { text: "Browser-Startseite · HTTPS" }
          TextField { id: browserUrl; text: rampi.configuration.browser_url; Layout.fillWidth: true }
          Label { text: "Browserprofile, SSH-Schlüssel und Konfigurationen bleiben im persönlichen Linux-Konto."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
      }
    }
    RowLayout {
      Button {
        text: "Speichern"
        onClicked: {
          if (rampi.save({address: address.text, username: username.text, port: port.value,
              identity: identity.text, project: project.text, board_kind: boardKind.currentText,
              board_source: boardSource.text, board_token_key: tokenKey.text,
              browser_url: browserUrl.text, reduce_motion: reducedMotion.checked})) dialog.close();
        }
      }
      Button { text: "Später einrichten"; onClicked: dialog.close() }
    }
  }
}
