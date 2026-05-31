"""
Detector 1 — IQR Speed Threshold (port of MohammedSuratwala/SybilDetection)

Each vehicle accumulates speed readings. Readings below Q1 - 1.5*IQR
are flagged as anomalous. A vehicle is classified Sybil if any reading
is flagged (i.e., its ID prefix is 'sybil_', which emits speed < Q1-fence).

In the benchmark we apply the IQR fence vehicle-by-vehicle over its
speed history across all steps.
"""
import numpy as np
import pandas as pd
from .base_detector import BaseDetector


class IQRDetector(BaseDetector):
    name = "IQR Speed Threshold"

    def __init__(self, iqr_multiplier: float = 1.5):
        self.k = iqr_multiplier
        self._thresholds: dict[str, float] = {}

    def fit(self, df: pd.DataFrame):
        # Compute global Q1/IQR from legitimate vehicles only (unsupervised: use all)
        speeds = df["speed"].values
        q1 = np.percentile(speeds, 25)
        q3 = np.percentile(speeds, 75)
        iqr = q3 - q1
        self._lower = q1 - self.k * iqr
        self._upper = q3 + self.k * iqr

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        # Per-vehicle: flag if ANY speed reading is outside [lower, upper]
        result = pd.Series(0, index=df.index)
        for vid, grp in df.groupby("vehicle_id"):
            speeds = grp["speed"].values
            if np.any(speeds < self._lower) or np.any(speeds > self._upper):
                result.loc[grp.index] = 1
        return result.values
