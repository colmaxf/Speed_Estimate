"""CLI runner for YOLOv5 + DeepSORT vehicle speed estimation using speed_config.json."""
from __future__ import annotations

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import argparse
from pathlib import Path

import cv2
import numpy as np

from TrafficSpeedFunc import (
    PipelineConfig,
    SpeedEstimator,
    TrafficPipeline,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Traffic Speed Estimation CLI")
    parser.add_argument("--config", type=str, default="speed_config.json", help="Path to JSON config")
    parser.add_argument("--source", type=str, default=None, help="Override video/stream source")
    parser.add_argument("--yolo-model", type=str, default=None, help="Override YOLO weights path")
    parser.add_argument("--imgsz", type=int, default=None, help="Override inference size")
    parser.add_argument("--conf-thres", type=float, default=None, help="Override confidence threshold")
    parser.add_argument("--iou-thres", type=float, default=None, help="Override NMS IoU threshold")
    parser.add_argument("--device", type=str, default=None, help="CUDA device or cpu")
    parser.add_argument("--no-show", action="store_true", help="Disable OpenCV preview window")
    parser.add_argument("--save-vid", action="store_true", help="Save annotated video")
    parser.add_argument("--output", type=str, default="inference/output/result.mp4", help="Output video path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg_path = Path(args.config)
    cfg = PipelineConfig.from_json(cfg_path) if cfg_path.exists() else PipelineConfig()

    if args.source is not None:
        cfg.source = args.source
    if args.yolo_model is not None:
        cfg.yolo_weights = args.yolo_model
    if args.imgsz is not None:
        cfg.imgsz = args.imgsz
    if args.conf_thres is not None:
        cfg.conf_thres = args.conf_thres
    if args.iou_thres is not None:
        cfg.iou_thres = args.iou_thres
    if args.device is not None:
        cfg.device = args.device

    cfg.loop_video = False
    cfg.realtime_pace = False

    pipeline = TrafficPipeline(cfg)
    writer: cv2.VideoWriter | None = None

    try:
        for res in pipeline.iter_frames():
            vis = res.frame_bgr.copy()
            h, w = vis.shape[:2]
            line_start_y, line_end_y = pipeline.estimator.resolve_lines_px(h)

            cv2.line(vis, (0, int(line_start_y)), (w, int(line_start_y)), (0, 255, 255), 2)
            cv2.line(vis, (0, int(line_end_y)), (w, int(line_end_y)), (0, 255, 0), 2)

            if cfg.estimator.calibration_mode == "homography":
                poly = np.array(
                    [[int(px * w), int(py * h)] for px, py in cfg.estimator.src_norm_points],
                    dtype=np.int32,
                )
                cv2.polylines(vis, [poly], isClosed=True, color=(255, 200, 0), thickness=2)

            for v in res.vehicles:
                x1, y1, x2, y2 = v.bbox_xyxy
                gx, gy = SpeedEstimator.get_ground_contact_point((x1, y1, x2, y2))
                color = (
                    (0, 0, 255)
                    if v.speed_kmh > cfg.estimator.speed_limit_kmh
                    else (0, 255, 0)
                )
                cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
                cv2.circle(vis, (int(gx), int(gy)), 4, (255, 255, 0), -1)
                tag = f"#{v.track_id} {v.class_name} {v.speed_kmh:.1f} km/h"
                cv2.putText(
                    vis,
                    tag,
                    (x1, max(y1 - 8, 18)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                )

            cv2.putText(
                vis,
                f"FPS: {res.fps:.1f} | Count: {res.total_count} | Limit: {cfg.estimator.speed_limit_kmh:.0f} km/h",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 255, 255),
                2,
            )

            if args.save_vid:
                if writer is None:
                    out_path = Path(args.output)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    writer = cv2.VideoWriter(
                        str(out_path),
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        30.0,
                        (w, h),
                    )
                writer.write(vis)

            if not args.no_show:
                cv2.imshow("Speed Estimate", cv2.resize(vis, (1280, 720)))
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        if writer is not None:
            writer.release()
        if not args.no_show:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
