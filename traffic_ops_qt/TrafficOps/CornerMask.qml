import QtQuick
import QtQuick.Shapes

// Rounds the corners of whatever is underneath by painting the four "outside corner"
// pieces in the surrounding background colour. Works on every Qt Quick backend
// (no ShaderEffect / MultiEffect needed) as long as the panel sits on a flat background.
Item {
    id: root

    property real radius: Theme.radiusCard
    property color maskColor: Theme.bg

    anchors.fill: parent

    component Piece: Shape {
        id: piece
        required property int corner          // 0 TL, 1 TR, 2 BL, 3 BR
        readonly property real r: root.radius

        width: r
        height: r
        x: corner % 2 === 1 ? root.width - r : 0
        y: corner >= 2 ? root.height - r : 0

        ShapePath {
            fillColor: root.maskColor
            strokeColor: "transparent"
            strokeWidth: 0
            PathSvg {
                path: {
                    var r = piece.r
                    switch (piece.corner) {
                    case 0: return "M 0 0 L " + r + " 0 A " + r + " " + r + " 0 0 0 0 " + r + " Z"
                    case 1: return "M " + r + " 0 L " + r + " " + r + " A " + r + " " + r + " 0 0 0 0 0 Z"
                    case 2: return "M 0 " + r + " L 0 0 A " + r + " " + r + " 0 0 0 " + r + " " + r + " Z"
                    default: return "M " + r + " " + r + " L 0 " + r + " A " + r + " " + r + " 0 0 0 " + r + " 0 Z"
                    }
                }
            }
        }
    }

    Piece { corner: 0 }
    Piece { corner: 1 }
    Piece { corner: 2 }
    Piece { corner: 3 }
}
