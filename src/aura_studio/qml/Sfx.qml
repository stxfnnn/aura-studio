pragma Singleton
import QtQuick
import QtMultimedia

QtObject {
    id: sfx
    property bool enabled: true
    property real volume: 0.55
    property real lastPaint: 0

    function play(name) {
        if (!enabled || volume <= 0) return
        if (name === "paint") {
            // Dragging across keys would otherwise machine-gun the sample.
            var now = Date.now()
            if (now - lastPaint < 55) return
            lastPaint = now
        }
        var sound = sounds[name]
        if (sound) sound.play()
    }

    readonly property var sounds: ({
        "tap": tap, "select": select, "nav": nav, "toggle_on": toggleOn, "toggle_off": toggleOff,
        "paint": paint, "success": success, "error": error
    })
    readonly property SoundEffect tap: SoundEffect { source: Qt.resolvedUrl("../assets/sounds/tap.wav"); volume: sfx.volume * 0.8 }
    readonly property SoundEffect select: SoundEffect { source: Qt.resolvedUrl("../assets/sounds/select.wav"); volume: sfx.volume }
    readonly property SoundEffect nav: SoundEffect { source: Qt.resolvedUrl("../assets/sounds/nav.wav"); volume: sfx.volume * 0.8 }
    readonly property SoundEffect toggleOn: SoundEffect { source: Qt.resolvedUrl("../assets/sounds/toggle_on.wav"); volume: sfx.volume }
    readonly property SoundEffect toggleOff: SoundEffect { source: Qt.resolvedUrl("../assets/sounds/toggle_off.wav"); volume: sfx.volume }
    readonly property SoundEffect paint: SoundEffect { source: Qt.resolvedUrl("../assets/sounds/paint.wav"); volume: sfx.volume * 0.7 }
    readonly property SoundEffect success: SoundEffect { source: Qt.resolvedUrl("../assets/sounds/success.wav"); volume: sfx.volume }
    readonly property SoundEffect error: SoundEffect { source: Qt.resolvedUrl("../assets/sounds/error.wav"); volume: sfx.volume }
}
