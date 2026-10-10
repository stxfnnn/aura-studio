import QtQuick

// Text button with an optional leading icon. ``primary`` fills it with the accent.
Rectangle {
    id: root
    property string text: ""
    property string icon: ""
    property bool primary: false
    property bool danger: false
    property string sound: "tap"
    signal clicked()

    implicitHeight: 36
    implicitWidth: row.implicitWidth + 28
    radius: height / 2
    opacity: enabled ? 1 : 0.4
    color: primary ? (area.containsMouse ? Qt.lighter(Theme.accent, 1.1) : Theme.accent)
                   : area.containsMouse ? Theme.hover : Theme.raised
    border.width: primary ? 0 : 1
    border.color: Theme.strokeSoft
    scale: area.pressed ? 0.96 : 1
    Behavior on color { ColorAnimation { duration: Theme.quick } }
    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }

    readonly property color ink: primary ? Theme.accentInk : danger ? Theme.bad : Theme.text

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 7
        Icon { visible: root.icon !== ""; name: root.icon; size: 15; color: root.ink; anchors.verticalCenter: parent.verticalCenter }
        Text {
            visible: root.text !== ""
            text: root.text; color: root.ink
            font.pixelSize: 13; font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: { Sfx.play(root.sound); root.clicked() }
    }
}
