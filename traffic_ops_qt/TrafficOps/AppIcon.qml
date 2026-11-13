import QtQuick

// Lucide icon rendered by the Python IconProvider (see icon_provider.py).
Image {
    id: root

    property string name: ""
    property color tint: Theme.white
    property int size: 16

    function hex(c) {
        function h(v) {
            var s = Math.round(v * 255).toString(16)
            return s.length < 2 ? "0" + s : s
        }
        return h(c.r) + h(c.g) + h(c.b)
    }

    width: size
    height: size
    sourceSize: Qt.size(Math.ceil(size * Screen.devicePixelRatio),
                        Math.ceil(size * Screen.devicePixelRatio))
    source: name === "" ? "" : "image://icons/" + name + "/" + hex(tint)
    fillMode: Image.PreserveAspectFit
    smooth: true
}
