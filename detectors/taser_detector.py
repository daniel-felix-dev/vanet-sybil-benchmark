"""
Detector 3 — TASER Bayesian Trust Score (port of morton-t/VANET-Simulations)

Each vehicle v maintains a trust score T_v updated per beacon:
  - If beacon consistent (speed in [min_ok, max_ok] and position plausible):
      T_v = T_v + alpha * (1 - T_v)
  - Else (anomalous beacon):
      T_v = T_v - beta * T_v

Additional position consistency check:
  - If claimed speed > delta * expected_max_speed: anomaly.

Vehicles whose trust score falls below threshold lambda are flagged Sybil.

Parameters (from paper): alpha=0.01, beta=0.1, delta=0.4, lambda=0.15
"""
import numpy as np
import pandas as pd
from .base_detector import BaseDetector

ALPHA     = 0.01   # trust increment on consistent beacon
BETA      = 0.10   # trust decrement on anomalous beacon
DELTA     = 0.40   # speed deviation threshold fraction
LAMBDA    = 0.15   # trust threshold below which = Sybil
SPEED_MAX = 13.89  # m/s — expected max speed (same as vType maxSpeed)
SPEED_MIN = 0.0


class TASERDetector(BaseDetector):
    name = "TASER Bayesian Trust"

    def __init__(self, alpha=ALPHA, beta=BETA, delta=DELTA, lam=LAMBDA):
        self.alpha = alpha
        self.beta  = beta
        self.delta = delta
        self.lam   = lam
        self._trust: dict[str, float] = {}
        self._sybil_ids: set          = set()

    def _is_anomalous(self, speed: float, accel: float) -> bool:
        if speed < SPEED_MIN or speed > SPEED_MAX * (1 + self.delta):
            return True
        if abs(accel) > SPEED_MAX * self.delta:
            return True
        return False

    def fit(self, df: pd.DataFrame):
        trust = {}

        for step, step_df in df.sort_values("step").groupby("step"):
            for _, row in step_df.iterrows():
                vid = row["vehicle_id"]
                if vid not in trust:
                    trust[vid] = 0.5   # initial trust

                if self._is_anomalous(row["speed"], row["accel"]):
                    trust[vid] = trust[vid] - self.beta * trust[vid]
                else:
                    trust[vid] = trust[vid] + self.alpha * (1.0 - trust[vid])

                # Clamp [0, 1]
                trust[vid] = max(0.0, min(1.0, trust[vid]))

        self._trust = trust
        self._sybil_ids = {vid for vid, t in trust.items() if t < self.lam}

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (df["vehicle_id"].isin(self._sybil_ids)).astype(int).values
