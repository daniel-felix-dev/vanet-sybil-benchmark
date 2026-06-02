# Detector Reference

All detectors share the same interface: `fit(df)` trains on the full dataset, `predict(df)` returns a binary array, `evaluate(df)` returns a metrics dict. Supervised detectors use vehicle-level out-of-sample splits (5-fold CV for RF, 80/20 for LSTM) to prevent data leakage.

---

## IQR Speed Threshold
**Source:** [MohammedSuratwala/SybilDetection](https://github.com/MohammedSuratwala/SybilDetection)

Flags vehicles with at least one speed reading below the lower Tukey fence:
`fence = Q1 - 1.5 × IQR`

No labeled data required. Recall = 1.000 at all rates; specificity ≈ 0 below 35% because the fence is positive (~6.2 m/s at 10%), which also flags legitimate vehicles that stop at intersections.

---

## RSU Position Verification
**Source:** [karthik-047/Detecting-Sybil-Attacks-in-VANETs](https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs)

20 RSUs at fixed positions detect vehicle pairs seen by the same RSU but > 150 m apart (min 5 events to confirm). Designed for **split-position attacks** (one device claiming multiple distinct locations). Fails on co-location attacks because all Sybil IDs share the same position (distance ≈ 0 < 150 m).

Results: F1 = 0.012 (co-location) → F1 = 0.835 (split-position).

---

## TASER Bayesian Trust
**Source:** [morton-t/VANET-Simulations](https://github.com/morton-t/VANET-Simulations)

Per-vehicle trust score updated each beacon:
- Consistent beacon: `T ← T + α(1 − T)` with α = 0.01
- Anomalous beacon: `T ← T(1 − β)` with β = 0.10

Anomaly condition: speed > 19.4 m/s or |Δspeed| > 5.6 m/s. Flag if T < 0.15.

Detection bound: `n* = ln(0.15/0.5) / ln(0.90) = 11.43` → any Sybil node injecting anomalous beacons is flagged within **12 steps**.

Results: F1 = 0.9997, std = 0.0006, Precision = 1.000 at all rates. Robust to both attack models.

---

## Random Forest
**Source:** [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet)

100 trees, max_depth = 10, trained on 8 features: speed, acceleration, heading angle, x, y, neighbors within 150 m, min/mean RSU distance.

Evaluated with 5-fold CV split by vehicle\_id (no leakage). In-sample estimate ≈ 0.987 vs OOS = 0.895 - a 9.3 percentage-point gap caused by data leakage without vehicle-level splitting.

---

## LSTM
**Source:** [SaiKumar-1608 Dual-Layer Framework](https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL)

Two-layer LSTM (64→32 units, 0.3 dropout), sequence length 50, same 8 features as RF. Evaluated 80/20 vehicle-level split (5-fold CV not used: 5 training cycles × 20 epochs × 8 rates would be computationally prohibitive in multi-seed design).

F1 ≈ 0 at 5–15% (positive fraction below 12%); improves significantly at 20% (21% positive records).

---

## Dynamic k-Means (Improved)
**Source:** [Gideon-Adele/Dynamic-k-means-Clustering](https://github.com/Gideon-Adele/Dynamic-k-means-Clustering)

Aggregates 8 behavioral features per vehicle (mean/std of x, y, speed, acceleration, neighbor count) and clusters with k = ⌊√(V/2)⌋. A cluster is flagged if any of three criteria hold:

1. **Small cluster** - fewer than 3 members
2. **High speed variance** - centroid std_speed z-score > 2.0 (via MAD)
   Rationale: Gaussian noise (σ = 8) raises std_speed to ≈ 8 m/s vs ≈ 2–4 m/s for legitimate vehicles
3. **Low position variance** - centroid pos_std z-score < −2.0 (via MAD)
   Rationale: split-position Sybil IDs are fixed near RSU centers (near-zero movement)

Uses **median + MAD** instead of mean + std to resist contamination when many Sybil vehicles are present (robust to up to ≈40% positive fraction).

Results: F1 = 0.9795 (co-location), F1 = 0.923 (split-position). Previous version (mean-speed z-score) gave F1 = 0.000.
