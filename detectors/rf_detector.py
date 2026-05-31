"""
Detector 4: Random Forest baseline (port of 126160042-crypto/sybil-attack-detection-vanet)

Train/test split is done by vehicle_id (not by row) to prevent data leakage.
Rows from the same vehicle must not appear in both train and test, because the
model could otherwise memorise per-vehicle patterns at training time and
recognise them at evaluation time without having learned anything general.

Evaluation protocol:
  - cv_evaluate(): 5-fold cross-validation by vehicle_id, returns mean +/- std
  - fit() / predict(): trains on full dataset for production deployment
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
from .base_detector import BaseDetector

FEATURES = ["speed", "accel", "angle", "x", "y", "n_neighbors",
            "min_rsu_dist", "mean_rsu_dist", "edge_enc"]


class RFDetector(BaseDetector):
    name = "Random Forest"

    def __init__(self, n_estimators=100, max_depth=10, seed=42):
        self._n_estimators = n_estimators
        self._max_depth    = max_depth
        self._seed         = seed
        self._le           = LabelEncoder()
        self.model         = self._new_model()
        self.cv_results_   = {}   # filled by cv_evaluate()

    def _new_model(self):
        return RandomForestClassifier(
            n_estimators=self._n_estimators,
            max_depth=self._max_depth,
            class_weight="balanced",
            random_state=self._seed,
            n_jobs=-1,
        )

    def _encode(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        df = df.copy()
        if fit:
            df["edge_enc"] = self._le.fit_transform(df["edge_id"])
        else:
            # Handle unseen edge labels gracefully
            known = set(self._le.classes_)
            df["edge_id"] = df["edge_id"].apply(lambda e: e if e in known else self._le.classes_[0])
            df["edge_enc"] = self._le.transform(df["edge_id"])
        return df[FEATURES]

    # ------------------------------------------------------------------
    # Cross-validation by vehicle_id (prevents data leakage)
    # ------------------------------------------------------------------
    def cv_evaluate(self, df: pd.DataFrame, k: int = 5) -> dict:
        """
        5-fold stratified cross-validation where folds are split by vehicle_id.
        A vehicle and all its rows belong exclusively to either train or test
        in each fold, so the model never sees test-vehicle beacons at training.
        """
        # One label per vehicle
        veh_labels = (df.groupby("vehicle_id")["is_sybil"]
                      .max().reset_index())
        veh_ids = veh_labels["vehicle_id"].values
        veh_y   = veh_labels["is_sybil"].values

        skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=self._seed)
        fold_metrics = {m: [] for m in ["accuracy","precision","recall","f1","specificity"]}

        for train_idx, test_idx in skf.split(veh_ids, veh_y):
            train_vids = set(veh_ids[train_idx])
            test_vids  = set(veh_ids[test_idx])

            train_df = df[df["vehicle_id"].isin(train_vids)].copy()
            test_df  = df[df["vehicle_id"].isin(test_vids)].copy()

            le = LabelEncoder().fit(train_df["edge_id"])
            def enc(d, ref_le):
                dc = d.copy()
                known = set(ref_le.classes_)
                dc["edge_id"] = dc["edge_id"].apply(lambda e: e if e in known else ref_le.classes_[0])
                dc["edge_enc"] = ref_le.transform(dc["edge_id"])
                return dc[FEATURES].values

            X_tr = enc(train_df, le)
            y_tr = train_df["is_sybil"].values
            X_te = enc(test_df,  le)
            y_te = test_df["is_sybil"].values

            clf = self._new_model()
            clf.fit(X_tr, y_tr)
            y_pred = clf.predict(X_te)

            tn = int(((y_te == 0) & (y_pred == 0)).sum())
            fp = int(((y_te == 0) & (y_pred == 1)).sum())
            spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0

            fold_metrics["accuracy"].append(accuracy_score(y_te, y_pred))
            fold_metrics["precision"].append(precision_score(y_te, y_pred, zero_division=0))
            fold_metrics["recall"].append(recall_score(y_te, y_pred, zero_division=0))
            fold_metrics["f1"].append(f1_score(y_te, y_pred, zero_division=0))
            fold_metrics["specificity"].append(spec)

        self.cv_results_ = {
            m: {"mean": float(np.mean(v)), "std": float(np.std(v))}
            for m, v in fold_metrics.items()
        }
        return self.cv_results_

    # ------------------------------------------------------------------
    # Full-dataset training for production / deployment
    # ------------------------------------------------------------------
    def fit(self, df: pd.DataFrame):
        X = self._encode(df, fit=True).values
        y = df["is_sybil"].values
        self.model.fit(X, y)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict(self._encode(df, fit=False).values)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Probability of Sybil class (used for ROC curves)."""
        return self.model.predict_proba(self._encode(df, fit=False).values)[:, 1]
