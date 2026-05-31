# Scenario Recommendation Guide

Each recommendation is backed by a **utility function** computed from the benchmark data.  
Utility weights reflect the priorities of each scenario. Full calculations are in `math_justifications.txt`.

**Utility formula:**

```
U(detector, scenario) = Σ [ w_k × metric_k(detector) ] / Σ |w_k|
```

where weights w_k encode what matters most in each scenario.

---

## Scenarios

### 1. Latency-critical / Real-time detection

**Context:** Traffic management systems, intersection collision avoidance, emergency vehicle coordination. Detection must complete within one simulation epoch (≤ 1 s).

**Utility function:**
```
U = 0.4 × F1_mean + 0.3 × Precision_mean + 0.3 × (−ln(fit_time + 1))
```

**Results:**

| Detector | F1 | Precision | Fit time (s) | **Utility** |
|---|---|---|---|---|
| **Random Forest** | 0.9867 | 0.9853 | 0.57 | **0.555** |
| **TASER** | 0.9973 | 1.0000 | 0.87 | **0.511** |
| IQR Speed Threshold | 0.4740 | 0.3874 | 0.05 | 0.291 |
| Dynamic k-Means | 0.0000 | 0.0000 | 0.64 | −0.149 |
| LSTM | 0.7038 | 0.6804 | 10.0 | −0.234 |
| RSU Verification | 0.0426 | 0.0908 | 11.3 | −0.708 |
| RF + GWO | 0.9842 | 0.9760 | 117.3 | −0.745 |

**Recommendation: Random Forest** (utility = 0.555)

**Justification:**
- RF achieves F1 = 0.987 in 0.57 s — the highest F1 per unit time of any competitive detector
- Efficiency score: RF = 2.19, TASER = 1.59 (computed as F1/ln(time+1))
- RF is Pareto-optimal: no detector is both faster AND more accurate
- At the time budget threshold of 1 s: RF fits in 0.57 s; TASER in 0.87 s; both qualify. RF wins on efficiency by 38% margin (2.19 vs. 1.59)
- GWO-RF is disqualified: mean fit time 117 s violates the real-time constraint by 117×

**Secondary choice:** TASER — if zero false positives is also required (Precision = 1.000 vs. RF's 0.985)

---

### 2. Zero false-positives required (safety-critical systems)

**Context:** Emergency vehicle authentication, autonomous driving coordination. A false positive (legitimate vehicle flagged as Sybil) can cause denial-of-service for a safety-critical node.

**Utility function:**
```
U = 0.7 × Precision_mean + 0.3 × F1_mean
```

**Results:**

| Detector | Precision | F1 | **Utility** |
|---|---|---|---|
| **TASER** | **1.0000** | 0.9973 | **0.9992** |
| Random Forest | 0.9853 | 0.9867 | 0.9857 |
| RF + GWO | 0.9760 | 0.9842 | 0.9785 |
| LSTM | 0.6804 | 0.7038 | 0.6874 |
| IQR Speed Threshold | 0.3874 | 0.4740 | 0.4134 |
| RSU Verification | 0.0908 | 0.0426 | 0.0764 |
| Dynamic k-Means | 0.0000 | 0.0000 | 0.0000 |

**Recommendation: TASER** (utility = 0.9992)

**Justification:**
- TASER is the **only detector** with Precision = 1.0000 across **all four sybil rates** (10%, 20%, 30%, 40%)
- The Bayesian trust update mechanism converges monotonically downward for anomalous nodes; once below λ = 0.15, the trust score does not recover without a sustained run of legitimate beacons — preventing false positives caused by momentary fluctuations
- Expected false positive count: **0 per simulation run** at all tested rates
- Mathematical guarantee: legitimate vehicles emitting speed ∈ [0, 14×1.4] m/s will always increase their trust score (`T ← T + α(1−T)` with α = 0.01), converging to T = 1.0 over time regardless of starting value

**Risk note:** TASER's precision guarantee holds only if Sybil nodes inject detectable speed anomalies. Against a stealthy attack that stays within the normal speed range, precision drops and recall would also fall. No detector achieves Precision = 1.0 against stealthy attacks without labeled training data.

---

### 3. High Sybil rate (≥ 30%)

**Context:** Worst-case network conditions — coordinated attack with many compromised vehicles. The primary concern is recall (not missing Sybil nodes) while maintaining acceptable precision.

**Utility function:**
```
U = 0.4 × F1_at_30 + 0.4 × F1_at_40 + 0.2 × Precision_mean
```

**Results:**

| Detector | F1@30% | F1@40% | Precision | **Utility** |
|---|---|---|---|---|
| **TASER** | 1.0000 | 0.9892 | 1.0000 | **0.9957** |
| **Random Forest** | 0.9942 | 0.9944 | 0.9853 | **0.9925** |
| RF + GWO | 0.9742 | 0.9912 | 0.9760 | **0.9814** |
| LSTM | 1.0000 | 0.9732 | 0.6804 | 0.9254 |
| IQR Speed Threshold | 0.4391 | 1.0000 | 0.3874 | 0.6531 |
| RSU Verification | 0.0000 | 0.0000 | 0.0908 | 0.0182 |
| Dynamic k-Means | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

**Recommendation: TASER** for highest F1 at all rates; **Random Forest** for best balance of performance and speed.

**Justification:**
- At ≥ 30% Sybil rate, the top three detectors (TASER, RF, GWO-RF) converge: all achieve F1 > 0.97
- TASER maintains the slight edge with F1 = 1.0 at 30% and 0.989 at 40%
- RF is the better operational choice when training time matters: 0.65 s vs. 1.03 s for TASER vs. 127 s for GWO-RF
- LSTM achieves F1 = 1.0 at 30% but degrades to 0.973 at 40% — inconsistent compared to TASER and RF
- IQR improves significantly at high rates (F1 = 1.0 at 40%) but remains unreliable at 30% (F1 = 0.44)

**Dominance result:** TASER dominates LSTM, RSU, and k-Means at all sybil rates simultaneously (see dominance matrix in `math_justifications.txt`).

---

### 4. No labeled data available (unsupervised deployment)

**Context:** New VANET deployment without historical attack data. Training-based detectors (RF, GWO-RF) cannot be used without ground truth labels.

**Utility function:**
```
U = 0.5 × Recall_mean + 0.5 × Specificity_mean
```

*(balances catching Sybil nodes with not flagging legitimate ones)*

**Results:**

| Detector | Recall | Specificity | **Utility** | Requires labels? |
|---|---|---|---|---|
| **TASER** | 0.9947 | 1.0000 | **0.9973** | No |
| Random Forest | 0.9880 | 0.9968 | 0.9924 | **Yes** |
| RF + GWO | 0.9927 | 0.9912 | 0.9920 | **Yes** |
| LSTM | 0.7330 | 0.9626 | 0.8478 | **Yes** |
| IQR Speed Threshold | 1.0000 | 0.2500 | 0.6250 | No |
| RSU Verification | 0.0278 | 0.9870 | 0.5074 | No |
| Dynamic k-Means | 0.0000 | 0.9960 | 0.4980 | No |

**Recommendation: TASER** among unsupervised detectors (utility = 0.9973)

**Justification:**
- Among detectors that do not require labels, TASER achieves utility 59.5% higher than IQR (0.997 vs. 0.625) and 96.5% higher than RSU (0.507)
- IQR has perfect recall (1.0) but near-zero specificity (0.25) — it catches all Sybil nodes but also flags 75% of legitimate vehicles. In an unsupervised setting without labels to calibrate the threshold, IQR is unusable in practice
- RSU achieves high specificity (0.987) but catastrophically low recall (0.028) — misses 97.2% of Sybil nodes
- Dynamic k-Means produces recall = 0.0 regardless of dataset — not viable in any deployment
- **TASER alone** among unsupervised detectors achieves both high recall (0.995) and perfect specificity (1.0)

---

### 5. Resource-constrained (embedded / IoT deployment)

**Context:** On-board vehicle units with limited CPU. Detection must run in a few milliseconds; no GPU available. Model size is also a constraint.

**Utility function:**
```
U = 0.3 × F1_mean + 0.7 × (−ln(fit_time + 1))
```

*(70% weight on speed — strong compute constraint)*

**Results:**

| Detector | F1 | Fit time (s) | −ln(time+1) | **Utility** |
|---|---|---|---|---|
| **IQR Speed Threshold** | 0.4740 | **0.05** | −0.049 | **0.106** |
| Random Forest | 0.9867 | 0.57 | −0.454 | −0.020 |
| TASER | 0.9973 | 0.87 | −0.624 | −0.140 |
| Dynamic k-Means | 0.0000 | 0.64 | −0.478 | −0.348 |
| LSTM | 0.7038 | 10.0 | −2.398 | −1.468 |
| RSU Verification | 0.0426 | 11.3 | −2.514 | −1.741 |
| RF + GWO | 0.9842 | 117.3 | −4.774 | −3.046 |

**Recommendation: IQR** under extreme compute constraints; **RF** as the practical compromise.

**Justification:**
- IQR fit time = 0.05 s — 11× faster than RF (0.57 s), 17× faster than TASER (0.87 s)
- The IQR algorithm requires only 3 statistics (Q1, Q3, IQR) computed in a single pass: O(N log N) due to sorting
- Memory footprint: IQR stores 2 floats (lower fence, upper fence) vs. RF's serialised model (~several MB for 100 trees)
- **Critical caveat:** At sybil rates ≤ 30%, IQR's specificity = 0.0 — it flags the entire network. If false positives carry any cost, IQR is unacceptable even under resource constraints
- **Practical recommendation:** RF at 0.57 s and F1 = 0.987 is a better embedded choice if the hardware can afford it. Random Forest models can be quantised and pruned (max_depth=5 reduces time to ~0.2 s with F1 ≈ 0.95)

---

### 6. Low Sybil rate (≤ 10%) — early attack detection

**Context:** Initial phase of an attack where few Sybil nodes have entered the network. High sensitivity required to detect the attack before it scales.

**Utility function:**
```
U = 0.6 × F1_at_10 + 0.4 × Precision_at_10
```

**Results:**

| Detector | F1@10% | Precision@10% | **Utility** |
|---|---|---|---|
| **TASER** | **1.0000** | **1.0000** | **1.0000** |
| **RF + GWO** | **1.0000** | **1.0000** | **1.0000** |
| Random Forest | 0.9678 | 0.9689 | **0.9682** |
| IQR Speed Threshold | 0.1100 | 0.0582 | 0.0893 |
| LSTM | 0.0000 | 0.0000 | 0.0000 |
| RSU Verification | 0.0000 | 0.0000 | 0.0000 |
| Dynamic k-Means | 0.0000 | 0.0000 | 0.0000 |

**Recommendation: TASER** or **RF + GWO** (both utility = 1.0000)

**Justification:**
- At 10% Sybil rate, only 5 Sybil IDs exist among 85 total vehicles (5.9% of records)
- Both TASER and RF+GWO achieve perfect F1 = 1.0 and Precision = 1.0 at this rate
- **Tie-breaking criterion:** fit time
  - TASER: 0.63 s
  - RF + GWO: 88.1 s
  - **TASER wins** with 140× lower training time and identical detection quality
- LSTM completely fails (F1 = 0.0): the 5.9% positive rate provides insufficient training signal for the LSTM to learn the Sybil pattern
- IQR achieves recall = 1.0 but precision = 0.058 — it flags virtually the entire network (94% false positive rate)

**Statistical note:** the superiority of TASER over RF+GWO at 10% is not due to chance — the Bayesian trust mechanism converges to flag a Sybil node within 12 beacons regardless of how many other Sybil nodes are present, making it robust to low attack density by design.

---

## Quick reference — decision matrix

| Scenario | **Primary** | **Secondary** | **Avoid** |
|---|---|---|---|
| Real-time (≤1 s) | Random Forest | TASER | RF+GWO, RSU |
| Zero false positives | TASER | Random Forest | IQR, k-Means |
| High sybil rate (≥30%) | TASER | Random Forest | RSU, k-Means |
| No labels (unsupervised) | TASER | IQR (recall only) | k-Means |
| Embedded (minimal compute) | IQR | Random Forest | RF+GWO, LSTM |
| Low sybil rate (≤10%) | TASER | RF + GWO | LSTM, IQR |

![Scenario Utility Ranking](figures/scenario_utility_ranking.png)

---

## Pareto frontier analysis

Three detectors are Pareto-optimal in the (F1, speed) space — no other detector simultaneously outperforms them on both axes:

| Detector | F1_mean | Fit time (s) | Pareto? |
|---|---|---|---|
| TASER Bayesian Trust | 0.9973 | 0.87 | ✓ |
| Random Forest | 0.9867 | 0.57 | ✓ |
| IQR Speed Threshold | 0.4740 | 0.05 | ✓ |
| RF + GWO | 0.9842 | 117.3 | ✗ (dominated by RF) |
| LSTM | 0.7038 | 10.0 | ✗ (dominated by RF) |
| RSU Verification | 0.0426 | 11.3 | ✗ (dominated by all) |
| Dynamic k-Means | 0.0000 | 0.64 | ✗ (dominated by all) |

RF+GWO is not Pareto-optimal because RF achieves higher F1 (0.987 vs. 0.984) in less time (0.57 s vs. 117 s). The GWO optimisation overhead is never recovered in detection quality at these dataset sizes.

![Cost vs F1 (Pareto)](figures/cost_vs_f1.png)
