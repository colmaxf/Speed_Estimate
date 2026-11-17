"""Backend exposed to QML as `TrafficBackend` (import TrafficOpsCore).

Connects the live YOLOv5 + DeepSORT + SpeedEstimator `TrafficWorker` to the
QML dashboard via `QVideoSink`, `VehicleModel`, `AlertModel`, and telemetry.
Falls back to mock simulation automatically if the video source is missing.
"""
from __future__ import annotations

import json
import random
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import (
    QCoreApplication,
    Property,
    QObject,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtMultimedia import QVideoFrame, QVideoSink
from PySide6.QtQml import QmlElement

from traffic_models import ALERT_SPEED, WARN_SPEED, AlertModel, VehicleModel
from worker import PROJECT_ROOT, PipelineConfig, TrafficWorker

QML_IMPORT_NAME = "TrafficOpsCore"
QML_IMPORT_MAJOR_VERSION = 1

SPEED_LIMIT = 60                      # km/h
ALERT_COOLDOWN_S = 20.0               # min. gap between two speeding alerts for the same track
TELEMETRY_WINDOWS = (("Last 20 Mins", 20), ("Last Hour", 60))

VEHICLE_TICK_MS = 1000
TELEMETRY_TICK_MS = 5000
ALERT_LABEL_TICK_MS = 15000

DEFAULT_VIDEO = "videos/real_1.mp4"
CONFIG_FILE = "speed_config.json"


@QmlElement
class TrafficBackend(QObject):
    telemetryChanged = Signal()
    statsChanged = Signal()
    feedStateChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rng = random.Random()
        self._video_sink: QVideoSink | None = None
        self._worker: TrafficWorker | None = None

        self._config_path = PROJECT_ROOT / CONFIG_FILE
        self._pipeline_cfg, self._speed_limit, self._warn_speed, self._alert_speed = (
            self._load_app_config()
        )
        source_path = Path(self._pipeline_cfg.source)
        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path
        is_stream = str(self._pipeline_cfg.source).isdigit() or str(
            self._pipeline_cfg.source
        ).startswith(("rtsp://", "http://", "https://"))
        self._has_video = is_stream or source_path.exists()
        self._simulation_mode = not self._has_video

        self._vehicles = VehicleModel(
            self._rng,
            self,
            seed_mock=self._simulation_mode,
            warn_speed=self._warn_speed,
            alert_speed=self._alert_speed,
        )
        self._alerts = AlertModel(self)
        self._window_index = 0
        self._telemetry: deque[dict] = deque(maxlen=TELEMETRY_WINDOWS[0][1])
        self._telemetry.extend(self._generate_history(TELEMETRY_WINDOWS[0][1]))
        self._seed_alerts()

        # Live runtime stats
        self._fps_text = "0.0" if self._has_video else "59.94"
        self._latency_text = "--" if self._has_video else "12ms"
        tracker_tag = (
            "FASTSORT" if self._pipeline_cfg.tracker_type == "fast_sort" else "DEEPSORT"
        )
        self._model_name = (
            f"{Path(self._pipeline_cfg.yolo_weights).stem.upper()} + {tracker_tag}"
            if self._has_video
            else "SIMULATED"
        )
        self._cam_name = (
            f"CAM-01 : {Path(self._pipeline_cfg.source).name}"
            if self._has_video
            else "CAM-04 : SIMULATED"
        )
        self._feed_status = "LOADING" if self._has_video else "SIMULATED"
        self._line1_ratio = self._pipeline_cfg.estimator.line1_y_ratio
        self._line2_ratio = self._pipeline_cfg.estimator.line2_y_ratio
        self._total_count = 0

        # Live telemetry aggregation buffers
        self._recent_speeds: deque[float] = deque(maxlen=300)
        self._alert_cooldowns: dict[str, float] = {}
        self._last_window_count = 0

        self._vehicle_timer = QTimer(self, interval=VEHICLE_TICK_MS)
        self._vehicle_timer.timeout.connect(self._tick_vehicles)
        self._telemetry_timer = QTimer(self, interval=TELEMETRY_TICK_MS)
        self._telemetry_timer.timeout.connect(self._tick_telemetry)
        self._label_timer = QTimer(self, interval=ALERT_LABEL_TICK_MS)
        self._label_timer.timeout.connect(self._alerts.refresh_times)

        self._telemetry_timer.start()
        self._label_timer.start()

        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stopFeed)

        if self._has_video:
            self.startFeed(self._pipeline_cfg.source)
        else:
            self._vehicle_timer.start()

    def _load_app_config(self) -> tuple[PipelineConfig, int, float, float]:
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                est_raw = raw.get("speed_estimation", raw)
                cfg = PipelineConfig.from_json(self._config_path)
                limit = int(est_raw.get("speed_limit_kmh", SPEED_LIMIT))
                warn = float(est_raw.get("warn_speed_kmh", WARN_SPEED))
                alert = float(est_raw.get("alert_speed_kmh", ALERT_SPEED))
                return cfg, limit, warn, alert
            except Exception as exc:
                print(f"[Config WARNING] Failed to load {self._config_path}: {exc}")
        return PipelineConfig(source=DEFAULT_VIDEO), SPEED_LIMIT, float(WARN_SPEED), float(ALERT_SPEED)

    # ------------------------------------------------------------------ #
    # Static & live info (shown in header / video overlay)
    # ------------------------------------------------------------------ #
    @Property(str, constant=True)
    def siteName(self) -> str:
        return "Sector 4 : Traffic Speed Monitor"

    @Property(str, notify=statsChanged)
    def camName(self) -> str:
        return self._cam_name

    @Property(str, notify=statsChanged)
    def modelName(self) -> str:
        return self._model_name

    @Property(str, notify=statsChanged)
    def fps(self) -> str:
        return self._fps_text

    @Property(str, notify=statsChanged)
    def latency(self) -> str:
        return self._latency_text

    @Property(int, notify=statsChanged)
    def speedLimit(self) -> int:
        return self._speed_limit

    @Property(int, constant=True)
    def volumeTrendPercent(self) -> int:
        return 12

    @Property(list, constant=True)
    def windowOptions(self) -> list:
        return [label for label, _ in TELEMETRY_WINDOWS]

    @Property(str, notify=feedStateChanged)
    def feedStatus(self) -> str:
        return self._feed_status

    @Property(bool, notify=feedStateChanged)
    def feedActive(self) -> bool:
        return self._feed_status == "LIVE"

    @Property(float, notify=feedStateChanged)
    def line1Ratio(self) -> float:
        return self._line1_ratio

    @Property(float, notify=feedStateChanged)
    def line2Ratio(self) -> float:
        return self._line2_ratio

    @Property(list, notify=feedStateChanged)
    def homographyPoints(self) -> list:
        pts = getattr(self._pipeline_cfg.estimator, "src_norm_points", ())
        return [{"x": float(p[0]), "y": float(p[1])} for p in pts]

    @Property(int, notify=statsChanged)
    def totalCount(self) -> int:
        return self._total_count

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
    # Video Sink & Worker Control
    # ------------------------------------------------------------------ #
    @Slot(QObject)
    def setVideoSink(self, sink: QObject | None) -> None:
        """Bind QML VideoOutput.videoSink so Python can push decoded frames."""
        self._video_sink = sink if isinstance(sink, QVideoSink) else None

    @Slot()
    def reloadConfig(self) -> None:
        """Reload speed_config.json and restart the live feed."""
        self._pipeline_cfg, self._speed_limit, self._warn_speed, self._alert_speed = (
            self._load_app_config()
        )
        self._vehicles.set_thresholds(self._warn_speed, self._alert_speed)
        self._line1_ratio = self._pipeline_cfg.estimator.line1_y_ratio
        self._line2_ratio = self._pipeline_cfg.estimator.line2_y_ratio
        self.feedStateChanged.emit()
        self.statsChanged.emit()
        self.startFeed(self._pipeline_cfg.source)

    @Slot()
    @Slot(str)
    def startFeed(self, source: str = DEFAULT_VIDEO) -> None:
        self.stopFeed()
        self._simulation_mode = False
        self._vehicle_timer.stop()
        self._vehicles.clear()
        self._recent_speeds.clear()
        self._alert_cooldowns.clear()
        self._last_window_count = 0

        self._pipeline_cfg, self._speed_limit, self._warn_speed, self._alert_speed = (
            self._load_app_config()
        )
        self._vehicles.set_thresholds(self._warn_speed, self._alert_speed)
        cfg = self._pipeline_cfg
        if source:
            cfg.source = source
        self._line1_ratio = cfg.estimator.line1_y_ratio
        self._line2_ratio = cfg.estimator.line2_y_ratio
        self._cam_name = f"CAM-01 : {Path(cfg.source).name}"
        tracker_tag = "FASTSORT" if cfg.tracker_type == "fast_sort" else "DEEPSORT"
        self._model_name = f"{Path(cfg.yolo_weights).stem.upper()} + {tracker_tag}"
        self.feedStateChanged.emit()
        self.statsChanged.emit()

        worker = TrafficWorker(cfg, parent=self)
        worker.frameProcessed.connect(self._on_frame_processed)
        worker.statusChanged.connect(self._on_worker_status)
        worker.errorOccurred.connect(self._on_worker_error)
        self._worker = worker
        worker.start()

    @Slot()
    def stopFeed(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            if not self._worker.wait(10000):
                self._worker.terminate()
                self._worker.wait(1000)
            self._worker.deleteLater()
            self._worker = None

    def _on_worker_status(self, status: str) -> None:
        self._feed_status = status
        self.feedStateChanged.emit()

    def _on_worker_error(self, message: str) -> None:
        print(f"[TrafficWorker ERROR] {message}")
        # Fall back cleanly to simulation if inference fails
        self._simulation_mode = True
        self._feed_status = "SIMULATED"
        self._model_name = "SIMULATED (FALLBACK)"
        self._vehicle_timer.start()
        self.feedStateChanged.emit()
        self.statsChanged.emit()

    @Slot(object, object)
    def _on_frame_processed(self, vframe: QVideoFrame, payload: dict) -> None:
        if self._video_sink is not None:
            self._video_sink.setVideoFrame(vframe)

        tracked = payload["vehicles"]
        newly_speeding = self._vehicles.sync_tracks(tracked, alert_speed=self._alert_speed)

        for t in tracked:
            if t.speed_kmh > 1.0:
                self._recent_speeds.append(t.speed_kmh)

        now_mono = time.monotonic()
        for vehicle in newly_speeding:
            last_t = self._alert_cooldowns.get(vehicle.vid, float("-inf"))
            if now_mono - last_t < ALERT_COOLDOWN_S:
                continue
            self._alert_cooldowns[vehicle.vid] = now_mono
            self._alerts.push(
                kind="Speeding",
                plate=vehicle.plate,
                severity="critical",
                created=datetime.now(),
                speed=round(vehicle.speed),
                limit=self._speed_limit,
            )

        self._fps_text = f"{payload['fps']:.1f}"
        self._latency_text = f"{payload['latency_ms']:.0f}ms"
        self._total_count = int(payload["total_count"])
        if (
            abs(self._line1_ratio - payload["line1_y_ratio"]) > 1e-4
            or abs(self._line2_ratio - payload["line2_y_ratio"]) > 1e-4
        ):
            self._line1_ratio = float(payload["line1_y_ratio"])
            self._line2_ratio = float(payload["line2_y_ratio"])
            self.feedStateChanged.emit()
        self.statsChanged.emit()

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
        if self._simulation_mode:
            self._telemetry.append(self._sample(datetime.now()))
        else:
            delta_count = max(0, self._total_count - self._last_window_count)
            self._last_window_count = self._total_count
            est_per_min = max(delta_count * int(60_000 / TELEMETRY_TICK_MS), self._vehicles.count * 4)
            avg_speed = (
                round(sum(self._recent_speeds) / len(self._recent_speeds))
                if self._recent_speeds
                else 0
            )
            self._telemetry.append(
                {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "volume": est_per_min,
                    "speed": avg_speed,
                }
            )
        self.telemetryChanged.emit()

    # ------------------------------------------------------------------ #
    # Mock Vehicles fallback (only active when no video / fallback mode)
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
        self._alerts.push("Stopped Vehicle", "29C-555.22", "high", now - timedelta(minutes=15))
        self._alerts.push("Lane Departure", "51F-678.90", "warning", now - timedelta(minutes=2))
        self._alerts.push("Speeding", "30A-123.45", "critical", now, speed=95, limit=SPEED_LIMIT)
