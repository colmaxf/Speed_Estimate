"""Refactored YOLOv5 + DeepSORT + SpeedEstimator inference pipeline."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generator, Optional, Tuple

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
YOLOV5_ROOT = PROJECT_ROOT / "yolov5"
REID_ROOT = PROJECT_ROOT / "deep_sort" / "deep" / "reid"


def _ensure_paths() -> None:
    # Avoid matplotlib auto-selecting QtAgg when PySide6 >= 6.4 is loaded.
    os.environ.setdefault("MPLBACKEND", "Agg")
    for p in (PROJECT_ROOT, YOLOV5_ROOT, REID_ROOT):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)


from .speed_estimator import SpeedEstimator, SpeedEstimatorConfig, TrackedVehicle  # noqa: E402


@dataclass
class PipelineConfig:
    """Runtime settings for YOLOv5 + DeepSORT speed estimation."""

    source: str = "videos/real_1.mp4"
    yolo_weights: str = "yolov5n.pt"
    tracker_type: str = "fast_sort"  # "fast_sort" (Kalman+IoU, ~30 FPS) or "deepsort" (OSNet ReID)
    filter_roi_before_track: bool = True
    reid_model: str = "deep_sort/deep/checkpoint/osnet_ibn_x1_0_MSMT17.pth"
    deepsort_config: str = "deep_sort/configs/deep_sort.yaml"
    imgsz: int = 640
    conf_thres: float = 0.35
    iou_thres: float = 0.50
    max_det: int = 100
    classes: Optional[Tuple[int, ...]] = (2, 3, 5, 7)  # car, motorcycle, bus, truck
    device: str = ""  # "" -> auto select GPU if available
    half: bool = True
    loop_video: bool = True
    realtime_pace: bool = True
    estimator: SpeedEstimatorConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.estimator is None:
            self.estimator = SpeedEstimatorConfig()

    @classmethod
    def from_json(cls, json_path: str | Path) -> "PipelineConfig":
        """Load pipeline and speed estimation settings from a JSON file."""
        p = Path(json_path)
        if not p.is_absolute() and not p.exists():
            p = PROJECT_ROOT / p
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)

        classes_raw = raw.get("classes", [2, 3, 5, 7])
        classes = tuple(int(c) for c in classes_raw) if classes_raw is not None else None
        est_data = raw.get("speed_estimation", raw)

        return cls(
            source=str(raw.get("source", "videos/real_1.mp4")),
            yolo_weights=str(raw.get("yolo_weights", "yolov5n.pt")),
            tracker_type=str(raw.get("tracker_type", "fast_sort")).lower(),
            filter_roi_before_track=bool(raw.get("filter_roi_before_track", True)),
            reid_model=str(
                raw.get("reid_model", "deep_sort/deep/checkpoint/osnet_ibn_x1_0_MSMT17.pth")
            ),
            deepsort_config=str(raw.get("deepsort_config", "deep_sort/configs/deep_sort.yaml")),
            imgsz=int(raw.get("imgsz", 640)),
            conf_thres=float(raw.get("conf_thres", 0.35)),
            iou_thres=float(raw.get("iou_thres", 0.50)),
            max_det=int(raw.get("max_det", 100)),
            classes=classes,
            device=str(raw.get("device", "")),
            half=bool(raw.get("half", True)),
            loop_video=bool(raw.get("loop_video", True)),
            realtime_pace=bool(raw.get("realtime_pace", True)),
            estimator=SpeedEstimatorConfig.from_dict(est_data),
        )


@dataclass
class FrameResult:
    """Output produced for each processed video frame."""

    frame_bgr: np.ndarray
    frame_idx: int
    timestamp_s: float
    fps: float
    latency_ms: float
    vehicles: list[TrackedVehicle]
    total_count: int
    line1_y_ratio: float
    line2_y_ratio: float


class TrafficPipeline:
    """Encapsulates model loading and frame-by-frame inference."""

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        _ensure_paths()
        import torch  # noqa: WPS433
        from deep_sort.deep_sort import DeepSort
        from deep_sort.utils.parser import get_config
        from yolov5.models.common import DetectMultiBackend
        from yolov5.utils.augmentations import letterbox
        from yolov5.utils.general import check_img_size, non_max_suppression, scale_coords, xyxy2xywh
        from yolov5.utils.torch_utils import select_device, time_sync

        self._torch = torch
        self._letterbox = letterbox
        self._nms = non_max_suppression
        self._scale_coords = scale_coords
        self._xyxy2xywh = xyxy2xywh
        self._time_sync = time_sync

        self.cfg = config or PipelineConfig()
        self.device = select_device(self.cfg.device)
        self.half = bool(self.cfg.half and self.device.type != "cpu")

        yolo_path = self._resolve_path(self.cfg.yolo_weights)
        reid_path = self._resolve_path(self.cfg.reid_model)
        ds_cfg_path = self._resolve_path(self.cfg.deepsort_config)

        # Load YOLOv5 detector
        self.model = DetectMultiBackend(
            str(yolo_path), device=self.device, dnn=False, fp16=self.half
        )
        self.stride = int(self.model.stride)
        self.pt = bool(self.model.pt)
        self.half = bool(getattr(self.model, "fp16", False))
        self.names = self.model.module.names if hasattr(self.model, "module") else self.model.names
        self.imgsz = check_img_size((self.cfg.imgsz, self.cfg.imgsz), s=self.stride)
        self.model.warmup(imgsz=(1, 3, *self.imgsz))

        # Load tracker ("fast_sort" skips OSNet CNN for ~30 FPS; "deepsort" uses OSNet ReID)
        ds_cfg = get_config()
        ds_cfg.merge_from_file(str(ds_cfg_path))
        if self.cfg.tracker_type == "fast_sort":
            from .fast_tracker import FastSortTracker

            self.tracker = FastSortTracker(
                max_iou_distance=ds_cfg.DEEPSORT.MAX_IOU_DISTANCE,
                max_age=ds_cfg.DEEPSORT.MAX_AGE,
                n_init=ds_cfg.DEEPSORT.N_INIT,
            )
        else:
            self.tracker = DeepSort(
                str(reid_path),
                self.device,
                max_dist=ds_cfg.DEEPSORT.MAX_DIST,
                max_iou_distance=ds_cfg.DEEPSORT.MAX_IOU_DISTANCE,
                max_age=ds_cfg.DEEPSORT.MAX_AGE,
                n_init=ds_cfg.DEEPSORT.N_INIT,
                nn_budget=ds_cfg.DEEPSORT.NN_BUDGET,
            )
        self.estimator = SpeedEstimator(self.cfg.estimator)

    @property
    def model_label(self) -> str:
        tracker_tag = "FASTSORT" if self.cfg.tracker_type == "fast_sort" else "DEEPSORT"
        return f"{Path(self.cfg.yolo_weights).stem.upper()} + {tracker_tag}"

    def iter_frames(
        self, stop_event: Optional[threading.Event] = None
    ) -> Generator[FrameResult, None, None]:
        """Yield `FrameResult` for each frame from `cfg.source` until stopped or EOF."""
        src = self._resolve_source(self.cfg.source)
        is_live = isinstance(src, int) or str(src).startswith(("rtsp://", "http://", "https://"))

        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {src}")

        src_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if src_fps <= 1.0 or src_fps > 120.0:
            src_fps = 30.0
        frame_interval_s = 1.0 / src_fps

        frame_idx = 0
        ema_fps = src_fps
        last_tick = time.perf_counter()

        try:
            with self._torch.no_grad():
                while stop_event is None or not stop_event.is_set():
                    loop_start = time.perf_counter()
                    ok, frame_bgr = cap.read()
                    if not ok:
                        if not is_live and self.cfg.loop_video:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            self.estimator.reset()
                            frame_idx = 0
                            continue
                        break

                    timestamp_s = time.monotonic() if is_live else (frame_idx / src_fps)
                    t_infer_start = self._time_sync()
                    vehicles = self._process_frame(frame_bgr, frame_idx, timestamp_s)
                    latency_ms = (self._time_sync() - t_infer_start) * 1000.0

                    if self.cfg.realtime_pace and not is_live:
                        elapsed = time.perf_counter() - loop_start
                        sleep_s = frame_interval_s - elapsed
                        if sleep_s > 0.001:
                            time.sleep(sleep_s)

                    now = time.perf_counter()
                    dt = max(now - last_tick, 1e-4)
                    last_tick = now
                    ema_fps = 0.15 * (1.0 / dt) + 0.85 * ema_fps

                    yield FrameResult(
                        frame_bgr=frame_bgr,
                        frame_idx=frame_idx,
                        timestamp_s=timestamp_s,
                        fps=ema_fps,
                        latency_ms=latency_ms,
                        vehicles=vehicles,
                        total_count=self.estimator.total_count,
                        line1_y_ratio=self.estimator.cfg.line1_y_ratio,
                        line2_y_ratio=self.estimator.cfg.line2_y_ratio,
                    )
                    frame_idx += 1
        finally:
            cap.release()

    def _process_frame(
        self, frame_bgr: np.ndarray, frame_idx: int, timestamp_s: float
    ) -> list[TrackedVehicle]:
        h, w = frame_bgr.shape[:2]

        img, _, _ = self._letterbox(frame_bgr, self.imgsz, stride=self.stride, auto=self.pt)
        img = img.transpose((2, 0, 1))[::-1]  # HWC BGR -> CHW RGB
        img = np.ascontiguousarray(img)

        tensor = self._torch.from_numpy(img).to(self.device)
        tensor = tensor.half() if self.half else tensor.float()
        tensor /= 255.0
        if tensor.ndim == 3:
            tensor = tensor[None]

        pred = self.model(tensor, augment=False, visualize=False)
        classes_arg = list(self.cfg.classes) if self.cfg.classes is not None else None
        det = self._nms(
            pred,
            self.cfg.conf_thres,
            self.cfg.iou_thres,
            classes=classes_arg,
            agnostic=False,
            max_det=self.cfg.max_det,
        )[0]

        tracks: list[tuple[int, int, int, int, int, int]] = []
        if det is not None and len(det):
            det[:, :4] = self._scale_coords(tensor.shape[2:], det[:, :4], frame_bgr.shape).round()
            if self.cfg.filter_roi_before_track:
                # Keep detections whose bottom edge is near/inside the ROI to avoid
                # running tracker/ReID on tiny horizon vehicles outside the measurement zone.
                min_y2 = max(0.0, (self.estimator.cfg.roi_top_ratio - 0.05) * h)
                det = det[det[:, 3] >= min_y2]

        if det is not None and len(det):
            xywhs = self._xyxy2xywh(det[:, 0:4]).cpu()
            confs = det[:, 4].cpu()
            clss = det[:, 5].cpu()
            outputs = self.tracker.update(xywhs, confs, clss, frame_bgr)
            if len(outputs) > 0:
                for out in outputs:
                    x1, y1, x2, y2, tid, cid = (
                        int(out[0]),
                        int(out[1]),
                        int(out[2]),
                        int(out[3]),
                        int(out[4]),
                        int(out[5]),
                    )
                    tracks.append((x1, y1, x2, y2, tid, cid))
        else:
            self.tracker.increment_ages()

        return self.estimator.update(
            tracks=tracks,
            frame_width=w,
            frame_height=h,
            frame_idx=frame_idx,
            timestamp_s=timestamp_s,
            class_names=self.names,
        )

    @staticmethod
    def _resolve_path(path_str: str) -> Path:
        p = Path(path_str)
        if p.is_absolute() or p.exists():
            return p
        return PROJECT_ROOT / p

    @classmethod
    def _resolve_source(cls, source: str) -> str | int:
        if source.isdigit():
            return int(source)
        if source.startswith(("rtsp://", "http://", "https://")):
            return source
        return str(cls._resolve_path(source))


def run_cli_preview(
    source: str = "videos/real_1.mp4",
    on_frame: Optional[Callable[[FrameResult], None]] = None,
) -> None:
    """Quick standalone runner for testing the refactored core without Qt."""
    pipeline = TrafficPipeline(PipelineConfig(source=source))
    for res in pipeline.iter_frames():
        if on_frame is not None:
            on_frame(res)
        vis = res.frame_bgr.copy()
        h, w = vis.shape[:2]
        y1 = int(res.line1_y_ratio * h)
        y2 = int(res.line2_y_ratio * h)
        cv2.line(vis, (0, y1), (w, y1), (0, 255, 255), 2)
        cv2.line(vis, (0, y2), (w, y2), (0, 255, 0), 2)
        for v in res.vehicles:
            bx1, by1, bx2, by2 = v.bbox_xyxy
            color = (0, 0, 255) if v.speed_kmh > 85 else (0, 255, 0)
            cv2.rectangle(vis, (bx1, by1), (bx2, by2), color, 2)
            cv2.putText(
                vis,
                f"ID {v.track_id} {v.class_name} {v.speed_kmh:.0f} km/h",
                (bx1, max(by1 - 6, 16)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )
        cv2.putText(
            vis,
            f"FPS: {res.fps:.1f} | Count: {res.total_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
        )
        cv2.imshow("TrafficSpeedFunc Preview", cv2.resize(vis, (1280, 720)))
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()
