pragma Singleton
import QtQuick

// Design tokens taken from the Tailwind classes used in the React dashboard.
QtObject {
    // slate ramp
    readonly property color slate50:  "#f8fafc"
    readonly property color slate100: "#f1f5f9"
    readonly property color slate200: "#e2e8f0"
    readonly property color slate300: "#cbd5e1"
    readonly property color slate400: "#94a3b8"
    readonly property color slate500: "#64748b"
    readonly property color slate600: "#475569"
    readonly property color slate700: "#334155"
    readonly property color slate800: "#1e293b"
    readonly property color slate900: "#0f172a"

    readonly property color blue300:   "#93c5fd"
    readonly property color blue400:   "#60a5fa"
    readonly property color blue500:   "#3b82f6"
    readonly property color indigo600: "#4f46e5"
    readonly property color teal400:   "#2dd4bf"
    readonly property color teal500:   "#14b8a6"
    readonly property color green400:  "#4ade80"
    readonly property color purple400: "#c084fc"
    readonly property color yellow400: "#facc15"
    readonly property color yellow500: "#eab308"
    readonly property color yellow900: "#713f12"
    readonly property color orange400: "#fb923c"
    readonly property color orange500: "#f97316"
    readonly property color orange900: "#7c2d12"
    readonly property color red400:    "#f87171"
    readonly property color red500:    "#ef4444"
    readonly property color red600:    "#dc2626"
    readonly property color red900:    "#7f1d1d"
    readonly property color black:     "#000000"
    readonly property color white:     "#ffffff"

    readonly property color bg: slate900
    readonly property int radiusCard: 12

    readonly property string mono: Qt.platform.os === "windows" ? "Consolas"
                                 : (Qt.platform.os === "osx" || Qt.platform.os === "macos") ? "Menlo"
                                 : "DejaVu Sans Mono"

    // Same colour with another alpha. Use instead of "transparent" in gradients:
    // a fully transparent *black* stop would darken the blend.
    function alpha(c, a) {
        return Qt.rgba(c.r, c.g, c.b, a)
    }
}
