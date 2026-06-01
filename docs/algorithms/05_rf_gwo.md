# Random Forest + Grey Wolf Optimizer

**Source:** [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet)
**Reimplementation:** `detectors/gwo_rf_detector.py`
**Category:** Supervised ML with metaheuristic hyperparameter optimization
**Requires labeled data:** Yes

---

## 1. Objective

Use the Grey Wolf Optimizer (GWO) to find better hyperparameters for the Random Forest classifier than the defaults, then evaluate the resulting model out-of-sample via 5-fold CV by vehicle_id. The hypothesis is that optimizing n_estimators and max_depth for the specific class distribution improves generalization performance.

---

## 2. Theoretical Background

### 2.1 Hyperparameter Optimization

Machine learning models have hyperparameters -- settings that control the learning algorithm rather than being learned from data. For Random Forest, n_estimators (number of trees) and max_depth (maximum tree depth) are the two most impactful hyperparameters. Their optimal values depend on the specific dataset: a highly imbalanced dataset (many more legitimate than Sybil records) may benefit from shallower trees to reduce the tendency to learn majority-class rules.

Grid search and random search are common approaches to hyperparameter optimization, but they scale poorly with the number of hyperparameters. Metaheuristic optimization methods -- genetic algorithms, particle swarm optimization, grey wolf optimization -- can find good solutions with fewer objective function evaluations.

### 2.2 The Grey Wolf Optimizer

The GWO (Mirjalili et al., 2014) is a population-based optimization algorithm inspired by the social hierarchy and hunting behavior of grey wolves. It requires only two user-defined parameters (number of agents and number of iterations) and is designed for continuous optimization problems.

**Wolf hierarchy:**
- Alpha (alpha): the best solution found so far (lowest fitness value)
- Beta (beta): the second-best solution
- Delta (delta): the third-best solution
- Omega wolves: all other agents, which update positions relative to alpha, beta, delta

**Fitness function:** For a candidate hyperparameter vector theta = (n_estimators, max_depth):

```
fitness(theta) = 1 - accuracy(RF(theta), D_train, k=3)
```

where RF(theta) denotes a Random Forest with hyperparameters theta, evaluated via 3-fold cross-validation on D_train.

---

## 3. Mathematical Formulation

### 3.1 Position Update Equations

At each iteration, every omega wolf i updates its position based on the alpha, beta, and delta wolves:

```
A_j = 2 * a * r1_j - a,   C_j = 2 * r2_j
```

where a decreases linearly from 2 to 0 over N_ITER iterations, and r1_j, r2_j are uniform random numbers in [0, 1].

```
D_alpha_j = |C_1 * pos_alpha_j - pos_i_j|
X1_j = pos_alpha_j - A_1 * D_alpha_j

D_beta_j = |C_2 * pos_beta_j - pos_i_j|
X2_j = pos_beta_j - A_2 * D_beta_j

D_delta_j = |C_3 * pos_delta_j - pos_i_j|
X3_j = pos_delta_j - A_3 * D_delta_j

pos_i_j_new = (X1_j + X2_j + X3_j) / 3
```

The new position is the average of three weighted steps toward alpha, beta, and delta.

### 3.2 Search Space

```
n_estimators in [10, 200]   (integer after rounding)
max_depth in [3, 20]         (integer after rounding)
```

Total discrete combinations: 191 * 18 = 3,438.

With N_AGENTS = 6 and N_ITER = 10, the optimizer evaluates 6 * 10 = 60 candidate solutions, each requiring a 3-fold CV training run. This means GWO explores approximately 60 / 3438 = 1.75% of the search space.

---

## 4. Why GWO Provides No Statistically Confirmed Benefit

**Statistical evidence:**

| Test | Result |
|---|---|
| Wilcoxon signed-rank RF vs GWO (n=8 rates) | W = 14.0, p = 0.640 |
| Bootstrap 95% CI for RF mean F1 | [0.790, 0.957] |
| Bootstrap 95% CI for GWO mean F1 | [0.823, 0.949] |

The p-value of 0.640 is far above the standard alpha = 0.05 significance threshold. The bootstrap confidence intervals overlap substantially. The 1.1% mean F1 difference (GWO: 0.893 vs RF: 0.882) is not statistically distinguishable from zero.

**Why this happens:**

1. scikit-learn's defaults (n_estimators=100, max_depth=10) are already well-calibrated for medium-sized classification datasets. The GWO search rarely finds significantly better values.

2. With only 60 evaluations across 3,438 candidates, GWO is likely to miss the true optimum and return a locally good but globally suboptimal solution.

3. The 3-fold CV fitness function is itself noisy (different random splits each call), which can mislead the wolf position updates.

**Optimal parameters found (per scenario):**

| Sybil Rate | n_estimators | max_depth | CV loss |
|---|---|---|---|
| 5% | 32 | 19 | 0.015 |
| 10% | 167 | 20 | 0.015 |
| 15% | 126 | 5 | 0.036 |
| 20% | 171 | 8 | 0.032 |
| 25% | 182 | 9 | 0.047 |
| 30% | 141 | 7 | 0.027 |
| 35% | 139 | 5 | 0.050 |
| 40% | 150 | 9 | 0.048 |

The variability in optimal parameters across scenarios (max_depth ranging from 5 to 20) suggests the GWO search is not converging to a stable optimum but rather finding different local solutions in each run.

---

## 5. Out-of-Sample Evaluation Protocol

GWO finds hyperparameters using the full dataset, then those fixed hyperparameters are evaluated via 5-fold CV by vehicle_id -- identical to the RF OOS protocol. This ensures RF and GWO are compared under identical evaluation conditions:

```
Procedure GWO_RF.cv_evaluate(D, k=5):
    // Use GWO to find best hyperparameters on full D
    best_params = GWO.optimize(D)

    // Create RF with those fixed params
    rf_oos = RandomForestClassifier(**best_params)

    // Evaluate via 5-fold CV by vehicle_id
    return rf_oos.cv_evaluate(D, k=k)
```

---

## 6. Complexity Analysis

**GWO optimization phase:**

Each of the N_AGENTS * N_ITER = 60 candidate evaluations requires a 3-fold CV on the full dataset:

```
O(60 * 3 * E * N * sqrt(F) * D * log N)
```

where E, N, F, D have the same meaning as in the RF analysis.

**OOS evaluation phase:**

```
O(5 * E_best * N * sqrt(F) * D_best * log N)
```

where E_best and D_best are the GWO-found optimal parameters.

**Total:**

```
O((180 + 5) * E * N * sqrt(F) * D * log N)   approximately O(185 * E * N * sqrt(F) * D * log N)
```

This is 37x more computation than RF's 5-fold CV (which requires only 5 * E * ...). The measured overhead is 98 s vs 2.7 s for RF, a factor of 36.

---

## 7. Results (OOS, 5-fold CV by vehicle_id)

| Sybil Rate | F1 | F1 std | Precision | Recall | Specificity |
|---|---|---|---|---|---|
| 5% | 0.776 | 0.162 | 0.987 | 0.663 | 1.000 |
| 10% | 0.704 | 0.169 | 0.976 | 0.576 | 0.999 |
| 15% | 0.889 | 0.059 | 0.883 | 0.900 | 0.984 |
| 20% | 0.945 | 0.029 | 0.919 | 0.975 | 0.975 |
| 25% | 0.947 | 0.030 | 0.923 | 0.976 | 0.970 |
| 30% | 0.964 | 0.010 | 0.952 | 0.977 | 0.979 |
| 35% | 0.949 | 0.027 | 0.919 | 0.982 | 0.955 |
| 40% | 0.966 | 0.016 | 0.948 | 0.985 | 0.964 |
| **Mean** | **0.893** | **0.063** | **0.938** | **0.879** | **0.978** |

GWO shows slightly higher F1 at low sybil rates (5%: GWO 0.776 vs RF 0.665) where the hyperparameter tuning helps with class imbalance. At moderate to high rates (20-40%), the difference is within 1% and statistically indistinguishable.

---

## 8. Strengths

- Provides marginal F1 improvement at low sybil rates (5-10%) where class imbalance is most severe.
- Automatically adapts hyperparameters to the specific dataset distribution.

---

## 9. Weaknesses

- 36x computational overhead (98 s vs 2.7 s for RF) with no statistically confirmed benefit at rates >= 15%.
- GWO explores only 1.75% of the hyperparameter search space -- likely misses the true optimum.
- Results vary between runs due to random initialization of wolf positions.

---

## 10. References

Mirjalili, S., Mirjalili, S. M., and Lewis, A. (2014). Grey Wolf Optimizer. *Advances in Engineering Software*, 69, 46-61.

Sakthi Sahana V. (2024). *sybil-attack-detection-vanet*. GitHub repository. https://github.com/126160042-crypto/sybil-attack-detection-vanet
