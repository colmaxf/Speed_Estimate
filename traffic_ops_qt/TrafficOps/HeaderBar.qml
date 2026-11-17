import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes

// 56px top bar: logo, site name, live clock, alert bell, operator avatar.
Rectangle {
    id: root

    required property var backend

    signal bellClicked()

    implicitHeight: 56
    color: Theme.alpha(Theme.slate800, 0.5)

    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: 1
        color: Theme.slate800
    }

    RowLayout {
        anchors { fill: parent; leftMargin: 24; rightMargin: 24 }
        spacing: 24

        // ---- logo + title ---------------------------------------------- //
        RowLayout {
            spacing: 12

            Item {
                implicitWidth: 32
                implicitHeight: 32
                Shape {
                    anchors.fill: parent
                    ShapePath {
                        strokeColor: "transparent"
                        strokeWidth: 0
                        fillGradient: LinearGradient {
                            x1: 0; y1: 0; x2: 32; y2: 32
                            GradientStop { position: 0.0; color: Theme.blue500 }
                            GradientStop { position: 1.0; color: Theme.indigo600 }
                        }
                        PathSvg {
                            path: "M 8 0 H 24 A 8 8 0 0 1 32 8 V 24 A 8 8 0 0 1 24 32 H 8 A 8 8 0 0 1 0 24 V 8 A 8 8 0 0 1 8 0 Z"
                        }
                    }
                }
                AppIcon { anchors.centerIn: parent; name: "activity"; size: 20; tint: Theme.white }
            }

            Row {
                Text {
                    text: "Nexus"
                    color: Theme.white
                    font.pixelSize: 18
                    font.bold: true
                    font.letterSpacing: 0.45
                }
                Text {
                    text: "TrafficOps"
                    color: Theme.blue400
                    font.pixelSize: 18
                    font.weight: Font.Light
                    font.letterSpacing: 0.45
                }
            }
        }

        Item { Layout.fillWidth: true }

        // ---- site name -------------------------------------------------- //
        Row {
            spacing: 8
            AppIcon { anchors.verticalCenter: parent.verticalCenter; name: "map-pin"; size: 14; tint: Theme.slate500 }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.backend.siteName
                color: Theme.slate400
                font.pixelSize: 14
            }
        }

        Rectangle { implicitWidth: 1; implicitHeight: 16; color: Theme.slate700 }

        // ---- clock ------------------------------------------------------ //
        Rectangle {
            implicitWidth: clockRow.implicitWidth + 24
            implicitHeight: clockRow.implicitHeight + 8
            radius: 6
            color: Theme.alpha(Theme.slate800, 0.8)
            border.width: 1
            border.color: Theme.slate700

            Row {
                id: clockRow
                anchors.centerIn: parent
                spacing: 8
                AppIcon { anchors.verticalCenter: parent.verticalCenter; name: "clock"; size: 14; tint: Theme.slate500 }
                Text {
                    id: clockText
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.slate300
                    font.family: Theme.mono
                    font.pixelSize: 14
                    text: Qt.formatTime(new Date(), "HH:mm:ss")
                }
            }
            Timer {
                interval: 1000
                running: true
                repeat: true
                onTriggered: clockText.text = Qt.formatTime(new Date(), "HH:mm:ss")
            }
        }

        // ---- bell with ping dot ---------------------------------------- //
        IconButton {
            icon: "alert-triangle"
            iconColor: Theme.slate400
            iconHoverColor: Theme.white
            onClicked: root.bellClicked()

            Item {
                visible: root.backend.alerts.count > 0
                x: parent.width - 4 - 8
                y: 4
                width: 8
                height: 8

                Rectangle {          // expanding ring (animate-ping)
                    id: ping
                    anchors.fill: parent
                    radius: 4
                    color: Theme.red500
                    transformOrigin: Item.Center
                    ParallelAnimation {
                        running: true
                        loops: Animation.Infinite
                        NumberAnimation { target: ping; property: "scale"; from: 1; to: 2; duration: 1000; easing.type: Easing.OutCubic }
                        NumberAnimation { target: ping; property: "opacity"; from: 0.75; to: 0; duration: 1000; easing.type: Easing.OutCubic }
                    }
                }
                Rectangle {
                    anchors.fill: parent
                    radius: 4
                    color: Theme.red500
                }
            }
        }

        // ---- operator avatar ------------------------------------------- //
        Rectangle {
            implicitWidth: 32
            implicitHeight: 32
            radius: 16
            color: Theme.slate700
            border.width: 1
            border.color: Theme.slate600
            Text {
                anchors.centerIn: parent
                text: "OP"
                color: Theme.slate300
                font.pixelSize: 12
                font.bold: true
            }
        }
    }
}
