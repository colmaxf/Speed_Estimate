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

    def __init__(
        self,
        rng: random.Random,
        parent=None,
        seed_mock: bool = True,
        warn_speed: float = WARN_SPEED,
        alert_speed: float = ALERT_SPEED,
    ):
        super().__init__(parent)
        self._rng = rng
        self._items: list[Vehicle] = []
        self._next_id = 1
        self._warn_speed = float(warn_speed)
        self._alert_speed = float(alert_speed)
        if seed_mock:
            for x, y, w, h, speed, plate in _INITIAL:
                v = Vehicle(self._new_id(), x, y, w, h, speed, plate)
                v.alert_active = v.speed > self._alert_speed
                self._items.append(v)
        self.rowsInserted.connect(lambda *_: self.countChanged.emit())
        self.rowsRemoved.connect(lambda *_: self.countChanged.emit())

    def set_thresholds(self, warn_speed: float, alert_speed: float) -> None:
        self._warn_speed = float(warn_speed)
        self._alert_speed = float(alert_speed)

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
            if v.speed > self._alert_speed:
                return 2
            if v.speed > self._warn_speed:
                return 1
            return 0
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

    def clear(self) -> None:
        """Remove all tracked vehicles from the model."""
        if not self._items:
            return
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def sync_tracks(
        self,
        tracked: list,
        alert_speed: float = ALERT_SPEED,
    ) -> list[Vehicle]:
        """Synchronize model rows with live tracker detections by `track_id`.

        Returns vehicles that just crossed `alert_speed` on this frame.
        """
        incoming_by_vid = {str(t.track_id): t for t in tracked}
        newly_speeding: list[Vehicle] = []

        # 1. Remove tracks no longer present
        idx = 0
        while idx < len(self._items):
            if self._items[idx].vid not in incoming_by_vid:
                self.beginRemoveRows(QModelIndex(), idx, idx)
                self._items.pop(idx)
                self.endRemoveRows()
            else:
                idx += 1

        # 2. Update existing tracks in-place
        existing_map = {v.vid: row for row, v in enumerate(self._items)}
        updated_rows: list[int] = []
        for vid, t in incoming_by_vid.items():
            row = existing_map.get(vid)
            label = f"#{t.track_id} {t.class_name.upper()}"
            if row is not None:
                v = self._items[row]
                v.x = t.x_pct
                v.y = t.y_pct
                v.w = t.w_pct
                v.h = t.h_pct
                v.speed = t.speed_kmh
                v.plate = label
                speeding = v.speed > alert_speed
                if speeding and not v.alert_active:
                    newly_speeding.append(v)
                v.alert_active = speeding
                updated_rows.append(row)

        if updated_rows:
            self.dataChanged.emit(
                self.index(min(updated_rows)),
                self.index(max(updated_rows)),
            )

        # 3. Insert newly appeared tracks
        to_insert = [t for vid, t in incoming_by_vid.items() if vid not in existing_map]
        if to_insert:
            start = len(self._items)
            end = start + len(to_insert) - 1
            self.beginInsertRows(QModelIndex(), start, end)
            for t in to_insert:
                speeding = t.speed_kmh > alert_speed
                v = Vehicle(
                    vid=str(t.track_id),
                    x=t.x_pct,
                    y=t.y_pct,
                    w=t.w_pct,
                    h=t.h_pct,
                    speed=t.speed_kmh,
                    plate=f"#{t.track_id} {t.class_name.upper()}",
                    alert_active=speeding,
                )
                self._items.append(v)
                if speeding:
                    newly_speeding.append(v)
            self.endInsertRows()

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
