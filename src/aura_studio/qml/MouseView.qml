import QtQuick
import QtQuick.Effects

// Stylised mouse with its single scroll-wheel lamp.
Item {
    id: root
    property var frame: []
    property color lamp: frame[0] || "#000000"
    Behavior on lamp { ColorAnimation { duration: 70 } }

    Item {
        id: body
        height: Math.min(root.height, 300)
        width: height * 0.58
        anchors.centerIn: parent

        Rectangle {
            anchors.fill: parent
            radius: width * 0.48
            gradient: Gradient {
                GradientStop { position: 0; color: "#24242d" }
                GradientStop { position: 1; color: "#131318" }
            }
            border.width: 1
            border.color: "#22ffffff"
        }
        Rectangle {
            width: 1; height: parent.height * 0.36
            anchors.horizontalCenter: parent.horizontalCenter
            y: parent.height * 0.03
            color: "#000000"; opacity: 0.6
        }
        Rectangle {
            width: parent.width * 0.86; height: 1
            anchors.horizontalCenter: parent.horizontalCenter
            y: parent.height * 0.4
            color: "#000000"; opacity: 0.35
        }
        // Light from the wheel spilling over the shell.
        Rectangle {
            id: halo
            anchors.centerIn: wheel
            width: body.width * 0.5; height: width; radius: width / 2
            color: root.lamp
            visible: false
        }
        MultiEffect {
            source: halo
            anchors.fill: halo
            blurEnabled: true; blur: 1.0; blurMax: 64
            opacity: 0.55
        }
        Rectangle {
            id: wheel
            width: body.width * 0.15; height: body.height * 0.17
            radius: width / 2
            anchors.horizontalCenter: parent.horizontalCenter
            y: body.height * 0.12
            color: Qt.rgba(Math.max(root.lamp.r, 0.07), Math.max(root.lamp.g, 0.07), Math.max(root.lamp.b, 0.09), 1)
            border.width: 2
            border.color: "#0b0b0f"
            Column {
                anchors.centerIn: parent
                spacing: 3
                Repeater {
                    model: 4
                    Rectangle { width: wheel.width * 0.5; height: 1.5; radius: 1; color: "#000000"; opacity: 0.35 }
                }
            }
        }
    }
}
