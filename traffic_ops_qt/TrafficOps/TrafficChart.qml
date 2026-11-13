import QtQuick

// Dual-axis line chart (volume on the left axis, speed on the right) drawn with Canvas.
// Replaces recharts: monotone curves, dashed horizontal grid, hover cursor + tooltip.
Item {
    id: root

    property var points: []                      // [{time, volume, speed}, ...]
    property color volumeColor: Theme.blue500
    property color speedColor: Theme.teal500
    property int hoverIndex: -1

    readonly property real padL: 34
    readonly property real padR: 34
    readonly property real padT: 8
    readonly property real padB: 24
    readonly property int intervals: 4
    readonly property real plotW: Math.max(1, width - padL - padR)
    readonly property real plotH: Math.max(1, height - padT - padB)
    readonly property real stepX: points.length > 1 ? plotW / (points.length - 1) : 0

    onPointsChanged: canvas.requestPaint()
    onHoverIndexChanged: canvas.requestPaint()

    // ---- helpers -------------------------------------------------------- //
    function niceMax(value, n) {
        if (value <= 0)
            return n
        var raw = value / n
        var pow = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10))
        var f = raw / pow
        var steps = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
        var step = 10
        for (var i = 0; i < steps.length; i++) {
            if (steps[i] >= f - 1e-9) { step = steps[i]; break }
        }
        return step * pow * n
    }

    // Fritsch-Carlson tangents -> monotone cubic (same look as recharts type="monotone")
    function tangents(xs, ys) {
        var n = xs.length, d = [], m = [], i
        for (i = 0; i < n - 1; i++)
            d.push((ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]))
        m.push(d[0])
        for (i = 1; i < n - 1; i++)
            m.push(d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2)
        m.push(d[n - 2])
        for (i = 0; i < n - 1; i++) {
            if (d[i] === 0) { m[i] = 0; m[i + 1] = 0; continue }
            var a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b
            if (s > 9) {
                var t = 3 / Math.sqrt(s)
                m[i] = t * a * d[i]
                m[i + 1] = t * b * d[i]
            }
        }
        return m
    }

    function strokeSeries(ctx, xs, ys, color) {
        var m = tangents(xs, ys)
        ctx.strokeStyle = String(color)
        ctx.lineWidth = 2
        ctx.lineJoin = "round"
        ctx.beginPath()
        ctx.moveTo(xs[0], ys[0])
        for (var i = 0; i < xs.length - 1; i++) {
            var dx = (xs[i + 1] - xs[i]) / 3
            ctx.bezierCurveTo(xs[i] + dx, ys[i] + m[i] * dx,
                              xs[i + 1] - dx, ys[i + 1] - m[i + 1] * dx,
                              xs[i + 1], ys[i + 1])
        }
        ctx.stroke()
    }

    function paintChart(cv) {
        var ctx = cv.getContext("2d")
        var W = cv.width, H = cv.height
        ctx.clearRect(0, 0, W, H)

        var pts = root.points
        var n = pts ? pts.length : 0
        if (n < 2)
            return

        var maxV = 0, maxS = 0, i
        for (i = 0; i < n; i++) {
            maxV = Math.max(maxV, pts[i].volume)
            maxS = Math.max(maxS, pts[i].speed)
        }
        var topV = niceMax(maxV, intervals)
        var topS = niceMax(maxS, intervals)

        var xs = [], yV = [], yS = []
        for (i = 0; i < n; i++) {
            xs.push(padL + i * stepX)
            yV.push(padT + plotH * (1 - pts[i].volume / topV))
            yS.push(padT + plotH * (1 - pts[i].speed / topS))
        }

        // dashed horizontal grid + both y axes
        ctx.font = "10px sans-serif"
        ctx.textBaseline = "middle"
        ctx.strokeStyle = String(Theme.slate700)
        ctx.lineWidth = 1
        for (i = 0; i <= intervals; i++) {
            var gy = Math.round(padT + plotH * (1 - i / intervals)) + 0.5
            for (var gx = padL; gx < padL + plotW; gx += 6) {
                ctx.beginPath()
                ctx.moveTo(gx, gy)
                ctx.lineTo(Math.min(gx + 3, padL + plotW), gy)
                ctx.stroke()
            }
            ctx.fillStyle = String(Theme.slate500)
            ctx.textAlign = "right"
            ctx.fillText(String(Math.round(topV * i / intervals)), padL - 6, gy)
            ctx.textAlign = "left"
            ctx.fillText(String(Math.round(topS * i / intervals)), padL + plotW + 6, gy)
        }

        // x axis labels (skip some so they never overlap)
        var skip = Math.max(1, Math.ceil(44 / Math.max(stepX, 1)))
        ctx.textAlign = "center"
        ctx.textBaseline = "top"
        ctx.fillStyle = String(Theme.slate500)
        for (i = 0; i < n; i += skip)
            ctx.fillText(pts[i].time, xs[i], padT + plotH + 8)

        // hover cursor
        var hi = root.hoverIndex
        if (hi >= 0 && hi < n) {
            ctx.strokeStyle = String(Theme.slate500)
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(xs[hi] + 0.5, padT)
            ctx.lineTo(xs[hi] + 0.5, padT + plotH)
            ctx.stroke()
        }

        strokeSeries(ctx, xs, yV, root.volumeColor)
        strokeSeries(ctx, xs, yS, root.speedColor)

        if (hi >= 0 && hi < n) {
            var dots = [[yV[hi], root.volumeColor], [yS[hi], root.speedColor]]
            for (i = 0; i < dots.length; i++) {
                ctx.beginPath()
                ctx.arc(xs[hi], dots[i][0], 4, 0, 2 * Math.PI)
                ctx.fillStyle = String(dots[i][1])
                ctx.fill()
                ctx.strokeStyle = "#ffffff"
                ctx.lineWidth = 2
                ctx.stroke()
            }
        }
    }

    // ---- drawing surface ------------------------------------------------- //
    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: root.paintChart(canvas)
    }

    // ---- hover handling + tooltip ---------------------------------------- //
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        onPositionChanged: (mouse) => {
            if (root.points.length < 2 || root.stepX <= 0)
                return
            var idx = Math.round((mouse.x - root.padL) / root.stepX)
            root.hoverIndex = Math.max(0, Math.min(root.points.length - 1, idx))
        }
        onExited: root.hoverIndex = -1
    }

    Rectangle {
        id: tip
        readonly property bool active: root.hoverIndex >= 0 && root.hoverIndex < root.points.length
        readonly property var p: active ? root.points[root.hoverIndex] : null
        readonly property real px: root.padL + root.hoverIndex * root.stepX

        visible: active
        width: tipColumn.implicitWidth + 24
        height: tipColumn.implicitHeight + 20
        x: px + 14 + width > root.width ? px - 14 - width : px + 14
        y: root.padT + 8
        radius: 4
        color: Theme.slate800
        border.width: 1
        border.color: Theme.slate700

        Column {
            id: tipColumn
            anchors.centerIn: parent
            spacing: 4
            Text { text: tip.p ? tip.p.time : ""; color: Theme.slate400; font.pixelSize: 12 }
            Text { text: "Volume (veh/m) : " + (tip.p ? tip.p.volume : ""); color: Theme.slate200; font.pixelSize: 12 }
            Text { text: "Speed (km/h) : " + (tip.p ? tip.p.speed : ""); color: Theme.slate200; font.pixelSize: 12 }
        }
    }
}
