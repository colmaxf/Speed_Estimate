"""Background QThread worker running YOLOv5 + DeepSORT + SpeedEstimator."""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import QSize, QThread, Signal
from PySide6.QtMultimedia import QVideoFrame, QVideoFrameFormat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from TrafficSpeedFunc import PipelineConfig, TrafficPipeline  # noqa: E402


def _bgr_to_video_frame(frame_bgr: np.ndarray) -> QVideoFrame:
    """Convert an OpenCV BGR ndarray directly into a Qt QVideoFrame (RGBA8888)."""
    h, w = frame_bgr.shape[:2]
    vframe = QVideoFrame(QVideoFrameFormat(QSize(w, h), QVideoFrameFormat.Format_RGBA8888))
    if vframe.map(QVideoFrame.WriteOnly):
        try:
            bpl = vframe.bytesPerLine(0)
            arr = np.frombuffer(vframe.bits(0), dtype=np.uint8).reshape(h, bpl // 4, 4)
            cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGBA, dst=arr[:, :w])
        finally:
            vframe.unmap()
    return vframe


class TrafficWorker(QThread):
    """Runs `TrafficPipeline` off the GUI thread and emits frames + detections."""

    frameProcessed = Signal(object, object)  # (QVideoFrame, dict payload)
    statusChanged = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, config: Optional[PipelineConfig] = None, parent=None) -> None:
        super().__init__(parent)
        self.config = config or PipelineConfig()
        self._stop_event = threading.Event()
        self.model_label: str = Path(self.config.yolo_weights).stem.upper()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        self._stop_event.clear()
        self.statusChanged.emit("LOADING")
        try:
            pipeline = TrafficPipeline(self.config)
            self.model_label = pipeline.model_label
            self.statusChanged.emit("LIVE")

            for res in pipeline.iter_frames(stop_event=self._stop_event):
                if self._stop_event.is_set():
                    break
                vframe = _bgr_to_video_frame(res.frame_bgr)
                payload = {
                    "fps": res.fps,
                    "latency_ms": res.latency_ms,
                    "vehicles": res.vehicles,
                    "total_count": res.total_count,
                    "line1_y_ratio": res.line1_y_ratio,
                    "line2_y_ratio": res.line2_y_ratio,
                    "model_label": self.model_label,
                }
                self.frameProcessed.emit(vframe, payload)
        except Exception as exc:
            self.errorOccurred.emit(str(exc))
            self.statusChanged.emit("ERROR")
            return

        self.statusChanged.emit("STOPPED")
