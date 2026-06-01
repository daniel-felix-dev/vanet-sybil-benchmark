# Algorithm Overview and Comparative Analysis

## 1. Introduction

Seven Sybil detection algorithms are evaluated in this benchmark. They span four distinct algorithmic paradigms: statistical thresholding, infrastructure-based position verification, probabilistic trust modeling, and machine learning. This document provides a high-level comparison across all seven before the individual algorithm documents present full technical details.

---

## 2. Paradigm Classification

| Algorithm | Paradigm | Core Signal | Labeled Data | Online Capable |
|---|---|---|---|---|
| IQR Speed Threshold | Statistical | Speed distribution | No | Yes |
| RSU Position Verification | Positional | Proximity inconsistency | No | Yes |
| TASER Bayesian Trust | Probabilistic | Speed consistency + trust | No | Yes |
| Random Forest | Supervised ML | All 8 features | Yes | No (batch) |
| Random Forest + GWO | Supervised ML + metaheuristic | All 8 features | Yes | No (batch) |
| LSTM | Deep learning | Temporal speed sequence | Yes | No (batch) |
| Dynamic k-Means | Unsupervised ML | Behavioral profile | No | No (batch) |

---

## 3. Summary of Results (OOS)

All F1 values are out-of-sample. Supervised detectors use vehicle-level splits to prevent data leakage (see [docs/evaluation/methodology.md](../evaluation/methodology.md)).

| Detector | F1 (mean) | F1 (std) | Precision | Recall | Specificity | Time (s) | AUC |
|---|---|---|---|---|---|---|---|
| TASER | **0.999** | 0.004 | **1.000** | 0.997 | **1.000** | **0.64** | **1.000** |
| RF + GWO | 0.893 | 0.099 | 0.938 | 0.879 | 0.978 | 98 | -- |
| Random Forest | 0.882 | 0.128 | 0.901 | **0.875** | 0.981 | 2.7 | 0.9999 |
| LSTM | 0.507 | 0.437 | 0.536 | 0.531 | 0.941 | 16.8 | 0.865 |
| IQR | 0.391 | 0.289 | 0.290 | **1.000** | 0.125 | **0.06** | -- |
| RSU | 0.021 | 0.060 | 0.045 | 0.014 | 0.991 | 10.2 | -- |
| k-Means | 0.000 | 0.000 | 0.000 | 0.000 | 0.997 | 0.33 | -- |

F1 std = standard deviation across 8 sybil rates. AUC is the mean ROC-AUC across sybil rates 10%-40% (only for detectors with continuous probability output).

---

## 4. Complexity Summary

| Detector | Fit complexity | Space | Prediction |
|---|---|---|---|
| IQR | O(N log N) | O(1) -- 2 floats | O(N) |
| RSU | O(T * R * V^2) | O(V^2) | O(N) |
| TASER | O(N log N) | O(V) | O(N) |
| Random Forest (OOS CV) | O(5 * E * N * sqrt(F) * D * log N) | O(E * 2^D) | O(N * E * D) |
| RF + GWO (OOS CV) | O(A*I*3 + 5) * O(E * N * sqrt(F) * D * log N) | Same as RF | Same as RF |
| LSTM | O(epochs * N * L * H^2) | O(N * L * F) | O(V * L * H^2) |
| k-Means | O(N + V * F_k * k * n_init) | O(k * F_k) | O(N) |

Variables: N = total records, V = vehicles, T = time steps, R = RSUs, E = 100 trees, F = 8 features, D = 10 max depth, A = 6 GWO agents, I = 10 iterations, L = 50 sequence length, H = 64 LSTM units, F_k = 6 aggregated features, k = approx. 7 clusters.

---

## 5. Pareto Frontier

In the F1 vs training-time space, two detectors are Pareto-optimal: no other detector outperforms them on both dimensions simultaneously.

**TASER (F1=0.999, time=0.64s):** The fastest competitive detector AND the most accurate. No other detector has both higher F1 and lower training time.

**IQR (F1=0.391, time=0.06s):** The absolute fastest detector. While its F1 is low, it is faster than TASER and cannot be beaten on speed by any detector with higher F1.

All other detectors are dominated:
- Random Forest (F1=0.882, 2.7s): TASER has both higher F1 and lower time.
- RF+GWO (F1=0.893, 98s): TASER has both higher F1 and lower time.
- LSTM (F1=0.507, 16.8s): TASER and RF both dominate it.
- RSU (F1=0.021, 10.2s): dominated by all competitive detectors.
- k-Means (F1=0.000): dominated by all others.

---

## 6. Design Decisions and Trade-offs

### Why these 7 algorithms?

The algorithms were selected to cover the space of approaches used in the VANET Sybil detection literature: one from each of the four paradigms (statistical, positional, probabilistic, supervised ML), plus a clustering baseline and a meta-optimized variant of the best ML approach. Each algorithm originates from an independent open-source repository, so the benchmark measures the generalization of published approaches rather than in-house optimizations.

### Why is in-sample evaluation a problem?

A detector trained and evaluated on the same vehicle records can memorize per-vehicle speed patterns at training time and recognize them at evaluation time without learning any generalizable rule. The Random Forest demonstrated this: in-sample F1 = 0.987 vs. OOS F1 = 0.882 (a 10.7% overestimate). See [docs/evaluation/methodology.md](../evaluation/methodology.md) for a formal definition of data leakage and the vehicle-level splitting protocol used to prevent it.

### Why does GWO not significantly outperform RF?

The GWO hyperparameter search evaluates only 60 candidate solutions (6 agents x 10 iterations) in a space of 190 x 18 = 3,420 possible (n_estimators, max_depth) combinations. With scikit-learn's well-tuned defaults already at reasonable values, the limited search fails to consistently identify a better configuration. The Wilcoxon signed-rank test gives p = 0.640 (not significant at alpha = 0.05) for the RF vs. GWO comparison.

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
