"""
Detector 5: Random Forest + Grey Wolf Optimizer (port of 126160042-crypto, gwo_rf_model.py)

GWO searches for optimal (n_estimators, max_depth) to minimise 1-accuracy.
Search space: n_estimators in [10, 200], max_depth in [3, 20].
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score
from .base_detector import BaseDetector

FEATURES = ["speed", "accel", "angle", "x", "y", "n_neighbors",
            "min_rsu_dist", "mean_rsu_dist", "edge_enc"]

# GWO hyperparameter bounds: [n_estimators, max_depth]
BOUNDS_LOW  = [10,  3]
BOUNDS_HIGH = [200, 20]
N_AGENTS    = 6
N_ITER      = 10
SEED        = 42


class GWORFDetector(BaseDetector):
    name = "Random Forest + GWO"

    def __init__(self):
        self._le    = LabelEncoder()
        self.model  = None
        self.best_params = {}

    def _prepare(self, df: pd.DataFrame) -> np.ndarray:
        df = df.copy()
        df["edge_enc"] = self._le.transform(df["edge_id"])
        return df[FEATURES].values

    def _fitness(self, params, X, y):
        n_est  = max(10, int(round(params[0])))
        depth  = max(3,  int(round(params[1])))
        clf = RandomForestClassifier(
            n_estimators=n_est, max_depth=depth,
            class_weight="balanced", random_state=SEED, n_jobs=-1
        )
        scores = cross_val_score(clf, X, y, cv=3, scoring="accuracy")
        return 1.0 - scores.mean()

    def fit(self, df: pd.DataFrame):
        df = df.copy()
        df["edge_enc"] = self._le.fit_transform(df["edge_id"])
        X = df[FEATURES].values
        y = df["is_sybil"].values

        rng = np.random.default_rng(SEED)
        dim = len(BOUNDS_LOW)

        # Initialise wolves
        pos = rng.uniform(0, 1, (N_AGENTS, dim))
        pos = pos * (np.array(BOUNDS_HIGH) - np.array(BOUNDS_LOW)) + np.array(BOUNDS_LOW)

        alpha_pos = pos[0].copy(); alpha_score = float("inf")
        beta_pos  = pos[1].copy(); beta_score  = float("inf")
        delta_pos = pos[2].copy(); delta_score = float("inf")

        for it in range(N_ITER):
            for i in range(N_AGENTS):
                s = self._fitness(pos[i], X, y)
                if s < alpha_score:
                    delta_pos, delta_score = beta_pos.copy(), beta_score
                    beta_pos,  beta_score  = alpha_pos.copy(), alpha_score
                    alpha_pos, alpha_score = pos[i].copy(), s
                elif s < beta_score:
                    delta_pos, delta_score = beta_pos.copy(), beta_score
                    beta_pos,  beta_score  = pos[i].copy(), s
                elif s < delta_score:
                    delta_pos, delta_score = pos[i].copy(), s

            a = 2 - it * (2 / N_ITER)
            for i in range(N_AGENTS):
                for j in range(dim):
                    r1, r2 = rng.random(), rng.random()
                    A1 = 2*a*r1 - a; C1 = 2*r2
                    D_alpha = abs(C1*alpha_pos[j] - pos[i][j])
                    X1 = alpha_pos[j] - A1*D_alpha

                    r1, r2 = rng.random(), rng.random()
                    A2 = 2*a*r1 - a; C2 = 2*r2
                    D_beta = abs(C2*beta_pos[j] - pos[i][j])
                    X2 = beta_pos[j] - A2*D_beta

                    r1, r2 = rng.random(), rng.random()
                    A3 = 2*a*r1 - a; C3 = 2*r2
                    D_delta = abs(C3*delta_pos[j] - pos[i][j])
                    X3 = delta_pos[j] - A3*D_delta

                    pos[i][j] = np.clip((X1+X2+X3)/3,
                                        BOUNDS_LOW[j], BOUNDS_HIGH[j])

        best_n   = max(10, int(round(alpha_pos[0])))
        best_d   = max(3,  int(round(alpha_pos[1])))
        self.best_params = {"n_estimators": best_n, "max_depth": best_d}

        self.model = RandomForestClassifier(
            n_estimators=best_n, max_depth=best_d,
            class_weight="balanced", random_state=SEED, n_jobs=-1
        )
        self.model.fit(X, y)
        print(f"    GWO best params: n_est={best_n}, depth={best_d}, loss={alpha_score:.4f}")

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict(self._prepare(df))
