"""Vehicle speed estimation using 4-point Homography road calibration."""
from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np

DEFAULT_SRC_NORM_POINTS: Tuple[Tuple[float, float], ...] = (
    (0.344, 0.530),  # P1: Top-left dash L1 row 2
    (0.605, 0.528),  # P2: Top-right dash L3 row 2
    (0.696, 0.963),  # P3: Bottom-right dash L3 row 1
    (0.223, 0.963),  # P4: Bottom-left dash L1 row 1
)

DEFAULT_DST_METER_POINTS: Tuple[Tuple[float, float], ...] = (
    (0.0, 0.0),
    (7.0, 0.0),
    (7.0, 10.0),
    (0.0, 10.0),
)


def compute_distance_px(
    point_start_px: Tuple[float, float],
    point_end_px: Tuple[float, float],
) -> float:
    """1. Compute Euclidean pixel displacement between start and end points."""
    return float(
        math.hypot(point_end_px[0] - point_start_px[0], point_end_px[1] - point_start_px[1])
    )


def convert_pixel_to_meter(
    point_start_px: Tuple[float, float],
    point_end_px: Tuple[float, float],
    homography_matrix: Optional[np.ndarray] = None,
    calibration_scale_m_per_px: Optional[float] = None,
    min_displacement_px: float = 0.0,
) -> float:
    """2. Convert pixel displacement to real-world meters via Homography (or linear scale)."""
    dist_px = compute_distance_px(point_start_px, point_end_px)
    if dist_px < min_displacement_px or dist_px <= 0.0:
        return 0.0

    if homography_matrix is not None:
        pts_px = np.array([[point_start_px, point_end_px]], dtype=np.float32)
        pts_meter = cv2.perspectiveTransform(pts_px, homography_matrix)[0]
        dx_m = float(pts_meter[1][0] - pts_meter[0][0])
        dy_m = float(pts_meter[1][1] - pts_meter[0][1])
        return float(math.hypot(dx_m, dy_m))

    if calibration_scale_m_per_px is not None and calibration_scale_m_per_px > 0.0:
        return dist_px * calibration_scale_m_per_px

    return 0.0


def compute_speed_kmh(
    distance_m: float,
    time_start_s: float,
    time_end_s: float,
    min_dt_s: float = 0.15,
    max_speed_kmh: Optional[float] = None,
) -> Optional[float]:
    """3. Compute speed in km/h with strict time-delta and plausibility guards."""
    dt = time_end_s - time_start_s
    if dt <= 0.0 or dt < min_dt_s or distance_m <= 0.0:
        return None
    speed_kmh = (distance_m / dt) * 3.6
    if max_speed_kmh is not None and speed_kmh > max_speed_kmh:
        return None
    return float(speed_kmh)


@dataclass
class SpeedEstimatorConfig:
    """Configuration for Homography/ROI-based vehicle speed estimation."""

    calibration_mode: str = "homography"
    roi_top_ratio: float = 0.37
    roi_bottom_ratio: float = 0.96
    counting_line_y_ratio: float = 0.75
    sliding_window_frames: int = 15
    min_history_frames: int = 5
    min_displacement_px: float = 6.0
    min_time_delta_s: float = 0.15
    distance_meters: float = 10.0
    calibration_scale_m_per_px: Optional[float] = None
    speed_limit_kmh: float = 60.0
    smoothing_alpha: float = 0.35
    max_speed_kmh: float = 180.0
    stale_ttl_frames: int = 90
    src_norm_points: Tuple[Tuple[float, float], ...] = DEFAULT_SRC_NORM_POINTS
    dst_meter_points: Tuple[Tuple[float, float], ...] = DEFAULT_DST_METER_POINTS

    @property
    def line1_y_ratio(self) -> float:
        return self.roi_top_ratio

    @property
    def line2_y_ratio(self) -> float:
        return self.roi_bottom_ratio

    @classmethod
    def from_dict(cls, data: dict) -> "SpeedEstimatorConfig":
        """Build validated config from a JSON dictionary."""
        raw_top = data.get(
            "roi_top_ratio", data.get("line_start_y_ratio", data.get("line1_y_ratio", 0.37))
        )
        raw_bot = data.get(
            "roi_bottom_ratio", data.get("line_end_y_ratio", data.get("line2_y_ratio", 0.96))
        )
        roi_top = min(max(float(raw_top), 0.05), 0.90)
        roi_bot = min(max(float(raw_bot), 0.10), 0.99)
        if roi_top > roi_bot:
            roi_top, roi_bot = roi_bot, roi_top
        if abs(roi_bot - roi_top) < 0.05:
            roi_bot = min(0.99, roi_top + 0.05)

        raw_count = float(data.get("counting_line_y_ratio", 0.75))
        count_ratio = min(max(raw_count, roi_top), roi_bot)

        raw_scale = data.get("calibration_scale_m_per_px")
        scale = float(raw_scale) if raw_scale is not None and float(raw_scale) > 0.0 else None

        homog = data.get("homography", {})
        src_pts_raw = homog.get("src_norm_points", data.get("src_norm_points"))
        dst_pts_raw = homog.get("dst_meter_points", data.get("dst_meter_points"))

        src_pts = (
            tuple((float(p[0]), float(p[1])) for p in src_pts_raw)
            if src_pts_raw and len(src_pts_raw) == 4
            else DEFAULT_SRC_NORM_POINTS
        )
        dst_pts = (
            tuple((float(p[0]), float(p[1])) for p in dst_pts_raw)
            if dst_pts_raw and len(dst_pts_raw) == 4
            else DEFAULT_DST_METER_POINTS
        )

        return cls(
            calibration_mode=str(data.get("calibration_mode", "homography")),
            roi_top_ratio=roi_top,
            roi_bottom_ratio=roi_bot,
            counting_line_y_ratio=count_ratio,
            sliding_window_frames=max(5, int(data.get("sliding_window_frames", 15))),
            min_history_frames=max(2, int(data.get("min_history_frames", 5))),
            min_displacement_px=max(0.0, float(data.get("min_displacement_px", 6.0))),
            min_time_delta_s=max(0.03, float(data.get("min_time_delta_s", 0.15))),
            distance_meters=max(0.5, float(data.get("distance_meters", 10.0))),
            calibration_scale_m_per_px=scale,
            speed_limit_kmh=max(1.0, float(data.get("speed_limit_kmh", 60.0))),
            smoothing_alpha=min(max(float(data.get("smoothing_alpha", 0.35)), 0.01), 1.0),
            max_speed_kmh=max(20.0, float(data.get("max_speed_kmh", 180.0))),
            stale_ttl_frames=max(10, int(data.get("stale_ttl_frames", 90))),
            src_norm_points=src_pts,
            dst_meter_points=dst_pts,
        )

    @classmethod
    def from_lines_json(
        cls,
        json_path: str | Path,
        frame_height: int = 1080,
        distance_meters: float = 10.0,
    ) -> "SpeedEstimatorConfig":
        """Build config from legacy lines.json pixel coordinates."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        h = max(int(frame_height), 1)
        top = float(data.get("h_firstline", int(h * 0.37))) / h
        bot = float(data.get("h_secondline", int(h * 0.96))) / h
        if top > bot:
            top, bot = bot, top
        return cls(
            roi_top_ratio=min(max(top, 0.05), 0.90),
            roi_bottom_ratio=min(max(bot, 0.10), 0.99),
            distance_meters=distance_meters,
        )


@dataclass
class TrackedVehicle:
    """Per-frame vehicle state ready for UI or logging."""

    track_id: int
    class_id: int
    class_name: str
    bbox_xyxy: Tuple[int, int, int, int]
    x_pct: float
    y_pct: float
    w_pct: float
    h_pct: float
    speed_kmh: float
    speed_confirmed: bool


@dataclass
class _TrackState:
    history: Deque[Tuple[float, Tuple[float, float]]]
    last_seen_frame: int
    prev_y: float
    ema_speed_kmh: float = 0.0
    counted: bool = False


class SpeedEstimator:
    """Estimates vehicle speed via 4-point road Homography and ground contact points."""

    def __init__(self, config: Optional[SpeedEstimatorConfig] = None) -> None:
        self.cfg = config or SpeedEstimatorConfig()
        self._states: Dict[int, _TrackState] = {}
        self.total_count: int = 0
        self._cached_size: Optional[Tuple[int, int]] = None
        self._homography_matrix: Optional[np.ndarray] = None

    def reset(self) -> None:
        self._states.clear()
        self.total_count = 0

    @staticmethod
    def get_ground_contact_point(
        bbox: Tuple[float, float, float, float],
    ) -> Tuple[float, float]:
        """Return bottom-center (tire/bumper road contact point) instead of centerY."""
        x1, _, x2, y2 = bbox
        return ((x1 + x2) * 0.5, float(y2))

    def resolve_lines_px(self, frame_height: int) -> Tuple[float, float]:
        """Return (line_start_y, line_end_y) ROI bounds in pixels."""
        h = max(float(frame_height), 1.0)
        line_start_y = self.cfg.roi_top_ratio * h
        line_end_y = self.cfg.roi_bottom_ratio * h
        if line_start_y > line_end_y:
            line_start_y, line_end_y = line_end_y, line_start_y
        return float(line_start_y), float(line_end_y)

    def get_homography_matrix(self, frame_width: int, frame_height: int) -> Optional[np.ndarray]:
        """Compute (and cache) the 3x3 Homography matrix for the current frame size."""
        if self.cfg.calibration_mode != "homography":
            return None
        size = (int(frame_width), int(frame_height))
        if self._cached_size != size or self._homography_matrix is None:
            src_norm = np.array(self.cfg.src_norm_points, dtype=np.float32)
            dst_m = np.array(self.cfg.dst_meter_points, dtype=np.float32)
            scale = np.array([float(size[0]), float(size[1])], dtype=np.float32)
            self._homography_matrix = cv2.getPerspectiveTransform(src_norm * scale, dst_m)
            self._cached_size = size
        return self._homography_matrix

    def resolve_calibration_scale(self, line_start_y: float, line_end_y: float) -> float:
        """Fallback linear scale (m/px) when homography is disabled."""
        if (
            self.cfg.calibration_scale_m_per_px is not None
            and self.cfg.calibration_scale_m_per_px > 0.0
        ):
            return self.cfg.calibration_scale_m_per_px
        gate_span_px = max(abs(line_end_y - line_start_y), 1.0)
        return self.cfg.distance_meters / gate_span_px

    def is_inside_roi(self, point_px: Tuple[float, float], frame_height: int) -> bool:
        """Check y_min <= y <= y_max validity inside calibrated ROI."""
        _, y = point_px
        y_min, y_max = self.resolve_lines_px(frame_height)
        return y_min <= y <= y_max

    def update(
        self,
        tracks: List[Tuple[int, int, int, int, int, int]],
        frame_width: int,
        frame_height: int,
        frame_idx: int,
        timestamp_s: float,
        class_names: Dict[int, str] | List[str],
    ) -> List[TrackedVehicle]:
        """Update tracked vehicles and compute Homography-calibrated speeds."""
        w = max(float(frame_width), 1.0)
        h = max(float(frame_height), 1.0)
        line_start_y, line_end_y = self.resolve_lines_px(frame_height)
        counting_y = self.cfg.counting_line_y_ratio * h
        homography = self.get_homography_matrix(frame_width, frame_height)
        linear_scale = self.resolve_calibration_scale(line_start_y, line_end_y)

        results: List[TrackedVehicle] = []
        for x1, y1, x2, y2, track_id, class_id in tracks:
            ground_pt = self.get_ground_contact_point((x1, y1, x2, y2))
            _, curr_y = ground_pt
            cls_name = self._resolve_class_name(class_names, class_id)
            in_roi = self.is_inside_roi(ground_pt, frame_height)

            state = self._states.get(track_id)
            if state is None:
                state = _TrackState(
                    history=deque(maxlen=self.cfg.sliding_window_frames),
                    last_seen_frame=frame_idx,
                    prev_y=curr_y,
                )
                self._states[track_id] = state

            if not state.counted and (
                (state.prev_y < counting_y <= curr_y) or (state.prev_y > counting_y >= curr_y)
            ):
                state.counted = True
                self.total_count += 1

            state.prev_y = curr_y
            state.last_seen_frame = frame_idx

            speed_confirmed = False
            if in_roi:
                state.history.append((timestamp_s, ground_pt))
                if len(state.history) >= self.cfg.min_history_frames:
                    t_start, pt_start = state.history[0]
                    t_end, pt_end = state.history[-1]
                    dist_m = convert_pixel_to_meter(
                        pt_start,
                        pt_end,
                        homography_matrix=homography,
                        calibration_scale_m_per_px=linear_scale,
                        min_displacement_px=self.cfg.min_displacement_px,
                    )
                    raw_speed = compute_speed_kmh(
                        dist_m,
                        t_start,
                        t_end,
                        min_dt_s=self.cfg.min_time_delta_s,
                        max_speed_kmh=self.cfg.max_speed_kmh,
                    )
                    if raw_speed is not None:
                        speed_confirmed = True
                        if state.ema_speed_kmh <= 0.0:
                            state.ema_speed_kmh = raw_speed
                        else:
                            a = self.cfg.smoothing_alpha
                            state.ema_speed_kmh = a * raw_speed + (1.0 - a) * state.ema_speed_kmh

            results.append(
                TrackedVehicle(
                    track_id=int(track_id),
                    class_id=int(class_id),
                    class_name=cls_name,
                    bbox_xyxy=(int(x1), int(y1), int(x2), int(y2)),
                    x_pct=max(0.0, min(100.0, x1 / w * 100.0)),
                    y_pct=max(0.0, min(100.0, y1 / h * 100.0)),
                    w_pct=max(0.0, min(100.0, (x2 - x1) / w * 100.0)),
                    h_pct=max(0.0, min(100.0, (y2 - y1) / h * 100.0)),
                    speed_kmh=float(max(0.0, min(state.ema_speed_kmh, self.cfg.max_speed_kmh))),
                    speed_confirmed=speed_confirmed,
                )
            )

        self._evict_stale(frame_idx)
        return results

    def _evict_stale(self, current_frame: int) -> None:
        ttl = self.cfg.stale_ttl_frames
        stale_ids = [
            tid for tid, st in self._states.items() if current_frame - st.last_seen_frame > ttl
        ]
        for tid in stale_ids:
            del self._states[tid]

    @staticmethod
    def _resolve_class_name(class_names: Dict[int, str] | List[str], class_id: int) -> str:
        try:
            return str(class_names[int(class_id)])
        except (KeyError, IndexError, TypeError, ValueError):
            return f"cls_{class_id}"
