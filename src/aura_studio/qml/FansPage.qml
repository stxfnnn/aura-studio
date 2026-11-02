import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Fan control: the fans on the left, the selected one's curve on the right.
Item {
    id: page
    readonly property var ramp: fans.ramp
    readonly property var temps: fans.temps
    readonly property var config: fans.config
    readonly property var live: fans.live
    property string selectedId: ""
    readonly property string currentId: fans.ids.indexOf(selectedId) >= 0 ? selectedId : (fans.ids[0] || "")
    readonly property var cfg: page.config[currentId] || null
    readonly property var now: page.live[currentId] || {}

    function degrees(value) { return value === null || value === undefined ? "–" : Math.round(value) + " °C" }
    function modeName(mode) { return mode === "curve" ? L.t("Kurve") : mode === "fixed" ? L.t("Fest") : "BIOS" }

    component Label: Text {
        color: Theme.textFaint
        font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3
    }
    component Hint: Text {
        Layout.fillWidth: true
        color: Theme.textFaint; font.pixelSize: 12
        wrapMode: Text.Wrap
    }
    component Card: Rectangle {
        default property alias content: inner.data
        Layout.fillWidth: true
        implicitHeight: inner.implicitHeight + 36
        radius: Theme.radius
        color: Theme.card
        border.width: 1
        border.color: Theme.strokeSoft
        ColumnLayout {
            id: inner
            x: 18; y: 18
            width: parent.width - 36
            height: parent.height - 36   // lets the curve grow with the card
            spacing: 12
        }
    }
    component Problem: Rectangle {
        property alias text: problemText.text
        Layout.fillWidth: true
        implicitHeight: problemText.implicitHeight + 20
        radius: 12
        color: Qt.rgba(Theme.bad.r, Theme.bad.g, Theme.bad.b, 0.12)
        Text {
            id: problemText
            x: 12; y: 10
            width: parent.width - 24
            color: Theme.bad; font.pixelSize: 12
            wrapMode: Text.Wrap
        }
    }
    // Slider with its name on the left and the value on the right.
    component Knob: ColumnLayout {
        property string label: ""
        property string unit: "%"
        property real from: 0
        property real to: 100
        property real value: 0
        signal moved(int value)
        Layout.fillWidth: true
        spacing: 2
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: label; color: Theme.text; font.pixelSize: 13; elide: Text.ElideRight }
            Text { text: Math.round(value) + " " + unit; color: Theme.textDim; font.pixelSize: 12 }
        }
        ValueSlider {
            Layout.fillWidth: true
            from: parent.from; to: parent.to; value: parent.value
            onMoved: v => parent.moved(Math.round(v))
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

        // -------------------------------------------------------------- list
        ColumnLayout {
            Layout.preferredWidth: 280
            Layout.maximumWidth: 280
            Layout.fillHeight: true
            spacing: 12

            Column {
                Layout.fillWidth: true
                spacing: 3
                Text { text: L.t("Lüfter"); color: Theme.text; font.pixelSize: 23; font.weight: Font.Bold }
                Text {
                    text: "CPU " + page.degrees(page.temps.cpu) + (page.temps.gpu === null ? "" : "   GPU " + page.degrees(page.temps.gpu))
                    color: Theme.textFaint; font.pixelSize: 12
                }
            }
            Problem {
                visible: !fans.available
                text: L.t("Kein Lüfterchip gefunden. Lade den Treiber und starte Aura Studio neu:") + "\nsudo modprobe nct6775"
            }
            Problem {
                visible: fans.ids.some(id => !page.config[id].writable)
                text: L.t("Keine Schreibrechte. Installiere die udev-Regel einmalig und starte Aura Studio neu:") + "\n" + fans.rule
            }
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentHeight: rows.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: rows
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: fans.ids
                        delegate: Rectangle {
                            width: rows.width; height: 56
                            radius: 14
                            readonly property bool current: modelData === page.currentId
                            readonly property var c: page.config[modelData]
                            readonly property var l: page.live[modelData] || {}
                            readonly property bool idle: !l.rpm && !l.active   // no fan on this header, most likely
                            color: current ? Theme.accentSoft : rowArea.containsMouse ? Theme.raised : Theme.card
                            border.width: 1
                            border.color: current ? Theme.accentLine : Theme.strokeSoft
                            opacity: idle ? 0.45 : 1
                            MouseArea {
                                id: rowArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: { Sfx.play("tap"); page.selectedId = modelData }
                            }
                            Icon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: "fan"; color: l.active ? Theme.accent : Theme.textFaint }
                            Column {
                                x: 42
                                width: parent.width - 56
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                Text {
                                    width: parent.width
                                    text: c.name
                                    color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }
                                Text {
                                    width: parent.width
                                    text: idle ? L.t("Nicht belegt") : (l.rpm || 0) + " rpm  ·  " + (l.active ? l.level + " %" : page.modeName(c.mode))
                                    color: Theme.textFaint; font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }

        // ------------------------------------------------------------ editor
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16
            visible: page.cfg !== null

            Card {
                Layout.fillHeight: true
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Rectangle {
                        Layout.preferredWidth: 220
                        implicitHeight: 34; radius: 17
                        color: Theme.panel
                        border.width: 1
                        border.color: nameInput.activeFocus ? Theme.accentLine : Theme.strokeSoft
                        TextInput {
                            id: nameInput
                            anchors.fill: parent
                            anchors.leftMargin: 14; anchors.rightMargin: 14
                            verticalAlignment: TextInput.AlignVCenter
                            color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold
                            selectionColor: Theme.accent; selectedTextColor: Theme.accentInk
                            selectByMouse: true; clip: true
                            maximumLength: 24
                            readonly property string source: page.cfg ? page.cfg.name : ""
                            onSourceChanged: if (!activeFocus) text = source
                            Component.onCompleted: text = source
                            onEditingFinished: fans.setFanOption(page.currentId, "name", text)
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: page.cfg ? (page.now.rpm || 0) + " rpm  ·  " + (page.now.active ? page.now.level + " %" : L.t("BIOS regelt")) + "  ·  " + page.cfg.chip : ""
                        color: Theme.textFaint; font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                    Segmented {
                        options: [{value: "bios", label: "BIOS"}, {value: "fixed", label: L.t("Fest")}, {value: "curve", label: L.t("Kurve")}]
                        value: page.cfg ? page.cfg.mode : "bios"
                        onChosen: value => fans.setFanOption(page.currentId, "mode", value)
                    }
                }

                Hint {
                    visible: page.cfg && page.cfg.mode === "bios"
                    text: L.t("Das BIOS regelt diesen Lüfter wie bisher. Wähle „Fest“ für eine feste Drehzahl oder „Kurve“, um ihn nach Temperatur zu steuern.")
                }
                Knob {
                    visible: page.cfg && page.cfg.mode === "fixed"
                    label: L.t("Drehzahl"); value: page.cfg ? page.cfg.fixed : 0
                    onMoved: v => fans.setFanOption(page.currentId, "fixed", v)
                }
                RowLayout {
                    visible: page.cfg && page.cfg.mode === "curve"
                    Layout.fillWidth: true
                    Text { text: L.t("Richtet sich nach"); color: Theme.text; font.pixelSize: 13 }
                    Segmented {
                        options: [{value: "cpu", label: "CPU"}, {value: "gpu", label: "GPU"}, {value: "max", label: L.t("Wärmster")}]
                        value: page.cfg ? page.cfg.source : "max"
                        onChosen: value => fans.setFanOption(page.currentId, "source", value)
                    }
                    Text {
                        Layout.fillWidth: true
                        text: page.cfg && page.cfg.mode === "curve" ? page.degrees(page.now.temp) : ""
                        color: Theme.textDim; font.pixelSize: 13
                        horizontalAlignment: Text.AlignRight
                    }
                }
                CurveEditor {
                    visible: page.cfg && page.cfg.mode === "curve"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 220
                    points: page.cfg ? page.cfg.points : []
                    temp: page.now.temp === undefined ? null : page.now.temp
                    level: page.now.level || 0
                    onEdited: points => fans.setFanOption(page.currentId, "points", points)
                }
                RowLayout {
                    visible: page.cfg && page.cfg.mode === "curve"
                    Layout.fillWidth: true
                    Hint { text: L.t("Klicken setzt einen Punkt, Ziehen verschiebt ihn, Rechtsklick entfernt ihn.") }
                    PillButton {
                        visible: fans.ids.length > 1
                        icon: "copy"; text: L.t("Auf alle Lüfter übertragen"); implicitHeight: 32
                        onClicked: fans.copyPoints(page.currentId)
                    }
                }
                Item { Layout.fillHeight: true; visible: !(page.cfg && page.cfg.mode === "curve") }
            }

            Card {
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: L.t("RUHE  ·  GILT FÜR ALLE LÜFTER"); Layout.fillWidth: true }
                    Text {
                        text: L.t("geglättet") + ": CPU " + page.degrees(page.temps.cpuSmooth) + (page.temps.gpu === null ? "" : "   GPU " + page.degrees(page.temps.gpuSmooth))
                        color: Theme.textFaint; font.pixelSize: 12
                    }
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: 3; columnSpacing: 24; rowSpacing: 0
                    Knob { label: L.t("Temperatur glätten"); unit: "s"; to: 120; value: page.ramp.window; onMoved: v => fans.setRamp("window", v) }
                    Knob { label: L.t("Hochdrehen"); unit: "%/s"; from: 1; value: page.ramp.up; onMoved: v => fans.setRamp("up", v) }
                    Knob { label: L.t("Runterdrehen"); unit: "%/s"; from: 1; value: page.ramp.down; onMoved: v => fans.setRamp("down", v) }
                }
                Hint { text: L.t("Längeres Glätten und langsames Hoch- und Runterdrehen machen die Lüfter träge und leise. Ab 90 °C (CPU) bzw. 85 °C (GPU) drehen sie trotzdem sofort voll auf.") }
            }
        }
    }
}
