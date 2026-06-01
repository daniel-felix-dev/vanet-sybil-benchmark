# Algorithm Overview and Comparative Analysis

## 1. Introduction

Six Sybil detection algorithms are evaluated in this multi-seed benchmark. They span four distinct algorithmic paradigms: statistical thresholding, infrastructure-based position verification, probabilistic trust modeling, and machine learning. This document provides a high-level comparison across all six before the individual algorithm documents present full technical details.

---

## 2. Paradigm Classification

| Algorithm | Paradigm | Core Signal | Labeled Data | Online Capable |
|---|---|---|---|---|
| IQR Speed Threshold | Statistical | Speed distribution | No | Yes |
| RSU Position Verification | Positional | Proximity inconsistency | No | Yes |
| TASER Bayesian Trust | Probabilistic | Speed consistency + trust | No | Yes |
| Random Forest | Supervised ML | All 8 features | Yes | No (batch) |
| LSTM | Deep learning | Temporal speed sequence | Yes | No (batch) |
| Dynamic k-Means | Unsupervised ML | Behavioral profile | No | No (batch) |

**Note on GWO:** Random Forest + Grey Wolf Optimizer was evaluated in a single-seed run. Results showed no statistically significant improvement over the RF baseline (Wilcoxon p=0.640, Cohen's d=0.18 -- negligible). It was excluded from the multi-seed experiment to avoid ~8 hours of computation for an unconfirmed benefit. The implementation is preserved in `detectors/gwo_rf_detector.py`.

---

## 3. Summary of Results (OOS)

All F1 values are out-of-sample. Supervised detectors use vehicle-level splits to prevent data leakage (see [docs/evaluation/methodology.md](../evaluation/methodology.md)).

Values are means over 5 seeds x 8 rates = 40 runs. F1 std = standard deviation across all 40 runs.

| Detector | F1 (mean) | F1 (std) | Precision | Recall | Specificity | Time (s) | AUC |
|---|---|---|---|---|---|---|---|
| TASER | **0.9997** | **0.0006** | **1.0000** | 0.9995 | **1.0000** | **0.69** | **1.0000** |
| Random Forest | 0.8945 | 0.0242 | 0.9156 | **0.8856** | 0.9802 | 2.78 | 0.9999 |
| LSTM | 0.4821 | 0.2575 | 0.5031 | 0.5606 | 0.9074 | 16.7 | 0.865 |
| IQR | 0.4007 | 0.0326 | 0.3046 | **1.0000** | 0.1500 | **0.05** | -- |
| RSU | 0.0123 | 0.0276 | 0.0341 | 0.0076 | 0.9899 | 10.6 | -- |
| k-Means | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9978 | 0.14 | -- |

---

## 4. Complexity Summary

| Detector | Fit complexity | Space | Prediction |
|---|---|---|---|
| IQR | O(N log N) | O(1) -- 2 floats | O(N) |
| RSU | O(T * R * V^2) | O(V^2) | O(N) |
| TASER | O(N log N) | O(V) | O(N) |
| Random Forest (OOS CV) | O(5 * E * N * sqrt(F) * D * log N) | O(E * 2^D) | O(N * E * D) |
| LSTM | O(epochs * N * L * H^2) | O(N * L * F) | O(V * L * H^2) |
| k-Means | O(N + V * F_k * k * n_init) | O(k * F_k) | O(N) |

Variables: N = total records, V = vehicles, T = time steps, R = RSUs, E = 100 trees, F = 8 features, D = 10 max depth, L = 50 sequence length, H = 64 LSTM units, F_k = 6 aggregated features, k = approx. 7 clusters.

---

## 5. Pareto Frontier

In the F1 vs training-time space, two detectors are Pareto-optimal: no other detector outperforms them on both dimensions simultaneously.

**TASER (F1=0.999, time=0.64s):** The fastest competitive detector AND the most accurate. No other detector has both higher F1 and lower training time.

**IQR (F1=0.401, time=0.05s):** The absolute fastest detector. While its F1 is moderate, it is faster than TASER and cannot be beaten on speed by any detector with higher F1.

All other detectors are dominated:
- Random Forest (F1=0.895, 2.78s): TASER has both higher F1 and lower time.
- LSTM (F1=0.507, 16.8s): TASER and RF both dominate it.
- RSU (F1=0.012, 10.6s): dominated by all competitive detectors.
- k-Means (F1=0.000): dominated by all others.

---

## 6. Design Decisions and Trade-offs

### Why these 6 algorithms?

The algorithms were selected to cover the space of approaches used in the VANET Sybil detection literature: one from each of the four paradigms (statistical, positional, probabilistic, supervised ML), plus a clustering baseline and a meta-optimized variant of the best ML approach. Each algorithm originates from an independent open-source repository, so the benchmark measures the generalization of published approaches rather than in-house optimizations.

### Why is in-sample evaluation a problem?

A detector trained and evaluated on the same vehicle records can memorize per-vehicle speed patterns at training time and recognize them at evaluation time without learning any generalizable rule. The Random Forest demonstrated this: in-sample F1 approximately 0.987 vs. OOS F1 = 0.895 (multi-seed, a ~9% overestimate). See [docs/evaluation/methodology.md](../evaluation/methodology.md) for a formal definition of data leakage and the vehicle-level splitting protocol used to prevent it.

---

## 7. Scenario Recommendations

For deployment recommendations backed by computed utility functions, see [docs/evaluation/results.md](../evaluation/results.md). The brief summary:

| Scenario | Recommended | Reason |
|---|---|---|
| General purpose | TASER | Best F1 + fastest + no training data required |
| Zero false positives | TASER | Only detector with Precision = 1.000 at all rates |
| Minimal compute | IQR | 0.06 s, 2 floats of storage |
| Early detection (5-10% sybil) | TASER | F1 = 1.000 at 5% and 10%, 12-beacon convergence |
| High sybil rate (30%+) | TASER | F1 >= 0.989 at 30-40%, Precision = 1.000 |
