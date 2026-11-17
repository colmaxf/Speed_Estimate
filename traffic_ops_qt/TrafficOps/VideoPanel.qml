import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import QtMultimedia

// Camera feed card: live AI VideoOutput (or simulated road), tracked vehicles, header overlay and OSD footer.
Item {
    id: root

    required property var backend

    signal settingsClicked()
    signal maximizeClicked()

    component StatCard: Rectangle {
        property string label
        property string value
        property color valueColor: Theme.white
        property int valueSize: 16

        implicitHeight: statColumn.implicitHeight + 16
        radius: 4
        color: Theme.alpha(Theme.black, 0.5)
        border.width: 1
        border.color: Theme.alpha(Theme.slate700, 0.5)

        Column {
            id: statColumn
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 8 }
            spacing: 4
            Text {
                text: label
                color: Theme.slate400
                font.pixelSize: 12
            }
            Text {
                width: parent.width
                text: value
                color: valueColor
                elide: Text.ElideRight
                font.family: Theme.mono
                font.bold: true
                font.pixelSize: valueSize
            }
        }
    }

    // ---- frame background ------------------------------------------------- //
    Rectangle {
        anchors.fill: parent
        color: Theme.slate900
    }

    // ---- simulated feed ---------------------------------------------------- //
    Item {
        id: feed
        anchors.fill: parent
        clip: true

        Rectangle {
            anchors.fill: parent
            color: Theme.slate800
        }

        // faux road: darker bottom half + converging lane lines
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: parent.height / 2
            gradient: Gradient {
                GradientStop { position: 0.0; color: Theme.alpha(Theme.slate700, 0) }
                GradientStop { position: 1.0; color: Theme.slate700 }
            }
        }

        Shape {
            anchors.fill: parent
            ShapePath {
                strokeColor: Theme.alpha(Theme.slate500, 0.3)
                strokeWidth: 4
                strokeStyle: ShapePath.DashLine
                dashPattern: [3, 3]
                fillColor: "transparent"
                startX: feed.width * 0.22
                startY: feed.height
                PathLine { x: feed.width * 0.46; y: feed.height * 0.5 }
            }
            ShapePath {
                strokeColor: Theme.alpha(Theme.slate500, 0.3)
                strokeWidth: 4
                strokeStyle: ShapePath.DashLine
                dashPattern: [3, 3]
                fillColor: "transparent"
                startX: feed.width * 0.78
                startY: feed.height
                PathLine { x: feed.width * 0.54; y: feed.height * 0.5 }
            }
        }

        Text {
            anchors.centerIn: parent
            visible: !root.backend.feedActive
            text: root.backend.feedStatus === "LOADING" ? "LOADING AI MODEL..." : "NO SIGNAL / SIMULATED FEED"
            color: Theme.alpha(Theme.slate500, 0.7)
            font.family: Theme.mono
            font.pixelSize: 20
        }

        // Live video stream pushed from Python QVideoSink
        VideoOutput {
            id: videoOut
            anchors.fill: parent
            fillMode: VideoOutput.PreserveAspectFit
            visible: root.backend.feedActive
            Component.onCompleted: root.backend.setVideoSink(videoOut.videoSink)
        }

        // tracked vehicles (Repeater delegates use `parent` = this Item for % geometry)
        Item {
            id: scene
            readonly property bool hasRect: root.backend.feedActive && videoOut.contentRect.width > 0
            x: hasRect ? videoOut.contentRect.x : 0
            y: hasRect ? videoOut.contentRect.y : 0
            width: hasRect ? videoOut.contentRect.width : parent.width
            height: hasRect ? videoOut.contentRect.height : parent.height

            // Virtual ROI bounds (top = 37%, bottom = 96%)
            Rectangle {
                visible: root.backend.feedActive
                x: 0
                y: parent.height * root.backend.line1Ratio
                width: parent.width
                height: 2
                color: Theme.alpha(Theme.yellow400, 0.55)
            }
            Rectangle {
                visible: root.backend.feedActive
                x: 0
                y: parent.height * root.backend.line2Ratio
                width: parent.width
                height: 2
                color: Theme.alpha(Theme.green400, 0.55)
            }

            // Calibrated 4-point Homography lane-marking trapezoid
            Shape {
                anchors.fill: parent
                visible: root.backend.feedActive && root.backend.homographyPoints.length === 4
                ShapePath {
                    readonly property var pts: root.backend.homographyPoints
                    strokeColor: Theme.alpha(Theme.blue400, 0.85)
                    strokeWidth: 2
                    strokeStyle: ShapePath.DashLine
                    dashPattern: [6, 4]
                    fillColor: Theme.alpha(Theme.blue500, 0.08)
                    startX: pts.length === 4 ? scene.width * pts[0].x : 0
                    startY: pts.length === 4 ? scene.height * pts[0].y : 0
                    PathLine {
                        x: pts.length === 4 ? scene.width * pts[1].x : 0
                        y: pts.length === 4 ? scene.height * pts[1].y : 0
                    }
                    PathLine {
                        x: pts.length === 4 ? scene.width * pts[2].x : 0
                        y: pts.length === 4 ? scene.height * pts[2].y : 0
                    }
                    PathLine {
                        x: pts.length === 4 ? scene.width * pts[3].x : 0
                        y: pts.length === 4 ? scene.height * pts[3].y : 0
                    }
                    PathLine {
                        x: pts.length === 4 ? scene.width * pts[0].x : 0
                        y: pts.length === 4 ? scene.height * pts[0].y : 0
                    }
                }
            }

            Repeater {
                model: root.backend.vehicles
                delegate: BoundingBox {}
            }
        }
    }

    // ---- header overlay ---------------------------------------------------- //
    Rectangle {
        id: topBar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: topRow.implicitHeight + 32
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.alpha(Theme.black, 0.8) }
            GradientStop { position: 1.0; color: Theme.alpha(Theme.black, 0) }
        }

        RowLayout {
            id: topRow
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 12

            // camera name chip
            Rectangle {
                implicitWidth: camRow.implicitWidth + 24
                implicitHeight: camRow.implicitHeight + 12
                radius: 8
                color: Theme.alpha(Theme.slate800, 0.8)
                border.width: 1
                border.color: Theme.slate600
                Row {
                    id: camRow
                    anchors.centerIn: parent
                    spacing: 8
                    AppIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: "video"; size: 16; tint: Theme.blue400
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.backend.camName
                        color: Theme.slate200
                        font.pixelSize: 14
                        font.weight: Font.Medium
                        font.letterSpacing: 0.35
                    }
                }
            }

            // REC chip
            Rectangle {
                implicitWidth: recRow.implicitWidth + 24
                implicitHeight: recRow.implicitHeight + 12
                radius: 8
                color: Theme.alpha(Theme.red900, 0.3)
                border.width: 1
                border.color: Theme.alpha(Theme.red500, 0.5)
                Row {
                    id: recRow
                    anchors.centerIn: parent
                    spacing: 8
                    Rectangle {
                        id: recDot
                        anchors.verticalCenter: parent.verticalCenter
                        width: 8; height: 8; radius: 4
                        color: Theme.red500
                        SequentialAnimation on opacity {
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.5; duration: 1000; easing.type: Easing.InOutSine }
                            NumberAnimation { to: 1.0; duration: 1000; easing.type: Easing.InOutSine }
                        }
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "REC"
                        color: Theme.red400
                        font.pixelSize: 12
                        font.bold: true
                        font.letterSpacing: 0.6
                    }
                }
            }

            Item { Layout.fillWidth: true }

            IconButton {
                icon: "settings"
                iconColor: Theme.slate300
                fill: Theme.alpha(Theme.slate800, 0.6)
                hoverFill: Theme.slate700
                onClicked: root.settingsClicked()
            }
            IconButton {
                icon: "maximize-2"
                iconColor: Theme.slate300
                fill: Theme.alpha(Theme.slate800, 0.6)
                hoverFill: Theme.slate700
                onClicked: root.maximizeClicked()
            }
        }
    }

    // ---- OSD footer -------------------------------------------------------- //
    Rectangle {
        id: bottomBar
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: osdRow.implicitHeight + 32
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.alpha(Theme.black, 0) }
            GradientStop { position: 1.0; color: Theme.alpha(Theme.black, 0.9) }
        }

        Row {
            id: osdRow
            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
            spacing: 16
            readonly property real cardW: (width - 3 * spacing) / 4

            StatCard { width: osdRow.cardW; label: "FPS"; value: root.backend.fps; valueColor: Theme.green400 }
            StatCard { width: osdRow.cardW; label: "LATENCY"; value: root.backend.latency; valueColor: Theme.blue400 }
            StatCard { width: osdRow.cardW; label: "MODEL"; value: root.backend.modelName; valueColor: Theme.purple400; valueSize: 12 }
            StatCard { width: osdRow.cardW; label: "ACTIVE TRACKS"; value: String(root.backend.vehicles.count) }
        }
    }

    // ---- rounded corners + border ----------------------------------------- //
    CornerMask { radius: Theme.radiusCard }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        radius: Theme.radiusCard
        border.width: 1
        border.color: Theme.slate700
    }
}
