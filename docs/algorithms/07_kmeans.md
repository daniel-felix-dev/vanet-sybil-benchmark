# Dynamic k-Means Clustering Detector

**Source:** [Gideon-Adele/Dynamic-k-means-Clustering](https://github.com/Gideon-Adele/Dynamic-k-means-Clustering) (OMNeT++, C++)
**Reimplementation:** `detectors/kmeans_detector.py`
**Category:** Unsupervised clustering
**Requires labeled data:** No

---

## 1. Objective

Group vehicles by their aggregate behavioral profile using k-Means clustering. Clusters that are anomalously small or whose centroid speed deviates significantly from the global mean are flagged as Sybil. The hypothesis is that Sybil vehicles form behaviorally distinct clusters separable from legitimate vehicle groups.

---

## 2. Theoretical Background

### 2.1 k-Means Clustering

k-Means (MacQueen, 1967) partitions a dataset into k clusters by minimizing the sum of squared distances from each point to its assigned cluster centroid:

```
minimize: sum_{j=1}^{k} sum_{x in C_j} ||x - mu_j||^2
```

where C_j is the set of points assigned to cluster j and mu_j is the centroid of cluster j.

The algorithm alternates between:
1. **Assignment step:** assign each point to its nearest centroid.
2. **Update step:** recompute centroids as the mean of assigned points.

It converges when assignments no longer change. The standard initialization (k-means++) places initial centroids with probability proportional to distance, improving convergence.

### 2.2 Dynamic k

Rather than fixing k, the algorithm computes k dynamically:

```
k = floor(sqrt(V / 2))
```

where V is the number of unique vehicles. For V = 100 vehicles, k = 7. This heuristic is motivated by the observation that the optimal k for cluster separation tends to scale as the square root of the number of data points.

---

## 3. Feature Aggregation

Before clustering, each vehicle's records are aggregated into a single feature vector representing its behavioral profile over the entire simulation:

| Aggregated Feature | Computation |
|---|---|
| `mean_x` | mean(x) across all active steps |
| `mean_y` | mean(y) across all active steps |
| `mean_speed` | mean(speed) across all active steps |
| `std_speed` | std(speed) across all active steps |
| `mean_accel` | mean(|accel|) across all active steps |
| `mean_n_neighbors` | mean(n_neighbors) across all active steps |

All 6 features are standardized (zero mean, unit variance) before clustering.

---

## 4. Flagging Criteria

A cluster C_j is flagged if either condition holds:

1. **Small cluster:** |C_j| < MIN_CLUSTER_SIZE = 3

```
flag if |C_j| < 3
```

2. **Anomalous centroid speed:**

```
z_j = |mean_speed(C_j) - global_mean_speed| / global_std_speed
flag if z_j > SPEED_ANOMALY_Z = 2.0
```

All vehicles in a flagged cluster are classified as Sybil.

---

## 5. Why k-Means Fails: Mathematical Proof

The Sybil attack model injects Gaussian noise with mean zero into speed values:

```
speed_sybil(t) = speed_true(t) + epsilon(t),   epsilon ~ N(0, 64)
```

Therefore, the expected speed of a Sybil vehicle is:

```
E[speed_sybil] = E[speed_true] + E[epsilon] = E[speed_legit] + 0 = E[speed_legit]
```

The expected mean speed of a Sybil vehicle equals the expected mean speed of a legitimate vehicle. Consequently:

```
E[mean_speed(C_sybil)] approximately equal to E[mean_speed(C_legit)]
```

The z-score of a Sybil-heavy cluster's centroid:

```
z = |E[mean_speed(C_sybil)] - global_mean| / global_std approximately 0
```

The speed anomaly criterion never fires because Sybil cluster centroids are not anomalously fast or slow -- they are indistinguishable from legitimate cluster centroids in mean speed.

The small-cluster criterion also fails: k-Means assigns vehicles to clusters by proximity in the 6-dimensional feature space. Sybil vehicles (same mean position as their attacker, slightly elevated speed std) are not geometrically concentrated in a way that reliably produces small clusters. The clustering assignment is essentially random with respect to the Sybil label.

**Result:** F1 = 0.000 at all 8 tested sybil rates.

---

## 6. Algorithm Description

```
Procedure kMeans.fit(D):
    // Aggregate per-vehicle profiles
    for each vehicle v:
        profile_v = (mean_x, mean_y, mean_speed, std_speed,
                     mean_accel, mean_n_neighbors)

    // Standardize
    scaler = StandardScaler().fit(profiles)
    X = scaler.transform(profiles)

    // Cluster
    k = floor(sqrt(V / 2))
    labels = KMeans(n_clusters=k, n_init=10).fit_predict(X)

    // Compute global speed statistics
    global_mean = mean(mean_speed for all vehicles)
    global_std  = std(mean_speed for all vehicles)

    // Flag anomalous clusters
    flagged = empty set
    for each cluster j:
        members = {v : labels[v] == j}
        if |members| < MIN_CLUSTER_SIZE:
            flagged.update(members)
        else:
            centroid_speed = mean(mean_speed for v in members)
            z = |centroid_speed - global_mean| / global_std
            if z > SPEED_ANOMALY_Z:
                flagged.update(members)

    return flagged
```

---

## 7. Complexity Analysis

**Aggregation:**
- One pass over all records to compute per-vehicle statistics: O(N)

**Standardization:**
- Fit and transform V vehicle profiles with F_k = 6 features: O(V * F_k)

**k-Means clustering:**
- Each of n_init = 10 runs: O(k * V * F_k * iterations)
- Iterations until convergence is typically O(1/epsilon) for some convergence tolerance epsilon
- Total: O(n_init * k * V * F_k * iterations)
- With k = 7, V = 100, F_k = 6, iterations ~= 20: O(10 * 7 * 100 * 6 * 20) = O(84,000)

**Flagging:**
- One pass over cluster assignments: O(V)

**Total fit:** O(N + V * F_k * k * n_init)

**Total prediction:** O(N) -- one set membership check per record.

**Space:** O(k * F_k) for centroids.

**Big-O:** O(N) dominated by the aggregation step for large N. The k-Means step is O(V * ...) which is much smaller than O(N) since V << N (each vehicle has ~500 records).

---

## 8. Results

| Sybil Rate | F1 | Precision | Recall | Specificity |
|---|---|---|---|---|
| All rates | **0.000** | **0.000** | **0.000** | **0.998** |

F1 = 0.000 at every tested sybil rate. The very high specificity (0.998) confirms that the detector rarely produces false positives -- it simply fails to detect any Sybil vehicles at all.

---

## 9. When k-Means Could Work

The detector would be effective if Sybil vehicles formed behaviorally distinct clusters:

- **Geographic isolation:** if all Sybil vehicles enter from one corner of the grid, their mean position would be geographically distinct, forming a small spatially isolated cluster. The uniform 6x6 grid prevents this.
- **Speed-biased attack model:** if the attack injected a non-zero mean bias (e.g., speed_sybil = speed_true + 10), the mean speed of Sybil clusters would be elevated and detectable by the z-score criterion.
- **Fewer Sybil identities per attacker:** if each attacker controlled only 1-2 Sybil identities, those vehicles might form singleton clusters (size 1 < MIN_CLUSTER_SIZE = 3), triggering the small-cluster criterion.

None of these conditions hold in the current benchmark.

---

## 10. References

MacQueen, J. (1967). Some methods for classification and analysis of multivariate observations. *Proceedings of the 5th Berkeley Symposium on Mathematical Statistics and Probability*, vol. 1, pp. 281-297.

Gideon-Adele (2024). *Dynamic-k-means-Clustering*. GitHub repository. https://github.com/Gideon-Adele/Dynamic-k-means-Clustering

Arthur, D. and Vassilvitskii, S. (2007). k-means++: the advantages of careful seeding. *Proceedings of the 18th Annual ACM-SIAM Symposium on Discrete Algorithms (SODA)*, pp. 1027-1035.
