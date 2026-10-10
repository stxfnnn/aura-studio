import QtQuick
import QtQuick.Shapes

// Line icons drawn on a 24 x 24 grid.
Item {
    id: root
    property string name: ""
    property color color: Theme.textDim
    property real size: 18
    property real weight: 1.7
    implicitWidth: size
    implicitHeight: size

    readonly property var paths: ({
        "keyboard": "M4 6h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z M6 10h.01 M10 10h.01 M14 10h.01 M18 10h.01 M7.5 14h9",
        "mouse": "M12 3a6 6 0 0 1 6 6v6a6 6 0 0 1-12 0V9a6 6 0 0 1 6-6z M12 7v3.5",
        "chip": "M7 7h10v10H7z M10 3v4 M14 3v4 M10 17v4 M14 17v4 M3 10h4 M3 14h4 M17 10h4 M17 14h4",
        "spark": "M12 3L14 10L21 12L14 14L12 21L10 14L3 12L10 10Z",
        "layers": "M12 3l9 5-9 5-9-5 9-5z M3 12.5l9 5 9-5 M3 17l9 5 9-5",
        "sliders": "M4 6h9 M17 6h3 M4 12h3 M11 12h9 M4 18h11 M19 18h1 M15 4v4 M9 10v4 M17 16v4",
        "refresh": "M20 11a8 8 0 0 0-14.9-3 M4 4v4h4 M4 13a8 8 0 0 0 14.9 3 M20 20v-4h-4",
        "check": "M5 12.5l4.5 4.5L19 7.5",
        "plus": "M12 5v14 M5 12h14",
        "close": "M6 6l12 12 M18 6L6 18",
        "trash": "M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13 M10 11v6 M14 11v6",
        "volume": "M4 10v4h3l5 4V6L7 10H4z M16 9a4 4 0 0 1 0 6 M18.5 6.5a8 8 0 0 1 0 11",
        "mute": "M4 10v4h3l5 4V6L7 10H4z M16 9.5l5 5 M21 9.5l-5 5",
        "link": "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
        "power": "M12 3v8 M6.3 7a8 8 0 1 0 11.4 0",
        "dice": "M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z M8.5 8.5h.01 M15.5 8.5h.01 M12 12h.01 M8.5 15.5h.01 M15.5 15.5h.01",
        "undo": "M4 9h10a5 5 0 0 1 0 10H9 M4 9l4-4 M4 9l4 4",
        "save": "M5 4h11l3 3v13H5z M8 4v5h7V4 M8 20v-6h8v6",
        "copy": "M9 9h11v11H9z M5 15H4V4h11v1",
        "brush": "M14 4l6 6-8 8H6v-6z M4 21h16",
        "eraser": "M8 19l-4-4L14 5l6 6-8 8H8z M9 10l6 6 M12 19h8",
        "sun": "M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8z M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.4 1.4 M17.6 17.6L19 19 M5 19l1.4-1.4 M17.6 6.4L19 5",
        "home": "M4 11l8-7 8 7 M6 9.5V20h12V9.5 M10 20v-6h4v6",
        "moon": "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
        "clock": "M12 4a8 8 0 1 0 0 16a8 8 0 1 0 0-16z M12 8v4.5l3 2",
        "zap": "M13 3L5 13.5h6L10 21l8-10.5h-6z",
        "up": "M6 14l6-6 6 6",
        "down": "M6 10l6 6 6-6",
        "record": "M12 7a5 5 0 1 0 0 10a5 5 0 1 0 0-10z",
        "play": "M8 5l11 7-11 7z",
        "display": "M3 6h18v11H3z M9 21h6 M12 17v4",
        "chevron": "M9 6l6 6-6 6",
        "arrow": "M5 12h14 M13 6l6 6-6 6"
    })

    Shape {
        width: 24; height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: root.color
            strokeWidth: root.weight * 24 / root.size
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: root.paths[root.name] || "" }
        }
    }
}
