import QtQuick
import QtQuick.Controls.Basic

// Dark-themed ComboBox (the little "Last 20 Mins" select).
ComboBox {
    id: control

    implicitWidth: 128
    implicitHeight: 28
    font.pixelSize: 12

    background: Rectangle {
        radius: 4
        color: Theme.slate900
        border.width: 1
        border.color: control.visualFocus || control.popup.visible ? Theme.blue500 : Theme.slate700
    }

    contentItem: Text {
        leftPadding: 8
        rightPadding: 24
        text: control.displayText
        font: control.font
        color: Theme.slate300
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: AppIcon {
        x: control.width - width - 6
        y: (control.height - height) / 2
        name: "chevron-down"
        size: 12
        tint: Theme.slate400
    }

    delegate: ItemDelegate {
        id: item
        required property var modelData
        required property int index

        width: control.width - 4
        height: 28
        highlighted: control.highlightedIndex === index

        contentItem: Text {
            leftPadding: 4
            text: item.modelData
            font: control.font
            color: Theme.slate300
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 3
            color: item.highlighted ? Theme.slate700 : "transparent"
        }
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 2
        implicitHeight: contentItem.implicitHeight + 4

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
        }
        background: Rectangle {
            radius: 4
            color: Theme.slate900
            border.width: 1
            border.color: Theme.slate700
        }
    }
}
