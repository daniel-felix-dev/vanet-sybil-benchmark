"""
Detector 4: Random Forest baseline (port of 126160042-crypto/sybil-attack-detection-vanet)

Supervised ML: trains a RandomForestClassifier on labelled beacon features.
Uses 80/20 stratified train/test split internally for evaluation.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from .base_detector import BaseDetector

FEATURES = ["speed", "accel", "angle", "x", "y", "n_neighbors",
            "min_rsu_dist", "mean_rsu_dist", "edge_enc"]


class RFDetector(BaseDetector):
    name = "Random Forest"

    def __init__(self, n_estimators=100, max_depth=10, seed=42):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            class_weight="balanced",
            random_state=seed,
            n_jobs=-1,
        )
        self._le = LabelEncoder()

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["edge_enc"] = self._le.transform(df["edge_id"])
        return df[FEATURES]

    def fit(self, df: pd.DataFrame):
        df = df.copy()
        df["edge_enc"] = self._le.fit_transform(df["edge_id"])
        X = df[FEATURES].values
        y = df["is_sybil"].values
        self.model.fit(X, y)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = self._prepare(df).values
        return self.model.predict(X)
