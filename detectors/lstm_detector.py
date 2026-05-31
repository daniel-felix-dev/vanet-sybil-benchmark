"""
Detector 6: LSTM (port of SaiKumar-1608 dual-layer framework, lstm.ipynb)

Train/test split is performed by vehicle_id to prevent data leakage.
All rows belonging to a vehicle appear exclusively in either the training
or the test partition. A random 80/20 split by vehicle_id is used.

Architecture: two LSTM layers (64 -> 32), dropout 0.3, binary sigmoid output.
Input: sequence of up to SEQ_LEN beacon records per vehicle.
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
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
from .base_detector import BaseDetector

SEQ_LEN  = 50
FEATURES = ["speed", "accel", "angle", "x", "y",
            "n_neighbors", "min_rsu_dist", "mean_rsu_dist"]
SEED = 42
tf.random.set_seed(SEED)


def build_sequences(df: pd.DataFrame, seq_len: int, scaler=None, fit_scaler=False):
    """
    Build (n_vehicles, seq_len, n_features) array.
    Returns (X, y, vehicle_ids, scaler).
    """
    vids, X_list, y_list = [], [], []

    # Fit scaler on the feature columns only
    if fit_scaler:
        scaler = StandardScaler()
        scaler.fit(df[FEATURES].values)

    for vid, grp in df.sort_values("step").groupby("vehicle_id"):
        vals = grp[FEATURES].values.astype(np.float32)
        vals = scaler.transform(vals)
        if len(vals) >= seq_len:
            vals = vals[:seq_len]
        else:
            pad  = np.zeros((seq_len - len(vals), vals.shape[1]), dtype=np.float32)
            vals = np.vstack([pad, vals])
        X_list.append(vals)
        y_list.append(int(grp["is_sybil"].iloc[0]))
        vids.append(vid)

    return (np.array(X_list, dtype=np.float32),
            np.array(y_list, dtype=np.int32),
            vids, scaler)


class LSTMDetector(BaseDetector):
    name = "LSTM"

    def __init__(self, seq_len=SEQ_LEN, epochs=20, batch_size=32, test_size=0.20):
        self.seq_len    = seq_len
        self.epochs     = epochs
        self.batch_size = batch_size
        self.test_size  = test_size
        self.model      = None
        self._scaler    = None
        self._vid_labels: dict = {}
        self.test_metrics_: dict = {}  # out-of-sample metrics from fit()

    def _build(self, n_features: int) -> Sequential:
        m = Sequential([
            Masking(mask_value=0.0, input_shape=(self.seq_len, n_features)),
            LSTM(64, return_sequences=True),
            Dropout(0.3),
            LSTM(32),
            Dropout(0.3),
            Dense(16, activation="relu"),
            Dense(1,  activation="sigmoid"),
        ])
        m.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        return m

    def fit(self, df: pd.DataFrame):
        """
        Splits vehicles 80/20 by vehicle_id, trains on the 80% partition,
        evaluates on the held-out 20%, and then retrains on the full dataset
        for production use. test_metrics_ stores the out-of-sample result.
        """
        # Per-vehicle labels for stratified split
        veh_labels = (df.groupby("vehicle_id")["is_sybil"]
                      .max().reset_index())
        veh_ids = veh_labels["vehicle_id"].values
        veh_y   = veh_labels["is_sybil"].values

        # 80/20 split by vehicle_id, stratified
        train_vids, test_vids = train_test_split(
            veh_ids, test_size=self.test_size,
            stratify=veh_y, random_state=SEED
        )
        train_df = df[df["vehicle_id"].isin(train_vids)]
        test_df  = df[df["vehicle_id"].isin(test_vids)]

        # Build sequences - fit scaler on train only
        X_tr, y_tr, _, scaler = build_sequences(train_df, self.seq_len, fit_scaler=True)
        X_te, y_te, te_vids, _ = build_sequences(test_df, self.seq_len, scaler=scaler)

        # Train on 80%
        model_tmp = self._build(X_tr.shape[-1])
        es = EarlyStopping(patience=3, restore_best_weights=True, verbose=0)
        model_tmp.fit(X_tr, y_tr, epochs=self.epochs, batch_size=self.batch_size,
                      validation_split=0.15, callbacks=[es], verbose=0)

        # Evaluate on held-out 20%
        probs_te = model_tmp.predict(X_te, verbose=0).flatten()
        y_pred   = (probs_te >= 0.5).astype(int)

        tn = int(((y_te == 0) & (y_pred == 0)).sum())
        fp = int(((y_te == 0) & (y_pred == 1)).sum())
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        self.test_metrics_ = {
            "accuracy":    float(accuracy_score(y_te, y_pred)),
            "precision":   float(precision_score(y_te, y_pred, zero_division=0)),
            "recall":      float(recall_score(y_te, y_pred, zero_division=0)),
            "f1":          float(f1_score(y_te, y_pred, zero_division=0)),
            "specificity": spec,
            "n_train_veh": len(train_vids),
            "n_test_veh":  len(test_vids),
        }

        # Retrain on full dataset for production predict()
        X_all, y_all, all_vids, scaler_all = build_sequences(df, self.seq_len, fit_scaler=True)
        self._scaler = scaler_all
        self.model   = self._build(X_all.shape[-1])
        self.model.fit(X_all, y_all, epochs=self.epochs, batch_size=self.batch_size,
                       validation_split=0.15, callbacks=[es], verbose=0)

        probs_all = self.model.predict(X_all, verbose=0).flatten()
        self._vid_labels = {vid: int(p >= 0.5) for vid, p in zip(all_vids, probs_all)}

    def evaluate(self, df: pd.DataFrame) -> dict:
        """Override to return out-of-sample metrics from fit(), not in-sample."""
        if self.test_metrics_:
            return {
                "detector":    self.name,
                "accuracy":    round(self.test_metrics_["accuracy"], 4),
                "precision":   round(self.test_metrics_["precision"], 4),
                "recall":      round(self.test_metrics_["recall"], 4),
                "f1":          round(self.test_metrics_["f1"], 4),
                "specificity": round(self.test_metrics_["specificity"], 4),
            }
        return super().evaluate(df)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (df["vehicle_id"].map(lambda v: self._vid_labels.get(v, 0))
                .fillna(0).astype(int).values)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Sybil probability per row (for ROC curves), using production model."""
        if self.model is None:
            return np.zeros(len(df))
        X, _, vids, _ = build_sequences(df, self.seq_len, scaler=self._scaler)
        probs_map = {vid: float(p)
                     for vid, p in zip(vids,
                        self.model.predict(X, verbose=0).flatten())}
        return df["vehicle_id"].map(lambda v: probs_map.get(v, 0.0)).values
