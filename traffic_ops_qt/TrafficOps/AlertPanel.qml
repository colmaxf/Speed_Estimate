import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// "Live Violations" card: header + scrollable, newest-first list of AlertCard.
Rectangle {
    id: root

    required property var backend

    signal viewAllClicked()

    radius: Theme.radiusCard
    color: Theme.slate800
    border.width: 1
    border.color: Theme.slate700

    ColumnLayout {
        anchors { fill: parent; margins: 16 }
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            AppIcon { name: "alert-triangle"; size: 16; tint: Theme.red400 }
            Text {
                text: "Live Violations"
                color: Theme.slate200
                font.pixelSize: 16
                font.weight: Font.DemiBold
            }
            Item { Layout.fillWidth: true }

            Item {
                implicitWidth: viewAllRow.implicitWidth
                implicitHeight: viewAllRow.implicitHeight
                Row {
                    id: viewAllRow
                    spacing: 4
                    AppIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        name: "list"; size: 12
                        tint: viewAllMouse.containsMouse ? Theme.blue300 : Theme.blue400
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "View All"
                        font.pixelSize: 12
                        color: viewAllMouse.containsMouse ? Theme.blue300 : Theme.blue400
                    }
                }
                MouseArea {
                    id: viewAllMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.viewAllClicked()
                }
            }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 12
            model: root.backend.alerts
            boundsBehavior: Flickable.StopAtBounds

            delegate: AlertCard {
                width: ListView.view.width - 8      // pr-2 gutter for the scrollbar
            }

            footer: Item {
                width: ListView.view.width - 8
                height: 44
                Text {
                    anchors.centerIn: parent
                    text: "End of recent alerts"
                    color: Theme.slate500
                    font.pixelSize: 12
                }
            }

            add: Transition {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 250 }
            }
            displaced: Transition {
                NumberAnimation { property: "y"; duration: 250; easing.type: Easing.OutCubic }
            }

            ScrollBar.vertical: ScrollBar {
                id: bar
                policy: ScrollBar.AsNeeded
                implicitWidth: 6
                contentItem: Rectangle {
                    implicitWidth: 6
                    radius: 3
                    color: bar.pressed ? Theme.slate500 : Theme.slate600
                    opacity: bar.active ? 1 : 0.6
                }
                background: Item {}
            }
        }
    }
}
