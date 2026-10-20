import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

FullPage {
  id: pairing
  objectName: "bluetoothPairingDialog"
  title: "Bluetooth-Kopplung"
  property var request: rampi.bluetoothChallenge
  property int activeRequestId: 0
  readonly property bool needsInput: request.kind === "RequestPinCode" || request.kind === "RequestPasskey"
  readonly property var device: rampi.bluetooth.devices.find(function(d) { return d.path === pairing.request.device; }) || ({})
  onRequestChanged: {
    if (request.id && request.id !== activeRequestId) {
      activeRequestId = request.id; pin.clear(); reviewed.checked = false; open();
    } else if (!request.id) { activeRequestId = 0; close(); }
  }
  onOpened: { if (needsInput) pin.forceActiveFocus(); else rejectButton.forceActiveFocus(); }
  onRejected: {
    if (!request.id) return;
    if (request.display) rampi.bluetoothAction("cancel-pair", request.device, false);
    else rampi.answerBluetooth(request.id, false, "");
  }
  contentItem: ColumnLayout {
    spacing: 16
    Label { text: pairing.device.name || "Bluetooth-Gerät"; font.bold: true; font.pixelSize: 24; textFormat: Text.PlainText; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Label { text: pairing.device.address || pairing.request.device || ""; textFormat: Text.PlainText; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Label { text: pairing.request.display ? "Diesen Code auf dem anderen Gerät eingeben und dort bestätigen:" : pairing.needsInput ? "Den am anderen Gerät angezeigten PIN oder Passkey eingeben:" : pairing.request.kind === "RequestConfirmation" ? "Stimmen die Codes auf beiden Geräten überein?" : "Die Verbindung dieses Geräts zulassen?"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Label { objectName: "bluetoothPairingCode"; text: pairing.request.code || ""; visible: text !== ""; font.family: "monospace"; font.pixelSize: 42; textFormat: Text.PlainText }
    TextField { id: pin; objectName: "bluetoothPairingPin"; visible: pairing.needsInput; maximumLength: pairing.request.kind === "RequestPasskey" ? 6 : 16; echoMode: TextInput.Password; Layout.fillWidth: true; onAccepted: if (acceptButton.enabled) acceptButton.clicked()
      validator: RegularExpressionValidator { regularExpression: pairing.request.kind === "RequestPasskey" ? /^[0-9]{0,6}$/ : /^[A-Za-z0-9]{0,16}$/ }
    }
    CheckBox { id: reviewed; objectName: "bluetoothPairingReviewed"; visible: !pairing.needsInput && !pairing.request.display; text: pairing.request.kind === "RequestConfirmation" ? "Codes bewusst verglichen: sie stimmen überein" : "Ich möchte dieses Gerät zulassen" }
    RowLayout {
      RampiButton { id: rejectButton; objectName: "bluetoothPairingReject"; text: "Abbrechen"; onClicked: pairing.reject() }
      RampiButton { id: acceptButton; objectName: "bluetoothPairingAccept"; text: "Bestätigen"; visible: !pairing.request.display; enabled: pairing.needsInput ? pin.text.length > 0 : reviewed.checked; onClicked: { rampi.answerBluetooth(pairing.request.id, true, pin.text); pin.clear(); } }
    }
  }
  onClosed: pin.clear()
}
