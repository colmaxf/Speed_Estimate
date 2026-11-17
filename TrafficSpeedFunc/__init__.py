"""Core vehicle detection, tracking, and speed estimation package."""

from .fast_tracker import FastSortTracker
from .pipeline import FrameResult, PipelineConfig, TrafficPipeline
from .speed_estimator import (
    SpeedEstimator,
    SpeedEstimatorConfig,
    TrackedVehicle,
    compute_distance_px,
    compute_speed_kmh,
    convert_pixel_to_meter,
)

__all__ = [
    "FastSortTracker",
    "FrameResult",
    "PipelineConfig",
    "SpeedEstimator",
    "SpeedEstimatorConfig",
    "TrackedVehicle",
    "TrafficPipeline",
    "compute_distance_px",
    "compute_speed_kmh",
    "convert_pixel_to_meter",
]
