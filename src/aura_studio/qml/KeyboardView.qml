import QtQuick
import QtQuick.Effects

// Live per-key preview. ``frame`` holds one colour per entry of ``keys``.
Item {
    id: root
    property var keys: []
    property var frame: []
    property bool paintMode: false
    property real layoutWidth: 16.25
    property real layoutHeight: 6.25
    signal painted(int led, bool erase)

    readonly property real unit: Math.max(1, Math.min(width / layoutWidth, height / layoutHeight))
    property int hoverIndex: -1

    Item {
        id: board
        width: root.unit * root.layoutWidth
        height: root.unit * root.layoutHeight
        anchors.centerIn: parent

        // The keys once more, heavily blurred: light spilling onto the desk.
        ShaderEffectSource {
            id: glowSource
            sourceItem: keysLayer
            anchors.fill: keysLayer
            textureSize: Qt.size(Math.max(1, Math.round(board.width / 2)), Math.max(1, Math.round(board.height / 2)))
            visible: false
        }
        MultiEffect {
            source: glowSource
            anchors.fill: keysLayer
            blurEnabled: true
            blur: 1.0
            blurMax: 64
            saturation: 0.35
            brightness: 0.12
            opacity: 0.8
        }
        Item {
            id: keysLayer
            anchors.fill: parent
            Repeater {
                model: root.keys
                delegate: Item {
                    id: key
                    x: modelData.x * root.unit
                    y: modelData.y * root.unit
                    width: modelData.w * root.unit
                    height: modelData.h * root.unit
                    property color lamp: root.frame[index] || "#000000"
                    readonly property real glow: Math.max(lamp.r, lamp.g, lamp.b)
                    Behavior on lamp { ColorAnimation { duration: 70 } }

                    Rectangle {
                        id: cap
                        anchors.fill: parent
                        anchors.margins: Math.max(1.5, root.unit * 0.045)
                        radius: root.unit * 0.17
                        // Unlit keys stay visible as dark keycaps.
                        color: Qt.rgba(Math.max(key.lamp.r, 0.085), Math.max(key.lamp.g, 0.085), Math.max(key.lamp.b, 0.105), 1)
                        border.width: index === root.hoverIndex ? 2 : 0
                        border.color: "#ffffff"
                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: root.unit * 0.075
                            anchors.bottomMargin: root.unit * 0.13
                            radius: parent.radius * 0.75
                            color: "#000000"
                            opacity: 0.2
                        }
                        Text {
                            anchors.centerIn: parent
                            anchors.verticalCenterOffset: -root.unit * 0.03
                            text: modelData.label
                            color: key.glow > 0.75 && (key.lamp.r + key.lamp.g * 1.6 + key.lamp.b * 0.4) > 1.7 ? "#16161c" : "#ffffff"
                            opacity: 0.4 + 0.5 * key.glow
                            font.pixelSize: root.unit * (modelData.label.length > 2 ? 0.2 : 0.27)
                            font.weight: Font.DemiBold
                        }
                    }
                }
            }
        }
        MouseArea {
            anchors.fill: parent
            enabled: root.paintMode
            visible: root.paintMode
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.CrossCursor
            property int lastLed: -1
            function indexAt(mouseX, mouseY) {
                var ux = mouseX / root.unit, uy = mouseY / root.unit
                for (var i = 0; i < root.keys.length; i++) {
                    var k = root.keys[i]
                    if (ux >= k.x && ux < k.x + k.w && uy >= k.y && uy < k.y + k.h) return i
                }
                return -1
            }
            function paint(mouse) {
                var i = indexAt(mouse.x, mouse.y)
                root.hoverIndex = i
                if (i < 0 || !(mouse.buttons & (Qt.LeftButton | Qt.RightButton))) return
                var erase = (mouse.buttons & Qt.RightButton) !== 0
                var stamp = root.keys[i].id * (erase ? -1 : 1) - (erase ? 1 : 0)
                if (stamp === lastLed) return
                lastLed = stamp
                root.painted(root.keys[i].id, erase)
            }
            onPressed: mouse => { lastLed = -1; paint(mouse) }
            onPositionChanged: mouse => paint(mouse)
            onReleased: lastLed = -1
            onExited: root.hoverIndex = -1
        }
    }
}
