import QtQuick

// Pill-shaped option switcher with a sliding highlight. ``options``: [{value, label}].
Rectangle {
    id: root
    property var options: []
    property var value
    signal chosen(var value)

    implicitHeight: 34
    implicitWidth: row.implicitWidth + 6
    radius: height / 2
    color: Theme.panel
    border.width: 1
    border.color: Theme.strokeSoft

    readonly property int index: Math.max(0, options.findIndex(option => option.value === value))

    Rectangle {
        readonly property Item target: repeater.count > root.index ? repeater.itemAt(root.index) : null
        x: target ? target.x + 3 : 3
        y: 3
        width: target ? target.width : 0
        height: parent.height - 6
        radius: height / 2
        color: Theme.hover
        border.width: 1
        border.color: Theme.stroke
        Behavior on x { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutCubic } }
        Behavior on width { NumberAnimation { duration: Theme.smooth; easing.type: Easing.OutCubic } }
    }
    Row {
        id: row
        x: 3
        anchors.verticalCenter: parent.verticalCenter
        Repeater {
            id: repeater
            model: root.options
            delegate: Item {
                width: label.implicitWidth + 26
                height: root.height - 6
                Text {
                    id: label
                    anchors.centerIn: parent
                    text: modelData.label
                    color: index === root.index ? Theme.text : Theme.textDim
                    font.pixelSize: 12; font.weight: Font.DemiBold
                    Behavior on color { ColorAnimation { duration: Theme.quick } }
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: if (index !== root.index) { Sfx.play("tap"); root.chosen(modelData.value) }
                }
            }
        }
    }
}
