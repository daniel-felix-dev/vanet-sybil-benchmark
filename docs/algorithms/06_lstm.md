# LSTM Temporal Sybil Detector

**Source:** [SaiKumar-1608 Dual-Layer Framework](https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL)
**Reimplementation:** `detectors/lstm_detector.py`
**Category:** Deep learning (supervised)
**Requires labeled data:** Yes

---

## 1. Objective

Treat each vehicle's beacon history as a time series and classify it as Sybil or legitimate using a Long Short-Term Memory (LSTM) network. The hypothesis is that temporal patterns -- correlations between speed values across consecutive steps -- provide discrimination beyond what single-step features offer.

---

## 2. Theoretical Background

### 2.1 Sequential Data in VANETs

Vehicle beacons are inherently sequential: each vehicle emits one beacon per second, and consecutive beacons are correlated because vehicle speed and position change smoothly over time. A legitimate vehicle accelerating from 0 to 50 km/h will show a gradual speed increase over 10-20 steps. A Sybil vehicle injecting Gaussian noise will show no such correlation: consecutive speed values are statistically independent.

Standard classifiers (Random Forest, SVM) treat each beacon record independently. They cannot directly model the correlation structure of consecutive records from the same vehicle. Recurrent neural networks (RNNs) and their gated variant, LSTM, are designed for exactly this setting.

### 2.2 LSTM Architecture

Hochreiter and Schmidhuber (1997) introduced the Long Short-Term Memory (LSTM) to address the vanishing gradient problem that prevents standard RNNs from learning long-range dependencies. An LSTM cell maintains a cell state C_t (long-term memory) and a hidden state h_t (short-term memory), updated by three gating mechanisms:

**Forget gate:** determines what fraction of the previous cell state to discard:

```
f_t = sigmoid(W_f * [h_{t-1}, x_t] + b_f)
```

**Input gate:** determines what new information to add to the cell state:

```
i_t = sigmoid(W_i * [h_{t-1}, x_t] + b_i)
C_tilde_t = tanh(W_C * [h_{t-1}, x_t] + b_C)
C_t = f_t * C_{t-1} + i_t * C_tilde_t
```

**Output gate:** determines the hidden state from the cell state:

```
o_t = sigmoid(W_o * [h_{t-1}, x_t] + b_o)
h_t = o_t * tanh(C_t)
```

---

## 3. Architecture Specification

```
Input: (n_vehicles, SEQ_LEN=50, n_features=8)
   |
Masking (mask_value=0.0)         -- ignores padded steps for short sequences
   |
LSTM(units=64, return_sequences=True)
   |
Dropout(rate=0.3)
   |
LSTM(units=32)
   |
Dropout(rate=0.3)
   |
Dense(units=16, activation='relu')
   |
Dense(units=1, activation='sigmoid')

Optimizer: Adam (learning_rate=0.001)
Loss: binary crossentropy
Metric: accuracy
Early stopping: patience=3 epochs, restore_best_weights=True
Maximum epochs: 20
Batch size: 32
Validation split: 15% of training data
```

**Sequence construction:** Each vehicle's records are sorted by step and used as the time series. Sequences shorter than SEQ_LEN = 50 steps are left-padded with zeros; sequences longer are truncated to the first 50 steps. The Masking layer ensures that padded zeros do not contribute to the LSTM's gradient updates.

**Input features:** speed, accel, angle, x, y, n_neighbors, min_rsu_dist, mean_rsu_dist (8 features). All features are standardized using a StandardScaler fitted on the training partition only.

---

## 4. The Class Imbalance Problem

### 4.1 Why LSTM Fails Below 15% Sybil Rate

At 5% sybil rate, the dataset contains 443 Sybil records out of 7,754 total (5.71%). After splitting 80/20 by vehicle_id for OOS evaluation, the training partition has approximately 80% of vehicles, of which 5.71% are Sybil. The effective training positive fraction is approximately 5.71%.

For a binary classifier with 5.71% positive records, the baseline strategy of always predicting "Legitimate" achieves 94.29% accuracy. Cross-entropy loss reward for predicting the majority class:

```
loss(always_Legit) = -(0.9429 * log(0.9429 + epsilon) + 0.0571 * log(epsilon))
```

With a small epsilon (before the network learns to recognize Sybil vehicles), this is approximately:

```
loss = -(0.9429 * log(0.9429)) + 0.0571 * C    (C = some large constant)
```

With early stopping at patience = 3 epochs and 20 maximum epochs, the network terminates before the gradient signal from the 5.71% minority class overrides the gradient signal from the 94.29% majority class. The result is F1 = 0.

### 4.2 Empirical Threshold

| Sybil Rate | Positive fraction | LSTM F1 |
|---|---|---|
| 5% | 5.71% | 0.000 |
| 10% | 5.82% | 0.000 |
| 15% | 11.54% | 0.000 |
| 20% | 21.00% | 0.667 |
| 25% | 25.14% | 0.625 |
| 30% | 28.13% | 1.000 |
| 35% | 34.73% | 0.857 |
| 40% | 39.78% | 0.909 |

The transition from F1 = 0 to F1 > 0 occurs between 15% and 20% sybil rate, corresponding to approximately 12-21% positive records in the training partition. This is consistent with the general finding in deep learning literature that models require approximately 10-15% minority fraction for stable learning without specialized handling.

### 4.3 AUC vs Operating-Point F1

At 20% sybil rate, the LSTM achieves AUC = 0.9992 despite F1 = 0.667. This apparent contradiction is explained by the decision threshold:

- AUC measures the quality of the probability ranking across all possible thresholds.
- F1 at the default threshold (0.5) reflects performance at one specific operating point.

The sigmoid output is not calibrated for the imbalanced distribution: it may produce outputs in [0.1, 0.3] for actual Sybil vehicles (correct ranking, AUC near 1) while the default threshold of 0.5 still classifies them as Legitimate. Calibrating the threshold (e.g., using the validation set to find the threshold that maximizes F1) would substantially improve the reported F1.

---

## 5. Out-of-Sample Evaluation Protocol

```
Procedure LSTM.fit(D):
    // Split vehicles 80/20 by vehicle_id (stratified)
    train_vids, test_vids = stratified_split(vehicle_ids, y_vehicle, test_size=0.20)

    D_train = {records where vehicle_id in train_vids}
    D_test  = {records where vehicle_id in test_vids}

    // Fit scaler on training data ONLY
    scaler = StandardScaler().fit(D_train[features])

    // Build sequences
    X_train, y_train = build_sequences(D_train, scaler)
    X_test,  y_test  = build_sequences(D_test,  scaler)

    // Train on 80%
    model_tmp = build_LSTM()
    model_tmp.fit(X_train, y_train, early_stopping)

    // Evaluate on held-out 20%
    self.test_metrics_ = evaluate(model_tmp, X_test, y_test)

    // Retrain on FULL dataset for production use
    scaler_all = StandardScaler().fit(D[features])
    X_all, y_all = build_sequences(D, scaler_all)
    self.model = build_LSTM()
    self.model.fit(X_all, y_all, early_stopping)
```

The `evaluate()` call at the split returns the OOS metrics stored in `self.test_metrics_`. When `benchmark.py` calls `det.evaluate(df)`, the LSTM overrides the base class method to return these stored OOS metrics rather than recomputing on the full dataset.

---

## 6. Complexity Analysis

**Training (single pass on full dataset):**

Each epoch processes N/batch_size batches. Each batch requires one forward pass and one backward pass through the LSTM:

```
O(epochs * N * SEQ_LEN * H^2)
```

where H = 64 (first LSTM layer units). The H^2 factor comes from the LSTM gate computations, which involve matrix multiplications of dimension H x H for the hidden-to-hidden weights.

With epochs ~15 (average with early stopping), N = 9153, SEQ_LEN = 50, H = 64:
Approximately 15 * 9153 * 50 * 4096 = 28 billion multiplications.
On CPU this takes approximately 10-15 seconds per dataset.

**Two passes per call to fit():** OOS evaluation trains once on 80% data, production training trains once on 100% data. Total: approximately 2x the single-pass cost.

**Space:**
- Input tensor: O(V * SEQ_LEN * n_features) where V = number of unique vehicles
- Model weights: O(H^2 + H * n_features) for LSTM gates
- Total: O(V * SEQ_LEN * n_features) dominates at N = 10,000 records

---

## 7. Results (OOS, 80/20 vehicle-level split)

Values are means over 5 seeds. F1 values at 5-15% are near zero due to class imbalance.

| Sybil Rate | F1 | Precision | Recall | Specificity | AUC |
|---|---|---|---|---|---|
| 5% | 0.000 | 0.000 | 0.000 | 1.000 | -- |
| 10% | 0.160 | 0.100 | 0.400 | 0.929 | 0.840 |
| 15% | 0.248 | 0.156 | 0.700 | 0.600 | -- |
| 20% | 0.635 | 0.667 | 0.650 | 0.906 | 0.999 |
| 25% | 0.490 | 0.533 | 0.480 | 0.929 | -- |
| 30% | 0.782 | 0.893 | 0.800 | 0.953 | 0.874 |
| 35% | 0.718 | 0.775 | 0.675 | 0.988 | -- |
| 40% | 0.824 | 0.901 | 0.780 | 0.953 | 0.746 |
| **Mean** | **0.482** | **0.503** | **0.561** | **0.907** | **0.865** |

---

## 8. Strengths

- Captures temporal correlations that step-wise classifiers miss.
- Excellent AUC (0.865 mean, 0.999 at 20%) when the positive class is adequately represented.
- No feature engineering required beyond raw beacon data.

---

## 9. Weaknesses

- F1 = 0 at sybil rates below 15% due to class imbalance.
- Slow training (16.8 s per dataset).
- High variance (F1 std = 0.437) across sybil rates.
- Black-box: individual predictions cannot be interpreted.
- Threshold calibration required for optimal operating-point F1.

---

## 10. Possible Improvements

- **SMOTE oversampling** before training to address class imbalance at low sybil rates.
- **Threshold calibration** using the validation set to find the optimal decision boundary.
- **Attention mechanism** to highlight which time steps were most influential in the classification.
- **Bidirectional LSTM** to capture patterns in both forward and backward temporal directions.

---

## 11. References

Hochreiter, S. and Schmidhuber, J. (1997). Long Short-Term Memory. *Neural Computation*, 9(8), 1735-1780.

SaiKumar-1608 (2024). *Dual-Layer Sybil Detection Framework*. GitHub. https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL

Chawla, N. V. et al. (2002). SMOTE: Synthetic Minority Over-sampling Technique. *JAIR*, 16, 321-357.
