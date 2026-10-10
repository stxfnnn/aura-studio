import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Live preview, effect gallery and the inspector for the selected device.
Item {
    id: page
    property var cfg: ({})
    property var device: null
    property var effectDef: null
    property var frame: []
    property var picker: null
    property var catalog: []

    property string group: "all"
    property string paintColor: "#ff4d8d"
    property bool eraser: false
    readonly property bool isKeyboard: device !== null && device.kind === "keyboard"
    readonly property bool painting: isKeyboard && effectDef !== null && effectDef.paint
    readonly property var colors: cfg.colors || []

    component SectionLabel: Text {
        color: Theme.textFaint
        font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3
    }

    component ParamRow: Column {
        id: param
        property string label: ""
        property real value: 0
        property string suffix: " %"
        signal moved(real value)
        spacing: 4
        RowLayout {
            width: parent.width
            Text { text: param.label; color: Theme.textDim; font.pixelSize: 13; Layout.fillWidth: true }
            Text { text: Math.round(param.value) + param.suffix; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
        }
        ValueSlider {
            width: parent.width
            value: param.value
            onMoved: value => param.moved(value)
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

        // ------------------------------------------------ preview + gallery
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Column {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        text: page.device ? page.device.name : ""
                        color: Theme.text
                        font.pixelSize: 23; font.weight: Font.Bold
                    }
                    Text {
                        text: page.device ? page.device.source + "  ·  " + page.device.detail : ""
                        color: Theme.textFaint
                        font.pixelSize: 12
                        width: parent.width
                        elide: Text.ElideRight
                    }
                }
                IconButton {
                    icon: "link"
                    tip: service.settings.linked ? L.t("Geräte gekoppelt: Änderungen gelten für alle") : L.t("Geräte koppeln")
                    active: service.settings.linked
                    sound: service.settings.linked ? "toggle_off" : "toggle_on"
                    onClicked: service.setSetting("linked", !service.settings.linked)
                }
                IconButton {
                    icon: "power"
                    tip: page.cfg.enabled ? L.t("Beleuchtung ausschalten") : L.t("Beleuchtung einschalten")
                    active: page.cfg.enabled === true
                    sound: page.cfg.enabled ? "toggle_off" : "toggle_on"
                    onClicked: service.setEnabled(!page.cfg.enabled)
                }
            }

            Rectangle {
                id: stage
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(190, Math.min((width - 64) / 2.6 + 64, page.height * 0.46))
                radius: 22
                color: Theme.well
                border.width: 1
                border.color: Theme.strokeSoft
                clip: true

                KeyboardView {
                    anchors.fill: parent
                    anchors.margins: 32
                    visible: page.isKeyboard
                    keys: page.isKeyboard ? page.device.keys : []
                    frame: page.frame
                    layoutWidth: service.layoutWidth
                    layoutHeight: service.layoutHeight
                    paintMode: page.painting
                    onPainted: (led, erase) => {
                        Sfx.play("paint")
                        service.paintKeys([led], erase || page.eraser ? "" : page.paintColor)
                    }
                }
                MouseView {
                    anchors.fill: parent
                    anchors.margins: 22
                    visible: page.device !== null && page.device.kind === "mouse"
                    frame: page.frame
                }
                Row {
                    x: 16; y: 14
                    spacing: 7
                    Rectangle {
                        width: 7; height: 7; radius: 3.5
                        anchors.verticalCenter: parent.verticalCenter
                        color: page.cfg.enabled ? "#5fe0a4" : "#6a6a79"
                        SequentialAnimation on opacity {
                            running: page.cfg.enabled === true
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.35; duration: 900; easing.type: Easing.InOutSine }
                            NumberAnimation { to: 1; duration: 900; easing.type: Easing.InOutSine }
                        }
                    }
                    Text {
                        text: !page.cfg.enabled ? L.t("AUS") : page.device && page.device.virtual ? L.t("VORSCHAU") : "LIVE"
                        color: "#6a6a79"
                        font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3
                    }
                }
            }

            // Tools for the "Eigene Tasten" effect.
            RowLayout {
                Layout.fillWidth: true
                visible: page.painting
                spacing: 8
                Rectangle {
                    id: brushChip
                    implicitWidth: 34; implicitHeight: 34; radius: 17
                    color: page.paintColor
                    border.width: 2
                    border.color: page.eraser ? Theme.strokeSoft : "#ffffff"
                    opacity: page.eraser ? 0.45 : 1
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            Sfx.play("tap")
                            page.eraser = false
                            page.picker.openFor(brushChip, page.paintColor, value => page.paintColor = value)
                        }
                    }
                }
                IconButton {
                    icon: "eraser"; tip: L.t("Radierer")
                    active: page.eraser
                    onClicked: page.eraser = !page.eraser
                }
                Rectangle { implicitWidth: 1; implicitHeight: 20; color: Theme.stroke; Layout.leftMargin: 4; Layout.rightMargin: 4 }
                Flickable {
                    Layout.fillWidth: true
                    implicitHeight: 34
                    contentWidth: groupRow.implicitWidth
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    Row {
                        id: groupRow
                        spacing: 6
                        Repeater {
                            model: service.keyGroups
                            delegate: PillButton {
                                implicitHeight: 34
                                text: modelData.name
                                sound: "paint"
                                onClicked: service.paintKeys(modelData.ids, page.eraser ? "" : page.paintColor)
                            }
                        }
                    }
                }
                Text {
                    text: L.t("Klicken und ziehen malt · Rechtsklick löscht")
                    color: Theme.textFaint
                    font.pixelSize: 11
                    visible: page.width > 1180
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 2
                Text {
                    text: L.t("Effekte")
                    color: Theme.text
                    font.pixelSize: 17; font.weight: Font.Bold
                    Layout.fillWidth: true
                }
                Segmented {
                    options: [{value: "all", label: L.t("Alle")}].concat(service.groups.map(g => ({value: g.id, label: g.name})))
                    value: page.group
                    onChosen: value => page.group = value
                }
            }

            Flickable {
                id: gallery
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: width
                contentHeight: cards.implicitHeight + 8
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                Flow {
                    id: cards
                    width: gallery.width - 10
                    spacing: 12
                    readonly property int columns: Math.max(2, Math.floor((width + spacing) / 180))
                    Repeater {
                        model: page.catalog.filter(effect => page.group === "all" || effect.group === page.group)
                        delegate: EffectCard {
                            width: (cards.width - (cards.columns - 1) * cards.spacing) / cards.columns
                            height: 112
                            effect: modelData
                            selected: page.cfg.effect === modelData.id
                            onClicked: if (!selected) { Sfx.play("select"); service.setEffect(modelData.id) }
                        }
                    }
                }
            }
        }

        // --------------------------------------------------------- inspector
        Rectangle {
            Layout.preferredWidth: 326
            Layout.fillHeight: true
            radius: 22
            color: Theme.card
            border.width: 1
            border.color: Theme.strokeSoft

            Flickable {
                id: inspector
                anchors.fill: parent
                anchors.margins: 1
                contentWidth: width
                contentHeight: content.implicitHeight + 44
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                Column {
                    id: content
                    x: 22; y: 22
                    width: inspector.width - 44
                    spacing: 20

                    Column {
                        width: parent.width
                        spacing: 8
                        RowLayout {
                            width: parent.width
                            Text {
                                text: page.effectDef ? page.effectDef.name : ""
                                color: Theme.text
                                font.pixelSize: 19; font.weight: Font.Bold
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            IconButton {
                                icon: "undo"; tip: L.t("Effekt zurücksetzen"); flat: true; size: 30
                                onClicked: service.resetEffect()
                            }
                        }
                        Text {
                            width: parent.width
                            text: page.effectDef ? page.effectDef.description : ""
                            color: Theme.textDim
                            font.pixelSize: 13
                            lineHeight: 1.25
                            wrapMode: Text.Wrap
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 8
                        visible: page.colors.length > 0
                        RowLayout {
                            width: parent.width
                            SectionLabel { text: L.t("FARBEN"); Layout.fillWidth: true }
                            IconButton {
                                icon: "dice"; tip: L.t("Zufällige Palette"); flat: true; size: 28; sound: "select"
                                onClicked: service.shuffleColors()
                            }
                        }
                        // The strip shows how the palette blends.
                        Rectangle {
                            width: parent.width; height: 10; radius: 5
                            visible: page.colors.length > 1
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: page.colors[0] || "#000" }
                                GradientStop { position: 0.2; color: page.colors[Math.round((page.colors.length - 1) * 0.2)] || "#000" }
                                GradientStop { position: 0.4; color: page.colors[Math.round((page.colors.length - 1) * 0.4)] || "#000" }
                                GradientStop { position: 0.6; color: page.colors[Math.round((page.colors.length - 1) * 0.6)] || "#000" }
                                GradientStop { position: 0.8; color: page.colors[Math.round((page.colors.length - 1) * 0.8)] || "#000" }
                                GradientStop { position: 1; color: page.colors[page.colors.length - 1] || "#000" }
                            }
                        }
                        Repeater {
                            model: page.colors.length
                            delegate: Rectangle {
                                id: colorRow
                                width: content.width; height: 44
                                readonly property string value: page.colors[index] || "#000000"
                                radius: 12
                                color: rowArea.containsMouse ? Theme.raised : "transparent"
                                readonly property bool removable: page.effectDef && page.effectDef.flex
                                                                  && page.colors.length > page.effectDef.minColors
                                Behavior on color { ColorAnimation { duration: Theme.quick } }
                                MouseArea {
                                    id: rowArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        Sfx.play("tap")
                                        var slot = index
                                        page.picker.openFor(swatch, colorRow.value, value => service.setColor(slot, value))
                                    }
                                }
                                Rectangle {
                                    id: swatch
                                    x: 7; width: 30; height: 30; radius: 10
                                    anchors.verticalCenter: parent.verticalCenter
                                    color: colorRow.value
                                    border.width: 1
                                    border.color: Theme.stroke
                                }
                                Text {
                                    x: 49
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: (page.effectDef && page.effectDef.colorLabels[index]) || L.t("Farbe ") + (index + 1)
                                    color: Theme.text
                                    font.pixelSize: 13
                                }
                                Text {
                                    anchors.right: parent.right
                                    anchors.rightMargin: colorRow.removable ? 38 : 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: colorRow.value.toUpperCase()
                                    color: Theme.textFaint
                                    font.family: "monospace"; font.pixelSize: 11
                                }
                                IconButton {
                                    visible: colorRow.removable
                                    anchors.right: parent.right; anchors.rightMargin: 6
                                    anchors.verticalCenter: parent.verticalCenter
                                    icon: "close"; flat: true; size: 26; tip: L.t("Farbe entfernen")
                                    onClicked: service.removeColor(index)
                                }
                            }
                        }
                        PillButton {
                            visible: page.effectDef !== null && page.effectDef.flex && page.colors.length < 6
                            icon: "plus"; text: L.t("Farbe hinzufügen")
                            implicitHeight: 32
                            onClicked: service.addColor()
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 14
                        SectionLabel { text: L.t("EINSTELLUNGEN") }
                        ParamRow {
                            width: parent.width
                            label: L.t("Helligkeit")
                            value: page.cfg.brightness || 0
                            onMoved: value => service.setParam("brightness", Math.round(value))
                        }
                        Repeater {
                            model: page.effectDef ? page.effectDef.params : []
                            delegate: Item {
                                id: paramItem
                                width: content.width
                                height: isAngle ? 46 : slider.implicitHeight
                                readonly property bool isAngle: modelData.key === "angle"
                                readonly property real current: page.cfg[modelData.key] !== undefined
                                                                ? page.cfg[modelData.key] : modelData["default"]
                                ParamRow {
                                    id: slider
                                    width: parent.width
                                    visible: !paramItem.isAngle
                                    label: modelData.label
                                    value: paramItem.current
                                    onMoved: value => service.setParam(modelData.key, Math.round(value))
                                }
                                RowLayout {
                                    anchors.fill: parent
                                    visible: paramItem.isAngle
                                    spacing: 12
                                    Text { text: modelData.label; color: Theme.textDim; font.pixelSize: 13; Layout.fillWidth: true }
                                    Text { text: Math.round(paramItem.current) + "°"; color: Theme.text; font.pixelSize: 12; font.weight: Font.DemiBold }
                                    AngleDial {
                                        value: paramItem.current
                                        onMoved: value => {
                                            if (value !== paramItem.current) { Sfx.play("paint"); service.setParam("angle", value) }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: Theme.strokeSoft }

                    Column {
                        width: parent.width
                        spacing: 10
                        SectionLabel { text: L.t("PROFILE") }
                        RowLayout {
                            width: parent.width
                            spacing: 8
                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 36; radius: 18
                                color: Theme.panel
                                border.width: 1
                                border.color: profileName.activeFocus ? Theme.accentLine : Theme.strokeSoft
                                TextInput {
                                    id: profileName
                                    anchors.fill: parent
                                    anchors.leftMargin: 14; anchors.rightMargin: 14
                                    verticalAlignment: TextInput.AlignVCenter
                                    color: Theme.text
                                    selectionColor: Theme.accent
                                    selectedTextColor: Theme.accentInk
                                    font.pixelSize: 13
                                    maximumLength: 40
                                    selectByMouse: true
                                    clip: true
                                    onAccepted: saveButton.clicked()
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        visible: profileName.text === ""
                                        text: L.t("Aktuellen Stand speichern als …")
                                        color: Theme.textFaint
                                        font.pixelSize: 13
                                    }
                                }
                            }
                            IconButton {
                                id: saveButton
                                icon: "save"; tip: L.t("Als Profil speichern"); size: 36
                                onClicked: {
                                    service.saveProfile(profileName.text)
                                    if (profileName.text.trim() !== "") profileName.text = ""
                                }
                            }
                        }
                        // Saved profiles, one click to apply.
                        Repeater {
                            model: service.profiles
                            delegate: Rectangle {
                                id: quick
                                width: content.width; height: 42
                                radius: 12
                                readonly property bool active: service.activeProfile === modelData.file
                                color: active ? Theme.accentSoft : quickArea.containsMouse ? Theme.raised : "transparent"
                                Behavior on color { ColorAnimation { duration: Theme.quick } }
                                MouseArea {
                                    id: quickArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: if (!quick.active) service.applyProfile(modelData.file)
                                }
                                KeyGrid {
                                    x: 6; width: 58; height: 30; radius: 7
                                    anchors.verticalCenter: parent.verticalCenter
                                    cells: modelData.thumb
                                }
                                Column {
                                    x: 74
                                    width: parent.width - 74 - 34
                                    anchors.verticalCenter: parent.verticalCenter
                                    Text {
                                        width: parent.width
                                        text: modelData.name
                                        color: Theme.text
                                        font.pixelSize: 13; font.weight: quick.active ? Font.DemiBold : Font.Normal
                                        elide: Text.ElideRight
                                    }
                                    Text { text: modelData.effectName; color: Theme.textFaint; font.pixelSize: 11 }
                                }
                                Icon {
                                    visible: quick.active
                                    anchors.right: parent.right; anchors.rightMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: "check"; size: 15; weight: 2.2; color: Theme.accent
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
