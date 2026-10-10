import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

ApplicationWindow {
    id: window
    width: 1440
    height: 920
    minimumWidth: 930
    minimumHeight: 680
    visible: true
    title: "Aura Studio"
    color: "#0b0c10"

    property var devices: []
    property var profiles: []
    property int selectedDevice: 0
    property string selectedEffect: "Breathing"
    property string selectedColor: "#8c6bff"
    property int brightness: 76
    property int speed: 48
    property bool busy: false
    property string statusText: "Verbinde mit Hardware-Backends …"
    property string page: "studio"
    property string logText: ""
    property bool soundsEnabled: true
    property bool showDetectedOnly: false
    property var effectCatalog: [
        {name:"Static", kind:"solid"}, {name:"Breathing", kind:"breathe"},
        {name:"Rainbow", kind:"rainbow"}, {name:"Color cycle", kind:"cycle"},
        {name:"Pulse", kind:"pulse"}, {name:"Ocean", kind:"ocean"},
        {name:"Aurora", kind:"aurora"}, {name:"Fire", kind:"fire"},
        {name:"Pastel flow", kind:"pastel"}
    ]
    readonly property var manageableDevices: devices.filter(function (device) { return device.controllable })
    readonly property var detectedOnlyDevices: devices.filter(function (device) { return !device.controllable })
    readonly property var currentDevice: selectedDevice >= 0 && selectedDevice < devices.length ? devices[selectedDevice] : null
    readonly property bool canApply: currentDevice !== null && !!currentDevice.controllable && !busy

    function apply() {
        if (devices.length && selectedDevice < devices.length)
            deviceService.applyEffect(devices[selectedDevice].id, selectedEffect, selectedColor, brightness, speed)
        else statusText = "Verbinde zuerst ein unterstütztes RGB-Gerät."
    }
    function openDevice(index) {
        selectDevice(index)
        page = "device"
    }
    function setEffectForSelectedDevice(effect) {
        var modes = devices.length && devices[selectedDevice] ? devices[selectedDevice].modes : null
        selectedEffect = modes && modes.length && !modes.includes(effect) ? modes[0] : effect
    }
    function saveProfile() { deviceService.saveProfile(profileName.text, selectedEffect, selectedColor, brightness, speed) }
    function playUiSound(kind) {
        if (!soundsEnabled) return
        if (kind === "success") successSound.play()
        else if (kind === "error") errorSound.play()
        else tapSound.play()
    }
    function openColorPicker() {
        colorDialog.draftColor = selectedColor
        colorDialog.syncFromDraft()
        colorDialog.open()
    }
    function selectDevice(index) {
        if (index < 0 || index >= devices.length) return
        selectedDevice = index
        if (!devices[index].modes || !devices[index].modes.includes(selectedEffect))
            selectedEffect = devices[index].modes && devices[index].modes.length ? devices[index].modes[0] : "Static"
        statusText = devices[index].name + " ausgewählt"
        playUiSound("tap")
        toast.open()
    }

    Connections {
        target: deviceService
        function onDevicesChanged(value) {
            window.devices = value
            var firstEditable = value.findIndex(function (device) { return device.controllable })
            window.selectedDevice = firstEditable >= 0 ? firstEditable : 0
            toast.open()
        }
        function onProfilesChanged(value) { window.profiles = value }
        function onStatusChanged(value) { window.statusText = value; if (value.startsWith("✓") || value.indexOf("gespeichert") >= 0 || value.indexOf("kopiert") >= 0) window.playUiSound("success") }
        function onErrorRaised(value) { window.statusText = value; window.playUiSound("error"); toast.open() }
        function onApplyingChanged(value) { window.busy = value }
        function onLogsChanged(value) { window.logText = value }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#111219" }
            GradientStop { position: 1.0; color: "#0a0b0f" }
        }
    }

    SoundEffect { id: tapSound; source: Qt.resolvedUrl("../assets/ui-tap.wav"); volume: 0.35 }
    SoundEffect { id: successSound; source: Qt.resolvedUrl("../assets/ui-success.wav"); volume: 0.38 }
    SoundEffect { id: errorSound; source: Qt.resolvedUrl("../assets/ui-error.wav"); volume: 0.28 }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 244
            color: "#111218"
            border.color: "#20212a"
            border.width: 1
            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 18; anchors.rightMargin: 18
                anchors.topMargin: 24; anchors.bottomMargin: 18
                spacing: 20
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    Rectangle { width: 38; height: 38; radius: 12; color: "#8c6bff"
                        Text { anchors.centerIn: parent; text: "A"; color: "white"; font.pixelSize: 20; font.weight: Font.Black }
                    }
                    ColumnLayout { spacing: 1
                        Text { text: "AURA STUDIO"; color: "#f5f4fa"; font.pixelSize: 14; font.weight: Font.Bold; font.letterSpacing: 1.2 }
                        Text { text: "DEVICE CONTROL"; color: "#747583"; font.pixelSize: 9; font.letterSpacing: 1.4 }
                    }
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: "#24252d" }
                Text { text: "WORKSPACE"; color: "#6d6e7a"; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.2; Layout.leftMargin: 8 }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 5
                    Repeater {
                        model: [{key:"studio", icon:"◈", label:"Lighting studio"}, {key:"devices", icon:"⌘", label:"My devices"}, {key:"profiles", icon:"▦", label:"Profiles"}, {key:"logs", icon:"≋", label:"Diagnoseprotokoll"}]
                        delegate: Rectangle {
                            Layout.fillWidth: true; height: 44; radius: 12
                            property bool hovered: false
                            color: window.page === modelData.key ? "#211d32" : hovered ? "#191a22" : "transparent"
                            Rectangle { width: 3; height: 22; radius: 2; color: "#9a7bff"; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; visible: window.page === modelData.key }
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 13; anchors.rightMargin: 12; spacing: 12
                                Text { text: modelData.icon; color: window.page === modelData.key ? "#a78bff" : "#858693"; font.pixelSize: 17; Layout.preferredWidth: 20; horizontalAlignment: Text.AlignHCenter }
                                Text { text: modelData.label; color: window.page === modelData.key ? "#f2efff" : "#a1a1ac"; font.pixelSize: 13; font.weight: window.page === modelData.key ? Font.DemiBold : Font.Normal; Layout.fillWidth: true }
                            }
                            Behavior on color { ColorAnimation { duration: 120 } }
                            HoverHandler { cursorShape: Qt.PointingHandCursor; onHoveredChanged: parent.hovered = hovered }
                            TapHandler { onTapped: { window.page = modelData.key; deviceService.uiAction("navigation", modelData.key); window.playUiSound("tap"); window.statusText = modelData.label + " geöffnet"; if (modelData.key === "logs") deviceService.refreshLogs(); toast.open() } }
                        }
                    }
                }
                Text { text: "CONNECTED DEVICES"; color: "#6d6e7a"; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.2; Layout.leftMargin: 8; Layout.topMargin: 7 }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 5
                    Repeater {
                        model: window.manageableDevices
                        delegate: Rectangle {
                            Layout.fillWidth: true; height: 42; radius: 10
                            color: window.currentDevice && modelData.id === window.currentDevice.id ? "#191a22" : "transparent"
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10; spacing: 10
                                Rectangle { width: 7; height: 7; radius: 4; color: "#61dfa0" }
                                Text { text: modelData.name; color: "#c7c7d0"; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                            }
                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: window.openDevice(window.devices.findIndex(function (device) { return device.id === modelData.id })) }
                        }
                    }
                    Text { visible: window.manageableDevices.length === 0; text: "Keine steuerbaren Geräte"; color: "#666773"; font.pixelSize: 11; Layout.leftMargin: 10 }
                }
                Item { Layout.fillHeight: true }
                Rectangle {
                    Layout.fillWidth: true; height: 88; radius: 14; color: "#171820"; border.color: "#24252e"
                    ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 5
                        RowLayout { spacing: 7
                            Rectangle { width: 7; height: 7; radius: 4; color: window.devices.length ? "#61dfa0" : "#e6ae61" }
                            Text { text: window.devices.length ? "BACKEND READY" : "WAITING FOR DEVICE"; color: "#d0ced8"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: .8 }
                        }
                        Text { text: window.statusText; color: "#777985"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true; maximumLineCount: 2; elide: Text.ElideRight }
                    }
                }
                RowLayout { Layout.fillWidth: true
                    Text { text: "Aura Studio"; color: "#777985"; font.pixelSize: 10; Layout.fillWidth: true }
                    Text { text: "v0.1.0"; color: "#5d5e68"; font.pixelSize: 10 }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 0
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 74
                Layout.leftMargin: 32; Layout.rightMargin: 32
                Text { text: window.page === "studio" ? "Lighting studio" : window.page === "devices" ? "My devices" : window.page === "device" ? (window.currentDevice ? window.currentDevice.name : "Gerät") : window.page === "profiles" ? "Profiles" : "Diagnoseprotokoll"; color: "#f3f2f7"; font.pixelSize: 20; font.weight: Font.DemiBold; Layout.fillWidth: true }
                Button {
                    text: window.soundsEnabled ? "♫" : "♪"
                    ToolTip.visible: hovered
                    ToolTip.text: window.soundsEnabled ? "Bediengeräusche an" : "Bediengeräusche aus"
                    onClicked: { window.soundsEnabled = !window.soundsEnabled; if (window.soundsEnabled) window.playUiSound("tap"); window.statusText = window.soundsEnabled ? "Bediengeräusche eingeschaltet" : "Bediengeräusche ausgeschaltet"; toast.open() }
                    contentItem: Text { text: parent.text; color: "#dcd3ff"; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    background: Rectangle { radius: 9; color: parent.hovered ? "#29233c" : "#171820"; border.color: "#343541" }
                    implicitWidth: 36; implicitHeight: 36
                }
                Rectangle {
                    height: 36; width: 112; radius: 10; color: "#171820"; border.color: "#2a2b35"
                    RowLayout { anchors.centerIn: parent; spacing: 8
                        Rectangle { width: 7; height: 7; radius: 4; color: "#61dfa0" }
                        Text { text: "LOCAL MODE"; color: "#c7c7d0"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: .7 }
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#20212a" }
            Flickable {
                Layout.fillWidth: true; Layout.fillHeight: true
                contentWidth: width; contentHeight: window.page === "studio" ? body.implicitHeight : subPage.implicitHeight
                clip: true; boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                ColumnLayout {
                    id: body
                    width: parent.width - 64
                    x: 32
                    visible: window.page === "studio"
                    spacing: 20
                    Item { height: 5 }

                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 300; radius: 20
                        color: "#111219"; border.color: "#282934"
                        Rectangle { anchors.fill: parent; radius: parent.radius; clip: true
                            gradient: Gradient { GradientStop { position: 0; color: "#171525" } GradientStop { position: .65; color: "#101117" } GradientStop { position: 1; color: "#101117" } }
                            Rectangle { x: parent.width * .54; y: -180; width: 440; height: 440; radius: 220; color: "#2d2350"; opacity: .14 }
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 28; spacing: 8
                                ColumnLayout { Layout.fillWidth: true; Layout.alignment: Qt.AlignVCenter; spacing: 14
                                    Rectangle { width: 106; height: 25; radius: 7; color: "#25203a"
                                        Text { anchors.centerIn: parent; text: "AURA CONTROL"; color: "#ae95ff"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: .8 }
                                    }
                                    Text { text: "Make it\nyours."; color: "#f7f5fd"; font.pixelSize: 34; font.weight: Font.DemiBold; lineHeight: 1.02 }
                                    Text { text: window.currentDevice ? window.currentDevice.name : "Personalisiere das Licht deiner ASUS Geräte."; color: "#a5a4b1"; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.maximumWidth: 300 }
                                    RowLayout { spacing: 10; Layout.topMargin: 2
                                        Button {
                                            text: window.busy ? "Wird angewendet …" : "Effekt anwenden"
                                            enabled: window.canApply
                                            onClicked: { window.playUiSound("tap"); window.apply() }
                                            contentItem: Text { text: parent.text; color: parent.enabled ? "white" : "#92919b"; font.pixelSize: 12; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { radius: 10; color: parent.enabled ? "#8c6bff" : "#393640" }
                                            implicitHeight: 40; implicitWidth: 146
                                        }
                                        Button {
                                            text: "⌁  Suchen"
                                            onClicked: { window.playUiSound("tap"); deviceService.scan() }
                                            contentItem: Text { text: parent.text; color: "#d4d2dd"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { radius: 10; color: "#20212a"; border.color: "#343541" }
                                            implicitHeight: 40; implicitWidth: 103
                                        }
                                    }
                                }
                                Item { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumWidth: 215
                                    Column {
                                        anchors.centerIn: parent; spacing: 9; rotation: -7
                                        Repeater {
                                            model: 5
                                            delegate: Row {
                                                spacing: 5
                                                Repeater {
                                                    model: index === 0 ? 10 : index === 4 ? 9 : 12
                                                    delegate: Rectangle {
                                                        width: index === 0 ? 20 : 21; height: 23; radius: 5
                                                        color: ["#352b57", "#473477", "#6f49bb", "#6242a5", "#302b44"][((index * 7 + model.index * 3) % 5)]
                                                        opacity: .65 + ((index + model.index) % 3) * .1
                                                        border.color: "#a887ff"; border.width: .5
                                                    }
                                                }
                                            }
                                        }
                                        Rectangle { width: 310; height: 4; radius: 2; color: "#8c6bff"; opacity: .3; anchors.horizontalCenter: parent.horizontalCenter }
                                    }
                                }
                            }
                        }
                    }

                    RowLayout { Layout.fillWidth: true; spacing: 18
                        ColumnLayout { Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; spacing: 16
                            RowLayout { Layout.fillWidth: true
                                ColumnLayout { Layout.fillWidth: true; spacing: 4
                                    Text { text: "Lighting"; color: "#f0eff5"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                    Text { text: "Effekt, Farbe und Intensität fein abstimmen"; color: "#858692"; font.pixelSize: 11 }
                                }
                                ComboBox {
                                    id: devicePicker
                                    visible: window.manageableDevices.length > 0
                                    Layout.preferredWidth: 185; Layout.preferredHeight: 38
                                    model: window.manageableDevices.map(d => d.name)
                                    currentIndex: window.currentDevice ? window.manageableDevices.findIndex(d => d.id === window.currentDevice.id) : -1
                                    onActivated: window.selectDevice(window.devices.findIndex(d => d.id === window.manageableDevices[currentIndex].id))
                                    contentItem: Text { leftPadding: 12; text: devicePicker.displayText; color: "#e2e0e8"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                                    background: Rectangle { radius: 9; color: "#171820"; border.color: "#30313b" }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; radius: 16; color: "#121319"; border.color: "#252630"
                                implicitHeight: controls.implicitHeight + 34
                                ColumnLayout { id: controls; anchors.fill: parent; anchors.margins: 17; spacing: 17
                                    Text { text: "PRESET EFFECTS"; color: "#777985"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                                    GridLayout {
                                        Layout.fillWidth: true; columns: width > 700 ? 3 : width > 430 ? 2 : 1; columnSpacing: 9; rowSpacing: 9
                                        Repeater { model: window.effectCatalog
                                            delegate: Rectangle {
                                                id: effectTile
                                                Layout.fillWidth: true; Layout.preferredHeight: 78; radius: 12
                                                property bool supported: !window.currentDevice || !window.currentDevice.modes || window.currentDevice.modes.includes(modelData.name)
                                                property bool hovered: false
                                                property bool pressed: false
                                                opacity: supported ? 1 : .42
                                                color: window.selectedEffect === modelData.name ? "#211d32" : hovered ? "#21222d" : pressed ? "#242433" : "#181920"
                                                border.color: window.selectedEffect === modelData.name ? "#7253c9" : hovered ? "#494259" : "#292a34"
                                                Behavior on color { ColorAnimation { duration: 120 } }
                                                ColumnLayout { anchors.fill: parent; anchors.margins: 11; spacing: 8
                                                    RowLayout { Layout.fillWidth: true
                                                        Row { spacing: 3
                                                            Repeater { model: effectTile.kind === "rainbow" || effectTile.kind === "cycle" || effectTile.kind === "pastel" ? ["#fb6679", "#ffc064", "#70d9a6", "#64baff", "#a77cff"] : effectTile.kind === "fire" ? ["#ff5a36", "#ffbd43", "#bb2525"] : effectTile.kind === "ocean" ? ["#20c5d8", "#367bff", "#302fba"] : effectTile.kind === "aurora" ? ["#44e2a0", "#4ca9d9", "#9b69ee"] : [window.selectedColor, effectTile.kind === "breathe" || effectTile.kind === "pulse" ? "#4b3981" : window.selectedColor]
                                                                delegate: Rectangle { width: 17; height: 17; radius: 6; color: modelData; opacity: 1 }
                                                            }
                                                        }
                                                        Item { Layout.fillWidth: true }
                                                        Text { text: window.selectedEffect === modelData.name ? "✓" : ""; color: "#c6b7ff"; font.pixelSize: 12 }
                                                    }
                                                    Text { text: modelData.name; color: "#dedce5"; font.pixelSize: 10; font.weight: Font.Medium }
                                                }
                                                HoverHandler { enabled: effectTile.supported; cursorShape: Qt.PointingHandCursor; onHoveredChanged: effectTile.hovered = hovered }
                                                TapHandler { enabled: effectTile.supported; onPressedChanged: effectTile.pressed = pressed; onTapped: { window.selectedEffect = modelData.name; window.statusText = modelData.name + " ausgewählt"; deviceService.uiAction("effect selected", modelData.name); window.playUiSound("tap"); toast.open() } }
                                            }
                                        }
                                    }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: "#282932" }
                                    RowLayout { Layout.fillWidth: true; spacing: 12
                                        ColumnLayout { Layout.fillWidth: true; spacing: 10
                                            RowLayout { Layout.fillWidth: true
                                                Text { text: "Farbe"; color: "#b8b7c1"; font.pixelSize: 11; Layout.fillWidth: true }
                                                Text { text: window.selectedColor.toUpperCase(); color: "#777985"; font.pixelSize: 9; font.family: "monospace" }
                                            }
                                            Row { spacing: 8
                                                Repeater { model: ["#8c6bff", "#41b7ff", "#47d9a0", "#ff6c89", "#ffbd5c", "#f4f4f7"]
                                                    delegate: Rectangle { width: 23; height: 23; radius: 8; color: modelData; border.color: window.selectedColor === modelData ? "white" : "#454650"; border.width: window.selectedColor === modelData ? 2 : 1
                                                        scale: swatchHover.hovered ? 1.14 : 1
                                                        Behavior on scale { NumberAnimation { duration: 100 } }
                                                        HoverHandler { id: swatchHover; cursorShape: Qt.PointingHandCursor }
                                                        TapHandler { onTapped: { window.selectedColor = modelData; window.statusText = "Farbe " + modelData.toUpperCase() + " ausgewählt"; deviceService.uiAction("color selected", modelData); window.playUiSound("tap"); toast.open() } }
                                                    }
                                                }
                                                Rectangle { width: 23; height: 23; radius: 8; color: "#252630"; border.color: "#454650"
                                                    Text { anchors.centerIn: parent; text: "+"; color: "#dddbe5"; font.pixelSize: 17 }
                                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                                    TapHandler { onTapped: { window.openColorPicker(); window.playUiSound("tap") } }
                                                }
                                            }
                                        }
                                    }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: "#282932" }
                                    RowLayout { Layout.fillWidth: true; spacing: 18
                                        ColumnLayout { Layout.fillWidth: true; spacing: 7
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text { text: "Helligkeit"; color: "#b8b7c1"; font.pixelSize: 11; Layout.fillWidth: true }
                                                Text { text: brightness + "%"; color: "#8d8e9a"; font.pixelSize: 10 }
                                            }
                                            Slider { Layout.fillWidth: true; from: 0; to: 100; value: window.brightness; onMoved: window.brightness = Math.round(value) }
                                        }
                                        ColumnLayout { Layout.fillWidth: true; spacing: 7
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text { text: "Geschwindigkeit"; color: "#b8b7c1"; font.pixelSize: 11; Layout.fillWidth: true }
                                                Text { text: speed + "%"; color: "#8d8e9a"; font.pixelSize: 10 }
                                            }
                                            Slider { Layout.fillWidth: true; from: 0; to: 100; value: window.speed; onMoved: window.speed = Math.round(value) }
                                        }
                                    }
                                    Button {
                                        Layout.alignment: Qt.AlignRight
                                        text: "Auf Gerät anwenden  →"; enabled: window.canApply
                                        onClicked: { window.playUiSound("tap"); window.apply() }
                                        contentItem: Text { text: parent.text; color: parent.enabled ? "#dcd3ff" : "#6f6e78"; font.pixelSize: 11; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 9; color: parent.enabled ? "#29233c" : "#1d1e25"; border.color: "#514174" }
                                        implicitHeight: 37; implicitWidth: 177
                                    }
                                }
                            }
                        }

                        ColumnLayout { Layout.preferredWidth: 250; Layout.minimumWidth: 205; Layout.alignment: Qt.AlignTop; spacing: 14
                            Rectangle {
                                visible: window.currentDevice && window.currentDevice.name.indexOf("Azoth") >= 0
                                Layout.fillWidth: true; implicitHeight: oledContent.implicitHeight + 34; radius: 16; color: "#121319"; border.color: "#252630"
                                ColumnLayout { id: oledContent; anchors.fill: parent; anchors.margins: 16; spacing: 11
                                    RowLayout { Layout.fillWidth: true
                                        Text { text: window.devices.length && window.devices[window.selectedDevice].category === "Maus" ? "MOUSE WHEEL LED" : "OLED DISPLAY"; color: "#c9c6d1"; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: .8; Layout.fillWidth: true }
                                        Rectangle { visible: !window.devices.length || window.devices[window.selectedDevice].category !== "Maus"; width: 44; height: 20; radius: 7; color: "#2c243d"; Text { anchors.centerIn: parent; text: "BETA"; color: "#bc9dff"; font.pixelSize: 8; font.weight: Font.Bold } }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; height: 103; radius: 12; color: "#07080b"; border.color: "#33343d"
                                        ColumnLayout { anchors.centerIn: parent; spacing: 5
                                            Text { text: window.devices.length && window.devices[window.selectedDevice].category === "Maus" ? "●" : "ROG"; color: window.devices.length && window.devices[window.selectedDevice].category === "Maus" ? window.selectedColor : "#d7d2e6"; font.pixelSize: window.devices.length && window.devices[window.selectedDevice].category === "Maus" ? 28 : 18; font.weight: Font.Black; font.letterSpacing: 4; Layout.alignment: Qt.AlignHCenter }
                                            Text { text: window.devices.length && window.devices[window.selectedDevice].category === "Maus" ? "RGB LAMP ARRAY" : "DISPLAY PREVIEW"; color: "#666873"; font.pixelSize: 7; font.letterSpacing: 1.4; Layout.alignment: Qt.AlignHCenter }
                                        }
                                        Rectangle { x: 10; y: 10; width: 4; height: 4; radius: 2; color: "#69dda2" }
                                    }
                                    Text { text: window.devices.length && window.devices[window.selectedDevice].category === "Maus" ? window.devices[window.selectedDevice].name + " · Mausrad" : "ROG Azoth · OLED"; color: "#e4e1e9"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                    Text { text: window.devices.length && window.devices[window.selectedDevice].category === "Maus" ? "Direkte HID LampArray-Steuerung" : "Adapter in Entwicklung"; color: "#858692"; font.pixelSize: 10 }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: "#282932" }
                                    Text { text: window.devices.length && window.devices[window.selectedDevice].category === "Maus" ? "Die einzelne LED im Mausrad wird über die standardisierte HID-LampArray-Schnittstelle gesteuert." : "Azoth-OLED-Schreibzugriff ist noch nicht integriert. Die RGB-Steuerung nutzt den nativen HID-Adapter."; color: "#a09eaa"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true; lineHeight: 1.2 }
                                    Button {
                                        visible: !window.devices.length || window.devices[window.selectedDevice].category !== "Maus"
                                        Layout.fillWidth: true; text: "OLED-Steuerung nicht verfügbar"; enabled: false
                                        contentItem: Text { text: parent.text; color: "#75747e"; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 9; color: "#1b1c23"; border.color: "#292a33" }
                                        implicitHeight: 34
                                    }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; implicitHeight: profileBox.implicitHeight + 28; radius: 16; color: "#121319"; border.color: "#252630"
                                ColumnLayout { id: profileBox; anchors.fill: parent; anchors.margins: 14; spacing: 10
                                    RowLayout { Layout.fillWidth: true
                                        Text { text: "QUICK PROFILES"; color: "#c9c6d1"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: .8; Layout.fillWidth: true }
                                        Text { text: "⌘"; color: "#878794"; font.pixelSize: 12 }
                                    }
                                    Repeater {
                                        model: window.profiles.slice(0, 3)
                                        delegate: Rectangle {
                                            Layout.fillWidth: true; height: 39; radius: 9; color: "#191a21"
                                            RowLayout { anchors.fill: parent; anchors.leftMargin: 9; anchors.rightMargin: 9; spacing: 8
                                                Rectangle { width: 9; height: 9; radius: 3; color: modelData.color }
                                                Text { text: modelData.name; color: "#c9c7d1"; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                                Text { text: "↗"; color: "#8b8997"; font.pixelSize: 12 }
                                            }
                                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                                            TapHandler { onTapped: { window.setEffectForSelectedDevice(modelData.effect); window.selectedColor = modelData.color; window.brightness = modelData.brightness; window.speed = modelData.speed; window.statusText = "Profil „" + modelData.name + "“ geladen"; deviceService.uiAction("profile loaded", modelData.name); window.playUiSound("tap"); toast.open() } }
                                        }
                                    }
                                    TextField { id: profileName; Layout.fillWidth: true; placeholderText: "Profilname"; color: "#e6e3ed"; font.pixelSize: 10; implicitHeight: 34; leftPadding: 10
                                        background: Rectangle { radius: 8; color: "#1a1b22"; border.color: "#2b2c35" }
                                    }
                                    Button { Layout.fillWidth: true; text: "Aktuelles Profil speichern"; onClicked: { window.playUiSound("tap"); window.saveProfile() }
                                        contentItem: Text { text: parent.text; color: "#c9b9ff"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 9; color: "#29233c"; border.color: "#514174" }
                                        implicitHeight: 34
                                    }
                                }
                            }
                        }
                    }
                    Item { height: 3 }
                }
                ColumnLayout {
                    id: subPage
                    width: parent.width - 64
                    x: 32
                    visible: window.page !== "studio"
                    spacing: 18
                    Item { height: 5 }
                    Rectangle {
                        visible: window.page === "device"
                        Layout.fillWidth: true
                        radius: 16; color: "#121319"; border.color: "#252630"
                        implicitHeight: deviceSettings.implicitHeight + 36
                        ColumnLayout {
                            id: deviceSettings
                            anchors.fill: parent; anchors.margins: 20; spacing: 16
                            RowLayout {
                                Layout.fillWidth: true
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 5
                                    Text { text: window.currentDevice ? window.currentDevice.name : "Kein Gerät ausgewählt"; color: "#f0eff5"; font.pixelSize: 19; font.weight: Font.DemiBold }
                                    Text { text: window.currentDevice ? window.currentDevice.category + " · " + window.currentDevice.detail : ""; color: "#858692"; font.pixelSize: 11; wrapMode: Text.Wrap }
                                }
                                Button {
                                    text: "‹  Alle Geräte"; onClicked: window.page = "devices"
                                    contentItem: Text { text: parent.text; color: "#d4d2dd"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    background: Rectangle { radius: 9; color: "#20212a"; border.color: "#343541" }
                                    implicitHeight: 36; implicitWidth: 112
                                }
                            }
                            Text { visible: !window.currentDevice || window.currentDevice.controllable !== true; text: "Keine Einstellmöglichkeiten für dieses Gerät verfügbar."; color: "#a09eaa"; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                            ColumnLayout {
                                visible: window.currentDevice && window.currentDevice.controllable === true
                                Layout.fillWidth: true; spacing: 16
                                Rectangle { Layout.fillWidth: true; height: 1; color: "#282932" }
                                Text { text: "BELEUCHTUNG"; color: "#777985"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                                GridLayout {
                                    Layout.fillWidth: true; columns: width > 680 ? 3 : width > 410 ? 2 : 1; columnSpacing: 9; rowSpacing: 9
                                    Repeater {
                                        model: window.effectCatalog
                                        delegate: Rectangle {
                                            Layout.fillWidth: true; Layout.preferredHeight: 48; radius: 10
                                            color: window.selectedEffect === modelData.name ? "#211d32" : "#191a21"
                                            border.color: window.selectedEffect === modelData.name ? "#7253c9" : "#292a34"
                                            Text { anchors.centerIn: parent; text: modelData.name; color: "#dedce5"; font.pixelSize: 10 }
                                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                                            TapHandler { onTapped: { window.setEffectForSelectedDevice(modelData.name); window.playUiSound("tap") } }
                                        }
                                    }
                                }
                                Text { visible: window.currentDevice && window.currentDevice.category === "Maus"; text: "Mausrad-LED · Farbeffekte werden fließend animiert"; color: "#c9c6d1"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                Row {
                                    spacing: 9
                                    Repeater {
                                        model: ["#8c6bff", "#41b7ff", "#47d9a0", "#ff6c89", "#ffbd5c", "#f4f4f7"]
                                        delegate: Rectangle {
                                            width: 28; height: 28; radius: 9; color: modelData
                                            border.color: window.selectedColor === modelData ? "white" : "#454650"
                                            border.width: window.selectedColor === modelData ? 2 : 1
                                            HoverHandler { cursorShape: Qt.PointingHandCursor }
                                            TapHandler { onTapped: { window.selectedColor = modelData; window.playUiSound("tap") } }
                                        }
                                    }
                                    Button {
                                        text: "＋ Eigene Farbe"
                                        onClicked: { window.openColorPicker(); window.playUiSound("tap") }
                                        contentItem: Text { text: parent.text; color: "#dcd3ff"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                        background: Rectangle { radius: 8; color: "#211d32"; border.color: "#514174" }
                                        implicitHeight: 32; implicitWidth: 118
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Text { text: "Helligkeit · " + window.brightness + "%"; color: "#b8b7c1"; font.pixelSize: 11 }
                                        Slider { Layout.fillWidth: true; from: 0; to: 100; value: window.brightness; onMoved: window.brightness = Math.round(value) }
                                    }
                                    ColumnLayout {
                                        visible: window.currentDevice && window.currentDevice.controllable
                                        Layout.fillWidth: true
                                        Text { text: "Geschwindigkeit · " + window.speed + "%"; color: "#b8b7c1"; font.pixelSize: 11 }
                                        Slider { Layout.fillWidth: true; from: 0; to: 100; value: window.speed; onMoved: window.speed = Math.round(value) }
                                    }
                                }
                                Rectangle {
                                    visible: window.currentDevice && window.currentDevice.name.indexOf("Azoth") >= 0
                                    Layout.fillWidth: true; radius: 12; color: "#0b0c10"; border.color: "#292a34"
                                    implicitHeight: oledInfo.implicitHeight + 28
                                    ColumnLayout { id: oledInfo; anchors.fill: parent; anchors.margins: 14; spacing: 7
                                        Text { text: "OLED DISPLAY"; color: "#c9c6d1"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: .8 }
                                        Text { text: "Azoth-OLED-Schreibzugriff ist noch nicht integriert."; color: "#a09eaa"; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    }
                                }
                                Button {
                                    Layout.alignment: Qt.AlignRight
                                    text: window.busy ? "Wird angewendet …" : "Auf Gerät anwenden  →"
                                    enabled: window.canApply; onClicked: { window.playUiSound("tap"); window.apply() }
                                    contentItem: Text { text: parent.text; color: parent.enabled ? "#dcd3ff" : "#6f6e78"; font.pixelSize: 11; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    background: Rectangle { radius: 9; color: parent.enabled ? "#29233c" : "#1d1e25"; border.color: "#514174" }
                                    implicitHeight: 40; implicitWidth: 190
                                }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            Text { text: window.page === "devices" ? "Deine ASUS-Geräte" : window.page === "device" ? "Gerätespezifische Einstellungen" : window.page === "profiles" ? "Deine Lichtprofile" : "HID- und Anwendungsereignisse"; color: "#f0eff5"; font.pixelSize: 19; font.weight: Font.DemiBold }
                            Text { text: window.page === "devices" ? "Direkte Geräteerkennung über Linux HID" : window.page === "device" ? "Nur Funktionen, die dieses Gerät unterstützt" : window.page === "profiles" ? "Lokal gespeicherte Beleuchtungseinstellungen" : deviceService.logLocation(); color: "#858692"; font.pixelSize: 11 }
                        }
                        Button {
                            visible: window.page === "devices"
                            text: "⌁  Erneut suchen"
                            onClicked: { window.playUiSound("tap"); deviceService.scan() }
                            contentItem: Text { text: parent.text; color: "#d4d2dd"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            background: Rectangle { radius: 9; color: "#20212a"; border.color: "#343541" }
                            implicitHeight: 38; implicitWidth: 130
                        }
                    }
                    Rectangle {
                        visible: window.page === "devices"
                        Layout.fillWidth: true
                        radius: 16
                        color: "#121319"
                        border.color: "#252630"
                        implicitHeight: deviceRows.implicitHeight + 34
                        ColumnLayout {
                            id: deviceRows
                            anchors.fill: parent
                            anchors.margins: 17
                            spacing: 10
                            Text { text: window.manageableDevices.length ? "STEUERBARE GERÄTE" : "KEINE STEUERBAREN GERÄTE"; color: "#777985"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                            Repeater {
                                model: window.manageableDevices
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 78
                                    radius: 12
                                    color: "#191a21"
                                    border.color: "#292a34"
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 14
                                        anchors.rightMargin: 14
                                        spacing: 12
                                        Rectangle {
                                            width: 38; height: 38; radius: 11
                                            color: modelData.controllable ? "#29233c" : "#24252d"
                                            Text { anchors.centerIn: parent; text: modelData.category === "Tastatur" ? "⌨" : modelData.category === "Maus" ? "◉" : "◈"; color: modelData.controllable ? "#c6b4ff" : "#9899a3"; font.pixelSize: 17 }
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Text { text: modelData.name; color: "#e0dee7"; font.pixelSize: 12; font.weight: Font.DemiBold }
                                            Text { text: modelData.category + "  ·  " + modelData.product_id + "  ·  " + modelData.detail; color: "#858692"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
                                        }
                                        Rectangle {
                                            width: 88; height: 25; radius: 8
                                            color: modelData.controllable ? "#183127" : "#28252a"
                                            Text { anchors.centerIn: parent; text: modelData.controllable ? "STEUERBAR" : "ERKANNT"; color: modelData.controllable ? "#72dfa8" : "#c1a7a4"; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: .5 }
                                        }
                                        Button {
                                            text: "Gerät öffnen"
                                            onClicked: window.openDevice(window.devices.findIndex(function (device) { return device.id === modelData.id }))
                                            contentItem: Text { text: parent.text; color: "#dcd3ff"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { radius: 8; color: "#29233c"; border.color: "#514174" }
                                            implicitHeight: 34; implicitWidth: 104
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                visible: window.detectedOnlyDevices.length > 0
                                Layout.fillWidth: true; height: 44; radius: 10
                                color: detectedHover.hovered ? "#1b1c25" : "#171820"
                                border.color: "#292a34"
                                RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                                    Text { text: "Erkannt, nicht editierbar"; color: "#b4b2bd"; font.pixelSize: 11; Layout.fillWidth: true }
                                    Text { text: "" + window.detectedOnlyDevices.length; color: "#858692"; font.pixelSize: 10 }
                                    Text { text: window.showDetectedOnly ? "⌃" : "⌄"; color: "#aaa7b5"; font.pixelSize: 13 }
                                }
                                HoverHandler { id: detectedHover; cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: { window.showDetectedOnly = !window.showDetectedOnly; window.playUiSound("tap") } }
                            }
                            ColumnLayout {
                                visible: window.showDetectedOnly && window.detectedOnlyDevices.length > 0
                                Layout.fillWidth: true; spacing: 8
                                Repeater {
                                    model: window.detectedOnlyDevices
                                    delegate: Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 68; radius: 10
                                        color: "#171820"; border.color: "#252630"
                                        RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 14; spacing: 11
                                            Rectangle { width: 34; height: 34; radius: 10; color: "#22232b"
                                                Text { anchors.centerIn: parent; text: modelData.category === "Tastatur" ? "⌨" : modelData.category === "Maus" ? "◉" : "◈"; color: "#898a96"; font.pixelSize: 15 }
                                            }
                                            ColumnLayout { Layout.fillWidth: true; spacing: 4
                                                Text { text: modelData.name; color: "#c5c3cd"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                                Text { text: modelData.category + " · " + modelData.product_id + " · " + modelData.detail; color: "#777985"; font.pixelSize: 9; elide: Text.ElideRight; Layout.fillWidth: true }
                                            }
                                            Text { text: "Kein Adapter"; color: "#9a8b8b"; font.pixelSize: 9 }
                                        }
                                    }
                                }
                            }
                            Text {
                                visible: window.devices.length === 0 || window.manageableDevices.length === 0
                                text: window.devices.length === 0 ? "Schließe ein ASUS-Gerät per USB an und starte die Suche erneut." : "Es wurde noch kein direkt steuerbares ASUS-Gerät gefunden."
                                color: "#858692"; font.pixelSize: 11
                                Layout.fillWidth: true
                            }
                        }
                    }
                    Rectangle {
                        visible: window.page === "profiles"
                        Layout.fillWidth: true
                        radius: 16
                        color: "#121319"
                        border.color: "#252630"
                        implicitHeight: profilesLayout.implicitHeight + 34
                        ColumnLayout {
                            id: profilesLayout
                            anchors.fill: parent
                            anchors.margins: 17
                            spacing: 10
                            Text { text: "GESPEICHERTE PROFILE"; color: "#777985"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1.1 }
                            Repeater {
                                model: window.profiles
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 66
                                    radius: 11
                                    color: "#191a21"
                                    border.color: "#292a34"
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 13
                                        anchors.rightMargin: 13
                                        spacing: 10
                                        Rectangle { width: 12; height: 30; radius: 5; color: modelData.color }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 3
                                            Text { text: modelData.name; color: "#e0dee7"; font.pixelSize: 11; font.weight: Font.DemiBold }
                                            Text { text: modelData.effect + "  ·  " + modelData.color.toUpperCase() + "  ·  " + modelData.brightness + "%"; color: "#858692"; font.pixelSize: 10 }
                                        }
                                        Button {
                                            text: "Profil laden"
                                            onClicked: { window.setEffectForSelectedDevice(modelData.effect); window.selectedColor = modelData.color; window.brightness = modelData.brightness; window.speed = modelData.speed; window.page = "studio"; window.playUiSound("tap") }
                                            contentItem: Text { text: parent.text; color: "#dcd3ff"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            background: Rectangle { radius: 8; color: "#29233c"; border.color: "#514174" }
                                            implicitHeight: 34; implicitWidth: 105
                                        }
                                    }
                                }
                            }
                            Text {
                                visible: window.profiles.length === 0
                                text: "Noch keine Profile. Erstelle dein erstes im Lighting Studio."
                                color: "#858692"; font.pixelSize: 11
                                Layout.fillWidth: true
                            }
                        }
                    }
                    Rectangle {
                        visible: window.page === "logs"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 620
                        radius: 16
                        color: "#101116"
                        border.color: "#252630"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "LETZTE EREIGNISSE · HID-SCAN · SCHREIBVERSUCHE"; color: "#9e9ba9"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: .8; Layout.fillWidth: true }
                                Button {
                                    text: "Aktualisieren"
                                    onClicked: deviceService.refreshLogs()
                                    contentItem: Text { text: parent.text; color: "#ded9ed"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    background: Rectangle { radius: 8; color: parent.hovered ? "#353044" : "#24232c" }
                                    implicitHeight: 32
                                    implicitWidth: 95
                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                }
                                Button {
                                    text: "Protokoll kopieren"
                                    onClicked: deviceService.copyLogs()
                                    contentItem: Text { text: parent.text; color: "#ded9ed"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                    background: Rectangle { radius: 8; color: parent.hovered ? "#353044" : "#24232c" }
                                    implicitHeight: 32
                                    implicitWidth: 125
                                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true; Layout.fillHeight: true; radius: 10; color: "#0a0b0e"; border.color: "#252630"
                                Flickable {
                                    anchors.fill: parent; anchors.margins: 10; clip: true; contentWidth: width; contentHeight: logArea.implicitHeight
                                    TextArea { id: logArea; width: parent.width; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; text: window.logText; color: "#b7c8ba"; selectionColor: "#50417b"; selectedTextColor: "white"; font.family: "monospace"; font.pixelSize: 10; background: null }
                                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                                }
                            }
                            Text { text: "Seriennummern werden nicht protokolliert. Das Protokoll rotiert automatisch."; color: "#747581"; font.pixelSize: 9 }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: colorDialog
        title: "Eigene Farbe"
        modal: true
        anchors.centerIn: parent
        width: 440
        standardButtons: Dialog.Ok | Dialog.Cancel
        property real hue: 0
        property real saturation: 1
        property real value: 1
        property string draftColor: "#8c6bff"
        function colorHex() {
            var color = Qt.hsva(hue / 360, saturation, value, 1)
            function byteHex(channel) { var result = Math.round(channel * 255).toString(16); return result.length < 2 ? "0" + result : result }
            return "#" + byteHex(color.r) + byteHex(color.g) + byteHex(color.b)
        }
        function updateDraft() { draftColor = colorHex(); customColor.text = draftColor }
        function syncFromDraft() {
            var red = parseInt(draftColor.slice(1, 3), 16) / 255
            var green = parseInt(draftColor.slice(3, 5), 16) / 255
            var blue = parseInt(draftColor.slice(5, 7), 16) / 255
            var maximum = Math.max(red, green, blue)
            var minimum = Math.min(red, green, blue)
            var delta = maximum - minimum
            value = maximum
            saturation = maximum === 0 ? 0 : delta / maximum
            if (delta === 0) hue = 0
            else if (maximum === red) hue = 60 * (((green - blue) / delta) % 6)
            else if (maximum === green) hue = 60 * ((blue - red) / delta + 2)
            else hue = 60 * ((red - green) / delta + 4)
            if (hue < 0) hue += 360
            customColor.text = draftColor
        }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: "Farbton und Intensität frei wählen"; color: "#a6a3af"; font.pixelSize: 11 }
            Rectangle {
                Layout.fillWidth: true; height: 174; radius: 12; clip: true
                color: Qt.hsva(colorDialog.hue / 360, 1, 1, 1)
                border.color: "#393a45"
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: "white" }
                        GradientStop { position: 1; color: "transparent" }
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0; color: "transparent" }
                        GradientStop { position: 1; color: "black" }
                    }
                }
                Rectangle {
                    x: colorDialog.saturation * (parent.width - width) - width / 2
                    y: (1 - colorDialog.value) * (parent.height - height) - height / 2
                    width: 18; height: 18; radius: 9; color: "transparent"
                    border.color: "white"; border.width: 2
                    Rectangle { anchors.centerIn: parent; width: 5; height: 5; radius: 3; color: "white" }
                }
                MouseArea {
                    anchors.fill: parent
                    onPressed: updatePoint(mouse.x, mouse.y)
                    onPositionChanged: if (pressed) updatePoint(mouse.x, mouse.y)
                    function updatePoint(x, y) {
                        colorDialog.saturation = Math.max(0, Math.min(1, x / width))
                        colorDialog.value = 1 - Math.max(0, Math.min(1, y / height))
                        colorDialog.updateDraft()
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 11
                Text { text: "Farbton"; color: "#c7c5cf"; font.pixelSize: 10 }
                Slider {
                    id: hueSlider
                    Layout.fillWidth: true; from: 0; to: 360; value: colorDialog.hue
                    onMoved: { colorDialog.hue = value; colorDialog.updateDraft() }
                    background: Rectangle {
                        x: hueSlider.leftPadding; y: hueSlider.topPadding + hueSlider.availableHeight / 2 - height / 2
                        width: hueSlider.availableWidth; height: 10; radius: 5
                        gradient: Gradient {
                            GradientStop { position: 0; color: Qt.hsva(0, 1, 1, 1) }
                            GradientStop { position: .17; color: Qt.hsva(.17, 1, 1, 1) }
                            GradientStop { position: .34; color: Qt.hsva(.34, 1, 1, 1) }
                            GradientStop { position: .51; color: Qt.hsva(.51, 1, 1, 1) }
                            GradientStop { position: .68; color: Qt.hsva(.68, 1, 1, 1) }
                            GradientStop { position: .85; color: Qt.hsva(.85, 1, 1, 1) }
                            GradientStop { position: 1; color: Qt.hsva(1, 1, 1, 1) }
                        }
                    }
                    handle: Rectangle { width: 18; height: 18; radius: 9; color: "white"; border.color: "#383842" }
                }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                Rectangle { width: 42; height: 34; radius: 8; color: colorDialog.draftColor; border.color: "#ffffff55" }
                TextField {
                    id: customColor
                    Layout.fillWidth: true
                    placeholderText: "#8c6bff"
                    color: "#e6e3ed"; font.family: "monospace"; font.pixelSize: 12
                    selectByMouse: true
                    background: Rectangle { radius: 8; color: "#1a1b22"; border.color: "#343541" }
                    onEditingFinished: {
                        var colorValue = text.trim()
                        if (!colorValue.startsWith("#")) colorValue = "#" + colorValue
                        if (/^#[0-9a-fA-F]{6}$/.test(colorValue)) {
                            colorDialog.draftColor = colorValue.toLowerCase()
                            colorDialog.syncFromDraft()
                        } else text = colorDialog.draftColor
                    }
                }
                Text { text: "HEX"; color: "#7d7e8a"; font.pixelSize: 9; font.weight: Font.Bold }
            }
            Text { text: "Presets"; color: "#a6a3af"; font.pixelSize: 10 }
            Row {
                spacing: 8
                Repeater {
                    model: ["#8c6bff", "#41b7ff", "#47d9a0", "#ff6c89", "#ffbd5c", "#f4f4f7", "#ff5a36", "#28d7d0"]
                    delegate: Rectangle {
                        width: 25; height: 25; radius: 8; color: modelData
                        border.color: colorDialog.draftColor === modelData ? "white" : "#454650"
                        border.width: colorDialog.draftColor === modelData ? 2 : 1
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: { colorDialog.draftColor = modelData; colorDialog.syncFromDraft(); window.playUiSound("tap") } }
                    }
                }
            }
        }
        onAccepted: { window.selectedColor = draftColor; window.playUiSound("success") }
    }
    Popup {
        id: toast
        x: window.width - width - 28; y: window.height - height - 26
        width: Math.min(380, window.width - 40); height: 58
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { radius: 12; color: "#26212f"; border.color: "#69539a" }
        contentItem: Text { text: window.statusText; color: "#eeeaf7"; font.pixelSize: 11; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter; leftPadding: 12; rightPadding: 12 }
        Timer { interval: 3600; running: toast.opened; onTriggered: toast.close() }
    }
}
