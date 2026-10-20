import QtQuick
import QtQuick.Controls

Button {
  // Qt's platform theme can reserve button activation for Space. Rampi also
  // promises Enter; keep Qt rendering, focus, accessibility and Space handling.
  Keys.onReturnPressed: function(event) { if (!event.isAutoRepeat) clicked(); }
  Keys.onEnterPressed: function(event) { if (!event.isAutoRepeat) clicked(); }
}
