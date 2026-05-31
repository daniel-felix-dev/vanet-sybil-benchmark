"""
Detector 7 — Dynamic k-means Clustering (port of Gideon-Adele/Dynamic-k-means-Clustering)

Clusters vehicles by their mean (x, y, speed) profile.
Clusters that are small (fewer than MIN_CLUSTER_SIZE legitimate-looking nodes)
and whose centroid speed is anomalous are flagged as Sybil.

Unsupervised — no labels used in fit().
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from .base_detector import BaseDetector

CLUSTER_FEATURES = ["mean_x", "mean_y", "mean_speed",
                    "std_speed", "mean_accel", "mean_n_neighbors"]
MIN_CLUSTER_SIZE = 3   # clusters smaller than this → flag all members
SPEED_ANOMALY_Z  = 2.0 # z-score threshold for anomalous cluster centroid speed


class KMeansDetector(BaseDetector):
    name = "Dynamic k-Means"

    def __init__(self, n_clusters: int = None, seed: int = 42):
        self.n_clusters  = n_clusters
        self.seed        = seed
        self._sybil_ids  = set()

    def fit(self, df: pd.DataFrame):
        # Aggregate per-vehicle statistics
        agg = df.groupby("vehicle_id").agg(
            mean_x=("x", "mean"),
            mean_y=("y", "mean"),
            mean_speed=("speed", "mean"),
            std_speed=("speed", "std"),
            mean_accel=("accel", "mean"),
            mean_n_neighbors=("n_neighbors", "mean"),
        ).fillna(0).reset_index()

        n_veh = len(agg)
        k = self.n_clusters or max(2, int(np.sqrt(n_veh / 2)))

        scaler = StandardScaler()
        X = scaler.fit_transform(agg[CLUSTER_FEATURES].values)

        km = KMeans(n_clusters=k, random_state=self.seed, n_init=10)
        labels = km.fit_predict(X)
        agg["cluster"] = labels

        # Compute cluster-level stats for anomaly detection
        cluster_stats = agg.groupby("cluster").agg(
            size=("vehicle_id", "count"),
            centroid_speed=("mean_speed", "mean"),
        )
        global_mean_speed = agg["mean_speed"].mean()
        global_std_speed  = agg["mean_speed"].std() + 1e-9

        self._sybil_ids = set()
        for cl, row in cluster_stats.iterrows():
            z = abs(row["centroid_speed"] - global_mean_speed) / global_std_speed
            small = row["size"] < MIN_CLUSTER_SIZE
            anomalous_speed = z > SPEED_ANOMALY_Z
            if small or anomalous_speed:
                flagged = agg[agg["cluster"] == cl]["vehicle_id"].tolist()
                self._sybil_ids.update(flagged)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (df["vehicle_id"].isin(self._sybil_ids)).astype(int).values
