import QtQuick

// One tracked vehicle: coloured box, corner reticles and speed tag.
// Geometry comes from the model in % of the video frame (the parent Item).
Item {
    id: root

    required property real posX
    required property real posY
    required property real boxW
    required property real boxH
    required property int speed
    required property int level      // 0 ok, 1 near limit, 2 violation
    required property string plate

    readonly property color accent: level === 2 ? Theme.red500
                                  : level === 1 ? Theme.yellow400
                                  : Theme.green400

    // Animated copies of the model values (CSS: transition all 0.5s ease-in-out).
    // Animating copies keeps the box glued to the frame while the window is resized.
    property real animX: posX
    property real animY: posY
    property real animW: boxW
    property real animH: boxH

    component Glide: NumberAnimation {
        duration: 500
        easing.type: Easing.BezierSpline
        easing.bezierCurve: [0.42, 0, 0.58, 1, 1, 1]
    }
    Behavior on animX { Glide {} }
    Behavior on animY { Glide {} }
    Behavior on animW { Glide {} }
    Behavior on animH { Glide {} }

    x: parent.width * animX / 100
    y: parent.height * animY / 100
    width: parent.width * animW / 100
    height: parent.height * animH / 100

    opacity: 0
    Component.onCompleted: opacity = 1
    Behavior on opacity { NumberAnimation { duration: 400 } }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        radius: 4
        border.width: 2
        border.color: root.accent
        Behavior on border.color { ColorAnimation { duration: 200 } }
    }

    // Target reticle: four L-shaped corners just inside the border.
    Repeater {
        model: 4
        delegate: Item {
            id: corner
            required property int index
            readonly property bool atRight: index % 2 === 1
            readonly property bool atBottom: index > 1

            x: atRight ? root.width - 2 - 8 : 2
            y: atBottom ? root.height - 2 - 8 : 2
            width: 8
            height: 8

            Rectangle {      // horizontal arm
                y: corner.atBottom ? 6 : 0
                width: 8
                height: 2
                color: root.accent
            }
            Rectangle {      // vertical arm
                x: corner.atRight ? 6 : 0
                width: 2
                height: 8
                color: root.accent
            }
        }
    }

    // Speed tag above the box
    Rectangle {
        id: tag
        readonly property bool hot: root.level === 2
        property real pulse: 1

        width: tagText.implicitWidth + 16
        height: 20
        x: (root.width - width) / 2
        y: -24
        radius: 4
        opacity: hot ? pulse : 1
        color: hot ? Theme.red600
             : root.speed > 80 ? Theme.yellow500
             : Theme.alpha(Theme.black, 0.7)

        Text {
            id: tagText
            anchors.centerIn: parent
            text: root.speed + " km/h"
            color: Theme.white
            font.pixelSize: 12
            font.bold: true
        }

        SequentialAnimation on pulse {
            running: tag.hot
            loops: Animation.Infinite
            NumberAnimation { to: 0.5; duration: 1000; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0; duration: 1000; easing.type: Easing.InOutSine }
        }
    }
}
