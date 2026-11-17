import QtQuick

// Square icon button with hover state (the p-2 rounded-lg buttons of the React version).
Rectangle {
    id: root

    property string icon: ""
    property int iconSize: 18
    property color iconColor: Theme.slate300
    property color iconHoverColor: iconColor
    property color fill: "transparent"
    property color hoverFill: fill

    // Children declared inside an IconButton { } land here (used for the bell's ping dot).
    default property alias overlay: overlayLayer.data

    signal clicked()

    implicitWidth: iconSize + 16
    implicitHeight: iconSize + 16
    radius: 8
    color: mouse.containsMouse ? hoverFill : fill

    Behavior on color { ColorAnimation { duration: 150 } }

    AppIcon {
        anchors.centerIn: parent
        name: root.icon
        size: root.iconSize
        tint: mouse.containsMouse ? root.iconHoverColor : root.iconColor
    }

    Item {
        id: overlayLayer
        anchors.fill: parent
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
