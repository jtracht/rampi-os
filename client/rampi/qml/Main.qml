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
  property int selected: 0
  property string page: "dashboard"
  property bool keyboardMode: false
  readonly property var modules: [
    {title: "Kanban Board", subtitle: "Projekte im Blick", caption: "READ ONLY  |  PROJECTS", symbol: "▥", accent: "#ff3c61", key: "kanban", dark: false},
    {title: "ChatGPT", subtitle: "Codex", caption: "CHAT  |  CODE  |  CREATE", symbol: "⌘", accent: "#087cf5", key: "codex", dark: false},
    {title: "Claude", subtitle: "Claude Code", caption: "ANALYZE  |  BUILD  |  THINK", symbol: "✳", accent: "#ffd53d", key: "claude", dark: true},
    {title: "Gemini", subtitle: "Antigravity CLI", caption: "RESEARCH  |  MULTIMODAL", symbol: "✦", accent: "#15cbbb", key: "antigravity", dark: true},
    {title: "Remote Desktop", subtitle: "Deine Windows-Workstation", caption: "STREAMING  |  RDP", symbol: "▱", accent: "#4934c8", key: "remote", dark: false},
    {title: "Webbrowser", subtitle: "Dein Fenster ins Web", caption: "BROWSE  |  WORK  |  STREAM", symbol: "◎", accent: "#1d3448", key: "browser", dark: false}
  ]
  function activate(index) {
    selected = index;
    let key = modules[index].key;
    if (key === "kanban" || key === "remote") page = key;
    else rampi.launch(key);
  }
  Shortcut { sequence: "Ctrl+Alt+Home"; onActivated: { window.page = "dashboard"; window.raise(); window.requestActivate(); } }
  Shortcut { sequence: "Escape"; onActivated: { if (settings.visible) settings.close(); else window.page = "dashboard"; } }
  Shortcut { sequence: "Ctrl+,"; onActivated: settings.open() }
  Shortcut { sequence: "F11"; onActivated: window.visibility = window.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen }
  Component.onCompleted: if (!rampi.configuration.setup_complete && showSetup) setupWizard.open()

  Item {
    id: stage
    width: 1600; height: 900
    scale: Math.min(window.width / width, window.height / height)
    anchors.centerIn: parent

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
        model: [{label: "Netzwerk", key: "network", glyph: "◉"}, {label: "Bluetooth", key: "bluetooth", glyph: "ᛒ"}, {label: "VPN", key: "vpn", glyph: "◈"}]
        Row {
          spacing: 10
          Text { text: modelData.glyph; color: "#19d6b2"; font.pixelSize: 32 }
          Column {
            Text { text: modelData.label; color: "#f4f6fa"; font.pixelSize: 13; font.bold: true }
            Text { text: rampi.status[modelData.key]; width: 130; elide: Text.ElideRight; color: "#92a7ba"; font.pixelSize: 11 }
          }
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
          accent: modelData.accent; darkInk: modelData.dark
          selected: window.selected === index
          reducedMotion: rampi.configuration.reduce_motion
          onActiveFocusChanged: if (activeFocus) window.selected = index
          onActivated: window.activate(index)
          Keys.onRightPressed: { window.keyboardMode = true; tileRepeater.itemAt((index + 1) % 6).forceActiveFocus(); }
          Keys.onLeftPressed: { window.keyboardMode = true; tileRepeater.itemAt((index + 5) % 6).forceActiveFocus(); }
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
          Text { text: rampi.board.count + " Karten"; color: "#a9b8c7"; font.pixelSize: 12 }
          Button { text: "↻"; Accessible.name: "Kanban aktualisieren"; onClicked: rampi.refreshBoard() }
        }
        TextField {
          visible: window.page === "kanban"
          Layout.fillWidth: true
          placeholderText: "Titel, Beschreibung, Projekt oder Priorität suchen …"
          onTextChanged: rampi.search(text)
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
                    delegate: Rectangle {
                      required property var modelData
                      width: ListView.view.width; height: 49; radius: 8; color: "#d1dce5"
                      Row {
                        anchors.fill: parent; anchors.margins: 10; spacing: 8
                        Rectangle { width: 9; height: 9; radius: 3; color: "#ff4666"; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: modelData.title; width: parent.width - 20; elide: Text.ElideRight; color: "#101923"; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter; textFormat: Text.PlainText }
                      }
                      ToolTip.visible: cardMouse.containsMouse
                      ToolTip.text: modelData.description || modelData.title
                      MouseArea { id: cardMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
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
        model: [window.modules[1], window.modules[2], window.modules[3], window.modules[5]]
        Panel {
          required property var modelData
          Layout.fillWidth: true; Layout.fillHeight: true
          ColumnLayout {
            anchors.fill: parent; anchors.margins: 14; spacing: 8
            RowLayout {
              Text { text: modelData.symbol; color: modelData.accent; font.pixelSize: 30 }
              Text { text: modelData.title + (modelData.key === "browser" ? "" : " / " + modelData.subtitle); color: "#edf3fa"; font.pixelSize: 15; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
              Rectangle { width: 8; height: 8; radius: 3; color: "#627487" }
            }
            Rectangle {
              Layout.fillWidth: true; Layout.fillHeight: true; radius: 10; color: "#080f17"
              Column {
                anchors.fill: parent; anchors.margins: 13; spacing: 9
                Text { text: modelData.key === "browser" ? "https://www.raspberrypi.com" : "> " + (modelData.key === "antigravity" ? "agy" : modelData.key); color: modelData.key === "browser" ? "#78b9ff" : "#55d98b"; font.family: "monospace"; font.pixelSize: 13 }
                Text { text: modelData.key === "browser" ? "Lokaler Browser · eigenes Profil" : rampi.previews[modelData.key]; width: parent.width; height: 58; clip: true; wrapMode: Text.WordWrap; textFormat: Text.PlainText; color: "#9cacbe"; font.family: "monospace"; font.pixelSize: 12; lineHeight: 1.3 }
                Text { text: modelData.key === "browser" ? "Zum Öffnen auswählen →" : (rampi.configuration.hosts.length ? "Host eingerichtet · zum Verbinden auswählen →" : "Windows-Host noch nicht eingerichtet"); width: parent.width; wrapMode: Text.WordWrap; color: "#6f8498"; font.pixelSize: 11 }
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
        Button { text: "RDP · FreeRDP starten"; onClicked: rampi.launch("rdp") }
        Button { text: "Streaming · Moonlight starten"; onClicked: rampi.launch("stream") }
        Text { text: "Sunshine/Moonlight benötigen vorheriges Pairing.\nDie Hardwaredecodierung auf Pi 3 B+ ist noch nicht validiert."; color: "#c2b994"; font.pixelSize: 15 }
      }
    }

    Panel {
      x: 14; y: 804; width: 1572; height: 75; radius: 23
      RowLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 28
        Button { text: "⚙  Einstellungen"; font.pixelSize: 18; onClicked: settings.open() }
        Rectangle { width: 1; height: 38; color: "#4a5e70" }
        Repeater {
          model: [{label: "WLAN", value: rampi.status.network}, {label: "Bluetooth", value: rampi.status.bluetooth}, {label: "VPN", value: rampi.status.vpn}]
          Column {
            Text { text: modelData.label; color: "#f2f5fa"; font.pixelSize: 13 }
            Text { text: modelData.value; color: modelData.value === "Verbunden" || modelData.value === "Running" || modelData.value === "Bereit" ? "#1edbb5" : "#8fa2b5"; font.pixelSize: 12; width: 130; elide: Text.ElideRight }
          }
        }
        Button { text: "⌨  Konsole"; onClicked: rampi.launch("console") }
        Item { Layout.fillWidth: true }
        Text { text: "Rampi " + rampi.version + "\nKleine Hardware. Große Möglichkeiten."; color: "#8fa2b5"; font.pixelSize: 12; lineHeight: 1.5 }
        Button { visible: window.page !== "dashboard"; text: "← Dashboard"; onClicked: window.page = "dashboard" }
      }
    }
    MouseArea {
      anchors.fill: parent
      acceptedButtons: Qt.NoButton
      hoverEnabled: true
      cursorShape: window.keyboardMode ? Qt.BlankCursor : Qt.ArrowCursor
      onPositionChanged: window.keyboardMode = false
    }
  }
  SettingsDialog { id: settings; anchors.centerIn: parent; width: Math.min(window.width - 50, 1000); height: Math.min(window.height - 50, 780) }
  SetupWizard {
    id: setupWizard
    anchors.centerIn: parent
    width: Math.min(window.width - 50, 900); height: Math.min(window.height - 50, 650)
    onSettingsRequested: function(page) { settings.showPage(page); }
  }
  Dialog {
    id: notification
    anchors.centerIn: parent
    width: Math.min(window.width - 60, 800); height: Math.min(window.height - 60, 480)
    modal: true; title: "Rampi"; standardButtons: Dialog.Ok
    property string detail: ""
    ScrollView {
      anchors.fill: parent
      TextArea { text: notification.detail; readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true; textFormat: TextEdit.PlainText }
    }
  }
  Connections {
    target: rampi
    function onMessage(text) { notification.detail = text; notification.open(); }
  }
}
