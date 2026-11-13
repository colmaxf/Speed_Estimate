"""List models exposed to QML: tracked vehicles on the feed and violation alerts."""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    Qt,
    Signal,
)

WARN_SPEED = 75   # km/h -> yellow bounding box
ALERT_SPEED = 85  # km/h -> red bounding box + speeding alert

_PLATE_PREFIXES = ("30A", "51F", "29C", "51G", "29D", "15C", "43B", "92A")


# --------------------------------------------------------------------------- #
# Vehicles
# --------------------------------------------------------------------------- #
@dataclass
class Vehicle:
    vid: str
    x: float          # left edge, % of frame width
    y: float          # top edge, % of frame height
    w: float          # width, % of frame width
    h: float          # height, % of frame height
    speed: float      # km/h
    plate: str
    alert_active: bool = False
    last_alert_at: float = float("-inf")

    @property
    def level(self) -> int:
        """0 = normal, 1 = near limit, 2 = violation."""
        if self.speed > ALERT_SPEED:
            return 2
        if self.speed > WARN_SPEED:
            return 1
        return 0


# Same four mock vehicles as the original React demo.
_INITIAL = (
    (20, 60, 15, 25, 65, "30A-xxx"),
    (55, 40, 12, 20, 58, "51G-xxx"),
    (35, 75, 18, 30, 92, "29D-xxx"),
    (70, 30, 10, 18, 60, "15C-xxx"),
)


class VehicleModel(QAbstractListModel):
    PosX = Qt.ItemDataRole.UserRole + 1
    PosY = PosX + 1
    BoxW = PosX + 2
    BoxH = PosX + 3
    Speed = PosX + 4
    Plate = PosX + 5
    Level = PosX + 6

    countChanged = Signal()

    def __init__(self, rng: random.Random, parent=None):
        super().__init__(parent)
        self._rng = rng
        self._items: list[Vehicle] = []
        self._next_id = 1
        for x, y, w, h, speed, plate in _INITIAL:
            v = Vehicle(self._new_id(), x, y, w, h, speed, plate)
            v.alert_active = v.level == 2  # already speeding at start-up: no duplicate alert
            self._items.append(v)
        self.rowsInserted.connect(lambda *_: self.countChanged.emit())
        self.rowsRemoved.connect(lambda *_: self.countChanged.emit())

    # -- QAbstractListModel ------------------------------------------------- #
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        v = self._items[index.row()]
        if role == self.PosX:
            return v.x
        if role == self.PosY:
            return v.y
        if role == self.BoxW:
            return v.w
        if role == self.BoxH:
            return v.h
        if role == self.Speed:
            return round(v.speed)
        if role == self.Plate:
            return v.plate
        if role == self.Level:
            return v.level
        return None

    def roleNames(self):
        return {
            self.PosX: b"posX",
            self.PosY: b"posY",
            self.BoxW: b"boxW",
            self.BoxH: b"boxH",
            self.Speed: b"speed",
            self.Plate: b"plate",
            self.Level: b"level",
        }

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    # -- simulation --------------------------------------------------------- #
    def advance(self) -> list[Vehicle]:
        """Move every vehicle one step. Returns vehicles that just crossed into violation."""
        rng = self._rng
        newly_speeding: list[Vehicle] = []
        i = 0
        while i < len(self._items):
            v = self._items[i]
            v.y += v.speed / 100
            if v.y > 100:
                # Left the frame: a new vehicle enters at the top (replaces the row so the
                # delegate is recreated and does not animate back across the whole frame).
                self._respawn(i)
                i += 1
                continue
            v.x = min(max(v.x + (rng.random() - 0.5) * 0.5, 2.0), 98.0 - v.w)
            v.speed = min(max(v.speed + (rng.random() - 0.5) * 5, 40.0), 120.0)
            speeding = v.level == 2
            if speeding and not v.alert_active:
                newly_speeding.append(v)
            v.alert_active = speeding
            i += 1
        if self._items:
            self.dataChanged.emit(self.index(0), self.index(len(self._items) - 1))
        return newly_speeding

    def _new_id(self) -> str:
        vid = f"v{self._next_id}"
        self._next_id += 1
        return vid

    def _respawn(self, row: int) -> None:
        rng = self._rng
        self.beginRemoveRows(QModelIndex(), row, row)
        self._items.pop(row)
        self.endRemoveRows()

        w = rng.uniform(10, 18)
        vehicle = Vehicle(
            vid=self._new_id(),
            x=rng.uniform(8, 90 - w),
            y=0.0,
            w=w,
            h=w * 1.67,
            speed=rng.uniform(50, 90),
            plate=f"{rng.choice(_PLATE_PREFIXES)}-xxx",
        )
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.insert(row, vehicle)
        self.endInsertRows()


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
@dataclass
class Alert:
    aid: int
    kind: str
    plate: str
    severity: str          # critical | high | warning
    created: datetime
    speed: int = 0
    limit: int = 0


def relative_time(created: datetime, now: datetime | None = None) -> str:
    seconds = max(0, int(((now or datetime.now()) - created).total_seconds()))
    if seconds < 10:
        return "Just now"
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    return f"{seconds // 3600}h ago"


class AlertModel(QAbstractListModel):
    Kind = Qt.ItemDataRole.UserRole + 1
    Plate = Kind + 1
    Speed = Kind + 2
    Limit = Kind + 3
    TimeLabel = Kind + 4
    Severity = Kind + 5

    MAX_ITEMS = 50
    countChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[Alert] = []
        self._next_id = 1
        self.rowsInserted.connect(lambda *_: self.countChanged.emit())
        self.rowsRemoved.connect(lambda *_: self.countChanged.emit())

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        a = self._items[index.row()]
        if role == self.Kind:
            return a.kind
        if role == self.Plate:
            return a.plate
        if role == self.Speed:
            return a.speed
        if role == self.Limit:
            return a.limit
        if role == self.TimeLabel:
            return relative_time(a.created)
        if role == self.Severity:
            return a.severity
        return None

    def roleNames(self):
        return {
            self.Kind: b"kind",
            self.Plate: b"plate",
            self.Speed: b"speed",
            self.Limit: b"limit",
            self.TimeLabel: b"timeLabel",
            self.Severity: b"severity",
        }

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._items)

    # -- mutation ----------------------------------------------------------- #
    def push(self, kind: str, plate: str, severity: str, created: datetime,
             speed: int = 0, limit: int = 0) -> None:
        """Insert a new alert at the top of the list (newest first)."""
        alert = Alert(self._next_id, kind, plate, severity, created, speed, limit)
        self._next_id += 1
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._items.insert(0, alert)
        self.endInsertRows()
        if len(self._items) > self.MAX_ITEMS:
            last = len(self._items) - 1
            self.beginRemoveRows(QModelIndex(), last, last)
            self._items.pop()
            self.endRemoveRows()

    def refresh_times(self) -> None:
        """Re-evaluate the "2m ago" labels."""
        if self._items:
            self.dataChanged.emit(
                self.index(0), self.index(len(self._items) - 1), [self.TimeLabel]
            )
