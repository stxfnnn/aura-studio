import QtQuick
import QtQuick.Controls

// Floating HSV picker. Reports every change live through the ``apply`` callback.
Popup {
    id: root
    property real hue: 0
    property real saturation: 1
    property real brightness: 1
    property var apply: null
    property var recent: []
    readonly property color current: Qt.hsva(hue, saturation, brightness, 1)
    readonly property var swatches: ["#ff3b4e", "#ff7a1a", "#ffc531", "#b8f23c", "#35e07a", "#19d9c3",
                                     "#2bb8ff", "#3d6dff", "#7a5cff", "#b455ff", "#ff4fc4", "#ff5f8f",
                                     "#ffffff", "#ffd9a8", "#a8d8ff", "#101018"]

    function hex(c) {
        function part(v) { var s = Math.round(v * 255).toString(16); return s.length < 2 ? "0" + s : s }
        return "#" + part(c.r) + part(c.g) + part(c.b)
    }
    function load(value) {
        var c = Qt.color(value)
        brightness = c.hsvValue
        saturation = c.hsvSaturation
        if (c.hsvHue >= 0) hue = c.hsvHue
        field.text = hex(c).toUpperCase()
    }
    function commit() {
        field.text = hex(current).toUpperCase()
        if (apply) apply(hex(current))
    }
    function openFor(item, value, callback) {
        apply = null
        load(value)
        apply = callback
        var point = item.mapToItem(parent, 0, 0)
        x = Math.max(12, Math.min(parent.width - width - 12, point.x + item.width / 2 - width / 2))
        y = point.y + item.height + 10
        if (y + height > parent.height - 12) y = Math.max(12, point.y - height - 10)
        open()
    }
    onClosed: {
        var value = hex(current)
        recent = [value].concat(recent.filter(c => c !== value)).slice(0, 8)
    }

    width: 276
    padding: 14
    modal: false
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 }
        NumberAnimation { property: "scale"; from: 0.94; to: 1; duration: 180; easing.type: Easing.OutCubic }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 110 } }
    background: Rectangle {
        radius: Theme.radius
        color: Theme.popup
        border.width: 1
        border.color: Theme.stroke
    }

    contentItem: Column {
        spacing: 12
        Rectangle {
            id: square
            width: parent.width; height: 150
            radius: 10
            color: Qt.hsva(root.hue, 1, 1, 1)
            Rectangle {
                anchors.fill: parent; radius: parent.radius
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "#ffffffff" }
                    GradientStop { position: 1; color: "#00ffffff" }
                }
            }
            Rectangle {
                anchors.fill: parent; radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0; color: "#00000000" }
                    GradientStop { position: 1; color: "#ff000000" }
                }
            }
            Rectangle {
                x: root.saturation * square.width - width / 2
                y: (1 - root.brightness) * square.height - height / 2
                width: 18; height: 18; radius: 9
                color: root.current
                border.width: 2.5
                border.color: "#ffffff"
            }
            MouseArea {
                anchors.fill: parent
                preventStealing: true
                cursorShape: Qt.CrossCursor
                function update(mouse) {
                    root.saturation = Math.max(0, Math.min(1, mouse.x / width))
                    root.brightness = 1 - Math.max(0, Math.min(1, mouse.y / height))
                    root.commit()
                }
                onPressed: mouse => update(mouse)
                onPositionChanged: mouse => { if (pressed) update(mouse) }
            }
        }
        ValueSlider {
            width: parent.width
            from: 0; to: 1
            value: root.hue
            trackGradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#ff0000" }
                GradientStop { position: 0.167; color: "#ffff00" }
                GradientStop { position: 0.333; color: "#00ff00" }
                GradientStop { position: 0.5; color: "#00ffff" }
                GradientStop { position: 0.667; color: "#0000ff" }
                GradientStop { position: 0.833; color: "#ff00ff" }
                GradientStop { position: 1.0; color: "#ff0000" }
            }
            onMoved: value => { root.hue = Math.min(value, 0.9999); root.commit() }
        }
        Row {
            width: parent.width
            spacing: 10
            Rectangle {
                width: 34; height: 34; radius: 10
                color: root.current
                border.width: 1
                border.color: Theme.stroke
            }
            Rectangle {
                width: parent.width - 44; height: 34; radius: 10
                color: Theme.panel
                border.width: 1
                border.color: field.activeFocus ? Theme.accentLine : Theme.strokeSoft
                TextInput {
                    id: field
                    anchors.fill: parent
                    anchors.leftMargin: 12; anchors.rightMargin: 12
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.text
                    selectionColor: Theme.accent
                    selectedTextColor: Theme.accentInk
                    font.family: "monospace"; font.pixelSize: 13
                    selectByMouse: true
                    maximumLength: 7
                    onEditingFinished: {
                        var value = text.trim()
                        if (value.charAt(0) !== "#") value = "#" + value
                        if (/^#[0-9a-fA-F]{6}$/.test(value)) { root.load(value); root.commit() }
                        else text = root.hex(root.current).toUpperCase()
                    }
                }
            }
        }
        Grid {
            width: parent.width
            columns: 8
            spacing: 6
            Repeater {
                model: root.swatches
                delegate: Rectangle {
                    width: (parent.width - 42) / 8; height: width
                    radius: 8
                    color: modelData
                    border.width: 1
                    border.color: Theme.stroke
                    scale: swatchArea.containsMouse ? 1.15 : 1
                    Behavior on scale { NumberAnimation { duration: 100 } }
                    MouseArea {
                        id: swatchArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { Sfx.play("select"); root.load(modelData); root.commit() }
                    }
                }
            }
        }
        Column {
            width: parent.width
            spacing: 6
            visible: root.recent.length > 0
            Text { text: L.t("ZULETZT"); color: Theme.textFaint; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.1 }
            Row {
                spacing: 6
                Repeater {
                    model: root.recent
                    delegate: Rectangle {
                        width: 22; height: 22; radius: 11
                        color: modelData
                        border.width: 1
                        border.color: Theme.stroke
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: { Sfx.play("select"); root.load(modelData); root.commit() }
                        }
                    }
                }
            }
        }
    }
}
