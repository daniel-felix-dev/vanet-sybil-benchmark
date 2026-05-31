# Scenario Recommendation Guide

Picking a detection algorithm is not just about the highest F1 score. What matters most depends on what you are actually trying to do: maybe you need near-instant results, or you cannot afford to accuse a legitimate vehicle, or you simply do not have labeled training data. Each of those priorities points to a different winner.

The recommendations here are computed using utility functions applied directly to the benchmark data. All F1 values are out-of-sample (OOS): Random Forest and RF+GWO use 5-fold cross-validation split by vehicle ID; LSTM uses an 80/20 vehicle-level split. No number here comes from evaluating a model on data it trained on. The raw calculations are in `math_justifications.txt`.

**How utility is calculated:**

```
U(detector, scenario) = sum( w_k * metric_k ) / sum( |w_k| )
```

Each scenario has a different set of weights reflecting what matters most. The detector with the highest U for a scenario is the recommendation.

**Important note on RF vs RF+GWO:** Wilcoxon signed-rank test between RF (OOS F1 mean = 0.882) and RF+GWO (OOS F1 mean = 0.893) gives p = 0.64, not significant at alpha = 0.05. Bootstrap 95% CI for RF is [0.79, 0.96] and for GWO is [0.82, 0.95] -- they overlap substantially. The 1.1% mean F1 difference cannot be statistically confirmed with n = 8 observations. GWO costs 36x more training time (98s vs 2.7s) for an unconfirmed benefit.

---

## Scenario 1: Detection must finish in under one second

**When this applies:** Traffic management systems, intersection controllers, emergency response coordination.

**Utility function:**
```
U = 0.4 * F1_mean + 0.3 * Precision_mean + 0.3 * (-ln(fit_time + 1))
```

**Ranking:**

| Detector | F1 (OOS) | Precision | Time (s) | Utility |
|---|---|---|---|---|
| **TASER** | **0.999** | **1.000** | 0.64 | **0.552** |
| Random Forest | 0.882 | 0.901 | 2.68 | 0.232 |
| IQR | 0.391 | 0.290 | 0.06 | 0.225 |
| RF + GWO | 0.893 | 0.938 | 98.3 | -0.741 |

**Recommendation: TASER**

With OOS-corrected numbers, TASER wins the real-time scenario outright. It achieves F1 = 0.999 in 0.64 seconds, which beats Random Forest (F1 = 0.882, 2.68s) on both quality and speed simultaneously. The in-sample evaluation of RF (F1 = 0.987) made it appear competitive, but proper OOS assessment reveals a 10% gap.

The efficiency score (F1 divided by ln(time + 1)) confirms this: TASER = 2.025, RF = 0.677, IQR = 6.45. IQR is faster but its F1 of 0.391 is too low for most real-time applications. TASER is the correct choice when both speed and quality matter.

RF + GWO is disqualified: 98 seconds violates any real-time constraint.

---

## Scenario 2: Zero false positives required

**When this applies:** Emergency vehicle authentication, autonomous intersection management.

**Utility function:**
```
U = 0.7 * Precision_mean + 0.3 * F1_mean
```

**Ranking:**

| Detector | Precision | F1 (OOS) | Utility |
|---|---|---|---|
| **TASER** | **1.000** | 0.999 | **1.000** |
| RF + GWO | 0.938 | 0.893 | 0.924 |
| Random Forest | 0.901 | 0.882 | 0.895 |
| LSTM | 0.536 | 0.507 | 0.527 |
| IQR | 0.290 | 0.391 | 0.320 |

**Recommendation: TASER**

TASER is the only detector with Precision = 1.000 at every tested attack intensity. The Bayesian update rule proves this structurally: a legitimate vehicle that always reports valid-range speeds will always increase its trust score and never fall below the detection threshold. The 500-step simulation contains no exception to this guarantee across all 8 sybil rates tested.

---

## Scenario 3: The attack is already at 30% or higher

**Utility function:**
```
U = 0.4 * F1_at_30 + 0.4 * F1_at_40 + 0.2 * Precision_mean
```

**Ranking:**

| Detector | F1 at 30% | F1 at 40% | Precision | Utility |
|---|---|---|---|---|
| **TASER** | **1.000** | 0.989 | **1.000** | **0.996** |
| RF + GWO | 0.964 | 0.966 | 0.938 | 0.960 |
| Random Forest | 0.975 | 0.967 | 0.901 | 0.957 |
| LSTM | 1.000 | 0.909 | 0.536 | 0.871 |
| IQR | 0.439 | 1.000 | 0.290 | 0.634 |

**Recommendation: TASER**

At high attack intensities, TASER dominates: F1 = 1.000 at 30% and 0.989 at 40%, with Precision = 1.000. RF and RF+GWO are within 2% on F1 but train 4x and 154x slower respectively. TASER dominates RF at all 8 tested sybil rates (see dominance matrix in `math_justifications.txt`).

---

## Scenario 4: No labeled data available

**When this applies:** Fresh deployment with no historical attack data.

**Utility function:**
```
U = 0.5 * Recall_mean + 0.5 * Specificity_mean
```

**Ranking, unsupervised detectors only:**

| Detector | Recall | Specificity | Utility | Needs labels? |
|---|---|---|---|---|
| **TASER** | 0.997 | 1.000 | **0.999** | No |
| IQR | 1.000 | 0.125 | 0.563 | No |
| RSU | 0.014 | 0.991 | 0.502 | No |
| k-Means | 0.000 | 0.997 | 0.499 | No |

**Recommendation: TASER**

Among detectors that require no labeled training data, TASER scores 78% higher than IQR (0.999 vs 0.563). IQR has perfect recall (1.0) but specificity of only 0.125 at the 8-rate average, meaning it flags 87.5% of legitimate vehicles as Sybil. In a fresh deployment without calibration data, IQR is operationally unusable.

RF and RF+GWO require labeled data and are excluded from this scenario.

---

## Scenario 5: Very limited compute

**When this applies:** On-board vehicle units, IoT roadside devices.

**Utility function:**
```
U = 0.3 * F1_mean + 0.7 * (-ln(fit_time + 1))
```

**Ranking:**

| Detector | F1 (OOS) | Time (s) | Utility |
|---|---|---|---|
| **IQR** | 0.391 | **0.06** | **0.075** |
| TASER | 0.999 | 0.64 | -0.046 |
| k-Means | 0.000 | 0.33 | -0.198 |
| Random Forest | 0.882 | 2.68 | -0.648 |
| LSTM | 0.507 | 16.81 | -1.864 |
| RF + GWO | 0.893 | 98.3 | -2.951 |

**Recommendation: IQR** under extreme compute constraints; **TASER** as the practical alternative.

IQR runs in 0.06 seconds and stores exactly two floating point values. The 70% weight on speed makes it the mathematical winner here. The critical caveat: IQR specificity is 0.0 at rates below 35%, so it flags virtually the entire network. Use IQR only if false positives have no operational consequence, or if you know the attack rate exceeds 35%.

TASER at 0.64 seconds with F1 = 0.999 is the practical choice whenever false positives matter.

---

## Scenario 6: Early detection at 5-10% attack rate

**When this applies:** Catching an attack in its early phase, before it scales.

**Utility function:**
```
U = 0.6 * F1_at_10 + 0.4 * Precision_at_10
```

**Ranking:**

| Detector | F1 at 5% | F1 at 10% | Precision at 10% | Utility |
|---|---|---|---|---|
| **TASER** | **1.000** | **1.000** | **1.000** | **1.000** |
| RF + GWO | 0.776 | 0.704 | 0.975 | 1.000*0.813 = **0.813** |
| Random Forest | 0.665 | 0.694 | 0.935 | **0.763** |
| IQR | 0.108 | 0.110 | 0.059 | 0.090 |
| LSTM | 0.000 | 0.000 | 0.000 | 0.000 |
| RSU | 0.000 | 0.000 | 0.000 | 0.000 |
| k-Means | 0.000 | 0.000 | 0.000 | 0.000 |

**Recommendation: TASER**

TASER achieves perfect F1 = 1.000 and Precision = 1.000 at 5% and 10% Sybil rate. Critically, it converges to flag a Sybil node in at most 12 beacons (proven in `statistical_proofs.md` Test 7), and this bound does not depend on how many Sybil nodes exist in the network.

RF and RF+GWO at 5-10% suffer from class imbalance: with only 5.7% Sybil records (out of a sample already split 80/20 for training), some CV folds contain too few positive examples for stable learning. RF shows f1_std = 0.330 at 5% -- the highest instability of any scenario. GWO mitigates this somewhat (f1_std = 0.162 at 5%) because hyperparameter optimization adapts to the imbalanced distribution, but TASER's structural advantage (no training required) makes it strictly superior at low attack rates.

LSTM fails completely at 5-10% (F1 = 0.000): with Sybil fractions of 5.7-5.8% in the test partition, the model cannot learn the minority class.

---

## Quick reference

| Situation | First choice | Alternative | Avoid |
|---|---|---|---|
| Real-time, speed matters | **TASER** | IQR (if FP acceptable) | RF+GWO |
| Zero false positives | **TASER** | RF+GWO | IQR, k-Means |
| Heavy attack (30%+) | **TASER** | RF, RF+GWO | RSU, k-Means |
| No training labels | **TASER** | IQR (recall only) | k-Means |
| Very limited compute | IQR | **TASER** | RF+GWO, LSTM |
| Catching early attacks (5-10%) | **TASER** | RF+GWO | LSTM, IQR |

---

## Pareto frontier (OOS-corrected)

With out-of-sample evaluation, only two detectors are Pareto-optimal in F1 vs training time space:

| Detector | F1 (OOS) | Time (s) | Pareto? | Reason |
|---|---|---|---|---|
| TASER | 0.999 | 0.64 | **Yes** | Not dominated by any other |
| IQR | 0.391 | 0.06 | **Yes** | Fastest detector; not dominated on speed |
| Random Forest | 0.882 | 2.68 | No | TASER has higher F1 AND lower time |
| RF + GWO | 0.893 | 98.3 | No | TASER has higher F1 AND lower time |
| LSTM | 0.507 | 16.81 | No | TASER dominates on both |
| RSU | 0.021 | 10.25 | No | Dominated by all top performers |
| k-Means | 0.000 | 0.33 | No | F1 = 0 |

**Important change from in-sample results:** With in-sample evaluation (the earlier version of this benchmark), RF appeared on the Pareto frontier because its F1 was inflated to 0.987. With OOS-corrected F1 = 0.882, TASER (F1=0.999, 0.64s) strictly dominates RF (F1=0.882, 2.68s) on both dimensions. RF is no longer Pareto-optimal.

This change is itself a scientific finding: supervised detectors evaluated in-sample appear competitive with TASER, but proper OOS evaluation reveals that TASER outperforms them while also being faster and requiring no labeled data.

![Pareto frontier](figures/cost_vs_f1.png)

![Utility ranking by scenario](figures/scenario_utility_ranking.png)
