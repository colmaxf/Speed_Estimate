import QtQuick
import QtQuick.Layouts

// One violation entry. Role names come straight from AlertModel.
Rectangle {
    id: root

    required property string kind
    required property string plate
    required property int speed
    required property int limit
    required property string timeLabel
    required property string severity     // critical | high | warning

    readonly property color accent: severity === "critical" ? Theme.red400
                                  : severity === "high" ? Theme.orange400
                                  : severity === "warning" ? Theme.yellow400
                                  : Theme.slate300
    readonly property color tint: severity === "critical" ? Theme.alpha(Theme.red900, 0.2)
                                : severity === "high" ? Theme.alpha(Theme.orange900, 0.2)
                                : severity === "warning" ? Theme.alpha(Theme.yellow900, 0.2)
                                : Theme.slate800
    readonly property color edge: severity === "critical" ? Theme.alpha(Theme.red500, 0.5)
                                : severity === "high" ? Theme.alpha(Theme.orange500, 0.5)
                                : severity === "warning" ? Theme.alpha(Theme.yellow500, 0.5)
                                : Theme.slate700

    signal clicked()

    implicitHeight: body.implicitHeight + 24
    radius: 8
    color: hover.hovered ? Theme.alpha(Theme.slate800, 0.8) : tint
    border.width: 1
    border.color: edge

    Behavior on color { ColorAnimation { duration: 150 } }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.clicked() }

    RowLayout {
        id: body
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
        spacing: 12

        AppIcon {
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: 4
            name: "alert-triangle"
            size: 18
            tint: root.accent
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: root.kind
                    color: Theme.slate200
                    font.pixelSize: 14
                    font.bold: true
                }
                Item { Layout.fillWidth: true }
                Row {
                    spacing: 4
                    opacity: 0.7
                    AppIcon { anchors.verticalCenter: parent.verticalCenter; name: "clock"; size: 10; tint: root.accent }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: root.timeLabel
                        color: root.accent
                        font.pixelSize: 12
                    }
                }
            }

            Row {
                id: chips
                Layout.fillWidth: true
                spacing: 8
                readonly property real chipW: (width - spacing) / 2

                Rectangle {
                    width: chips.chipW
                    height: plateRow.implicitHeight + 8
                    radius: 4
                    color: Theme.alpha(Theme.black, 0.3)
                    Row {
                        id: plateRow
                        anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                        spacing: 4
                        AppIcon { anchors.verticalCenter: parent.verticalCenter; name: "car"; size: 12; tint: root.accent; opacity: 0.7 }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.plate
                            color: root.accent
                            font.family: Theme.mono
                            font.pixelSize: 12
                        }
                    }
                }

                Rectangle {
                    visible: root.speed > 0
                    width: chips.chipW
                    height: plateRow.implicitHeight + 8
                    radius: 4
                    color: Theme.alpha(Theme.black, 0.3)
                    Text {
                        anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                        text: root.speed + " / " + root.limit + " km/h"
                        color: Theme.red400
                        font.family: Theme.mono
                        font.pixelSize: 12
                        font.bold: true
                    }
                }
            }

            // snapshot placeholder
            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 4
                Layout.preferredHeight: 48
                radius: 4
                color: Theme.slate900
                border.width: 1
                border.color: Theme.alpha(Theme.slate700, 0.5)

                Rectangle {
                    anchors { fill: parent; margins: 1 }
                    radius: 3
                    color: Theme.alpha(Theme.slate800, 0.5)
                    AppIcon {
                        anchors.centerIn: parent
                        name: "camera"; size: 14; tint: Theme.alpha(Theme.slate500, 1); opacity: 0.5
                    }
                }
                Rectangle {
                    anchors { top: parent.top; bottom: parent.bottom; right: parent.right; margins: 1 }
                    width: (parent.width - 2) / 3
                    radius: 3
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: Theme.alpha(Theme.red500, 0) }
                        GradientStop { position: 1.0; color: Theme.alpha(Theme.red500, 0.2) }
                    }
                }
            }
        }
    }
}
