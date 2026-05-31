# Computational Complexity Analysis

Variables used throughout:

- N = total number of beacon records in the dataset
- V = number of unique vehicles
- T = number of simulation time steps
- F = number of features per record
- R = number of RSUs
- k = number of clusters (k-Means)
- E = number of estimators (Random Forest)
- D = maximum tree depth
- L = LSTM sequence length (fixed at 50)
- H = LSTM hidden units
- A = number of GWO search agents
- I = number of GWO iterations

Note: N = V * T in the worst case (every vehicle active at every step).
In our benchmark N is between 7 754 and 12 000, V between 85 and 130,
T = 500, F = 8.

---

## Per-detector complexity

### IQR Speed Threshold

**Training (fit):**

1. Compute Q1, Q3 on N speed values: sorting takes O(N log N).
2. Compute fence: O(1).
3. Flag vehicles with at least one reading below fence: one pass O(N).

Total fit: **O(N log N)**

Space: **O(1)** (stores two floats).

**Prediction:** O(N) - one lookup per row.

---

### RSU Position Verification

**Training (fit):**

1. For each of T steps, find vehicles within RSU_RANGE of each RSU:
   R RSUs x (V vehicles per step) distances = O(R * V) per step.
2. For each RSU, check all pairs of nearby vehicles:
   worst case O(V^2) pairs per RSU per step.
3. Total: O(T * R * V^2)

In our setup: T=500, R=20, V~100 -> 500 * 20 * 10000 = **100 million operations** (the O(RSU^2 * Steps^2) noted in the code refers to a quadratic growth with both dimensions simultaneously).

Total fit: **O(T * R * V^2)**

Space: **O(V^2)** for the pair frequency dictionary.

**Prediction:** O(V) - set membership test per vehicle.

---

### TASER Bayesian Trust

**Training (fit):**

1. Iterate over all N records (sorted by step): O(N log N) for sort.
2. Update trust score for each record: O(1) per record.
3. Final classification: O(V).

Total fit: **O(N log N)** dominated by sort; effectively **O(N)** if data is pre-sorted.

Space: **O(V)** - one float per vehicle.

**Prediction:** O(N) - set membership per row.

---

### Random Forest

**Training (fit, full):**

1. LabelEncode edge_id: O(N).
2. Train E trees, each on a bootstrap sample of N with sqrt(F) features at
   each split, up to depth D: O(E * N * sqrt(F) * D * log N).
3. In practice E=100, F=8, D=10: roughly O(N log N) per tree.

Total fit: **O(E * N * sqrt(F) * D * log N)**

**Training (5-fold CV by vehicle_id):**

5 folds x the above = **O(5 * E * N * sqrt(F) * D * log N)**

Space: **O(E * 2^D)** for tree storage.

**Prediction:** O(E * D) per record = **O(N * E * D)** total.

---

### Random Forest + GWO

**Training:**

GWO runs A agents for I iterations. Each iteration evaluates all agents
using 3-fold CV = A * I * 3 RandomForest trainings.

Total: **O(A * I * 3 * E * N * sqrt(F) * D * log N)**

With A=6, I=10: 180 RF trainings on top of one final full fit.

Space: same as RF plus O(A * 2) for wolf positions.

---

### LSTM

**Training (80/20 vehicle-id split + full retrain):**

1. Build sequences: O(N) padding operations, total O(N * L).
2. One epoch of training: O(N/B * L * H^2) where B=batch_size=32.
3. Total with max_epochs=20 early-stopped: O(epochs * N * L * H^2).
4. Full retrain on all data: same complexity.

Effective: **O(epochs * N * L * H^2)**

In our benchmark: L=50, H=64 (first layer), epochs~10-15 with early stopping.

Space: **O(L * H + H^2)** for weights; O(N * L * F) for input tensor.

**Prediction:** O(V * L * H^2) - forward pass per vehicle sequence.

---

### Dynamic k-Means

**Training (fit):**

1. Aggregate V vehicle profiles: O(N) (groupby).
2. StandardScaler: O(V * F_agg) where F_agg=6 aggregated features.
3. k-Means with k = sqrt(V/2) ~ 7, n_init=10:
   O(n_init * k * V * F_agg * convergence_steps).
   k-Means typically converges in O(1/epsilon) steps.

Total fit: **O(N + V * F_agg * k * n_init)**

Space: **O(k * F_agg)** for centroids.

**Prediction:** O(V) - set membership per vehicle.

---

## Summary table

| Detector | Fit complexity | Prediction | Space |
|---|---|---|---|
| IQR | O(N log N) | O(N) | O(1) |
| RSU Position Verification | O(T * R * V^2) | O(N) | O(V^2) |
| TASER Bayesian Trust | O(N log N) | O(N) | O(V) |
| Random Forest (full fit) | O(E * N * sqrt(F) * D * log N) | O(N * E * D) | O(E * 2^D) |
| Random Forest (5-fold CV) | O(5 * E * N * sqrt(F) * D * log N) | same | same |
| Random Forest + GWO | O(A * I * 3 * E * N * sqrt(F) * D * log N) | same | same + O(A) |
| LSTM | O(epochs * N * L * H^2) | O(V * L * H^2) | O(N * L * F) |
| Dynamic k-Means | O(N + V * F_k * k * n_init) | O(N) | O(k * F_k) |

---

## Empirical verification

The measured training times confirm the theoretical ordering:

| Detector | Theoretical order | Measured avg (s) | Consistent? |
|---|---|---|---|
| IQR | O(N log N) | 0.05 | Yes (essentially constant at N~10k) |
| TASER | O(N) | 0.87 | Yes |
| Dynamic k-Means | O(N) | 0.64 | Yes |
| Random Forest | O(E * N * log N) | 0.57 | Yes (parallelised, n_jobs=-1) |
| LSTM | O(N) per epoch, ~15 epochs | 10.0 | Yes |
| RSU | O(T * R * V^2) | 11.3 | Yes (100M ops @ ~10M ops/s) |
| Random Forest + GWO | O(180 * RF) | 117 | Yes |

The only surprise is that RSU (11.3 s) is slower than LSTM (10.0 s) despite a
simpler algorithm, because the V^2 inner loop is implemented in pure Python
while LSTM uses TensorFlow's optimised C++ backend.

---

## Scalability projections

For a real VANET with V=1000 vehicles and T=3600 steps (1 hour):

| Detector | Projected fit time | Feasible for online use? |
|---|---|---|
| IQR | ~0.5 s | Yes |
| TASER | ~8 s | Yes |
| Random Forest | ~6 s | Yes |
| LSTM | ~100 s | With GPU, yes |
| RSU | ~6 hours | No (needs algorithmic optimization) |
| RF + GWO | ~20 min | Only for offline tuning |
