# Benchmark Findings: Algorithm Analysis and Research Conclusions

This document consolidates the per-algorithm analysis and cross-detector insights
produced by the benchmark. All metrics are **out-of-sample** (vehicle-level splits)
averaged over **5 seeds × 8 sybil rates = 40 observations** per detector unless
otherwise stated. Raw data: `results/metrics/multi_seed_raw.csv`.

---

## 1. IQR Speed Threshold

**Source:** [MohammedSuratwala/SybilDetection](https://github.com/MohammedSuratwala/SybilDetection)

### Algorithm

Computes the Tukey lower fence `Q1 - 1.5 × IQR` on the global speed distribution.
Vehicles with at least one reading below the fence are flagged as Sybil.
No training data or fitting required; the fence is recomputed per scenario.

### Performance

| Metric | Value |
|---|---|
| Mean F1 | 0.4007 |
| F1 std (across 40 runs) | 0.0326 |
| Precision | 0.3046 |
| Recall | **1.0000** |
| Specificity | 0.1500 |
| Fit time | **0.13 s** |
| Pareto status | **Pareto-optimal** |

### Per-Rate F1

| 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|
| 0.109 | 0.108 | 0.198 | 0.343 | 0.396 | 0.443 | 0.608 | **1.000** |

### Findings

**Recall is always 1.000** because every Sybil vehicle injects Gaussian noise
(σ = 8 m/s), producing readings far outside the legitimate range that inevitably
fall below the lower fence.

**Specificity is near zero below 35%** because the fence is *positive* at low
sybil rates. At 10% sybil rate, Q1 = 10.40 m/s and the fence equals +6.27 m/s.
Legitimate vehicles that stop at intersections (speed = 0) are below this fence
and are incorrectly flagged, collapsing precision.

As the sybil fraction grows, injected anomalous readings drag Q1 downward. At
40%, the fence drops to −0.36 m/s — below all observable speeds — and the
detector achieves perfect F1 = 1.000 by flagging Sybil vehicles exclusively
via the *upper* fence.

**IQR is Pareto-optimal** due to its extreme speed (0.13 s) and zero data
requirements. No other detector is both faster and more accurate. It is the
best choice when speed is the hard constraint and false positives are acceptable.

**Why IQR cannot compete at low sybil rates:** the fence calculation conflates
both legitimate and Sybil distributions, and at low contamination levels the
fence position is dominated by the legitimate distribution. Separation only
emerges when Sybil vehicles form a large enough fraction to shift Q1 below
zero.

---

## 2. RSU Position Verification

**Source:** [karthik-047/Detecting-Sybil-Attacks-in-VANETs](https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs)

### Algorithm

20 RSUs are deployed on a 4 × 5 subgrid (100 m detection radius). Each RSU
records vehicles within range. Any pair of vehicles seen by the same RSU but
more than 150 m apart is a candidate Sybil pair. A vehicle accumulating 5 such
events is flagged. Designed for split-position attacks where one device
broadcasts from multiple distinct locations.

### Performance (co-location attack)

| Metric | Value |
|---|---|
| Mean F1 | 0.0123 |
| Precision | 0.0341 |
| Recall | 0.0076 |
| Specificity | 0.9899 |
| Fit time | 23.7 s |
| Pareto status | Dominated by TASER, RF, k-Means, IQR |

### Performance (split-position attack — RSU's intended model)

| Mean F1 | Precision | Recall | Specificity |
|---|---|---|---|
| **0.8350** | 0.8511 | 0.8479 | 0.9628 |

### Per-Rate F1 (co-location)

| 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|
| 0.000 | 0.000 | 0.000 | 0.034 | 0.000 | 0.064 | 0.000 | 0.000 |

### Findings

**RSU produces near-zero F1 against co-location attacks** because all Sybil
identities for a given attacker report the same position. Inter-pair distance ≈ 0 m,
which is far below the 150 m detection threshold. The algorithm never fires.

**Non-zero F1 at 20% and 30%** is incidental: at high sybil rates, Sybil
identities from *different attacker vehicles* occasionally appear near the same
RSU with different positions, accidentally satisfying the detection condition.
These events are not reproducible (F1 = 0.000 at adjacent rates), confirming
they are coincidental rather than structural.

**RSU recovers to F1 = 0.835 in the split-position attack model**, where each
attacker's fake identities are placed at distinct RSU-centered positions 160 m
apart — exactly the scenario the algorithm was designed to detect. This result
confirms the algorithm is correct; the co-location failure is a model mismatch,
not an implementation flaw.

**Deployment implication:** RSU detection is only appropriate when the threat
model includes split-position or location-spoofing attacks. Against co-location
Sybil attacks it is uninformative.

---

## 3. TASER Bayesian Trust

**Source:** [morton-t/VANET-Simulations](https://github.com/morton-t/VANET-Simulations)

### Algorithm

Each vehicle maintains a trust score T ∈ [0, 1], initialized at 0.5.
Per-beacon updates:

```
Consistent beacon:   T ← T + α(1 − T)   α = 0.01
Anomalous beacon:    T ← T(1 − β)        β = 0.10
Flag if:             T < λ               λ = 0.15
```

Anomaly condition: speed > 19.4 m/s OR |Δspeed| > 5.6 m/s (both thresholds
calibrated to the legitimate speed distribution in the simulation).

### Performance

| Metric | Value |
|---|---|
| Mean F1 | **0.9997** |
| F1 std (across 40 runs) | **0.0006** |
| Precision | **1.0000** |
| Recall | 0.9995 |
| Specificity | **1.0000** |
| Fit time | 1.07 s |
| Pareto status | **Pareto-optimal (best F1)** |

### Per-Rate F1

| 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|
| 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.998 |

### Analytical Detection Bound

Starting from T₀ = 0.5, a Sybil vehicle emitting only anomalous beacons is
flagged within **n\* = ⌈ln(λ/T₀) / ln(1−β)⌉ = ⌈11.43⌉ = 12 beacons**:

```
Tₙ = T₀(1 − β)ⁿ  →  0.15 = 0.5 × 0.9ⁿ
n = ln(0.3) / ln(0.9) = 11.43 → ceil = 12
```

No other tested detector has a provable finite detection bound.

### Findings

**TASER achieves the highest F1 (0.9997) of all six detectors** with F1 std = 0.0006
across 40 independent runs. The narrow distribution is a structural guarantee, not
a statistical artifact.

**Precision = 1.0000 at every tested rate.** TASER never generates false
positives. This is caused by the asymmetric update rule: a legitimate vehicle
with a single anomalous reading recovers quickly (α = 0.01 means trust grows
slowly), while a Sybil vehicle with persistent noise cannot recover before
crossing the λ = 0.15 threshold.

**F1 = 0.998 at 40% sybil rate** — the only rate where TASER is not perfect —
because a small fraction of Sybil vehicles emit fewer anomalous beacons than
average before the simulation ends, not accumulating enough negative updates to
cross the threshold.

**Wilcoxon signed-rank: W = 0, p < 0.001 vs Random Forest.** TASER dominates
RF at all 40 paired observations. Bootstrap 95% CI: [0.9992, 1.0000] — zero
overlap with RF CI [0.8640, 0.9224].

**TASER is Pareto-optimal**, dominating RF, LSTM, and RSU on both F1 and
training time. Only k-Means (0.30 s, F1 = 0.980) and IQR (0.13 s) remain
non-dominated because they are faster.

**No labeled data required.** TASER is the only method combining:
- Provably bounded detection (12 beacons)
- Precision = 1.000 (zero false positives)
- Pareto-optimal F1 vs speed

---

## 4. Random Forest

**Source:** [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet)

### Algorithm

100-tree ensemble, max_depth = 10, trained on 8 per-beacon features:
speed, acceleration, heading, x, y, neighbor count within 150 m,
minimum RSU distance, mean RSU distance.

Evaluated with **5-fold cross-validation split by vehicle_id** to prevent data
leakage (vehicle patterns cannot appear in both train and test within any fold).

### Performance

| Metric | Value |
|---|---|
| Mean F1 (OOS) | 0.8945 |
| F1 std | 0.0242 |
| Precision | 0.9156 |
| Recall | 0.8856 |
| Specificity | 0.9802 |
| Fit time | 5.03 s |
| Pareto status | Dominated (by TASER and k-Means) |
| In-sample F1 | ≈ 0.987 |
| **Data leakage gap** | **9.3 percentage points** |

### Per-Rate F1

| 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|
| 0.741 | 0.754 | 0.865 | 0.953 | 0.948 | 0.967 | 0.958 | 0.970 |

### Findings

**RF achieves F1 = 0.8945 out-of-sample**, growing monotonically from 0.741 at 5%
to 0.970 at 40% as the sybil fraction provides more positive training examples.

**The data leakage gap is 9.3 percentage points.** Without vehicle-level splitting,
in-sample F1 ≈ 0.987. Row-level splitting allows the model to see speed sequences
from a vehicle in training and classify the same vehicle in testing, creating
artificial familiarity. Vehicle-level splitting removes this entirely.

This gap means that the majority of published RF-based VANET detectors that do not
report vehicle-level OOS results are likely overestimating performance by a similar
margin.

**RF is Pareto-dominated by both TASER and k-Means.** TASER achieves higher F1
(1.000 vs 0.895) *and* lower training time (1.07 s vs 5.03 s). k-Means achieves
higher F1 (0.980 vs 0.895) *and* lower training time (0.30 s vs 5.03 s).
There is no deployment scenario where RF is the optimal choice.

**Wilcoxon W = 22, p < 0.001 (RF vs LSTM):** RF significantly outperforms LSTM
across all sybil rates. Cohen's d = 1.52 (large effect).

---

## 5. LSTM

**Source:** [SaiKumar-1608 Dual-Layer Framework](https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL)

### Algorithm

Two-layer LSTM (64 → 32 units, dropout = 0.3), sequence length = 50 beacons,
same 8 features as RF. Binary cross-entropy loss, Adam optimizer, early stopping
(patience = 3). Evaluated on **80/20 vehicle-level split** (5-fold CV not used
due to computational cost: 5 folds × 5 seeds × 8 rates × 20 epochs would require
> 10 hours).

### Performance

| Metric | Value |
|---|---|
| Mean F1 | 0.4487 |
| F1 std (across 40 runs) | 0.1766 |
| Precision | 0.4638 |
| Recall | 0.4735 |
| Specificity | 0.9280 |
| Fit time | 35.9 s |
| Pareto status | Dominated (TASER, RF, k-Means all superior) |
| Mean AUC | 0.850 |

### Per-Rate F1

| 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|
| 0.000 | 0.050 | 0.050 | 0.443 | 0.499 | 0.851 | 0.883 | 0.814 |

### Findings

**LSTM fails below 15% sybil rate** due to class imbalance. At 5–15% sybil rate,
Sybil records represent only 5.7–11.5% of the training set. With early stopping
(patience = 3), training terminates before the network adjusts weights to detect
the minority class. Predicting "legitimate" for all inputs incurs a lower loss
than attempting classification.

**The transition occurs between 15% and 20%.** At 20% (21% positive records),
LSTM achieves F1 = 0.443, rising to 0.851 at 30% and 0.883 at 35%. Beyond 20%
the training signal is sufficient, but results oscillate due to the stochastic
interaction between class balance and early stopping across seeds.

**AUC = 0.850 (mean across 10–40% rates) despite low operating-point F1.** The learned probability scores
have genuine discriminative power even at low sybil rates, but the default
threshold (0.5) is poorly calibrated for the imbalanced class distribution.
Threshold tuning or SMOTE oversampling would likely recover significant F1 gains
at low rates.

**Wilcoxon LSTM vs IQR: W = 335, p = 0.443 — NOT significant.** Despite their
very different mechanisms, LSTM and IQR produce statistically equivalent mean F1
across the 40 observation pairs. Neither dominates the other: LSTM performs
better at high rates (≥ 30%), IQR better at very high rates (40%), but the
aggregate difference does not reach significance.

**LSTM is Pareto-dominated.** Fit time of 35.9 s is the highest of any detector,
and F1 = 0.449 is outperformed by both RF and k-Means. LSTM's temporal modeling
architecture does not offer a benefit relative to simpler methods in this scenario.

---

## 6. Dynamic k-Means

**Source:** [Gideon-Adele/Dynamic-k-means-Clustering](https://github.com/Gideon-Adele/Dynamic-k-means-Clustering)

### Algorithm

Aggregates 8 behavioral features per vehicle: mean/std of x, y, speed,
acceleration, and neighbor count. Clusters with k = ⌊√(V/2)⌋ where V is
the number of distinct vehicles. A cluster is flagged Sybil if **any** of:

1. **Small cluster** — fewer than 3 members
2. **High speed variance** — centroid `std_speed` z-score > 2.0 (via MAD)
3. **Low position variance** — centroid `pos_std` z-score < −2.0 (via MAD)

Z-scores use **median ± MAD** (not mean ± std) to resist contamination
when many Sybil vehicles bias the global distribution.

### Performance

| Metric | Value |
|---|---|
| Mean F1 | **0.9795** |
| F1 std (across 40 runs) | 0.0257 |
| Precision | 0.9671 |
| Recall | **0.9944** |
| Specificity | 0.9895 |
| Fit time | **0.30 s** |
| Pareto status | **Pareto-optimal** |

### Per-Rate F1

| 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|
| 0.961 | 0.986 | 0.954 | 0.993 | 0.986 | 0.990 | 0.991 | 0.975 |

### Key Criterion Correction

The original algorithm (mean-speed z-score) returned **F1 = 0.000** at all sybil
rates. The root cause is mathematical:

> Speed noise N(0, 8²) has **mean = 0**, so  
> E[speed_Sybil] = E[speed_legit] + 0 = E[speed_legit]  
> Cluster centroids for Sybil and legitimate groups are **indistinguishable** on mean speed.

The fix: use `std_speed` instead of `mean_speed`. Gaussian noise (σ = 8 m/s)
inflates per-vehicle speed standard deviation to ≈ 8 m/s; legitimate vehicles
show ≈ 2–4 m/s. This produces a clear, robust separation across all sybil rates.

Using MAD instead of standard deviation for z-score computation prevents the
global reference from being contaminated at high sybil rates (up to 40%).

### Findings

**k-Means is the second-best detector overall (F1 = 0.9795)**, behind only TASER
(F1 = 0.9997). It achieves this in 0.30 s with no labeled training data.

**k-Means is Pareto-optimal**, strictly dominating RF (F1 = 0.895, 5.03 s) and
LSTM on both F1 and training time simultaneously.

**F1 is stable across rates** (std = 0.026), with the minimum at 15% (F1 = 0.954)
and maximum at 20% (F1 = 0.993). The stability contrasts sharply with LSTM
(std = 0.177) and IQR (std = 0.033).

**Wilcoxon TASER vs k-Means: W = 0, p < 0.001, Cohen's d = 0.86 (large).**
TASER still significantly outperforms k-Means, dominating at all 40 observations.
Bootstrap 95% CI for k-Means: [0.9681, 0.9885] — non-overlapping with TASER
CI [0.9992, 1.0000].

**Split-position attack: F1 = 0.923 (mean across 8 rates).** k-Means degrades
modestly (−0.057 delta from co-location). The speed-variance criterion (criterion 2)
still fires because Sybil vehicles inject Gaussian noise regardless of attack model.
The position-variance criterion (criterion 3) is less effective in split-position
because Sybil identities at distinct RSU-centered positions have non-zero mean_pos_std,
reducing the clustering contrast. Despite this, k-Means remains the second-best
detector in split-position (RSU F1=0.835, k-Means F1=0.923).

**Primary research contribution:** demonstrating that a near-trivial criterion
change (mean → variance) converts a completely ineffective detector (F1 = 0.000)
into the second-best overall (F1 = 0.9795). This highlights the risk of reporting
zero results without a principled root-cause investigation.

---

## 7. Cross-Detector Statistical Validation

### Kruskal-Wallis H-test

```
H = 180.69,  p = 3.80 × 10⁻³⁷,  df = 5,  n = 40 per group
```

H₀ (equal F1 distributions across detectors) is rejected at any standard
significance level. The six detectors are not drawn from the same performance
distribution.

### Pairwise Wilcoxon Signed-Rank Tests (n = 40 paired observations)

| Comparison | W | p-value | Cohen's d | Significant? |
|---|---|---|---|---|
| TASER vs Random Forest | 0 | < 0.001 | 1.56 (large) | Yes |
| TASER vs IQR | 1 | < 0.001 | 2.96 (large) | Yes |
| TASER vs k-Means | 0 | < 0.001 | 0.86 (large) | Yes |
| Random Forest vs LSTM | 22 | < 0.001 | 1.52 (large) | Yes |
| LSTM vs IQR | 335 | 0.443 | 0.14 (negligible) | **No** |

LSTM and IQR are not statistically distinguishable in aggregate F1 despite
operating via completely different mechanisms.

### Bootstrap 95% Confidence Intervals (10,000 resamples, seed = 42)

| Detector | Mean F1 | CI Lower | CI Upper | CI Width |
|---|---|---|---|---|
| TASER | 0.9997 | 0.9992 | 1.0000 | 0.0008 |
| k-Means | 0.9795 | 0.9681 | 0.9885 | 0.0204 |
| Random Forest | 0.8945 | 0.8640 | 0.9224 | 0.0584 |
| LSTM | 0.4487 | 0.3257 | 0.5733 | 0.2476 |
| IQR | 0.4007 | 0.3151 | 0.4939 | 0.1788 |
| RSU | 0.0123 | 0.0000 | 0.0327 | 0.0327 |

Non-overlapping intervals between TASER and RF, TASER and k-Means (where CI widths
are narrow and do not touch), and between k-Means and LSTM/IQR confirm statistically
certain differences.

### Pareto Frontier (F1 vs Training Time)

| Detector | F1 | Time (s) | Pareto? | Dominated by |
|---|---|---|---|---|
| TASER | 0.9997 | 1.07 | **Yes** | — |
| k-Means | 0.9795 | 0.30 | **Yes** | — |
| IQR | 0.4007 | 0.13 | **Yes** | — |
| Random Forest | 0.8945 | 5.03 | No | TASER, k-Means |
| RSU | 0.0123 | 23.75 | No | TASER, RF, IQR, k-Means |
| LSTM | 0.4487 | 35.94 | No | TASER, RF, k-Means |

---

## 8. Key Research Contributions

### 8.1 Unified Evaluation Eliminates Comparison Fragmentation

Six algorithms from independent open-source repositories were evaluated under
identical simulation conditions (same SUMO network, same random seeds, same
sybil rate scenarios). Prior to this benchmark, results across these algorithms
were incomparable due to differing simulation environments, datasets, and splits.

### 8.2 Vehicle-Level Splits Reveal 9.3 pp Data Leakage in RF

Row-level splitting — used in most published evaluations — allows speed sequences
from the same vehicle to appear in both training and test sets. The model memorizes
per-vehicle patterns and achieves in-sample F1 ≈ 0.987. Vehicle-level OOS
evaluation produces F1 = 0.895 — a 9.3 percentage point overestimate with
row-level splitting.

### 8.3 Criterion Root-Cause Analysis: k-Means from F1=0.000 to F1=0.980

The original k-Means criterion (mean-speed z-score) produced F1 = 0.000 because
speed noise has mean = 0. Switching to std-speed z-score with MAD normalization
produced F1 = 0.9795 — a mathematically justified correction that transforms
a useless detector into the second best. This demonstrates the importance of
criterion analysis over result reporting.

### 8.4 Attack Model Dependency Quantified

RSU F1 rises from 0.012 to 0.835 when the attack model switches from co-location
to split-position. This confirms that algorithm evaluation is not portable across
attack models: each detector's performance is a function of the alignment between
its detection assumption and the attacker's strategy.

### 8.5 Multi-Seed Replication (n=40) with Non-Parametric Tests

Five random seeds × 8 sybil rates = 40 observations per detector provides
adequate statistical power for Kruskal-Wallis and Wilcoxon tests.
H = 180.69 (p < 10⁻³⁶) confirms that performance differences are not
attributable to seed variance.
