import QtQuick
import QtMultimedia

Item {
  id: feedback
  property double lastSelection: 0
  property int selectionCount: 0
  property int activationCount: 0
  function selection() {
    if (Date.now() - lastSelection < 65) return;
    lastSelection = Date.now();
    selectionCount++;
    if (rampi.configuration.sound_effects && tick.status === SoundEffect.Ready) tick.play();
  }
  function activate() {
    activationCount++;
    if (rampi.configuration.sound_effects && click.status === SoundEffect.Ready) click.play();
  }
  MediaDevices { id: audioDevices }
  SoundEffect { id: tick; objectName: "selectionSound"; source: audioDevices.audioOutputs.length ? "../sounds/select.wav" : ""; volume: 0.12; muted: !rampi.configuration.sound_effects }
  SoundEffect { id: click; objectName: "activationSound"; source: audioDevices.audioOutputs.length ? "../sounds/click.wav" : ""; volume: 0.22; muted: !rampi.configuration.sound_effects }
}
