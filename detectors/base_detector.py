"""Base class for all detectors."""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


class BaseDetector(ABC):
    name = "BaseDetector"

    @abstractmethod
    def fit(self, df: pd.DataFrame):
        """Train / calibrate on the full dataset (unsupervised detectors can skip)."""

    @abstractmethod
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Return binary array: 1=Sybil, 0=Legit, indexed like df."""

    def evaluate(self, df: pd.DataFrame) -> dict:
        y_true = df["is_sybil"].values
        y_pred = self.predict(df)
        tn = int(((y_true == 0) & (y_pred == 0)).sum())
        fp = int(((y_true == 0) & (y_pred == 1)).sum())
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        return {
            "detector":    self.name,
            "accuracy":    round(accuracy_score(y_true, y_pred), 4),
            "precision":   round(precision_score(y_true, y_pred, zero_division=0), 4),
            "recall":      round(recall_score(y_true, y_pred, zero_division=0), 4),
            "f1":          round(f1_score(y_true, y_pred, zero_division=0), 4),
            "specificity": round(specificity, 4),
        }
