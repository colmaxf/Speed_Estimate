import QtQuick
import QtQuick.Layouts

// Two KPI tiles on top, traffic-flow chart below.
Item {
    id: root

    required property var backend

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            KpiCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignTop
                title: "Vol / Minute"
                icon: "car"
                iconColor: Theme.blue400
                value: String(root.backend.latestVolume)
                unit: "veh"
                footerIcon: "activity"
                footer: "+" + root.backend.volumeTrendPercent + "% vs last hour"
                footerColor: Theme.green400
            }
            KpiCard {
                Layout.fillWidth: true
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignTop
                title: "Avg Speed"
                icon: "activity"
                iconColor: Theme.teal400
                value: String(root.backend.latestSpeed)
                unit: "km/h"
                footer: "Limit: " + root.backend.speedLimit + " km/h"
                footerColor: Theme.slate400
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 180
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
                    AppIcon { name: "activity"; size: 16; tint: Theme.blue400 }
                    Text {
                        text: "Traffic Flow Trend"
                        color: Theme.slate200
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                    }
                    Item { Layout.fillWidth: true }
                    DarkComboBox {
                        model: root.backend.windowOptions
                        onActivated: (index) => root.backend.setWindow(index)
                    }
                }

                TrafficChart {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    points: root.backend.telemetry
                }
            }
        }
    }
}
