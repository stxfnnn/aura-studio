import QtQuick
import QtQuick.Effects

// Small illustration of a device showing its current lighting: the real key
// layout for keyboards, a mouse seen from above otherwise.
Rectangle {
    id: root
    property string kind: "keyboard"
    property var keys: []
    property var colors: []
    radius: 14
    color: Theme.well
    clip: true

    // Keyboard: every key in its real place.
    Item {
        id: board
        visible: root.kind === "keyboard"
        readonly property real unit: Math.min((root.width - 20) / 16.25, (root.height - 20) / 6.25)
        width: unit * 16.25; height: unit * 6.25
        anchors.centerIn: parent
        Repeater {
            model: root.kind === "keyboard" ? root.keys : []
            delegate: Rectangle {
                x: modelData.x * board.unit + 0.6
                y: modelData.y * board.unit + 0.6
                width: modelData.w * board.unit - 1.2
                height: modelData.h * board.unit - 1.2
                radius: board.unit * 0.22
                readonly property color lamp: root.colors[index] || "#000000"
                color: Qt.rgba(Math.max(lamp.r, 0.09), Math.max(lamp.g, 0.09), Math.max(lamp.b, 0.11), 1)
            }
        }
    }

    // Mouse: shell, buttons and the lit scroll wheel.
    Item {
        id: mouse
        visible: root.kind !== "keyboard"
        height: root.height - 18
        width: height * 0.6
        anchors.centerIn: parent
        readonly property color lamp: root.colors[0] || "#000000"
        Rectangle {
            id: halo
            anchors.centerIn: wheel
            width: mouse.width * 0.9; height: width; radius: width / 2
            color: mouse.lamp
            visible: false
        }
        Rectangle {
            anchors.fill: parent
            radius: width * 0.48
            gradient: Gradient {
                GradientStop { position: 0; color: "#2a2a34" }
                GradientStop { position: 1; color: "#16161c" }
            }
            border.width: 1
            border.color: "#26ffffff"
        }
        MultiEffect {
            source: halo
            anchors.fill: halo
            blurEnabled: true; blur: 1.0; blurMax: 40
            opacity: 0.6
        }
        Rectangle { width: 1; height: parent.height * 0.36; anchors.horizontalCenter: parent.horizontalCenter; y: 2; color: "#000000"; opacity: 0.55 }
        Rectangle { width: parent.width * 0.84; height: 1; anchors.horizontalCenter: parent.horizontalCenter; y: parent.height * 0.4; color: "#000000"; opacity: 0.35 }
        Rectangle {
            id: wheel
            width: Math.max(5, mouse.width * 0.16); height: mouse.height * 0.19
            radius: width / 2
            anchors.horizontalCenter: parent.horizontalCenter
            y: mouse.height * 0.11
            color: Qt.rgba(Math.max(mouse.lamp.r, 0.1), Math.max(mouse.lamp.g, 0.1), Math.max(mouse.lamp.b, 0.12), 1)
            border.width: 1.5
            border.color: "#0b0b0f"
        }
    }
}
