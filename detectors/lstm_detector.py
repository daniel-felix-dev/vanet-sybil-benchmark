"""
Detector 6: LSTM (port of SaiKumar-1608 dual-layer framework, lstm.ipynb)

Treats each vehicle's beacon sequence as a time series.
Per-vehicle feature sequences are padded/truncated to SEQ_LEN steps.
Binary classifier: Sybil (1) vs Legit (0).
"""
import numpy as np
import pandas as pd
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Masking
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import LabelEncoder, StandardScaler
from .base_detector import BaseDetector

SEQ_LEN  = 50     # steps per vehicle sequence
FEATURES = ["speed", "accel", "angle", "x", "y",
            "n_neighbors", "min_rsu_dist", "mean_rsu_dist"]
SEED = 42
tf.random.set_seed(SEED)


def build_sequences(df: pd.DataFrame, seq_len: int):
    """Build (n_vehicles, seq_len, n_features) array from per-vehicle time series."""
    feat_arr = []
    labels   = []

    for vid, grp in df.sort_values("step").groupby("vehicle_id"):
        vals = grp[FEATURES].values
        # Pad or truncate
        if len(vals) >= seq_len:
            vals = vals[:seq_len]
        else:
            pad = np.zeros((seq_len - len(vals), vals.shape[1]))
            vals = np.vstack([pad, vals])
        feat_arr.append(vals)
        labels.append(int(grp["is_sybil"].iloc[0]))

    return np.array(feat_arr, dtype=np.float32), np.array(labels, dtype=np.int32)


class LSTMDetector(BaseDetector):
    name = "LSTM"

    def __init__(self, seq_len=SEQ_LEN, epochs=20, batch_size=32):
        self.seq_len    = seq_len
        self.epochs     = epochs
        self.batch_size = batch_size
        self.model      = None
        self._scaler    = StandardScaler()
        self._vid_labels: dict = {}

    def _scale(self, X: np.ndarray, fit=False) -> np.ndarray:
        shape = X.shape
        flat  = X.reshape(-1, shape[-1])
        if fit:
            flat = self._scaler.fit_transform(flat)
        else:
            flat = self._scaler.transform(flat)
        return flat.reshape(shape)

    def _build_model(self, n_features: int) -> Sequential:
        m = Sequential([
            Masking(mask_value=0.0, input_shape=(self.seq_len, n_features)),
            LSTM(64, return_sequences=True),
            Dropout(0.3),
            LSTM(32),
            Dropout(0.3),
            Dense(16, activation="relu"),
            Dense(1, activation="sigmoid"),
        ])
        m.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        return m

    def fit(self, df: pd.DataFrame):
        X, y = build_sequences(df, self.seq_len)
        X    = self._scale(X, fit=True)
        self.model = self._build_model(X.shape[-1])
        es = EarlyStopping(patience=3, restore_best_weights=True, verbose=0)
        self.model.fit(
            X, y,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.15,
            callbacks=[es],
            verbose=0,
        )
        # Cache per-vehicle label for predict
        probs = self.model.predict(X, verbose=0).flatten()
        vids  = [vid for vid, _ in df.sort_values("step").groupby("vehicle_id")]
        self._vid_labels = {vid: int(p >= 0.5) for vid, p in zip(vids, probs)}

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return df["vehicle_id"].map(
            lambda v: self._vid_labels.get(v, 0)
        ).fillna(0).astype(int).values
