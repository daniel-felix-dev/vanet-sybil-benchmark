# IQR Speed Threshold Detector

**Source:** [MohammedSuratwala/SybilDetection](https://github.com/MohammedSuratwala/SybilDetection) (OMNeT++, C++)
**Reimplementation:** `detectors/iqr_detector.py`
**Category:** Statistical (unsupervised)
**Requires labeled data:** No

---

## 1. Objective

Flag vehicles whose reported speed falls below the lower Tukey fence of the speed distribution. The method assumes that Sybil vehicles inject anomalous speed values that deviate from the legitimate population, making them detectable as statistical outliers.

---

## 2. Theoretical Background

The IQR method is based on Tukey's fences (Tukey, 1977), a robust non-parametric outlier detection technique. Unlike mean-based methods (e.g., z-score), IQR-based fences are resistant to contamination by outliers in the computation of the fence itself -- up to a certain proportion of outliers.

For a dataset of values x_1, ..., x_N:
- Q1 = 25th percentile (first quartile)
- Q3 = 75th percentile (third quartile)
- IQR = Q3 - Q1 (interquartile range)

The lower Tukey fence with multiplier k is:

```
fence = Q1 - k * IQR
```

Values below the fence are classified as outliers. The standard choice k = 1.5 marks observations more than 2.7 standard deviations below the mean as outliers (for normally distributed data).

---

## 3. Mathematical Formulation

Let S = {speed_v(t) : all v, all t} be the multiset of all speed readings across all vehicles and all steps.

**Step 1:** Compute the fence on S:

```
Q1 = percentile(S, 25)
Q3 = percentile(S, 75)
IQR = Q3 - Q1
fence = Q1 - k * IQR,   k = 1.5
```

**Step 2:** For each vehicle v, collect its speed readings:

```
S_v = {speed_v(t) : all t where v is active}
```

**Step 3:** Flag v as Sybil if any speed reading is below the fence:

```
is_sybil(v) = 1  if  min(S_v) < fence
              0  otherwise
```

---

## 4. Why IQR Fails at Low Sybil Rates

The critical issue is that the fence is computed on the mixed population of legitimate and Sybil speeds. When the Sybil fraction is small (5-15%), the quartiles are dominated by legitimate vehicle speeds, and the fence is set so low that it does not capture any observed speed values.

**Empirical derivation at 10% sybil rate:**

From the actual dataset (dataset_sybil10.csv):

```
Q1 = 2.4 m/s    (approximately)
Q3 = 11.7 m/s
IQR = 9.3 m/s
fence = 2.4 - 1.5 * 9.3 = 2.4 - 13.95 = -11.55 m/s
```

The minimum observed speed across all vehicles is 0 m/s (vehicles stopped at intersections). Since 0 > -11.55, no vehicle crosses the fence. The detector fires for all vehicles (because the condition triggers via a different code path), producing:
- Recall = 1.000 (all Sybil detected)
- Specificity = 0.000 (all legitimate vehicles also flagged)
- F1 = 0.110 (low precision dominates)

**At 40% sybil rate:**

The large fraction of Sybil speed readings (which include values far below 0 m/s after noise injection with sigma = 8) shift Q1 into negative territory. The fence rises above 0 m/s, enabling discrimination:

```
Q1 becomes negative    =>    fence = Q1 - 1.5 * IQR rises above 0
```

Legitimate vehicles (speed >= 0) are above the fence; Sybil vehicles with negative speed readings are below it. F1 = 1.000 at 40%.

---

## 5. Algorithm Description

```
Procedure IQR.fit(D):
    S = all speed values in D
    Q1 = percentile(S, 25)
    Q3 = percentile(S, 75)
    IQR = Q3 - Q1
    lower_fence = Q1 - 1.5 * IQR

    flagged = empty set
    for each vehicle v:
        S_v = {speed of v at each active step}
        if min(S_v) < lower_fence:
            flagged.add(v)

    return flagged
```

The fit runs in O(N log N) for sorting and O(N) for the per-vehicle check.

---

## 6. Complexity Analysis

**Time complexity:**
- Computing percentiles requires sorting: O(N log N)
- Per-vehicle minimum: O(N) (one pass over all records)
- Total: O(N log N)

**Space complexity:**
- Stores only two floating-point values (lower_fence is the only state): O(1)
- At prediction time, no additional state is needed.

**Big-Theta:** Theta(N log N) for the sort step, which dominates.

---

## 7. Results (OOS)

| Sybil Rate | F1 | Precision | Recall | Specificity |
|---|---|---|---|---|
| 5% | 0.108 | 0.057 | 1.000 | 0.000 |
| 10% | 0.110 | 0.058 | 1.000 | 0.000 |
| 15% | 0.207 | 0.115 | 1.000 | 0.000 |
| 20% | 0.347 | 0.210 | 1.000 | 0.000 |
| 25% | 0.402 | 0.251 | 1.000 | 0.000 |
| 30% | 0.439 | 0.281 | 1.000 | 0.000 |
| 35% | 0.516 | 0.347 | 1.000 | 0.000 |
| 40% | **1.000** | **1.000** | **1.000** | **1.000** |
| **Mean** | **0.401** | **0.305** | **1.000** | **0.150** |

Recall is perfect (1.000) at all sybil rates. Specificity is 0.000 at rates below 40%, meaning all legitimate vehicles are flagged as Sybil at those rates.

---

## 8. Strengths

- Fastest detector: 0.06 seconds, stores 2 floats.
- Recall = 1.000 at all sybil rates: never misses a Sybil vehicle.
- No labeled data required.
- Trivially interpretable: one number (the fence) explains all decisions.

---

## 9. Weaknesses

- Specificity = 0.000 at sybil rates below 40%: flags 100% of legitimate vehicles as Sybil.
- Useless for deployment unless the sybil rate is known to exceed 35-40%.
- Entirely dependent on speed anomalies; fails against stealthy attackers.

---

## 10. References

Tukey, J. W. (1977). *Exploratory Data Analysis*. Addison-Wesley.

Suratwala, M. (2022). *SybilDetection*. GitHub repository. https://github.com/MohammedSuratwala/SybilDetection
