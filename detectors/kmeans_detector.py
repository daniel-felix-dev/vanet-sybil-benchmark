"""
Detector 7: Dynamic k-means Clustering (port of Gideon-Adele/Dynamic-k-means-Clustering)

Improved version with three anomaly criteria:

  1. SMALL CLUSTER: clusters with fewer than MIN_CLUSTER_SIZE members.

  2. HIGH SPEED VARIANCE (z_std > STD_SPEED_Z):
     Sybil nodes inject Gaussian noise (sigma=8 m/s), dramatically increasing
     their within-vehicle speed standard deviation relative to legitimate drivers.
     E[std_speed_Sybil] ~ 8 m/s >> E[std_speed_legit] ~ 2-4 m/s.
     This criterion detects both co-location and split-position attack models.

  3. LOW POSITION VARIANCE (z_pos_std < -POS_STD_Z):
     In split-position mode, Sybil IDs are placed at fixed points around RSU
     centers, producing near-zero positional variance over time. Legitimate
     vehicles move continuously across the grid, producing much higher
     position std. This criterion specifically targets split-position attacks.

Unsupervised: no labels used in fit().
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from .base_detector import BaseDetector

CLUSTER_FEATURES = ["mean_x", "mean_y", "mean_speed",
                    "std_speed", "mean_accel", "mean_n_neighbors",
                    "std_x", "std_y"]

MIN_CLUSTER_SIZE = 3    # criterion 1: small cluster
STD_SPEED_Z      = 2.0  # criterion 2: z-score threshold for HIGH speed std
POS_STD_Z        = 2.0  # criterion 3: z-score threshold for LOW position std


class KMeansDetector(BaseDetector):
    name = "Dynamic k-Means"

    def __init__(self, n_clusters: int = None, seed: int = 42):
        self.n_clusters = n_clusters
        self.seed       = seed
        self._sybil_ids = set()

    def fit(self, df: pd.DataFrame):
        # Aggregate per-vehicle behavioral profile (8 features)
        agg = df.groupby("vehicle_id").agg(
            mean_x=("x", "mean"),
            mean_y=("y", "mean"),
            std_x=("x", "std"),           # position stability
            std_y=("y", "std"),
            mean_speed=("speed", "mean"),
            std_speed=("speed", "std"),   # speed variance (key Sybil signal)
            mean_accel=("accel", "mean"),
            mean_n_neighbors=("n_neighbors", "mean"),
        ).fillna(0).reset_index()

        n_veh = len(agg)
        k = self.n_clusters or max(2, int(np.sqrt(n_veh / 2)))

        scaler = StandardScaler()
        X = scaler.fit_transform(agg[CLUSTER_FEATURES].values)

        km = KMeans(n_clusters=k, random_state=self.seed, n_init=10)
        agg["cluster"] = km.fit_predict(X)

        # Global statistics using ROBUST estimators (median + MAD).
        # Mean/std would be contaminated when many Sybil vehicles are present
        # (e.g., at 40% sybil rate the global mean std_speed is elevated by
        # the Sybil majority). Median/MAD remain stable because the legitimate
        # population (80 vehicles) always outnumbers Sybil at tested rates.
        g_median_std = agg["std_speed"].median()
        g_mad_std    = (agg["std_speed"] - g_median_std).abs().median() + 1e-9

        agg["mean_pos_std"] = (agg["std_x"] + agg["std_y"]) / 2
        g_median_pos = agg["mean_pos_std"].median()
        g_mad_pos    = (agg["mean_pos_std"] - g_median_pos).abs().median() + 1e-9

        # Per-cluster statistics
        cluster_stats = agg.groupby("cluster").agg(
            size=("vehicle_id", "count"),
            centroid_std_speed=("std_speed", "mean"),
            centroid_pos_std=("mean_pos_std", "mean"),
        )

        self._sybil_ids = set()
        for cl, row in cluster_stats.iterrows():
            members = agg[agg["cluster"] == cl]["vehicle_id"].tolist()

            # Criterion 1: anomalously small cluster
            small = row["size"] < MIN_CLUSTER_SIZE

            # Criterion 2: anomalously HIGH speed std (robust z-score via MAD)
            z_std = (row["centroid_std_speed"] - g_median_std) / g_mad_std
            high_speed_var = z_std > STD_SPEED_Z

            # Criterion 3: anomalously LOW position std (split-position mode)
            z_pos = (row["centroid_pos_std"] - g_median_pos) / g_mad_pos
            low_pos_var = z_pos < -POS_STD_Z

            if small or high_speed_var or low_pos_var:
                self._sybil_ids.update(members)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (df["vehicle_id"].isin(self._sybil_ids)).astype(int).values
