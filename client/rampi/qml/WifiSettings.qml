import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
  id: page
  property string selectedKey: ""
  readonly property var selected: picker.currentIndex >= 0 ? rampi.wifi.networks[picker.currentIndex] : ({})
  spacing: 12
  Label { text: "WLAN · NetworkManager"; font.pixelSize: 23; font.bold: true }
  RowLayout {
    RampiButton { objectName: "wifiScan"; text: "WLANs suchen"; enabled: !rampi.wifi.busy; onClicked: rampi.refreshWifi(true) }
    RampiButton { objectName: "wifiRadio"; text: rampi.wifi.enabled ? "WLAN ausschalten" : "WLAN einschalten"; enabled: !rampi.wifi.busy; onClicked: rampi.enableWifi(!rampi.wifi.enabled) }
    BusyIndicator { running: rampi.wifi.busy; visible: running; implicitWidth: 28; implicitHeight: 28 }
  }
  Label { text: rampi.wifi.error; visible: text !== ""; textFormat: Text.PlainText; wrapMode: Text.WordWrap; Layout.fillWidth: true }
  ComboBox {
    id: picker; objectName: "wifiPicker"; Layout.fillWidth: true
    model: rampi.wifi.networks; textRole: "label"; valueRole: "key"
    currentIndex: model.findIndex(function(n) { return n.key === page.selectedKey; })
    displayText: currentIndex < 0 ? "WLAN auswählen" : currentText
    onActivated: { page.selectedKey = currentValue; password.clear(); }
    enabled: !rampi.wifi.busy
  }
  Label {
    text: page.selected.saved ? "Gespeichertes Profil wird unverändert wiederverwendet." : "Neue Profile und Zugangsdaten werden nur für dein Linux-Konto in NetworkManager gespeichert."
    wrapMode: Text.WordWrap; Layout.fillWidth: true
  }
  TextField {
    id: password; objectName: "wifiPassword"; placeholderText: "WLAN-Kennwort"
    echoMode: TextInput.Password; selectByMouse: true; Layout.fillWidth: true
    visible: !!page.selected.supported && !page.selected.saved && page.selected.mode !== "open"
    enabled: !rampi.wifi.busy
    onAccepted: if (connect.enabled) connect.clicked()
  }
  RampiButton {
    id: connect; objectName: "wifiConnect"; text: page.selected.active ? "Verbunden" : "Verbinden"
    enabled: !rampi.wifi.busy && !!page.selected.supported && !page.selected.active && (page.selected.saved || page.selected.mode === "open" || password.text.length > 0)
    onClicked: { rampi.connectWifi(page.selectedKey, password.text); password.clear(); }
  }
  RampiButton { objectName: "wifiDisconnect"; text: "Verbindung trennen"; enabled: !!page.selected.active && !rampi.wifi.busy; onClicked: { password.clear(); rampi.disconnectWifi(page.selectedKey); } }
  RampiButton { text: "Erweiterte Netzwerkverwaltung"; onClicked: { password.clear(); rampi.action("wifi-connect", ""); } }
  Label { text: "Versteckte Netze, Unternehmens-WLAN und Kennwortänderungen im erweiterten Dialog einrichten. Das Ein-/Ausschalten von WLAN gilt für das ganze Gerät."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
  onVisibleChanged: if (!visible) password.clear()
}
