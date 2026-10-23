import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
  id: panel
  property string adapterPath: ""
  property string devicePath: ""
  property string confirmedPath: ""
  property string confirmedAction: ""
  property bool confirmedValue: false
  readonly property var adapter: adapterPicker.currentIndex >= 0 ? rampi.bluetooth.adapters[adapterPicker.currentIndex] : ({})
  readonly property var devices: rampi.bluetooth.devices.filter(function(d) { return d.adapter === panel.adapter.path; })
  readonly property var device: devicePicker.currentIndex >= 0 ? devices[devicePicker.currentIndex] : ({})
  spacing: 12
  Label { text: "Bluetooth · BlueZ"; font.pixelSize: 23; font.bold: true }
  Label { text: rampi.bluetooth.error; visible: text !== ""; textFormat: Text.PlainText; wrapMode: Text.WordWrap; Layout.fillWidth: true }
  ComboBox {
    id: adapterPicker; objectName: "bluetoothAdapter"; Layout.fillWidth: true
    model: rampi.bluetooth.adapters; textRole: "name"; valueRole: "path"
    currentIndex: panel.adapterPath === "" && rampi.bluetooth.adapters.length > 0 ? 0 : model.findIndex(function(a) { return a.path === panel.adapterPath; })
    onActivated: { panel.adapterPath = currentValue; panel.devicePath = ""; }
    displayText: currentIndex < 0 ? "Bluetooth-Adapter auswählen" : currentText
  }
  RowLayout {
    RampiButton { objectName: "bluetoothRefresh"; text: "Aktualisieren"; onClicked: rampi.refreshBluetooth() }
    RampiButton {
      objectName: "bluetoothPower"; text: panel.adapter.powered ? "Bluetooth ausschalten" : "Bluetooth einschalten"
      enabled: !!panel.adapter.path && !rampi.bluetooth.busy
      onClicked: {
        if (panel.adapter.powered) panel.confirm("power", panel.adapter.path, false, "Bluetooth ausschalten? Alle verbundenen Geräte werden getrennt.");
        else rampi.bluetoothAction("power", panel.adapter.path, true);
      }
    }
    RampiButton { objectName: "bluetoothScan"; text: panel.adapter.own_scan ? "Suche beenden" : "Geräte suchen"; enabled: !!panel.adapter.powered && !rampi.bluetooth.busy; onClicked: rampi.bluetoothAction(panel.adapter.own_scan ? "stop-scan" : "scan", panel.adapter.path, false) }
  }
  BusyIndicator { running: rampi.bluetooth.busy || rampi.bluetooth.loading; visible: running; implicitWidth: 28; implicitHeight: 28 }
  ComboBox {
    id: devicePicker; objectName: "bluetoothDevice"; Layout.fillWidth: true
    model: panel.devices; textRole: "label"; valueRole: "path"
    currentIndex: model.findIndex(function(d) { return d.path === panel.devicePath; })
    onActivated: panel.devicePath = currentValue
    displayText: currentIndex < 0 ? "Bluetooth-Gerät auswählen" : currentText
    enabled: !rampi.bluetooth.busy
  }
  RowLayout {
    RampiButton { objectName: "bluetoothPair"; text: "Koppeln"; enabled: !!panel.device.path && !panel.device.paired && !rampi.bluetooth.busy; onClicked: rampi.bluetoothAction("pair", panel.device.path, false) }
    RampiButton { objectName: "bluetoothConnect"; text: panel.device.connected ? "Trennen" : "Verbinden"; enabled: !!panel.device.paired && !rampi.bluetooth.busy; onClicked: rampi.bluetoothAction(panel.device.connected ? "disconnect" : "connect", panel.device.path, false) }
    RampiButton { objectName: "bluetoothTrust"; text: panel.device.trusted ? "Vertrauen entfernen" : "Dauerhaft vertrauen"; enabled: !!panel.device.paired && !rampi.bluetooth.busy; onClicked: panel.confirm("trust", panel.device.path, !panel.device.trusted, "Vertrauen für " + panel.device.name + " ändern? Die Einstellung gilt für alle Benutzer dieses Geräts.") }
    RampiButton { objectName: "bluetoothRemove"; text: "Kopplung entfernen"; enabled: !!panel.device.paired && !rampi.bluetooth.busy; onClicked: panel.confirm("remove", panel.device.path, false, "Kopplung mit " + panel.device.name + " für alle Benutzer entfernen?") }
  }
  Label { text: "Adapter, Kopplungen und Vertrauen werden systemweit von BlueZ verwaltet. PINs und Codes werden nur während der Kopplung angezeigt. Neue Geräte erhalten nicht automatisch dauerhaftes Vertrauen."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
  function confirm(action, path, value, text) {
    confirmedAction = action; confirmedPath = path; confirmedValue = value;
    confirmationText.text = text; confirmation.open();
  }
  FullPage {
    id: confirmation; objectName: "bluetoothActionConfirmation"; title: "Bluetooth bestätigen"
    contentItem: ColumnLayout {
      spacing: 16
      Label { id: confirmationText; Layout.fillWidth: true; textFormat: Text.PlainText; wrapMode: Text.WordWrap }
      RowLayout {
        RampiButton { id: cancelAction; text: "Abbrechen"; onClicked: confirmation.reject() }
        RampiButton { objectName: "bluetoothConfirmYes"; text: "Bestätigen"; onClicked: confirmation.accept() }
      }
    }
    onOpened: cancelAction.forceActiveFocus()
    onAccepted: rampi.bluetoothAction(panel.confirmedAction, panel.confirmedPath, panel.confirmedValue)
  }
  onVisibleChanged: { if (visible) rampi.refreshBluetooth(); else rampi.stopBluetoothDiscovery(); }
}
