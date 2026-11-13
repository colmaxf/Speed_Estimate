"""Backend exposed to QML as `TrafficBackend` (import TrafficOpsCore).

Python owns the data and the simulation; QML only renders. To go from the mock to real data,
replace `_tick_vehicles` / `_tick_telemetry` with your detector / sensor feed and keep the
same properties and models.
"""
from __future__ import annotations

import random
import time
from collections import deque
from datetime import datetime, timedelta

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtQml import QmlElement

from models import AlertModel, VehicleModel

QML_IMPORT_NAME = "TrafficOpsCore"
QML_IMPORT_MAJOR_VERSION = 1

SPEED_LIMIT = 60                      # km/h
ALERT_COOLDOWN_S = 20.0               # min. gap between two speeding alerts for the same vehicle
TELEMETRY_WINDOWS = (("Last 20 Mins", 20), ("Last Hour", 60))

VEHICLE_TICK_MS = 1000
TELEMETRY_TICK_MS = 5000
ALERT_LABEL_TICK_MS = 15000


@QmlElement
class TrafficBackend(QObject):
    telemetryChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rng = random.Random()
        self._vehicles = VehicleModel(self._rng, self)
        self._alerts = AlertModel(self)
        self._window_index = 0
        self._telemetry: deque[dict] = deque(maxlen=TELEMETRY_WINDOWS[0][1])
        self._telemetry.extend(self._generate_history(TELEMETRY_WINDOWS[0][1]))
        self._seed_alerts()

        self._vehicle_timer = QTimer(self, interval=VEHICLE_TICK_MS)
        self._vehicle_timer.timeout.connect(self._tick_vehicles)
        self._telemetry_timer = QTimer(self, interval=TELEMETRY_TICK_MS)
        self._telemetry_timer.timeout.connect(self._tick_telemetry)
        self._label_timer = QTimer(self, interval=ALERT_LABEL_TICK_MS)
        self._label_timer.timeout.connect(self._alerts.refresh_times)
        for timer in (self._vehicle_timer, self._telemetry_timer, self._label_timer):
            timer.start()

    # ------------------------------------------------------------------ #
    # Static info (shown in header / video overlay)
    # ------------------------------------------------------------------ #
    @Property(str, constant=True)
    def siteName(self) -> str:
        return "Sector 4 : Gwangju Ring Road"

    @Property(str, constant=True)
    def camName(self) -> str:
        return "CAM-04 : HWY-NORTH"

    @Property(str, constant=True)
    def modelName(self) -> str:
        return "YOLOv8-NANO"

    @Property(str, constant=True)
    def fps(self) -> str:
        return "59.94"

    @Property(str, constant=True)
    def latency(self) -> str:
        return "12ms"

    @Property(int, constant=True)
    def speedLimit(self) -> int:
        return SPEED_LIMIT

    @Property(int, constant=True)
    def volumeTrendPercent(self) -> int:
        return 12

    @Property(list, constant=True)
    def windowOptions(self) -> list:
        return [label for label, _ in TELEMETRY_WINDOWS]

    # ------------------------------------------------------------------ #
    # Models
    # ------------------------------------------------------------------ #
    @Property(QObject, constant=True)
    def vehicles(self) -> QObject:
        return self._vehicles

    @Property(QObject, constant=True)
    def alerts(self) -> QObject:
        return self._alerts

    # ------------------------------------------------------------------ #
    # Telemetry
    # ------------------------------------------------------------------ #
    @Property(list, notify=telemetryChanged)
    def telemetry(self) -> list:
        return list(self._telemetry)

    @Property(int, notify=telemetryChanged)
    def latestVolume(self) -> int:
        return self._telemetry[-1]["volume"] if self._telemetry else 0

    @Property(int, notify=telemetryChanged)
    def latestSpeed(self) -> int:
        return self._telemetry[-1]["speed"] if self._telemetry else 0

    @Slot(int)
    def setWindow(self, index: int) -> None:
        """Switch the chart between "Last 20 Mins" and "Last Hour"."""
        if not 0 <= index < len(TELEMETRY_WINDOWS) or index == self._window_index:
            return
        self._window_index = index
        count = TELEMETRY_WINDOWS[index][1]
        self._telemetry = deque(self._generate_history(count), maxlen=count)
        self.telemetryChanged.emit()

    def _generate_history(self, count: int) -> list[dict]:
        start = datetime.now() - timedelta(minutes=count)
        return [self._sample(start + timedelta(minutes=i)) for i in range(count)]

    def _sample(self, when: datetime) -> dict:
        return {
            "time": when.strftime("%H:%M"),
            "volume": self._rng.randint(40, 120),
            "speed": self._rng.randint(45, 85),
        }

    def _tick_telemetry(self) -> None:
        self._telemetry.append(self._sample(datetime.now()))  # deque drops the oldest point
        self.telemetryChanged.emit()

    # ------------------------------------------------------------------ #
    # Vehicles and alerts
    # ------------------------------------------------------------------ #
    def _tick_vehicles(self) -> None:
        now = time.monotonic()
        for vehicle in self._vehicles.advance():
            if now - vehicle.last_alert_at < ALERT_COOLDOWN_S:
                continue
            vehicle.last_alert_at = now
            prefix = vehicle.plate.split("-")[0]
            self._alerts.push(
                kind="Speeding",
                plate=f"{prefix}-{self._rng.randint(100, 999)}.{self._rng.randint(10, 99)}",
                severity="critical",
                created=datetime.now(),
                speed=round(vehicle.speed),
                limit=SPEED_LIMIT,
            )

    def _seed_alerts(self) -> None:
        now = datetime.now()
        # pushed oldest-first because push() inserts at the top
        self._alerts.push("Stopped Vehicle", "29C-555.22", "high", now - timedelta(minutes=15))
        self._alerts.push("Lane Departure", "51F-678.90", "warning", now - timedelta(minutes=2))
        self._alerts.push("Speeding", "30A-123.45", "critical", now, speed=95, limit=SPEED_LIMIT)
