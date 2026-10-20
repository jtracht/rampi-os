import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
  id: dialog
  title: rampi.configuration.setup_complete ? "Einstellungen · persönliches Profil" : "Willkommen bei Rampi · Einrichtung"
  modal: true
  standardButtons: Dialog.Close
  property var host: rampi.configuration.hosts.length ? rampi.configuration.hosts[rampi.configuration.active_host] : ({})
  property bool addingHost: false
  property int editIndex: -1
  property string selectedVpnUuid: ""
  function loadHost(value) {
    hostName.text = value.name || "Windows";
    address.text = value.address || ""; username.text = value.username || "";
    port.value = value.port || 22; identity.text = value.identity || "";
    project.text = value.project || ""; resolution.text = value.resolution || "1280x720";
    verified.checked = false;
  }
  function showPage(index) { tabs.currentIndex = index; open(); }
  function hostValues() { return {name: hostName.text, address: address.text, username: username.text, port: port.value,
      identity: identity.text, project: project.text, resolution: resolution.text}; }
  onOpened: { addingHost = false; editIndex = rampi.configuration.hosts.length ? rampi.configuration.active_host : -1; loadHost(dialog.host); address.forceActiveFocus(); }
  contentItem: ColumnLayout {
    spacing: 12
    TabBar {
      id: tabs; objectName: "settingsTabs"; Layout.fillWidth: true
      onCurrentIndexChanged: { if (currentIndex === 2) rampi.refreshVpnProfiles(); if (currentIndex === 1) rampi.refreshWifi(false); }
      TabButton { text: "Host & SSH" }
      TabButton { text: "System" }
      TabButton { text: "VPN" }
      TabButton { text: "Kanban & Browser" }
      TabButton { text: "KI-Sitzungen" }
    }
    StackLayout {
      currentIndex: tabs.currentIndex
      Layout.fillWidth: true; Layout.fillHeight: true
      ScrollView {
        clip: true
        ColumnLayout {
          width: parent.width - 20; spacing: 12
          Label { text: "Windows 11 Pro · persönliche Verbindung"; font.pixelSize: 23; font.bold: true }
          Label { text: "Aktiver Host: " + (dialog.host.name || "Noch nicht eingerichtet") + (dialog.host.username ? " · " + dialog.host.username + "@" + dialog.host.address : ""); wrapMode: Text.WordWrap; Layout.fillWidth: true }
          ComboBox {
            id: hostPicker; objectName: "hostPicker"; Layout.fillWidth: true
            model: rampi.configuration.hosts.map(function(h) { return h.name + " · " + h.username + "@" + h.address; })
            currentIndex: dialog.editIndex
            onActivated: function(index) { dialog.addingHost = false; dialog.editIndex = index; dialog.loadHost(rampi.configuration.hosts[index]); }
          }
          RowLayout {
            RampiButton { objectName: "newHost"; text: "Neues Profil"; onClicked: { dialog.addingHost = true; dialog.editIndex = -1; dialog.loadHost({name: "Neuer Host"}); hostName.forceActiveFocus(); } }
            RampiButton { text: "Dieses Profil verwenden"; enabled: dialog.editIndex >= 0; onClicked: rampi.selectHost(dialog.editIndex) }
            RampiButton { text: "Profil entfernen"; enabled: dialog.editIndex >= 0; onClicked: removeProfile.open() }
          }
          Label { text: "Profilname" }
          TextField { id: hostName; objectName: "hostName"; Layout.fillWidth: true }
          Label { text: "Vor dem Verbinden die Fingerprints unabhängig am Windows-Host vergleichen. Ein Abruf allein bestätigt die Identität noch nicht."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          Label { text: "Hostname / VPN-IP" }
          TextField { id: address; objectName: "hostAddress"; placeholderText: "workstation.tailnet.ts.net"; Layout.fillWidth: true }
          Label { text: "Windows-Benutzername" }
          TextField { id: username; objectName: "hostUsername"; Layout.fillWidth: true }
          Label { text: "SSH-Port" }
          SpinBox { id: port; from: 1; to: 65535; value: dialog.host.port || 22; editable: true }
          Label { text: "Persönlicher privater SSH-Schlüssel · nur Dateipfad" }
          TextField { id: identity; text: dialog.host.identity || ""; placeholderText: "~/.ssh/id_ed25519"; Layout.fillWidth: true }
          RampiButton { text: "SSH-Schlüssel mit OpenSSH erzeugen"; onClicked: rampi.action("ssh-key", "") }
          RampiButton { text: "SSH-Hostschlüssel abrufen"; onClicked: { verified.checked = false; rampi.scanHost(dialog.hostValues()); } }
          TextArea { text: rampi.hostKey.fingerprints; readOnly: true; selectByMouse: true; textFormat: TextEdit.PlainText; wrapMode: TextEdit.Wrap; Layout.fillWidth: true }
          CheckBox { id: verified; text: "Fingerprints unabhängig am Windows-Host verglichen" }
          RampiButton {
            text: "Geprüfte Hostschlüssel speichern"
            enabled: verified.checked && rampi.hostKey.fingerprints !== ""
            onClicked: { rampi.trustHost(dialog.hostValues()); verified.checked = false; }
          }
          Label { text: "Projektverzeichnis auf Windows" }
          TextField { id: project; text: dialog.host.project || ""; placeholderText: "C:\\Projects\\MeinProjekt"; Layout.fillWidth: true }
          Label { text: "Streaming-Auflösung · Breite x Höhe" }
          TextField { id: resolution; placeholderText: "1280x720"; Layout.fillWidth: true }
          RampiButton {
            objectName: "saveHost"; text: dialog.addingHost || dialog.editIndex < 0 ? "Hostprofil hinzufügen" : "Hostprofil speichern"
            onClicked: {
              let creating = dialog.addingHost || dialog.editIndex < 0;
              if (rampi.saveHost(dialog.hostValues(), creating ? -1 : dialog.editIndex)) {
                dialog.addingHost = false;
                dialog.editIndex = creating ? rampi.configuration.hosts.length - 1 : dialog.editIndex;
                dialog.loadHost(rampi.configuration.hosts[dialog.editIndex]);
              }
            }
          }
          RampiButton { text: "Lokale Remote-Verbindungen schließen"; onClicked: rampi.disconnectClients() }
          Label { text: "Die offiziellen CLIs und psmux müssen im Windows-Benutzerkonto eingerichtet sein. Anmeldungen erfolgen in den jeweiligen offiziellen Programmen."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
      }
      ScrollView {
        ColumnLayout {
          width: parent.width - 20; spacing: 16
          Label { text: "Vorhandene Systemdienste"; font.pixelSize: 23; font.bold: true }
          WifiSettings { Layout.fillWidth: true }
          Label { text: "Weitere Systemdienste · BlueZ, polkit und PAM"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          RampiButton { text: "Bluetooth · Geräte koppeln"; onClicked: rampi.action("bluetooth", "") }
          RampiButton { text: "HDMI · Anzeige einstellen"; onClicked: rampi.action("display", "") }
          RampiButton { text: "Tastatur und Maus"; onClicked: rampi.action("keyboard", "") }
          RampiButton { text: "Linux-Systemkonsole öffnen"; onClicked: rampi.launch("console") }
          RampiButton { text: "Abschlussdiagnose / installierte Programme"; onClicked: rampi.action("diagnostics", "") }
          CheckBox { id: reducedMotion; text: "Bewegung reduzieren"; checked: rampi.configuration.reduce_motion }
          Label { text: "Neues Linux-Systemkonto · polkit fragt nach Administratorfreigabe"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          TextField { id: newUser; placeholderText: "Benutzername"; Layout.fillWidth: true }
          TextField { id: realName; placeholderText: "Anzeigename"; Layout.fillWidth: true }
          TextField { id: newPassword; placeholderText: "Passwort · mindestens 12 Zeichen"; echoMode: TextInput.Password; Layout.fillWidth: true }
          TextField { id: repeatPassword; placeholderText: "Passwort wiederholen"; echoMode: TextInput.Password; Layout.fillWidth: true }
          RampiButton {
            text: "Linux-Konto anlegen"
            enabled: newUser.text !== "" && newPassword.text.length >= 12 && newPassword.text === repeatPassword.text
            onClicked: { rampi.createUser(newUser.text, realName.text, newPassword.text); newPassword.clear(); repeatPassword.clear(); }
          }
          Label { text: "Benutzeranlage und Sprache: siehe Installationsanleitung.\nStrg+Alt+F2 öffnet den regulären TTY-Zugang."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
      }
      ScrollView {
        ColumnLayout {
          width: parent.width - 20; spacing: 16
          Label { text: "Tailscale & WireGuard"; font.pixelSize: 23; font.bold: true }
          Label { text: "VPN-Verbindungen verändern das systemweite Routing. polkit beziehungsweise der vorhandene Dienst entscheidet über Berechtigungen."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          RowLayout {
            RampiButton { text: "Tailscale verbinden"; onClicked: rampi.action("tailscale-up", "") }
            RampiButton { text: "Trennen"; onClicked: rampi.action("tailscale-down", "") }
            RampiButton { text: "Status"; onClicked: rampi.action("tailscale-status", "") }
          }
          Label { text: "WireGuard-Konfigurationsdatei" }
          TextField { id: wgFile; placeholderText: "/home/user/VPN.conf"; Layout.fillWidth: true }
          RampiButton { text: "In NetworkManager importieren"; enabled: !rampi.vpnProfiles.busy; onClicked: rampi.action("wg-import", wgFile.text) }
          RampiButton { text: "Persönliche Profile aktualisieren"; onClicked: rampi.refreshVpnProfiles() }
          Label { text: rampi.vpnProfiles.error; visible: text !== ""; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          ComboBox {
            id: vpnPicker; objectName: "vpnPicker"; Layout.fillWidth: true
            model: rampi.vpnProfiles.profiles; textRole: "label"; valueRole: "uuid"
            currentIndex: model.findIndex(function(p) { return p.uuid === dialog.selectedVpnUuid; })
            displayText: currentIndex < 0 ? "Persönliches WireGuard-Profil auswählen" : currentText
            onActivated: dialog.selectedVpnUuid = currentValue
          }
          RowLayout {
            RampiButton { objectName: "connectWireGuard"; text: "WireGuard verbinden"; enabled: vpnPicker.currentIndex >= 0 && !rampi.vpnProfiles.busy; onClicked: rampi.action("wg-up", vpnPicker.currentValue) }
            RampiButton { text: "Trennen"; enabled: vpnPicker.currentIndex >= 0 && !rampi.vpnProfiles.busy; onClicked: rampi.action("wg-down", vpnPicker.currentValue) }
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
          Label { text: "Spaltenreihenfolge · ein Name pro Zeile; leer übernimmt die Datenquelle"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          TextArea { id: boardColumns; objectName: "boardColumns"; text: rampi.configuration.board_columns.join("\n"); placeholderText: "Offen\nIn Arbeit\nReview\nErledigt"; Layout.fillWidth: true; wrapMode: TextEdit.Wrap }
          Label { text: "Zusätzliche Statuswerte der Datenquelle erscheinen automatisch rechts. Die Aufgaben selbst werden nicht verändert."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          Label { text: "Secret-Service-Profilname · kein Token im Konfigurationsfeld" }
          TextField { id: tokenKey; text: rampi.configuration.board_token_key; Layout.fillWidth: true }
          TextField { id: tokenAccount; visible: boardKind.currentText === "jira" || boardKind.currentText === "trello"; placeholderText: boardKind.currentText === "trello" ? "Trello API-Key" : "Jira E-Mail · bei OAuth leer lassen"; Layout.fillWidth: true }
          TextField { id: tokenValue; visible: boardKind.currentText !== "json"; placeholderText: "Persönliches Token · nur im Secret Service speichern"; echoMode: TextInput.Password; Layout.fillWidth: true }
          RampiButton {
            text: "Zugang im persönlichen Schlüsselspeicher speichern"
            visible: boardKind.currentText !== "json"
            enabled: tokenKey.text !== "" && tokenValue.text !== ""
            onClicked: { rampi.storeToken(tokenKey.text, boardKind.currentText, tokenAccount.text, tokenValue.text); tokenValue.clear(); }
          }
          Label { text: "Cloud-Connectoren sind implementiert, aber noch nicht gegen persönliche Anbieter-Konten validiert. Lokale JSON-Dateien benötigen kein Token."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          Label { text: "Browser-Startseite · HTTPS" }
          TextField { id: browserUrl; text: rampi.configuration.browser_url; Layout.fillWidth: true }
          Label { text: "Browserprofile, SSH-Schlüssel und Konfigurationen bleiben im persönlichen Linux-Konto."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
      }
      ScrollView {
        clip: true
        ColumnLayout {
          width: parent.width - 20; spacing: 18
          Label { text: "Persistente Windows-KI-Sitzungen"; font.pixelSize: 23; font.bold: true }
          Label { text: "Host: " + (dialog.host.name || "Nicht eingerichtet") + (dialog.host.username ? " · " + dialog.host.username : ""); wrapMode: Text.WordWrap; Layout.fillWidth: true }
          Label { text: "Pro Anbieter und Windows-Benutzer bleibt eine Sitzung erhalten. Öffnen verbindet erneut. Ein geändertes Projekt gilt beim nächsten Sitzungsstart; eine vorhandene Sitzung zuerst bewusst beenden."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
          RampiButton { text: "Sitzungen auf Windows prüfen"; onClicked: rampi.refreshSessions() }
          Repeater {
            model: rampi.sessions
            Frame {
              required property var modelData
              Layout.fillWidth: true
              contentItem: ColumnLayout {
                Label { text: modelData.title; font.pixelSize: 20; font.bold: true }
                Label { text: modelData.state; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout {
                  RampiButton { text: "Öffnen / wiederverbinden"; onClicked: rampi.launch(modelData.module) }
                  RampiButton { text: "Windows-Sitzung beenden"; enabled: modelData.state === "Läuft auf Windows"; onClicked: { stopSession.module = modelData.module; stopSession.open(); } }
                }
              }
            }
          }
          RampiButton { text: "Nur lokale Verbindungen schließen"; onClicked: rampi.disconnectClients() }
        }
      }
    }
    RowLayout {
      RampiButton {
        objectName: "saveGeneral"
        text: "Allgemeine Einstellungen speichern"
        onClicked: {
          if (rampi.save({board_kind: boardKind.currentText,
              board_source: boardSource.text, board_token_key: tokenKey.text,
              board_columns: boardColumns.text.split("\n").map(function(c) { return c.trim(); }).filter(function(c) { return c !== ""; }),
              browser_url: browserUrl.text, reduce_motion: reducedMotion.checked})) dialog.close();
        }
      }
      RampiButton { text: "Später einrichten"; onClicked: dialog.close() }
    }
  }
  Dialog {
    id: removeProfile; title: "Hostprofil entfernen?"; modal: true
    standardButtons: Dialog.Yes | Dialog.No
    Label { text: "Nur das ausgewählte Profil wird entfernt. SSH- und Streaming-Schlüssel sowie Windows-Prozesse bleiben erhalten."; width: 460; wrapMode: Text.WordWrap }
    onAccepted: { if (rampi.removeHost(dialog.editIndex)) { dialog.editIndex = rampi.configuration.hosts.length ? rampi.configuration.active_host : -1; dialog.loadHost(dialog.host); } }
  }
  Dialog {
    id: stopSession; property string module: ""; title: "Windows-KI-Sitzung beenden?"; modal: true
    standardButtons: Dialog.Yes | Dialog.No
    Label { text: "Der laufende KI-Prozess dieser Sitzung auf dem aktiven Windows-Host wird beendet. Zum bloßen Trennen stattdessen die lokale Verbindung schließen."; width: 460; wrapMode: Text.WordWrap }
    onAccepted: rampi.stopSession(module)
  }
}
