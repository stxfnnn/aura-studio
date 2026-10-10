import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Macro editor: a list of macros on the left, the selected one on the right.
Item {
    id: page
    readonly property var list: macros.macros
    property string selectedId: ""
    readonly property var macro: list.find(entry => entry.id === selectedId) || (list.length ? list[0] : null)
    readonly property string currentId: macro ? macro.id : ""
    property bool confirmDelete: false
    onCurrentIdChanged: confirmDelete = false

    component Label: Text {
        color: Theme.textFaint
        font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.3
    }
    component Field: Rectangle {
        id: field
        property alias text: input.text
        property string placeholder: ""
        property bool numeric: false
        // Shown whenever the field is not being typed in.
        property string source: ""
        onSourceChanged: if (!input.activeFocus) input.text = source
        Component.onCompleted: input.text = source
        signal edited(string text)
        implicitHeight: 34; radius: 17
        color: Theme.panel
        border.width: 1
        border.color: input.activeFocus ? Theme.accentLine : Theme.strokeSoft
        TextInput {
            id: input
            anchors.fill: parent
            anchors.leftMargin: 14; anchors.rightMargin: 14
            verticalAlignment: TextInput.AlignVCenter
            color: Theme.text
            selectionColor: Theme.accent
            selectedTextColor: Theme.accentInk
            font.pixelSize: 13
            selectByMouse: true
            clip: true
            validator: field.numeric ? numbers : null
            onTextEdited: field.edited(text)
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: input.text === ""
                text: field.placeholder
                color: Theme.textFaint
                font.pixelSize: 13
            }
        }
        IntValidator { id: numbers; bottom: 1; top: 60000 }
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

            RowLayout {
                Layout.fillWidth: true
                Column {
                    Layout.fillWidth: true
                    spacing: 3
                    Text { text: L.t("Makros"); color: Theme.text; font.pixelSize: 23; font.weight: Font.Bold }
                    Text { text: service.settings.macros ? L.t("Aktiv") : L.t("Angehalten"); color: Theme.textFaint; font.pixelSize: 12 }
                }
                Toggle { checked: service.settings.macros; onToggled: value => service.setSetting("macros", value) }
            }
            Rectangle {
                Layout.fillWidth: true
                visible: macros.problem !== ""
                implicitHeight: problemText.implicitHeight + 20
                radius: 12
                color: Qt.rgba(Theme.bad.r, Theme.bad.g, Theme.bad.b, 0.12)
                Text {
                    id: problemText
                    x: 12; y: 10
                    width: parent.width - 24
                    text: macros.problem
                    color: Theme.bad; font.pixelSize: 12
                    wrapMode: Text.Wrap
                }
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
                        model: page.list
                        delegate: Rectangle {
                            width: rows.width; height: 56
                            radius: 14
                            readonly property bool current: modelData.id === page.currentId
                            color: current ? Theme.accentSoft : rowArea.containsMouse ? Theme.raised : Theme.card
                            border.width: 1
                            border.color: current ? Theme.accentLine : Theme.strokeSoft
                            opacity: modelData.enabled ? 1 : 0.55
                            MouseArea {
                                id: rowArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: { Sfx.play("tap"); page.selectedId = modelData.id }
                            }
                            Column {
                                x: 14
                                width: parent.width - 28
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                Text {
                                    width: parent.width
                                    text: modelData.name !== "" ? modelData.name : L.t("Ohne Namen")
                                    color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }
                                Text {
                                    width: parent.width
                                    text: modelData.triggerLabel !== "" ? modelData.triggerLabel : L.t("Kein Auslöser")
                                    color: Theme.textFaint; font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
            PillButton {
                Layout.fillWidth: true
                primary: true
                icon: "plus"; text: L.t("Neues Makro")
                onClicked: page.selectedId = macros.add()
            }
        }

        // ------------------------------------------------------------ editor
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 22
            color: Theme.card
            border.width: 1
            border.color: Theme.strokeSoft

            Column {
                visible: page.macro === null
                anchors.centerIn: parent
                spacing: 10
                width: Math.min(parent.width - 60, 460)
                Icon { name: "zap"; size: 36; color: Theme.textFaint; anchors.horizontalCenter: parent.horizontalCenter }
                Text {
                    text: L.t("Noch keine Makros")
                    color: Theme.textDim; font.pixelSize: 15; font.weight: Font.DemiBold
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    text: L.t("Ein Makro spielt auf Tastendruck eine Folge von Tasten, Mausklicks, Texten und Pausen ab – ausgelöst von einer Taste oder Maustaste deiner ROG-Geräte.")
                    color: Theme.textFaint; font.pixelSize: 12
                    wrapMode: Text.Wrap
                }
            }

            Flickable {
                id: editor
                visible: page.macro !== null
                anchors.fill: parent
                anchors.margins: 1
                contentWidth: width
                contentHeight: form.implicitHeight + 44
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                ColumnLayout {
                    id: form
                    x: 22; y: 22
                    width: editor.width - 44
                    spacing: 18

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Field {
                            id: nameField
                            Layout.fillWidth: true
                            implicitHeight: 40; radius: 20
                            placeholder: L.t("Name")
                            source: page.macro ? page.macro.name : ""
                            onEdited: text => macros.update(page.currentId, "name", text)
                            // Selecting another macro replaces the text even while the field has focus.
                            Connections {
                                target: page
                                function onCurrentIdChanged() { nameField.text = page.macro ? page.macro.name : "" }
                            }
                        }
                        Toggle {
                            checked: page.macro ? page.macro.enabled : false
                            onToggled: value => macros.update(page.currentId, "enabled", value)
                        }
                        IconButton {
                            visible: !page.confirmDelete
                            icon: "trash"; tip: L.t("Makro löschen"); flat: true
                            onClicked: page.confirmDelete = true
                        }
                        PillButton { visible: page.confirmDelete; text: L.t("Löschen"); danger: true; onClicked: { macros.remove(page.currentId); page.confirmDelete = false } }
                        PillButton { visible: page.confirmDelete; text: L.t("Abbrechen"); onClicked: page.confirmDelete = false }
                    }

                    // ------------------------------------------------ trigger
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Label { text: L.t("AUSLÖSER") }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            readonly property bool waiting: macros.capturing === "trigger:" + page.currentId
                            PillButton {
                                primary: parent.waiting
                                icon: parent.waiting ? "" : "keyboard"
                                text: parent.waiting ? L.t("Jetzt Taste oder Kombination drücken …")
                                      : page.macro && page.macro.triggerLabel !== "" ? page.macro.triggerLabel : L.t("Auslöser festlegen")
                                implicitHeight: 40
                                onClicked: macros.capture("trigger:" + page.currentId)
                            }
                            IconButton {
                                visible: page.macro !== null && page.macro.triggerLabel !== "" && !parent.waiting
                                icon: "close"; tip: L.t("Auslöser entfernen"); flat: true
                                onClicked: macros.update(page.currentId, "trigger", "")
                            }
                            Item { Layout.fillWidth: true }
                            Segmented {
                                options: [{value: "once", label: L.t("Einmal")}, {value: "hold", label: L.t("Solange gedrückt")},
                                          {value: "toggle", label: L.t("Ein / Aus")}]
                                value: page.macro ? page.macro.mode : "once"
                                onChosen: value => macros.update(page.currentId, "mode", value)
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: L.t("Auslöser kann eine Taste, eine Maustaste oder eine Kombination aus bis zu vier davon sein. Die Auslösetaste behält dabei ihre normale Funktion – am besten eine Kombination oder Taste wählen, die sonst nichts tut.")
                            color: Theme.textFaint; font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }
                    }

                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.strokeSoft }

                    // -------------------------------------------------- steps
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Label { text: L.t("SCHRITTE"); Layout.fillWidth: true }
                        PillButton {
                            readonly property bool active: macros.recording === page.currentId
                            icon: "record"; danger: active
                            text: active ? L.t("Aufnahme beenden") : L.t("Aufnehmen")
                            implicitHeight: 32
                            onClicked: macros.record(page.currentId)
                        }
                        PillButton {
                            icon: "play"; text: L.t("Testen")
                            implicitHeight: 32
                            enabled: page.macro !== null && page.macro.steps.length > 0
                            onClicked: macros.play(page.currentId)
                        }
                        IconButton {
                            icon: "trash"; tip: L.t("Alle Schritte löschen"); flat: true; size: 32
                            onClicked: macros.clearSteps(page.currentId)
                        }
                    }
                    Text {
                        visible: macros.recording === page.currentId
                        Layout.fillWidth: true
                        text: L.t("Aufnahme läuft: Jede Taste und Maustaste deiner ROG-Geräte wird mit den Pausen dazwischen als Schritt übernommen.")
                        color: Theme.bad; font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                    Text {
                        visible: page.macro !== null && page.macro.steps.length === 0 && macros.recording !== page.currentId
                        text: L.t("Noch keine Schritte. Füge unten welche hinzu oder nimm sie auf.")
                        color: Theme.textFaint; font.pixelSize: 12
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 6
                        // Rows are keyed by position, so editing a step does not rebuild the list.
                        Repeater {
                            model: page.macro ? page.macro.steps.length : 0
                            delegate: Rectangle {
                                id: stepRow
                                width: parent.width; height: 46
                                radius: 12
                                color: Theme.raised
                                readonly property var step: page.macro && page.macro.steps[index] ? page.macro.steps[index] : ({type: ""})
                                readonly property bool waiting: macros.capturing === "step:" + page.currentId + ":" + index
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12; anchors.rightMargin: 6
                                    spacing: 8
                                    Text {
                                        text: (index + 1) + "."
                                        color: Theme.textFaint; font.pixelSize: 12
                                        Layout.preferredWidth: 24
                                    }
                                    Text {
                                        text: stepRow.step.type === "key" ? L.t("Taste") : stepRow.step.type === "text" ? L.t("Text") : L.t("Pause")
                                        color: Theme.textDim; font.pixelSize: 13
                                        Layout.preferredWidth: 52
                                    }
                                    PillButton {
                                        visible: stepRow.step.type === "key"
                                        primary: stepRow.waiting
                                        text: stepRow.waiting ? L.t("Taste drücken …") : stepRow.step.label || ""
                                        implicitHeight: 32
                                        onClicked: macros.capture("step:" + page.currentId + ":" + index)
                                    }
                                    Segmented {
                                        visible: stepRow.step.type === "key"
                                        implicitHeight: 32
                                        options: [{value: "tap", label: L.t("Antippen")}, {value: "down", label: L.t("Drücken")},
                                                  {value: "up", label: L.t("Loslassen")}]
                                        value: stepRow.step.action || "tap"
                                        onChosen: value => macros.updateStep(page.currentId, index, "action", value)
                                    }
                                    Field {
                                        visible: stepRow.step.type === "text"
                                        Layout.fillWidth: true
                                        placeholder: L.t("Text, der getippt wird")
                                        source: stepRow.step.text || ""
                                        onEdited: text => macros.updateStep(page.currentId, index, "text", text)
                                    }
                                    Field {
                                        visible: stepRow.step.type === "delay"
                                        Layout.preferredWidth: 96
                                        numeric: true
                                        source: stepRow.step.ms !== undefined ? String(stepRow.step.ms) : ""
                                        onEdited: text => { if (text !== "") macros.updateStep(page.currentId, index, "ms", parseInt(text)) }
                                    }
                                    Text { visible: stepRow.step.type === "delay"; text: "ms"; color: Theme.textFaint; font.pixelSize: 12 }
                                    Item { Layout.fillWidth: true; visible: stepRow.step.type !== "text" }
                                    IconButton { icon: "up"; flat: true; size: 28; tip: L.t("Nach oben"); onClicked: macros.moveStep(page.currentId, index, -1) }
                                    IconButton { icon: "down"; flat: true; size: 28; tip: L.t("Nach unten"); onClicked: macros.moveStep(page.currentId, index, 1) }
                                    IconButton { icon: "close"; flat: true; size: 28; tip: L.t("Schritt entfernen"); onClicked: macros.removeStep(page.currentId, index) }
                                }
                            }
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        PillButton { icon: "plus"; text: L.t("Taste"); implicitHeight: 34; onClicked: macros.addStep(page.currentId, "key", 0) }
                        PillButton { icon: "plus"; text: L.t("Text"); implicitHeight: 34; onClicked: macros.addStep(page.currentId, "text", 0) }
                        PillButton { icon: "plus"; text: L.t("Pause"); implicitHeight: 34; onClicked: macros.addStep(page.currentId, "delay", 0) }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Label { text: L.t("MEDIENTASTE HINZUFÜGEN") }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: macros.mediaKeys
                                delegate: PillButton {
                                    text: modelData.label
                                    implicitHeight: 32
                                    onClicked: macros.addStep(page.currentId, "key", modelData.code)
                                }
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: L.t("Tasten für einen Schritt wählst du, indem du sie auf Tastatur oder Maus drückst. Getippter Text richtet sich nach dem Tastaturlayout aus den Einstellungen. Makros laufen, solange Aura Studio geöffnet ist.")
                        color: Theme.textFaint; font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }
}
