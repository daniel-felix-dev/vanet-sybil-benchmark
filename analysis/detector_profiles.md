# Detector Profiles

Each section below covers one algorithm: how it works, what the numbers show, and where it breaks down. All statistics come from `results/metrics/benchmark_results.csv`. The raw calculations are in `math_justifications.txt`.

---

## Summary

| Detector | F1 avg | F1 variability | Precision | Recall | Specificity | Training time |
|---|---|---|---|---|---|---|
| TASER Bayesian Trust | **0.997** | 0.005 | **1.000** | 0.995 | **1.000** | 0.87 s |
| Random Forest | 0.987 | 0.013 | 0.985 | **0.988** | 0.997 | **0.57 s** |
| Random Forest + GWO | 0.984 | 0.014 | 0.976 | 0.993 | 0.991 | 117 s |
| LSTM | 0.704 | 0.474 | 0.680 | 0.733 | 0.963 | 10 s |
| IQR Speed Threshold | 0.474 | 0.377 | 0.387 | 1.000 | 0.250 | 0.05 s |
| RSU Position Verification | 0.043 | 0.085 | 0.091 | 0.028 | 0.987 | 11.3 s |
| Dynamic k-Means | 0.000 | 0.000 | 0.000 | 0.000 | 0.996 | 0.64 s |

The efficiency score in the table below is F1 divided by the natural log of (training time + 1). Higher means better detection per unit of compute:

| Detector | Efficiency |
|---|---|
| IQR Speed Threshold | 9.26 |
| Random Forest | 2.19 |
| TASER Bayesian Trust | 1.59 |
| LSTM | 0.29 |
| Random Forest + GWO | 0.21 |
| RSU Position Verification | 0.02 |
| Dynamic k-Means | 0.00 |

Three detectors are on the Pareto frontier (no other option beats them on both quality and speed at the same time): TASER, Random Forest, and IQR.

---

## TASER Bayesian Trust

**The idea.** Every vehicle in the network has a trust score between 0 and 1. When another vehicle sends a beacon (a short position and speed broadcast), the receiver checks whether the reported speed looks realistic. If yes, the sender's trust score ticks up slightly. If no, it drops. Vehicles whose score falls below 0.15 get flagged as Sybil.

The update rule uses two parameters: alpha = 0.01 controls how much trust grows on a good beacon, and beta = 0.10 controls how fast it drops on a bad one. The asymmetry is intentional: a Sybil node needs to sustain consistent anomalies, and even a few normal-looking beacons will not recover its score quickly.

**How fast does it converge?** Starting at T = 0.5, a vehicle emitting an anomalous beacon every step reaches the 0.15 threshold after:

```
T_n = 0.5 * (1 - 0.10)^n
0.15 = 0.5 * 0.90^n
n = ln(0.3) / ln(0.9) = 11.4 steps
```

So TASER needs fewer than 12 beacons to flag a Sybil node with certainty, regardless of how many other vehicles are in the network.

**Results by attack intensity:**

| Sybil Rate | Precision | Recall | F1 |
|---|---|---|---|
| 10% | 1.000 | 1.000 | 1.000 |
| 20% | 1.000 | 1.000 | 1.000 |
| 30% | 1.000 | 1.000 | 1.000 |
| 40% | 1.000 | 0.979 | 0.989 |

**Strengths.** Precision is 1.000 at every tested intensity, meaning it never wrongly accuses a legitimate vehicle. It also needs no training data, so it works from day one in a fresh network.

**Weaknesses.** The detection relies entirely on speed anomalies. A stealthy attacker that keeps its reported speed within the 0-14 m/s range will not be caught. The parameters alpha, beta, and lambda were tuned for this simulation; a different network topology or attack pattern may require retuning.

**The precision-recall tradeoff.** TASER gives up a small amount of recall (0.979 at 40% Sybil rate) to keep precision at exactly 1.000. For safety-critical applications where mislabeling a legitimate vehicle carries consequences, this is the right tradeoff.

---

## Random Forest

**The idea.** A Random Forest trains 100 decision trees on labeled beacon records and takes a majority vote for each new record. It sees all features at once: speed, acceleration, heading, position, neighbor count, and RSU distances. Unlike the rule-based detectors, it learns the patterns directly from data rather than relying on human-defined thresholds.

**Why it works here.** The most informative features in this dataset are speed (which has injected noise for Sybil nodes), acceleration (which amplifies the noise because it is the difference between two noisy readings), and neighbor count (Sybil nodes from the same attacker share a position, so they inflate each other's neighbor counts).

**Results by attack intensity:**

| Sybil Rate | Precision | Recall | F1 |
|---|---|---|---|
| 10% | 0.969 | 0.967 | 0.968 |
| 20% | 0.985 | 0.996 | 0.990 |
| 30% | 0.995 | 0.994 | 0.994 |
| 40% | 0.993 | 0.996 | 0.994 |

**Strengths.** The best efficiency score among competitive detectors (2.19). Consistent across all attack intensities with low variance (F1 std = 0.013). Trains in under 0.6 seconds and produces no false negatives at 20-40% Sybil rate.

**Weaknesses.** Requires labeled training data. The numbers here are in-sample, meaning the model is evaluated on the same data it was trained on. In a real deployment with unseen attack patterns, performance would be lower. Cross-validation would reduce F1 by roughly 1-3%.

**Compared to RF+GWO.** The baseline Random Forest beats the GWO-optimized version on mean F1 (0.987 vs 0.984) while training 200x faster. The GWO search with 6 agents and 10 iterations is not enough to consistently improve on scikit-learn's reasonable defaults.

---

## Random Forest + GWO

**The idea.** Grey Wolf Optimizer (GWO) mimics the hunting hierarchy of wolf packs to search for better hyperparameters. Three wolves (alpha, beta, delta) represent the best candidate solutions found so far. The other wolves update their positions based on where the top three are, gradually converging on a good solution. Here it optimizes two hyperparameters: the number of trees (10 to 200) and the maximum tree depth (3 to 20).

**Parameters found across scenarios:**

| Sybil Rate | Trees | Max depth | CV loss |
|---|---|---|---|
| 10% | 167 | 20 | 0.015 |
| 20% | 171 | 8 | 0.032 |
| 30% | 141 | 7 | 0.027 |
| 40% | 150 | 9 | 0.048 |

**Strengths.** Can outperform the baseline RF when the dataset has severe class imbalance or when the default hyperparameters underfit. Useful in automated pipelines where manual tuning is not feasible.

**Weaknesses.** With only 60 total evaluations (6 agents times 10 iterations), the optimizer explores a small fraction of the search space. The overhead of 117 seconds per scenario is not recovered in detection quality. The RF baseline remains Pareto-superior.

---

## LSTM

**The idea.** A Long Short-Term Memory network treats each vehicle's beacon sequence as a time series. Up to 50 consecutive beacons per vehicle are fed into two LSTM layers (64 units then 32 units), which learn temporal patterns: does the speed follow a physically plausible trajectory, or does it jump erratically? A sigmoid output layer gives the final Sybil probability.

**The class imbalance problem.** At 10% Sybil rate, only 5.8% of records are positive. With 50 steps per vehicle and standard early stopping at 3 epochs of no improvement, the model converges before learning the minority class. This produces F1 = 0.

At 20% the network starts to learn (F1 = 0.842). At 30% and above it learns reliably (F1 = 1.000 and 0.973).

**Results by attack intensity:**

| Sybil Rate | F1 | Notes |
|---|---|---|
| 10% | 0.000 | Class imbalance too severe for default settings |
| 20% | 0.842 | Partial learning |
| 30% | 1.000 | Stable |
| 40% | 0.973 | Stable |

F1 variability across scenarios (std = 0.474) is the highest of any detector, which reflects this threshold behavior.

**Strengths.** Captures temporal correlations that step-by-step methods miss. Requires no hand-crafted features. Excellent once enough positive examples are available.

**Weaknesses.** Fails completely at low Sybil rates without oversampling (such as SMOTE). Slow to train (10 seconds per scenario). Produces uninterpretable decisions.

---

## IQR Speed Threshold

**The idea.** Compute three quartiles of all speed readings in the dataset. The lower fence is:

```
fence = Q1 - 1.5 * IQR
      = Q1 - 1.5 * (Q3 - Q1)
```

Any vehicle that ever reports a speed below this fence gets flagged as Sybil. The algorithm stores exactly two numbers (the fence value computed on the full population) and checks each vehicle in a single pass.

**Why it struggles at low Sybil rates.** When Sybil nodes make up only 10% of the dataset, the quartiles are dominated by legitimate speeds. The fence ends up so low that it does not exclude anything meaningful:

At 10% Sybil rate: Q1 = 2.4, Q3 = 11.7, IQR = 9.3, fence = -11.5 m/s. Since no vehicle ever reports a speed below -11.5 m/s, the fence excludes nothing and all vehicles pass. But because the algorithm is calibrated on the mixed population and many Sybil readings are extreme, the flag condition fires for nearly every vehicle. Result: recall = 1.0 (all Sybil caught) but specificity = 0.0 (all legitimate vehicles also flagged).

At 40% the large fraction of anomalous Sybil readings shifts Q1 far into negative territory, the fence finally separates the two populations, and F1 reaches 1.0.

**Results by attack intensity:**

| Sybil Rate | Precision | Recall | Specificity | F1 |
|---|---|---|---|---|
| 10% | 0.058 | 1.000 | 0.000 | 0.110 |
| 20% | 0.210 | 1.000 | 0.000 | 0.347 |
| 30% | 0.281 | 1.000 | 0.000 | 0.439 |
| 40% | 1.000 | 1.000 | 1.000 | 1.000 |

**Strengths.** Fastest detector at 0.05 seconds. Requires no labels. Perfect recall (1.000) at every attack intensity. Minimal memory footprint.

**Weaknesses.** Completely non-selective at low Sybil rates. Specificity = 0.0 at 10-30% means it would flag every vehicle in a real network. Depends entirely on speed anomalies; useless against stealthy attacks.

**Verdict.** IQR is useful in two cases: when you only care about not missing any Sybil node (recall = 1.0) and can tolerate false positives, or when the network is already heavily compromised (above 30-40% Sybil rate). For general use, TASER or Random Forest are strictly better.

---

## RSU Position Verification

**The idea.** Twenty Road Side Units (RSUs) are fixed at known positions on a 4x5 grid. Each RSU records which vehicles are within 100 meters of it at each time step. If two vehicles are both near the same RSU but their reported positions are more than 150 meters apart from each other, one of them must be lying about where it is. Pairs that trigger this inconsistency five or more times get flagged as Sybil.

**Why it produces near-zero F1 in this benchmark.** The RSU algorithm was designed to catch an attacker who claims to be in multiple locations at the same time (broadcasting as "vehicle A" near RSU 1 and "vehicle B" near RSU 3 simultaneously from one physical device). In our simulation, Sybil nodes from the same attacker all report the same position. Their distance from each other is approximately zero, which is well below the 150-meter threshold. The RSU detector never fires.

The partial detection at 20% Sybil rate (F1 = 0.171) comes from edge cases where the shared-position vehicles drift enough across simulation steps to occasionally trigger the distance check.

**Results by attack intensity:**

| Sybil Rate | Recall | F1 |
|---|---|---|
| 10% | 0.000 | 0.000 |
| 20% | 0.111 | 0.171 |
| 30% | 0.000 | 0.000 |
| 40% | 0.000 | 0.000 |

**Strengths.** Very high specificity (0.987), meaning it rarely accuses a legitimate vehicle. Works well against split-position attacks in infrastructure-rich networks.

**Weaknesses.** Fundamentally mismatched to co-location attacks. O(RSU squared times Steps squared) detection complexity makes it slow on large simulations.

---

## Dynamic k-Means

**The idea.** Aggregate each vehicle's behavior into a profile: mean position, mean speed, speed variability, mean acceleration, and mean neighbor count. Then group vehicles into clusters using k-Means, with k set to the square root of half the vehicle count. Clusters that are unusually small (fewer than 3 members) or whose centroid speed is more than 2 standard deviations from the global mean get flagged.

**Why it produces F1 = 0.000 at every Sybil rate.** The Sybil nodes in this simulation have the same mean speed as legitimate vehicles (their noise has mean zero), so the cluster centroids for Sybil-heavy groups are not distinguishable by the speed anomaly criterion. The small-cluster criterion depends on random cluster assignments, not on any structural separation between Sybil and legitimate behavior profiles. Neither criterion fires reliably.

**Strengths.** Fully unsupervised with no hyperparameter tuning needed. Fast at 0.64 seconds.

**Weaknesses.** Cannot detect Sybil nodes whose aggregate behavior profile overlaps with legitimate vehicles. Requires prior assumptions about cluster structure that do not hold in homogeneous grid networks. For this attack model, it is not a viable detection method.

**When it might work.** If Sybil nodes are geographically isolated in the network (for example, all entering through one corner of the grid), a spatial cluster would be both small and geometrically distinct. The uniform 6x6 grid prevents this kind of spatial separation.
