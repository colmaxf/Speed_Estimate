import QtQuick 2.12
import QtQuick.Controls 2.12
import TrafficOps
import TrafficOpsCore

ApplicationWindow {
    id: win

    width: 1440
    height: 860
    minimumWidth: 1100
    minimumHeight: 720
    visible: true
    title: "NexusTrafficOps"
    color: Theme.bg

    TrafficBackend { id: traffic }

    HeaderBar {
        id: header
        z: 1
        anchors { left: parent.left; right: parent.right; top: parent.top }
        backend: traffic
    }

    // 12-column grid with 24px gutters, like `grid-cols-12 gap-6 p-6` in the React layout:
    // video = 8 columns, right-hand column = 4 columns (telemetry 3/5, alerts 2/5 of the height).
    Item {
        id: content
        anchors {
            left: parent.left; right: parent.right
            top: header.bottom; bottom: parent.bottom
            margins: 24
        }

        readonly property real gap: 24
        readonly property real col: (width - 11 * gap) / 12
        readonly property real rightW: col * 4 + gap * 3
        readonly property real rightH: height - gap

        VideoPanel {
            id: video
            width: content.col * 8 + content.gap * 7
            height: content.height
            backend: traffic
        }

        TelemetryPanel {
            id: telemetry
            x: video.width + content.gap
            width: content.rightW
            height: content.rightH * 3 / 5
            backend: traffic
        }

        AlertPanel {
            x: telemetry.x
            y: telemetry.height + content.gap
            width: content.rightW
            height: content.rightH * 2 / 5
            backend: traffic
        }
    }
}
