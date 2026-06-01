# Statistical Analysis

## 1. Overview

This document presents all statistical tests performed on the benchmark results. Tests are ordered from global (comparing all detectors) to specific (pairwise comparisons and analytical proofs).

Two data sources are used:
- `results/metrics/benchmark_results.csv`: aggregated results, one row per (detector, rate), mean over 5 seeds
- `results/metrics/multi_seed_raw.csv`: raw results, one row per (detector, rate, seed), 240 rows total

Statistical tests (Kruskal-Wallis, Wilcoxon, bootstrap) use the raw file with n=40 observations per detector (5 seeds x 8 rates). The auto-generated version (from current data) is in `analysis/statistical_proofs.md`.

**Note on GWO:** RF + Grey Wolf Optimizer was evaluated with single-seed (n=8). Wilcoxon p=0.640, Cohen's d=0.18 (negligible). It was excluded from the multi-seed experiment. Single-seed results are documented in `docs/algorithms/05_rf_gwo.md`.

---

## 2. Test 1: Global Comparison (Kruskal-Wallis)

**Purpose:** Determine whether all 6 detectors have the same underlying F1-Score distribution. If not, at least one pair differs.

**Test:** Kruskal-Wallis H-test (non-parametric one-way ANOVA). Chosen over standard ANOVA because normality cannot be assumed. Uses n=40 observations per group (5 seeds x 8 rates).

**Data:** F1-Score for each detector across all 40 observations (5 seeds x 8 rates).

**H0:** The 6 detectors have the same median F1-Score distribution.

**Result:**

```
H statistic = 193.13
p-value     = 0.000000
df          = 5
n per group = 40 (5 seeds x 8 sybil rates)
```

**Conclusion:** H0 is rejected at alpha = 0.001 (or any standard significance level). There is a statistically significant difference in F1-Score distributions among the 6 detectors.

**Interpretation:** This result justifies performing post-hoc pairwise comparisons. The benchmark does not merely show numerically different F1 values -- the differences are statistically significant.

---

## 3. Test 2: Pairwise Comparisons (Wilcoxon Signed-Rank)

**Purpose:** For specific pairs of detectors, determine whether one significantly outperforms the other.

**Test:** Wilcoxon signed-rank test on n=40 observations per detector (5 seeds x 8 sybil rates). The raw multi-seed data (`multi_seed_raw.csv`) is used so each (seed, rate) combination is an independent observation.

**Null hypothesis H0 (for each pair):** The two detectors have the same F1-Score distribution.

**Results (n=40 per group, 5 seeds x 8 rates):**

| Comparison | Direction | W stat | p-value | Reject H0 (alpha=0.05)? |
|---|---|---|---|---|
| TASER vs RF | TASER > RF at all 40 obs | 0.0 | 0.0000 | **Yes** |
| TASER vs LSTM | TASER > LSTM at all 40 obs | 0.0 | 0.0000 | **Yes** |
| TASER vs IQR | TASER > IQR at all 40 obs | 0.0 | 0.0000 | **Yes** |
| RF vs LSTM | RF > LSTM at most obs | ~47 | 0.0001 | **Yes** |

With n=40, all key comparisons reach statistical significance. W=0.0 for the first three comparisons means TASER outperforms the compared detector at every single one of the 40 (seed, rate) observations without exception.

**Note:** GWO was evaluated with single-seed (n=8). Results showed no significant benefit over RF (W=14.0, p=0.640). GWO is excluded from the multi-seed tests.

---

## 4. Test 3: Bootstrap Confidence Intervals

**Purpose:** Provide distributional estimates for the mean F1-Score that are not sensitive to normality assumptions.

**Method:** 10,000 bootstrap resamples of the n=40 F1 observations per detector (5 seeds x 8 rates). The 95% CI is the [2.5th, 97.5th] percentile of the bootstrap distribution of means.

**Results (n=40 per detector, 10,000 bootstrap resamples):**

| Detector | Mean F1 | 95% CI lower | 95% CI upper | CI width |
|---|---|---|---|---|
| TASER | 0.9997 | 0.9987 | 1.0000 | 0.0013 |
| Random Forest | 0.8945 | 0.8496 | 0.9329 | 0.0833 |
| LSTM | 0.4821 | 0.3588 | 0.6106 | 0.2518 |
| IQR | 0.4007 | 0.3569 | 0.4469 | 0.0900 |
| RSU | 0.0123 | 0.0000 | 0.0378 | 0.0378 |
| k-Means | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

**Interpretation:**

- TASER CI [0.999, 1.000] and RF CI [0.850, 0.933] have zero overlap. With n=40, the CIs are much tighter than with n=8, making the difference statistically certain.
- LSTM CI [0.359, 0.611] reflects the bimodal behavior (F1=0 at 5-10%, F1=0.7+ above 20%).
- IQR CI [0.357, 0.447] is relatively narrow, confirming that IQR's moderate performance is consistent across seeds (not a seed-specific artifact).

---

## 5. Test 4: Effect Sizes (Cohen's d)

**Purpose:** Quantify the practical significance of differences between detector pairs, independent of sample size.

**Formula:**

```
d = (mean_A - mean_B) / pooled_std
pooled_std = sqrt(((n-1)*std_A^2 + (n-1)*std_B^2) / (2n - 2))
```

**Interpretation:** |d| < 0.2 = negligible, 0.2-0.5 = small, 0.5-0.8 = medium, > 0.8 = large.

**Results:**

| Comparison | Cohen's d | Magnitude |
|---|---|---|
| TASER vs RF | +1.54 | **Large** |
| TASER vs LSTM | +1.10 | **Large** |
| TASER vs IQR | +2.15 | **Large** |
| RF vs LSTM | +0.87 | **Large** |
| RF vs IQR | +1.20 | **Large** |
| RF vs RSU | +18.5 | **Large** (extreme) |
| LSTM vs IQR | +0.54 | Medium |
| LSTM vs RSU | +1.94 | **Large** |

All comparisons involving the 6 benchmark detectors show large or extreme effect sizes, confirming that the observed differences are not due to sampling noise.

---

## 6. Test 5: F1 Trend (Linear Regression)

**Purpose:** Determine whether each detector's F1-Score systematically increases or decreases as the sybil rate increases.

**Model:** F1 = a * sybil_rate + b, fitted by ordinary least squares.

**Results:**

| Detector | Slope (F1/%sybil) | R-squared | p-value | Trend |
|---|---|---|---|---|
| TASER | -0.0017 | 0.40 | 0.09 | Flat (convergence property) |
| Random Forest | +0.0101 | 0.82 | 0.003 | **Improves** |
| LSTM | +0.0227 | 0.65 | 0.016 | **Improves** |
| IQR | +0.0319 | 0.95 | 0.000 | **Improves strongly** |
| RSU | +0.0002 | 0.002 | 0.91 | Flat |
| k-Means | 0.0000 | 0.000 | -- | Flat at zero |

**Interpretation:**

- Supervised ML detectors (RF, LSTM) and IQR all improve as sybil rate increases. Higher rates provide more positive examples for training and shift the IQR fence to a more discriminative position.
- TASER shows no significant trend (p = 0.09): the 12-beacon convergence guarantee ensures detection regardless of how many Sybil nodes are present.
- RSU shows no trend because its failure is structural (model incompatibility), not rate-dependent.

---

## 7. Test 6: TASER Convergence (Analytical Proof)

**Claim:** A Sybil vehicle emitting anomalous beacons is detectable in at most 12 beacons.

**Proof:**

Trust update for anomalous beacon: T_{n+1} = T_n * (1 - beta)

Closed form: T_n = T_0 * (1 - beta)^n

Setting T_n = lambda (detection threshold) and solving for n:

```
lambda = T_0 * (1 - beta)^n
n = ln(lambda / T_0) / ln(1 - beta)
```

With T_0=0.5, beta=0.10, lambda=0.15:

```
n = ln(0.15/0.5) / ln(0.90)
  = ln(0.30)    / ln(0.90)
  = -1.2040     / -0.10536
  = 11.43
```

Detection step = ceil(11.43) = **12 beacons**.

This proof is verified empirically: at all sybil rates 5% through 35%, TASER achieves Recall = 1.000 and Precision = 1.000, meaning every Sybil vehicle is detected with no false positives. At 40%, Recall = 0.979 (a small number of Sybil vehicles survive because they happen to emit a few legitimate-speed beacons during the 12-step convergence window, temporarily recovering trust above lambda).

---

## 8. Test 7: IQR Fence Analysis

**Claim:** At sybil rates below 35%, the IQR lower fence falls below the minimum observable speed, making it non-discriminative.

**Derivation from actual dataset distributions:**

| Sybil Rate | Q1 | Q3 | IQR | Fence = Q1 - 1.5*IQR | Min speed | Fence discriminates? |
|---|---|---|---|---|---|---|
| 5% | ~2.4 | ~11.7 | ~9.3 | ~-11.5 | 0.0 | No |
| 10% | ~2.4 | ~11.7 | ~9.3 | ~-11.5 | 0.0 | No |
| 20% | ~2.2 | ~11.5 | ~9.3 | ~-11.8 | ~-5.2 | No |
| 40% | ~0.3 | ~10.1 | ~9.8 | ~-14.4 | ~-31.2 | **Yes** |

At 40% sybil rate, a substantial fraction of Sybil speed readings (generated with sigma=8 added to true speed) take very negative values. These shift Q1 far into negative territory, raising the fence above -31.2 m/s. Legitimate vehicles (speed >= 0) are above the fence; many Sybil vehicles with extreme negative speeds are below it.

**Why recall = 1.000 at ALL rates despite the non-discriminative fence:**

At rates below 40%, the IQR implementation flags vehicles whose minimum speed is below the fence, not vehicles whose mean speed is below the fence. When the fence is -11.5 m/s and the minimum legitimate speed is 0 m/s, no vehicle is below the fence, and the flagging logic triggers via a different code path that marks all vehicles as Sybil. This produces Recall = 1.000 (all Sybil caught) at the cost of Specificity = 0.000 (all legitimate also flagged).

---

## 9. Test 8: Precision Stability (Coefficient of Variation)

**Claim:** TASER's Precision = 1.000 at every sybil rate is structural, not coincidental.

**Analysis:** The coefficient of variation (CV = std/mean) of Precision across 8 sybil rates:

| Detector | Precision values (5% to 40%) | Mean | Std | CV |
|---|---|---|---|---|
| TASER | 1.000 at all 8 rates | 1.000 | 0.000 | **0.000** |
| Random Forest | varies 0.724 to 0.995 | 0.916 | 0.079 | 0.086 |
| LSTM | varies 0.000 to 1.000 | 0.503 | 0.479 | 0.953 |
| IQR | varies 0.057 to 1.000 | 0.305 | 0.306 | 1.003 |
| RSU | varies 0.000 to 0.363 | 0.034 | 0.128 | 3.76 |

CV = 0.000 for TASER is a mathematical consequence of the update rule: a legitimate vehicle with T_0 = 0.5 that emits only consistent beacons has T converging monotonically to 1.0. It never reaches lambda = 0.15 from above unless it emits anomalous beacons. Since legitimate vehicles in this simulation use the SUMO vType maxSpeed=13.89 m/s and the anomaly threshold is 13.89 * 1.4 = 19.45 m/s, legitimate vehicles will always emit beacons classified as consistent by TASER.

---

## 10. Test 9: Pareto Dominance

**Formal definition:** Detector A Pareto-dominates detector B if:

```
A.F1_mean >= B.F1_mean  AND  A.fit_time <= B.fit_time
with at least one strict inequality
```

**Results:**

| Detector | F1 mean | Fit time (s) | Dominated by | Pareto? |
|---|---|---|---|---|
| TASER | **0.9997** | 0.69 | None | **Yes** |
| IQR | 0.4007 | **0.05** | None | **Yes** |
| Random Forest | 0.8945 | 2.78 | TASER | No |
| LSTM | 0.4821 | 16.7 | TASER, RF | No |
| RSU | 0.0123 | 10.6 | TASER, RF, LSTM, IQR | No |
| k-Means | 0.0000 | 0.14 | All others with F1>0 | No |

TASER strictly dominates RF: F1 0.9997 > 0.8945 AND time 0.69s < 2.78s. Both conditions hold strictly over the 40-run multi-seed evaluation. There is no trade-off -- TASER is better than RF on both relevant dimensions with high statistical confidence.

---

## 11. Test 10 and 11: LSTM Class Imbalance and RF CV Variance

See `analysis/statistical_proofs.md` (auto-generated) for the full numerical tables for these tests. The key findings are summarized in [docs/evaluation/results.md](results.md) Section 4.4 and Section 4.2 respectively.
