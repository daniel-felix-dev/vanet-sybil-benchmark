# Statistical Analysis

## 1. Overview

This document presents all statistical tests performed on the benchmark results, including the computed values, interpretation, and limitations. Tests are ordered from global (comparing all detectors) to specific (pairwise comparisons and convergence proofs).

All tests use `results/metrics/benchmark_results.csv` as input. The auto-generated version of this document (with current data) is in `analysis/statistical_proofs.md`.

---

## 2. Test 1: Global Comparison (Kruskal-Wallis)

**Purpose:** Determine whether all 7 detectors have the same underlying F1-Score distribution. If not, at least one pair differs.

**Test:** Kruskal-Wallis H-test (non-parametric one-way ANOVA). Chosen over standard ANOVA because normality cannot be assumed with n=8 samples per group.

**Data:** F1-Score for each detector across 8 sybil rates (5% to 40%).

**H0:** The 7 detectors have the same median F1-Score distribution.

**Result:**

```
H statistic = 43.08
p-value     = 0.000000
df          = 6
```

**Conclusion:** H0 is rejected at alpha = 0.001 (or any standard significance level). There is a statistically significant difference in F1-Score distributions among the 7 detectors.

**Interpretation:** This result justifies performing post-hoc pairwise comparisons. The benchmark does not merely show numerically different F1 values -- the differences are statistically significant.

---

## 3. Test 2: Pairwise Comparisons (Wilcoxon Signed-Rank)

**Purpose:** For specific pairs of detectors, determine whether one significantly outperforms the other.

**Test:** Wilcoxon signed-rank test on n=8 paired observations (one per sybil rate). Paired because each rate represents the same experimental condition applied to both detectors.

**Null hypothesis H0 (for each pair):** The two detectors have the same F1-Score distribution.

**Results:**

| Comparison | Direction | W stat | p-value | Reject H0 (alpha=0.05)? |
|---|---|---|---|---|
| TASER vs RF | TASER > RF at all 8 rates | 0.0 | 0.0078 | **Yes** |
| TASER vs LSTM | TASER > LSTM at all 8 rates | 0.0 | 0.0078 | **Yes** |
| TASER vs IQR | TASER > IQR at all 8 rates | 0.0 | 0.0078 | **Yes** |
| RF vs RF+GWO | Mixed direction | 14.0 | 0.640 | No |
| RF vs LSTM | RF >= LSTM at most rates | 1.0 | 0.250 | No* |
| RF vs RSU | RF > RSU at all 8 rates | 0.0 | 0.125 | No** |
| LSTM vs RSU | LSTM >= RSU at most rates | 0.0 | 0.250 | No* |
| IQR vs RSU | IQR >= RSU at most rates | 0.0 | 0.125 | No** |

(*) Borderline: all differences in one direction but p > 0.05.

(**) Exact test: with n=8, the Wilcoxon test can achieve minimum p-value of 0.0078 only if all differences are in the same direction (W = 0). For near-trivial comparisons where one detector is always much better, the test may fail to reach p < 0.05 due to small n.

**Key findings:**

1. TASER significantly outperforms RF (p = 0.0078). The F1 difference is in the same direction at all 8 sybil rates -- TASER >= RF at every rate, strictly greater at all rates where both have non-trivial F1.

2. RF and RF+GWO are not significantly different (p = 0.640). The direction of the difference reverses across rates (RF sometimes better, GWO sometimes better), and the magnitude is small (mean difference 1.1%).

---

## 4. Test 3: Bootstrap Confidence Intervals

**Purpose:** Provide distributional estimates for the mean F1-Score that are not sensitive to normality assumptions.

**Method:** 10,000 bootstrap resamples of the n=8 F1 observations per detector. The 95% CI is the [2.5th, 97.5th] percentile of the bootstrap distribution of means.

**Results:**

| Detector | Mean F1 | 95% CI lower | 95% CI upper | CI width |
|---|---|---|---|---|
| TASER | 0.9987 | 0.9919 | 1.0000 | 0.0081 |
| RF + GWO | 0.8925 | 0.8231 | 0.9489 | 0.1258 |
| Random Forest | 0.8815 | 0.7901 | 0.9567 | 0.1666 |
| LSTM | 0.5072 | 0.2433 | 0.9866 | 0.7433 |
| IQR | 0.3911 | 0.1923 | 0.8368 | 0.6445 |
| RSU | 0.0213 | 0.0000 | 0.1279 | 0.1279 |
| k-Means | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

**Interpretation:**

- TASER CI [0.992, 1.000] and RF CI [0.790, 0.957] do not overlap. This provides strong evidence that the population means differ.
- RF CI [0.790, 0.957] and GWO CI [0.823, 0.949] overlap substantially. This confirms that the 1.1% mean difference is not statistically robust.
- LSTM has a wide CI [0.243, 0.987] due to high variance (F1 = 0 at three rates, F1 ~ 1 at three others).

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
| TASER vs RF | +1.09 | **Large** |
| TASER vs LSTM | +0.88 | **Large** |
| TASER vs IQR | +1.96 | **Large** |
| RF vs RF+GWO | +0.18 | Negligible |
| RF vs LSTM | +0.84 | **Large** |
| RF vs RSU | +15.49 | **Large** (extreme) |
| LSTM vs IQR | +0.54 | Medium |
| LSTM vs RSU | +1.94 | **Large** |

The negligible effect size (d = 0.18) for RF vs GWO confirms that the numerical difference between them has no practical importance.

---

## 6. Test 5: F1 Trend (Linear Regression)

**Purpose:** Determine whether each detector's F1-Score systematically increases or decreases as the sybil rate increases.

**Model:** F1 = a * sybil_rate + b, fitted by ordinary least squares.

**Results:**

| Detector | Slope (F1/%sybil) | R-squared | p-value | Trend |
|---|---|---|---|---|
| TASER | -0.0017 | 0.40 | 0.09 | Flat (slight decline at 40%) |
| RF + GWO | +0.0072 | 0.61 | 0.025 | **Improves** |
| Random Forest | +0.0101 | 0.82 | 0.003 | **Improves** |
| LSTM | +0.0227 | 0.65 | 0.016 | **Improves** |
| IQR | +0.0319 | 0.95 | 0.000 | **Improves strongly** |
| RSU | +0.0002 | 0.002 | 0.91 | Flat |
| k-Means | 0.0000 | 0.000 | -- | Flat at zero |

**Interpretation:**

- Supervised ML detectors (RF, GWO, LSTM) and IQR all improve as sybil rate increases. This is expected: higher sybil rates provide more positive examples for training (ML) and shift the IQR fence to a more discriminative position (IQR).
- TASER shows no significant trend (p = 0.09): its convergence property guarantees detection regardless of sybil rate.
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

| Detector | Precision values | Mean | Std | CV |
|---|---|---|---|---|
| TASER | 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0 | 1.000 | 0.000 | **0.000** |
| Random Forest | varies 0.724 to 0.995 | 0.901 | 0.079 | 0.087 |
| RF + GWO | varies 0.883 to 1.000 | 0.938 | 0.034 | 0.036 |
| LSTM | varies 0.000 to 1.000 | 0.536 | 0.479 | 0.893 |
| IQR | varies 0.057 to 1.000 | 0.290 | 0.306 | 1.054 |

CV = 0.000 for TASER is a mathematical consequence of the update rule: a legitimate vehicle with T_0 = 0.5 that emits only consistent beacons has T converging monotonically to 1.0. It never reaches lambda = 0.15 from above unless it emits anomalous beacons. Since legitimate vehicles in this simulation use the SUMO vType maxSpeed=13.89 m/s and the anomaly threshold is 13.89 * 1.4 = 19.45 m/s, legitimate vehicles will always emit beacons classified as consistent by TASER.

---

## 10. Test 9: Pareto Dominance

**Formal definition:** Detector A Pareto-dominates detector B if:

```
A.F1_mean >= B.F1_mean  AND  A.fit_time <= B.fit_time
with at least one strict inequality
```

**Results:**

| Detector | F1 mean | Fit time | Dominated by | Pareto? |
|---|---|---|---|---|
| TASER | 0.999 | 0.64 | None | **Yes** |
| IQR | 0.391 | 0.06 | None | **Yes** |
| Random Forest | 0.882 | 2.7 | TASER | No |
| RF + GWO | 0.893 | 98 | TASER | No |
| LSTM | 0.507 | 16.8 | TASER, RF | No |
| RSU | 0.021 | 10.2 | TASER, RF, GWO, LSTM, IQR | No |
| k-Means | 0.000 | 0.33 | All others with F1>0 | No |

TASER strictly dominates RF: F1 0.999 > 0.882 AND time 0.64s < 2.7s. Both conditions hold strictly. This means there is no trade-off: TASER is better than RF on every relevant dimension.

---

## 11. Test 10 and 11: LSTM Class Imbalance and RF CV Variance

See `analysis/statistical_proofs.md` (auto-generated) for the full numerical tables for these tests. The key findings are summarized in [docs/evaluation/results.md](results.md) Section 4.4 and Section 4.2 respectively.
