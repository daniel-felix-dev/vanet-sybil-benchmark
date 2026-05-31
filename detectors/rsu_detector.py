"""
Detector 2: RSU Position Verification (port of karthik-047/Detecting-Sybil-Attacks-in-VANETs)

20 RSUs at fixed positions. A vehicle pair seen by the same RSU (within 100m)
at the same time step where both have positions that are more than DIST_THRESH
apart is flagged. Pairs with frequency >= MIN_FREQ are confirmed Sybil.
"""
import math
import numpy as np
import pandas as pd
from itertools import combinations
from collections import defaultdict
from .base_detector import BaseDetector

# RSU grid positions (same as collect_dataset.py)
GRID_SIZE = 1200.0
RSU_POSITIONS = [
    (GRID_SIZE * (c + 0.5) / 4, GRID_SIZE * (r + 0.5) / 5)
    for r in range(5) for c in range(4)
]
RSU_RANGE   = 100.0   # metres
DIST_THRESH = 150.0   # RSU-distance threshold to flag a pair
MIN_FREQ    = 5       # minimum flagging events to confirm Sybil


def dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)


class RSUDetector(BaseDetector):
    name = "RSU Position Verification"

    def __init__(self, rsu_range=RSU_RANGE, dist_thresh=DIST_THRESH, min_freq=MIN_FREQ):
        self.rsu_range   = rsu_range
        self.dist_thresh = dist_thresh
        self.min_freq    = min_freq
        self._sybil_ids  = set()

    def fit(self, df: pd.DataFrame):
        pair_count = defaultdict(int)

        for step, step_df in df.groupby("step"):
            # For each RSU, find vehicles within range
            for rx, ry in RSU_POSITIONS:
                nearby = step_df[
                    np.sqrt((step_df["x"] - rx)**2 + (step_df["y"] - ry)**2) <= self.rsu_range
                ]
                vids = nearby["vehicle_id"].tolist()
                if len(vids) < 2:
                    continue
                # Check all pairs
                coords = {row["vehicle_id"]: (row["x"], row["y"])
                          for _, row in nearby.iterrows()}
                for v1, v2 in combinations(vids, 2):
                    x1, y1 = coords[v1]
                    x2, y2 = coords[v2]
                    if dist(x1, y1, x2, y2) > self.dist_thresh:
                        key = tuple(sorted([v1, v2]))
                        pair_count[key] += 1

        self._sybil_ids = set()
        for (v1, v2), cnt in pair_count.items():
            if cnt >= self.min_freq:
                self._sybil_ids.add(v1)
                self._sybil_ids.add(v2)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (df["vehicle_id"].isin(self._sybil_ids)).astype(int).values
