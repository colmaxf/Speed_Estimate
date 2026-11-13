"""NexusTrafficOps - PySide6 + QML traffic management dashboard."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

import backend  # noqa: F401  (importing registers TrafficBackend with QML)
from icon_provider import IconProvider

# Trỏ trực tiếp vào thư mục chứa main.py (nơi chứa main.qml và folder TrafficOps)
BASE_DIR = Path(__file__).resolve().parent
os.environ["QML_IMPORT_PATH"] = str(BASE_DIR)


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("NexusTrafficOps")
    app.setOrganizationName("Colmaxf")

    engine = QQmlApplicationEngine()
    icons = IconProvider()
    engine.addImageProvider("icons", icons)

    # Thêm thư mục gốc vào Import Path để nhận diện folder TrafficOps
    engine.addImportPath(str(BASE_DIR))
    engine.load(QUrl.fromLocalFile(str(BASE_DIR / "main.qml")))

    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
