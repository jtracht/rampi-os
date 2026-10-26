import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
  id: window
  width: 1600; height: 900
  minimumWidth: 960; minimumHeight: 540
  visible: true
  visibility: windowed ? Window.Windowed : Window.FullScreen
  title: "Rampi"
  color: "#080f16"
  palette.window: "#101c26"
  palette.windowText: "#edf3fa"
  palette.base: "#080f16"
  palette.text: "#edf3fa"
  palette.button: "#253a4a"
  palette.buttonText: "#edf3fa"
  palette.highlight: "#087cf5"
  property var navigationStack: []
  property string lastMessage: ""
  signal showMessageDetails()
  onShowMessageDetails: notification.open()
  property alias feedback: interactionFeedback
  InteractionFeedback { id: interactionFeedback; objectName: "interactionFeedback" }
  property int selected: 0
  property string page: "dashboard"
  property bool keyboardMode: false
  property var selectedCard: ({title: "", description: "", project: "", priority: "", status: ""})
  readonly property var modules: [
    {title: "Kanban Board", subtitle: "Projekte im Blick", caption: "READ ONLY  |  PROJECTS", symbol: "▥", accent: "#ff3c61", key: "kanban", dark: false},
    {title: "Remote Desktop", subtitle: "Deine Windows-Workstation", caption: "STREAMING  |  RDP", symbol: "▱", accent: "#4934c8", key: "remote", dark: false},
    {title: "Webbrowser", subtitle: "Dein Fenster ins Web", caption: "BROWSE  |  WORK  |  STREAM", symbol: "◎", accent: "#1d3448", key: "browser", dark: false}
  ]
  function activate(index) {
    selected = index;
    let key = modules[index].key;
    if (key === "kanban" || key === "remote") page = key;
    else rampi.launch(key);
  }
  Shortcut { sequence: "Ctrl+Alt+Home"; onActivated: { while (window.navigationStack.length) window.navigationStack[window.navigationStack.length - 1].reject(); window.page = "dashboard"; window.raise(); window.requestActivate(); } }
  Shortcut {
    sequence: "Escape"
    enabled: window.navigationStack.length === 0
    onActivated: window.page = "dashboard"
  }
  Shortcut { sequence: "Ctrl+,"; onActivated: settings.open() }
  Shortcut { sequence: "F11"; onActivated: window.visibility = window.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen }
  Component.onCompleted: if (!rampi.configuration.setup_complete && showSetup) setupWizard.open()
  BluetoothPairingDialog { id: bluetoothPairing }

  Item {
    id: stage
    enabled: window.navigationStack.length === 0
    width: 1600; height: 900
    scale: Math.min(window.width / width, window.height / height)

    RowLayout {
      x: 26; y: 18; width: 1548; height: 100
      spacing: 16
      Image { visible: rampi.logoUrl !== ""; source: rampi.logoUrl; sourceClipRect: Qt.rect(75, 100, 1100, 730); Layout.preferredWidth: 78; Layout.preferredHeight: 85; fillMode: Image.PreserveAspectFit }
      Column {
        spacing: 0
        Text { text: "Rampi"; font.pixelSize: 62; font.weight: Font.Bold; font.letterSpacing: -2; color: "#f5f7fa" }
        Text { text: "R E M O T E   R A S P B E R R Y   P I   O S"; font.pixelSize: 10; color: "#edf3ff" }
      }
      Rectangle { Layout.leftMargin: 22; Layout.rightMargin: 12; width: 1; height: 55; color: "#566978" }
      Text { text: "SMALL PI.\nBIG REACH.\nREAL WORK."; font.pixelSize: 11; font.letterSpacing: 3; lineHeight: 1.5; color: "#a7b6c6" }
      Item { Layout.fillWidth: true }
      Repeater {
        model: [{label: "Netzwerk", key: "network", icon: "wifi"}, {label: "Bluetooth", key: "bluetooth", icon: "bluetooth"}, {label: "VPN", key: "vpn", icon: "shield-check"}]
        RampiButton {
          objectName: "dashboard-" + modelData.key
          text: modelData.label + "\n" + rampi.status[modelData.key]
          icon.source: "../icons/" + modelData.icon + ".svg"
          icon.color: "#19d6b2"
          Accessible.name: modelData.label + " einstellen"
          onClicked: settings.showPage(modelData.key === "network" ? 2 : modelData.key === "bluetooth" ? 3 : 4)
        }
      }
      Column {
        Layout.leftMargin: 12
        Text { id: clock; text: Qt.formatTime(new Date(), "HH:mm"); color: "#f7f8fa"; font.pixelSize: 27; horizontalAlignment: Text.AlignRight; width: 115 }
        Text { text: Qt.formatDate(new Date(), "ddd, dd. MMM"); color: "#9badbe"; font.pixelSize: 12; width: 115; horizontalAlignment: Text.AlignRight }
        Timer { interval: 1000; repeat: true; running: true; onTriggered: clock.text = Qt.formatTime(new Date(), "HH:mm") }
      }
    }

    Row {
      id: tiles
      x: 18; y: 132; width: 1564; height: 275
      spacing: 2
      visible: window.page === "dashboard"
      Repeater {
        id: tileRepeater
        model: window.modules
        LiquidTile {
          required property var modelData
          required property int index
          width: (tiles.width - 10) / 6; height: tiles.height
          title: modelData.title; subtitle: modelData.subtitle
          caption: modelData.caption; symbol: modelData.symbol
          iconFile: ["columns-3", "terminal", "asterisk", "sparkles", "monitor", "globe"][index]
          startupDelay: index * 35
          accent: modelData.accent; darkInk: modelData.dark
          selected: window.selected === index
          reducedMotion: rampi.configuration.reduce_motion
          onActiveFocusChanged: if (activeFocus) window.selected = index
          onActivated: window.activate(index)
          Keys.onRightPressed: { window.keyboardMode = true; tileRepeater.itemAt((index + 1) % window.modules.length).forceActiveFocus(); }
          Keys.onLeftPressed: { window.keyboardMode = true; tileRepeater.itemAt((index + window.modules.length - 1) % window.modules.length).forceActiveFocus(); }
          Component.onCompleted: if (index === 0) forceActiveFocus()
        }
      }
    }

    Panel {
      id: boardPanel
      x: 26; y: window.page === "kanban" ? 136 : 420
      width: window.page === "kanban" ? 1548 : 800
      height: window.page === "kanban" ? 650 : 365
      visible: window.page === "dashboard" || window.page === "kanban"
      ColumnLayout {
        anchors.fill: parent; anchors.margins: 17; spacing: 14
        RowLayout {
          Text { text: "▥"; color: "#ff486b"; font.pixelSize: 35 }
          Column {
            Text { text: rampi.board.title; color: "#edf4ff"; font.pixelSize: 22; font.bold: true }
            Text { text: (rampi.board.cached ? "Offline-Cache · " : "") + "Projektübersicht · Nur lesen"; color: "#9eb0c2"; font.pixelSize: 13 }
          }
          Item { Layout.fillWidth: true }
          Text { text: rampi.board.count + " / " + rampi.board.total + " Karten"; color: "#a9b8c7"; font.pixelSize: 12 }
          RampiButton { text: "↻"; Accessible.name: "Kanban aktualisieren"; onClicked: rampi.refreshBoard() }
        }
        TextField {
          id: boardSearch; objectName: "boardSearch"
          visible: window.page === "kanban"
          Layout.fillWidth: true
          placeholderText: "Titel, Beschreibung, Projekt oder Priorität suchen …"
          text: rampi.board.filters.query
          onTextChanged: rampi.search(text)
        }
        RowLayout {
          visible: window.page === "kanban"; Layout.fillWidth: true
          ComboBox {
            id: projectFilter; objectName: "projectFilter"; Layout.fillWidth: true
            model: ["Alle Projekte"].concat(rampi.board.projects)
            currentIndex: rampi.board.filters.project ? rampi.board.projects.indexOf(rampi.board.filters.project) + 1 : 0
            onActivated: rampi.filterBoard(currentIndex > 0 ? currentText : "",
                priorityFilter.currentIndex > 0 ? priorityFilter.currentText : "",
                statusFilter.currentIndex > 0 ? statusFilter.currentText : "")
          }
          ComboBox {
            id: priorityFilter; objectName: "priorityFilter"; Layout.fillWidth: true
            model: ["Alle Prioritäten"].concat(rampi.board.priorities)
            currentIndex: rampi.board.filters.priority ? rampi.board.priorities.indexOf(rampi.board.filters.priority) + 1 : 0
            onActivated: rampi.filterBoard(projectFilter.currentIndex > 0 ? projectFilter.currentText : "",
                currentIndex > 0 ? currentText : "", statusFilter.currentIndex > 0 ? statusFilter.currentText : "")
          }
          ComboBox {
            id: statusFilter; objectName: "statusFilter"; Layout.fillWidth: true
            model: ["Alle Status"].concat(rampi.board.statuses)
            currentIndex: rampi.board.filters.status ? rampi.board.statuses.indexOf(rampi.board.filters.status) + 1 : 0
            onActivated: rampi.filterBoard(projectFilter.currentIndex > 0 ? projectFilter.currentText : "",
                priorityFilter.currentIndex > 0 ? priorityFilter.currentText : "", currentIndex > 0 ? currentText : "")
          }
          RampiButton { objectName: "clearBoardFilters"; text: "Zurücksetzen"; onClicked: { boardSearch.clear(); projectFilter.currentIndex = 0; priorityFilter.currentIndex = 0; statusFilter.currentIndex = 0; rampi.filterBoard("", "", ""); } }
        }
        Text {
          visible: rampi.board.warning !== ""
          text: rampi.board.warning; color: "#a8b8c8"; font.pixelSize: 13
          wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
        Flickable {
          Layout.fillWidth: true; Layout.fillHeight: true
          contentWidth: boardColumns.width; contentHeight: height; clip: true
          ScrollBar.horizontal: ScrollBar {}
          Row {
            id: boardColumns
            height: parent.height; spacing: 12
            Repeater {
              model: rampi.board.columns
              Rectangle {
                required property var modelData
                required property int index
                width: Math.max(173, (boardPanel.width - 70) / Math.max(4, rampi.board.columns.length))
                height: boardColumns.height
                radius: 13
                color: ["#1c2b38", "#123760", "#3a3920", "#153931"][index % 4]
                ColumnLayout {
                  anchors.fill: parent; anchors.margins: 11
                  Text { text: modelData.name.toUpperCase() + "    " + modelData.cards.length; font.pixelSize: 11; font.letterSpacing: 1; font.bold: true; color: "#ebf3fc"; Layout.fillWidth: true; elide: Text.ElideRight }
                  ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8; clip: true
                    model: modelData.cards
                    delegate: RampiButton {
                      id: cardControl
                      required property var modelData
                      width: ListView.view.width; height: 49
                      focusPolicy: Qt.StrongFocus
                      Accessible.name: modelData.title
                      background: Rectangle { radius: 8; color: cardControl.activeFocus ? "#f3f7fa" : "#d1dce5" }
                      contentItem: Row {
                        spacing: 8
                        Rectangle { width: 9; height: 9; radius: 3; color: "#ff4666"; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: modelData.title; width: parent.width - 20; elide: Text.ElideRight; color: "#101923"; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; textFormat: Text.PlainText }
                      }
                      onClicked: { window.selectedCard = modelData; cardDetails.open(); }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }

    GridLayout {
      x: 840; y: 420; width: 734; height: 365
      columns: 2; columnSpacing: 12; rowSpacing: 12
      visible: window.page === "dashboard"
      Repeater {
        model: [window.modules[1], window.modules[2]]
        Panel {
          required property var modelData
          Layout.fillWidth: true; Layout.fillHeight: true
          ColumnLayout {
            anchors.fill: parent; anchors.margins: 14; spacing: 8
            Item {
              Layout.fillWidth: true; Layout.preferredHeight: 28
              Image { id: previewIcon; anchors.left: parent.left; width: 28; height: 28; source: "../icons/" + ({remote: "monitor", browser: "globe"})[modelData.key] + ".svg"; sourceSize: Qt.size(28, 28) }
              Text { anchors { left: previewIcon.right; leftMargin: 8; right: previewStatus.left; rightMargin: 8; verticalCenter: parent.verticalCenter } text: modelData.title + (modelData.key === "browser" ? "" : " / " + modelData.subtitle); color: "#edf3fa"; font.pixelSize: 15; font.bold: true; elide: Text.ElideRight }
              Rectangle { id: previewStatus; anchors { right: parent.right; verticalCenter: parent.verticalCenter } width: 8; height: 8; radius: 3; color: "#627487" }
            }
            Rectangle {
              Layout.fillWidth: true; Layout.fillHeight: true; radius: 10; color: "#080f17"
              ColumnLayout {
                anchors.fill: parent; anchors.margins: 13; spacing: 9
                Text { Layout.fillWidth: true; elide: Text.ElideRight; text: modelData.key === "browser" ? rampi.configuration.browser_url : "Windows-Desktop"; color: modelData.key === "browser" ? "#78b9ff" : "#55d98b"; font.family: "monospace"; font.pixelSize: 13 }
                Text { Layout.fillWidth: true; Layout.fillHeight: true; text: modelData.key === "browser" ? "Lokaler Browser · eigenes Profil" : "Persönliches Hostprofil · RDP oder Streaming"; clip: true; wrapMode: Text.WordWrap; textFormat: Text.PlainText; color: "#9cacbe"; font.family: "monospace"; font.pixelSize: 12; lineHeight: 1.3 }
                Text { Layout.fillWidth: true; visible: modelData.key === "browser" || !rampi.configuration.hosts.length; text: modelData.key === "browser" ? "Zum Öffnen auswählen →" : "Windows-Host noch nicht eingerichtet"; wrapMode: Text.WordWrap; color: "#6f8498"; font.pixelSize: 11 }
              }
            }
          }
        }
      }
    }

    Panel {
      x: 26; y: 136; width: 1548; height: 650
      visible: window.page === "remote"
      Column {
        anchors.centerIn: parent; spacing: 22; width: 800
        Text { text: "Deine Windows-Workstation"; color: "#f4f6fa"; font.pixelSize: 36; font.bold: true }
        Text { text: "Wähle dein Verbindungsverfahren.\nZurück zum Dashboard: Strg+Alt+Pos1. Windows erlaubt nur eine interaktive Desktopsitzung."; color: "#a4b5c7"; font.pixelSize: 18; lineHeight: 1.6; width: 800; wrapMode: Text.WordWrap }
        RampiButton { text: "RDP · FreeRDP starten"; onClicked: rampi.launch("rdp") }
        RampiButton { text: "Windows-Konsole teilen · Moonlight"; onClicked: rampi.launch("stream") }
        RampiButton { text: "Streaming-Host koppeln"; onClicked: rampi.action("stream-pair", "") }
        Text { text: "RDP meldet dich mit deinem Windows-Konto an. Sunshine teilt die aktive Windows-Konsole; die Kopplung ersetzt keine Windows-Anmeldung.\nKopplungsschlüssel sind pro Rampi-Benutzer, Host und Windows-Konto getrennt. Bei gemeinsam genutzten Hosts RDP verwenden."; width: 800; wrapMode: Text.WordWrap; color: "#c2b994"; font.pixelSize: 15 }
      }
    }

    Panel {
      x: 14; y: 804; width: 1572; height: 75; radius: 23
      RowLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 28
        RampiButton { text: "Einstellungen"; icon.source: "../icons/settings.svg"; icon.color: "#edf3fa"; font.pixelSize: 18; onClicked: settings.open() }
        Rectangle { width: 1; height: 38; color: "#4a5e70" }
        RampiButton { text: "Konsole"; icon.source: "../icons/terminal.svg"; icon.color: "#edf3fa"; onClicked: rampi.launch("console") }
        Item { Layout.fillWidth: true }
        Text { text: window.lastMessage || "Rampi " + rampi.version + "\nKleine Hardware. Große Möglichkeiten."; textFormat: Text.PlainText; maximumLineCount: 2; elide: Text.ElideRight; Layout.maximumWidth: 480; wrapMode: Text.WordWrap; color: "#8fa2b5"; font.pixelSize: 12; lineHeight: 1.5 }
        RampiButton { visible: window.lastMessage !== ""; text: "Details"; onClicked: notification.open() }
        RampiButton { visible: window.page !== "dashboard"; text: "← Dashboard"; onClicked: window.page = "dashboard" }
      }
    }
    HoverHandler {
      cursorShape: window.keyboardMode ? Qt.BlankCursor : Qt.ArrowCursor
      onPointChanged: window.keyboardMode = false
    }
  }
  SettingsDialog { id: settings; objectName: "settingsDialog" }
  SetupWizard {
    id: setupWizard
    onSettingsRequested: function(page) { settings.showPage(page); }
  }
  FullPage {
    id: cardDetails
    title: window.selectedCard.title || "Aufgabe"
    standardButtons: Dialog.Close
    ScrollView {
      anchors.fill: parent
      TextArea {
        readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
        textFormat: TextEdit.PlainText
        text: "Projekt: " + (window.selectedCard.project || "—") + "\nStatus: " + window.selectedCard.status + "\nPriorität: " + window.selectedCard.priority + "\n\n" + window.selectedCard.description
      }
    }
  }
  FullPage {
    id: notification; objectName: "notificationDialog"
    title: "Rampi"; standardButtons: Dialog.Ok
    property string detail: ""
    ScrollView {
      anchors.fill: parent
      TextArea { text: notification.detail; readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true; textFormat: TextEdit.PlainText }
    }
  }
  Connections {
    target: rampi
    function onMessage(text) { notification.detail = text; window.lastMessage = text; }
  }
}
