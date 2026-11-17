import QtQuick
import QtQuick.Layouts

// KPI tile: label + icon, big value with unit, one-line footer.
Rectangle {
    id: root

    property string title
    property string icon
    property color iconColor: Theme.blue400
    property string value: "0"
    property string unit
    property string footer
    property string footerIcon
    property color footerColor: Theme.slate400

    implicitHeight: content.implicitHeight + 32
    radius: Theme.radiusCard
    color: Theme.slate800
    border.width: 1
    border.color: Theme.slate700

    ColumnLayout {
        id: content
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 16 }
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: root.title
                color: Theme.slate400
                font.pixelSize: 14
                font.weight: Font.Medium
            }
            Item { Layout.fillWidth: true }
            AppIcon { name: root.icon; size: 16; tint: root.iconColor }
        }

        RowLayout {
            Layout.topMargin: 8
            spacing: 4
            Text {
                Layout.alignment: Qt.AlignBaseline
                text: root.value
                color: Theme.white
                font.pixelSize: 30
                font.bold: true
                font.letterSpacing: -0.3
            }
            Text {
                Layout.alignment: Qt.AlignBaseline
                text: root.unit
                color: Theme.slate500
                font.pixelSize: 14
            }
        }

        RowLayout {
            Layout.topMargin: 8
            spacing: 4
            AppIcon {
                visible: root.footerIcon !== ""
                name: root.footerIcon
                size: 12
                tint: root.footerColor
            }
            Text {
                text: root.footer
                color: root.footerColor
                font.pixelSize: 12
            }
        }
    }
}
