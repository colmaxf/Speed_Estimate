# Speed Estimate — Vehicle Speed Estimation & Traffic Monitoring Dashboard

Real-time vehicle detection, multi-object tracking, and speed estimation system powered by **YOLOv5**, **FastSort / DeepSORT**, **4-point Homography road calibration**, and a **PySide6 + QML (`NexusTrafficOps`)** live operations dashboard.

> **Disclaimer**: Estimated speeds depend on camera placement, frame rate, and geometric calibration (`speed_config.json`). This project is intended for research and traffic analytics prototypes, not certified law-enforcement radar replacement.

---

## Key Features

- **Real-time Vehicle Detection & Tracking**:
  - Uses **YOLOv5** (`DetectMultiBackend`, FP16 on CUDA) filtered to road vehicles (`car`, `motorcycle`, `bus`, `truck`).
  - Supports two tracker backends configurable in `speed_config.json`:
    - `fast_sort` *(default)*: Lightweight Kalman filter + IoU Hungarian matching (skips ReID CNN overhead for high real-time FPS).
    - `deepsort`: Full appearance-based OSNet ReID + Kalman tracking.
  - Pre-filters detections outside the measurement ROI (`filter_roi_before_track`) to eliminate distant horizon overhead.
- **4-Point Homography Speed Calibration**:
  - Maps the **bottom-center ground contact point** of each bounding box (avoiding `centerY` height inflation on SUVs, buses, and trucks) onto a calibrated real-world road plane (`cv2.getPerspectiveTransform`).
  - Uses a 15-frame sliding window, displacement/time-delta guards (`compute_distance_px`, `convert_pixel_to_meter`, `compute_speed_kmh`), and EMA smoothing.
  - Uses video frame timestamps (`frame_idx / fps`) for recorded videos so speed readings stay independent of processing FPS.
- **PySide6 + QML Live Dashboard (`traffic_ops_qt`)**:
  - Runs AI inference off the GUI thread via `QThread` (`TrafficWorker`) and streams frames directly into QML `VideoOutput` through `QVideoSink`.
  - Synchronizes live bounding boxes (`VehicleModel.sync_tracks`), overlays the ROI bounds and 4-point Homography calibration trapezoid, updates live FPS/latency/traffic charts, and triggers speeding violation cards (`AlertModel`).
- **JSON-Driven Configuration**:
  - All model paths, thresholds, ROI boundaries, speed limits, and Homography anchor points live in `speed_config.json`.

---

## Project Structure

```text
.
├── speed_config.json                # Unified AI, tracker, ROI, and Homography config
├── test_speed.py                    # OpenCV CLI runner reading speed_config.json
├── TrafficSpeedFunc/                # Core AI & speed estimation package
│   ├── __init__.py
│   ├── pipeline.py                  # TrafficPipeline (YOLOv5 + tracker + SpeedEstimator)
│   ├── speed_estimator.py           # Homography calibration, ROI checks, 3-step speed math
│   └── fast_tracker.py              # FastSortTracker (Kalman + IoU without ReID CNN)
├── traffic_ops_qt/                  # PySide6 + QML desktop dashboard (NexusTrafficOps)
│   ├── main.py                      # Application entry point
│   ├── main.qml                     # 12-column dashboard layout
│   ├── backend.py                   # TrafficBackend (QML bridge, telemetry, alerts)
│   ├── worker.py                    # TrafficWorker (QThread + QVideoFrame RGBA upload)
│   ├── traffic_models.py            # VehicleModel & AlertModel (QAbstractListModel)
│   ├── icon_provider.py             # SVG icon provider
│   ├── requirements.txt             # PySide6>=6.6
│   └── TrafficOps/                  # QML UI components (VideoPanel, BoundingBox, etc.)
├── deep_sort/                       # DeepSORT tracker & ReID checkpoints
├── yolov5/                          # YOLOv5 source
├── videos/                          # Input video files (e.g., real_1.mp4)
├── track.py / track1.py / track1_1.py / lines.json  # Legacy prototype scripts
└── requirements.txt                 # Core Python dependencies
```

---

## Requirements

- **Python**: 3.8+ (tested with Python 3.8.6)
- **PyTorch & torchvision**: Matching your Python version and CUDA setup (see [PyTorch](https://pytorch.org/get-started/locally/)). CUDA GPU is strongly recommended for real-time inference.
- **Packages**: Listed in `yolov5/requirements.txt`, `requirements.txt`, and `traffic_ops_qt/requirements.txt` (`PySide6>=6.6`).

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/colmaxf/Speed_Estimate.git
cd Speed_Estimate
```

2. Pull model weights if stored with Git LFS:

```bash
git lfs install
git lfs pull
```

3. Create and activate a virtual environment:

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

4. Install PyTorch/torchvision for your hardware, then install dependencies:

```bash
pip install -r yolov5/requirements.txt
pip install -r requirements.txt
pip install -r traffic_ops_qt/requirements.txt
```

---

## Usage

### 1. Run the PySide6 + QML Dashboard (Recommended)

From the repository root:

```bash
python traffic_ops_qt/main.py
```

The dashboard automatically reads `speed_config.json`, launches `TrafficWorker` on the configured video/stream source, and falls back to simulated mode if no video source is found.

### 2. Run the OpenCV CLI Preview

```bash
python test_speed.py
```

Useful CLI overrides:

```bash
python test_speed.py --config speed_config.json --source videos/real_1.mp4 --save-vid
python test_speed.py --no-show --save-vid --output inference/output/result.mp4
python test_speed.py --help
```

---

## Configuration & Calibration (`speed_config.json`)

Edit [speed_config.json](speed_config.json) without touching Python code:

- **Source & Model**: `source` (video path, RTSP URL, or `"0"` for webcam), `yolo_weights` (`yolov5n.pt` / `yolov5x.pt`), `imgsz`, `conf_thres`, `iou_thres`, `classes` (`[2, 3, 5, 7]`).
- **Tracker Mode**:
  - `"tracker_type": "fast_sort"` — Kalman + IoU matching (~43 FPS max throughput on RTX 3070 Ti Laptop GPU, ~16 ms AI latency).
  - `"tracker_type": "deepsort"` — OSNet ReID + Kalman (~18 FPS with ROI pre-filtering).
  - `"filter_roi_before_track": true` — skips detections above `roi_top_ratio - 0.05`.
- **ROI & Speed Thresholds (`speed_estimation`)**:
  - `roi_top_ratio` / `roi_bottom_ratio`: Vertical measurement zone (`0.37`–`0.96` by default).
  - `counting_line_y_ratio`: Virtual line used to count traffic volume.
  - `sliding_window_frames`, `min_history_frames`, `min_displacement_px`, `min_time_delta_s`: Sliding-window jitter suppression and time-delta guards.
  - `speed_limit_kmh`, `warn_speed_kmh`, `alert_speed_kmh`: Speed limit, yellow warning threshold, and red violation alert threshold.
- **Homography (`speed_estimation.homography`)**:
  - `src_norm_points`: 4 normalized `[x/W, y/H]` points ordered `[top-left, top-right, bottom-right, bottom-left]` aligned to road lane markings.
  - `dst_meter_points`: Corresponding real-world ground coordinates in meters `[X, Y]` (default `7.0m × 10.0m`).

### Speed Calculation Pipeline (`TrafficSpeedFunc/speed_estimator.py`)

Speed estimation is separated into three explicit functions:

1. `compute_distance_px(point_start_px, point_end_px)` — Euclidean pixel displacement between ground contact points `(cx, y2)`.
2. `convert_pixel_to_meter(...)` — Transforms pixel coordinates onto the calibrated road plane via `cv2.perspectiveTransform` (or linear `m/px` scale when `calibration_mode = "linear"`).
3. `compute_speed_kmh(distance_m, time_start_s, time_end_s, min_dt_s, max_speed_kmh)` — Computes `(distance_m / dt) * 3.6` only when `dt > min_dt_s` and within plausible bounds.

---

## License & Acknowledgments

This repository includes third-party components from **YOLOv5** and **DeepSORT** (`torchreid`); please review their respective licenses in `yolov5/` and `deep_sort/` before redistribution or commercial deployment.
