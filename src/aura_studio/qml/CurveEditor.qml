import QtQuick

// Fan curve, temperature → speed. Click adds a point, dragging moves it, right click removes it.
Item {
    id: root
    property var points: []        // [[°C, %], …] sorted by temperature
    property var temp: null        // current (smoothed) temperature, null when unknown
    property real level: 0         // speed the fan is at right now, in %
    signal edited(var points)

    implicitHeight: 230
    property var work: null        // the points while one is being dragged
    property int grab: -1
    readonly property var shown: work || points
    readonly property real px: 42
    readonly property real py: 16
    readonly property real pw: width - px - 16
    readonly property real ph: height - py - 28

    function xOf(t) { return px + (t - 20) / 80 * pw }
    function yOf(p) { return py + (1 - p / 100) * ph }
    function tOf(x) { return Math.round(Math.max(20, Math.min(100, 20 + (x - px) / pw * 80))) }
    function pOf(y) { return Math.round(Math.max(0, Math.min(100, (1 - (y - py) / ph) * 100))) }

    onPointsChanged: canvas.requestPaint()
    onTempChanged: canvas.requestPaint()
    onLevelChanged: canvas.requestPaint()
    onWorkChanged: canvas.requestPaint()
    onWidthChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.font = "10px sans-serif"
            ctx.lineWidth = 1
            ctx.strokeStyle = Theme.strokeSoft
            ctx.fillStyle = Theme.textFaint
            for (var p = 0; p <= 100; p += 25) {
                ctx.beginPath(); ctx.moveTo(root.px, root.yOf(p)); ctx.lineTo(root.px + root.pw, root.yOf(p)); ctx.stroke()
                ctx.textAlign = "right"; ctx.fillText(p + " %", root.px - 7, root.yOf(p) + 3)
            }
            for (var t = 20; t <= 100; t += 20) {
                ctx.beginPath(); ctx.moveTo(root.xOf(t), root.py); ctx.lineTo(root.xOf(t), root.py + root.ph); ctx.stroke()
                ctx.textAlign = "center"; ctx.fillText(t + " °C", root.xOf(t), root.height - 9)
            }
            var pts = root.shown
            if (pts.length === 0) return
            ctx.beginPath()
            ctx.moveTo(root.xOf(20), root.yOf(pts[0][1]))
            for (var i = 0; i < pts.length; i++) ctx.lineTo(root.xOf(pts[i][0]), root.yOf(pts[i][1]))
            ctx.lineTo(root.xOf(100), root.yOf(pts[pts.length - 1][1]))
            ctx.strokeStyle = Theme.accent; ctx.lineWidth = 2; ctx.stroke()
            ctx.lineTo(root.xOf(100), root.yOf(0)); ctx.lineTo(root.xOf(20), root.yOf(0)); ctx.closePath()
            ctx.fillStyle = Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.12); ctx.fill()
            if (root.temp !== null && root.temp !== undefined) {
                var x = root.xOf(Math.max(20, Math.min(100, root.temp)))
                ctx.setLineDash([3, 4]); ctx.lineWidth = 1; ctx.strokeStyle = Theme.textDim
                ctx.beginPath(); ctx.moveTo(x, root.py); ctx.lineTo(x, root.py + root.ph); ctx.stroke()
                ctx.setLineDash([])
                ctx.beginPath(); ctx.arc(x, root.yOf(root.level), 4, 0, Math.PI * 2)
                ctx.fillStyle = Theme.textDim; ctx.fill()
            }
            for (i = 0; i < pts.length; i++) {
                ctx.beginPath(); ctx.arc(root.xOf(pts[i][0]), root.yOf(pts[i][1]), i === root.grab ? 8 : 6, 0, Math.PI * 2)
                ctx.fillStyle = "#ffffff"; ctx.fill()
                ctx.lineWidth = 2; ctx.strokeStyle = Theme.accent; ctx.stroke()
            }
            var hot = root.grab >= 0 ? root.grab : area.hover
            if (hot >= 0 && hot < pts.length) {
                var label = pts[hot][0] + " °C  ·  " + pts[hot][1] + " %"
                var lx = Math.min(root.width - 80, Math.max(root.px, root.xOf(pts[hot][0]) - 40))
                var ly = root.yOf(pts[hot][1]) - 14
                if (ly < root.py + 8) ly = root.yOf(pts[hot][1]) + 24
                ctx.fillStyle = Theme.text; ctx.textAlign = "center"; ctx.font = "bold 11px sans-serif"
                ctx.fillText(label, lx + 40, ly)
            }
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true
        preventStealing: true
        property int hover: -1
        cursorShape: hover >= 0 || root.grab >= 0 ? Qt.SizeAllCursor : Qt.CrossCursor
        function near(mx, my) {
            for (var i = 0; i < root.shown.length; i++) {
                var dx = root.xOf(root.shown[i][0]) - mx, dy = root.yOf(root.shown[i][1]) - my
                if (dx * dx + dy * dy <= 144) return i
            }
            return -1
        }
        onPressed: mouse => {
            var i = near(mouse.x, mouse.y)
            var copy = root.points.map(p => p.slice())
            if (mouse.button === Qt.RightButton) {
                if (i >= 0 && copy.length > 1) { copy.splice(i, 1); Sfx.play("tap"); root.edited(copy) }
                return
            }
            if (i < 0) {
                var t = root.tOf(mouse.x)
                if (copy.length >= 16 || copy.some(p => p[0] === t)) return
                var added = [t, root.pOf(mouse.y)]
                copy.push(added)
                copy.sort((a, b) => a[0] - b[0])
                i = copy.indexOf(added)
            }
            root.grab = i
            root.work = copy
        }
        onPositionChanged: mouse => {
            if (root.grab < 0) { hover = near(mouse.x, mouse.y); canvas.requestPaint(); return }
            var copy = root.work.map(p => p.slice())
            var lo = root.grab > 0 ? copy[root.grab - 1][0] + 1 : 20
            var hi = root.grab < copy.length - 1 ? copy[root.grab + 1][0] - 1 : 100
            copy[root.grab] = [Math.max(lo, Math.min(hi, root.tOf(mouse.x))), root.pOf(mouse.y)]
            root.work = copy
        }
        onReleased: {
            if (root.grab >= 0) { Sfx.play("tap"); root.edited(root.work) }
            root.grab = -1
            root.work = null
        }
        onExited: { hover = -1; canvas.requestPaint() }
    }
}
