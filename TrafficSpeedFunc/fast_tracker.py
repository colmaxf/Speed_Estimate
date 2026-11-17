"""Lightweight Kalman + IoU tracker (SORT-style) without ReID CNN overhead."""
from __future__ import annotations

from typing import List

import numpy as np
import torch

from deep_sort.sort import iou_matching, kalman_filter, linear_assignment
from deep_sort.sort.detection import Detection
from deep_sort.sort.track import Track


class FastSortTracker:
    """Multi-object tracker using Kalman motion prediction + IoU Hungarian matching.

    Reuses `deep_sort.sort` primitives while skipping the OSNet ReID CNN,
    cutting per-frame tracking cost from ~47 ms down to ~1-2 ms.
    """

    GATING_THRESHOLD = float(np.sqrt(kalman_filter.chi2inv95[4]))

    def __init__(
        self,
        max_iou_distance: float = 0.7,
        max_age: int = 30,
        n_init: int = 3,
    ) -> None:
        self.max_iou_distance = max_iou_distance
        self.max_age = max_age
        self.n_init = n_init
        self.kf = kalman_filter.KalmanFilter()
        self.tracks: List[Track] = []
        self._next_id = 1
        self._dummy_feature = torch.zeros(1, dtype=torch.float32)

    def increment_ages(self) -> None:
        for track in self.tracks:
            track.increment_age()
            track.mark_missed()

    def update(
        self,
        bbox_xywh: torch.Tensor,
        confidences: torch.Tensor,
        classes: torch.Tensor,
        ori_img: np.ndarray,
    ) -> np.ndarray | list:
        height, width = ori_img.shape[:2]
        bbox_tlwh = self._xywh_to_tlwh(bbox_xywh)
        detections = [
            Detection(bbox_tlwh[i], float(confidences[i]), self._dummy_feature)
            for i in range(len(bbox_tlwh))
        ]

        for track in self.tracks:
            track.predict(self.kf)

        matches, unmatched_tracks, unmatched_detections = self._match(detections)

        for track_idx, det_idx in matches:
            self.tracks[track_idx].update(self.kf, detections[det_idx], classes[det_idx])
            self.tracks[track_idx].features.clear()
        for track_idx in unmatched_tracks:
            self.tracks[track_idx].mark_missed()
        for det_idx in unmatched_detections:
            mean, cov = self.kf.initiate(detections[det_idx].to_xyah())
            self.tracks.append(
                Track(
                    mean,
                    cov,
                    self._next_id,
                    classes[det_idx].item(),
                    self.n_init,
                    self.max_age,
                    detections[det_idx].feature,
                )
            )
            self._next_id += 1

        self.tracks = [t for t in self.tracks if not t.is_deleted()]

        outputs = []
        for track in self.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
            x, y, w, h = track.to_tlwh()
            x1 = max(int(x), 0)
            y1 = max(int(y), 0)
            x2 = min(int(x + w), width - 1)
            y2 = min(int(y + h), height - 1)
            outputs.append(np.array([x1, y1, x2, y2, track.track_id, track.class_id], dtype=int))

        if outputs:
            return np.stack(outputs, axis=0)
        return outputs

    def _iou_gated_cost(self, tracks, dets, track_indices, detection_indices):
        cost = iou_matching.iou_cost(tracks, dets, track_indices, detection_indices)
        msrs = np.asarray([dets[i].to_xyah() for i in detection_indices])
        for row, track_idx in enumerate(track_indices):
            gating = np.sqrt(
                self.kf.gating_distance(
                    tracks[track_idx].mean, tracks[track_idx].covariance, msrs, False
                )
            )
            cost[row, gating > self.GATING_THRESHOLD] = linear_assignment.INFTY_COST
        return cost

    def _match(self, detections):
        confirmed = [i for i, t in enumerate(self.tracks) if t.is_confirmed()]
        unconfirmed = [i for i, t in enumerate(self.tracks) if not t.is_confirmed()]

        matches_a, unmatched_a, unmatched_dets = linear_assignment.min_cost_matching(
            self._iou_gated_cost,
            self.max_iou_distance,
            self.tracks,
            detections,
            confirmed,
        )
        iou_candidates = unconfirmed + [
            k for k in unmatched_a if self.tracks[k].time_since_update == 1
        ]
        stale_unmatched = [
            k for k in unmatched_a if self.tracks[k].time_since_update != 1
        ]
        matches_b, unmatched_b, unmatched_dets = linear_assignment.min_cost_matching(
            iou_matching.iou_cost,
            self.max_iou_distance,
            self.tracks,
            detections,
            iou_candidates,
            unmatched_dets,
        )
        matches = matches_a + matches_b
        unmatched_tracks = list(set(stale_unmatched + unmatched_b))
        return matches, unmatched_tracks, unmatched_dets

    @staticmethod
    def _xywh_to_tlwh(bbox_xywh: torch.Tensor) -> torch.Tensor:
        bbox_tlwh = bbox_xywh.clone()
        bbox_tlwh[:, 0] = bbox_xywh[:, 0] - bbox_xywh[:, 2] / 2.0
        bbox_tlwh[:, 1] = bbox_xywh[:, 1] - bbox_xywh[:, 3] / 2.0
        return bbox_tlwh
