# Random Forest Sybil Detector

**Source:** [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet)
**Reimplementation:** `detectors/rf_detector.py`
**Category:** Supervised machine learning
**Requires labeled data:** Yes (vehicle-level labels used for 5-fold CV)

---

## 1. Objective

Train an ensemble of decision trees on labeled beacon features to distinguish Sybil from legitimate vehicles. The Random Forest classifier learns feature thresholds and combinations that discriminate the two classes, without requiring any explicit specification of what constitutes anomalous behavior.

---

## 2. Theoretical Background

### 2.1 Decision Trees

A decision tree is a binary classifier that partitions the feature space by recursively splitting on one feature at a time. Each internal node tests a feature threshold (e.g., speed > 14.2 m/s?), and each leaf node predicts a class label. Decision trees are fast to train and predict, but individual trees are sensitive to the specific training sample used.

### 2.2 Bootstrap Aggregation (Bagging)

Breiman (1996) introduced bagging as a way to reduce the variance of individual trees. Given a training set of N records, E bootstrap samples of size N are drawn with replacement. One tree is trained on each bootstrap sample. The final prediction for a new record is the majority vote across all E trees.

The key insight is that trees trained on different bootstrap samples will disagree on boundary cases, but will agree on clear cases. Averaging over disagreements reduces the variance without substantially increasing the bias.

### 2.3 Random Feature Subsampling

At each split in each tree, only a random subset of sqrt(F) features (where F is the total number of features) is considered. This further decorrelates the trees: if one feature dominates the dataset, bagging alone would produce very similar trees (all splitting on that feature first). Random feature subsampling ensures that other features get represented in at least some trees.

---

## 3. The Data Leakage Problem

### 3.1 Formal Definition

Let D = {(x_i, y_i, v_i)} be the dataset, where x_i is the feature vector for record i, y_i is the binary Sybil label, and v_i is the vehicle identifier. Vehicle v has multiple records (one per time step): all records with v_i = v form a time series of 500 rows.

**In-sample evaluation** (incorrect): train on D, evaluate on D. The classifier sees every record in both training and evaluation. It can learn per-vehicle patterns at training time (vehicle legit_42 always has speed near 9.3 m/s at step 150) and exploit them at evaluation time.

**Vehicle-level out-of-sample evaluation** (correct): partition the set of unique vehicle IDs V into disjoint subsets V_train and V_test. Let:

```
D_train = {(x, y, v) : v in V_train}
D_test  = {(x, y, v) : v in V_test}
```

The classifier trained on D_train has never seen any record from a vehicle in V_test. It can only use learned feature-level patterns (speed distributions, acceleration statistics) to classify test vehicles.

### 3.2 Why Row-Level Splitting is Insufficient

A common but incorrect approach splits rows randomly into 80% train / 20% test. Because each vehicle produces ~500 rows, a random split with high probability puts some rows from every vehicle in both train and test partitions. The classifier sees vehicle v's rows at training time and recognizes them at evaluation time, inflating F1.

### 3.3 Empirical Impact

In this benchmark, the same Random Forest trained on the 20% sybil dataset achieves:
- In-sample F1 (evaluated on training data): approximately 0.987
- Out-of-sample F1 (5-fold CV by vehicle_id): 0.954

The difference is 3.3 percentage points at 20% sybil rate. At 5% sybil rate (fewer Sybil vehicles, more unstable training signal), the gap is larger: approximately 0.665 OOS vs approximately 0.96 in-sample.

Across all 8 sybil rates, the mean F1 drops from approximately 0.987 (in-sample) to 0.882 (OOS), a 10.7% overestimate due to data leakage.

---

## 4. Out-of-Sample Evaluation Protocol

### 4.1 5-Fold Stratified Cross-Validation by Vehicle ID

```
Algorithm RF_CV(D, k=5):
    // Build vehicle-level labels (one per vehicle)
    for each vehicle v:
        y_v = max(y_i for all records i with vehicle_id = v)
                // 1 if any record is Sybil, else 0

    // Stratified k-fold split on vehicle IDs
    folds = StratifiedKFold(n_splits=k, shuffle=True).split(V, y_V)

    results = []
    for each (train_vehicles, test_vehicles) in folds:
        D_train = {records where vehicle_id in train_vehicles}
        D_test  = {records where vehicle_id in test_vehicles}

        // Fit LabelEncoder on training edge_ids only
        le = LabelEncoder().fit(D_train.edge_id)
        X_train = encode_features(D_train, le)
        X_test  = encode_features(D_test,  le)

        // Train classifier
        clf = RandomForestClassifier(n_estimators=100, max_depth=10,
                                     class_weight="balanced")
        clf.fit(X_train, y_train)

        // Evaluate on held-out vehicles
        y_pred = clf.predict(X_test)
        results.append(compute_metrics(y_test, y_pred))

    return mean(results), std(results)
```

**Why the LabelEncoder is fit on training data only:** The edge_id feature is categorical. If it were encoded using all edge IDs (including test), the encoding would leak information about the test distribution. Fitting on training data only ensures the test edges are encoded using only the mapping learned from training edges.

### 4.2 Feature Set

The 8 features used:

| Feature | Role |
|---|---|
| `speed` | Primary Sybil signal (Gaussian noise injection) |
| `accel` | Amplified noise signal (delta of two noisy readings) |
| `angle` | Heading: legitimate vehicles follow road geometry |
| `x`, `y` | Position: Sybil cluster at attacker location |
| `n_neighbors` | Co-location inflates neighbor counts |
| `min_rsu_dist` | Spatial context |
| `mean_rsu_dist` | Spatial context |
| `edge_enc` | Label-encoded road segment |

---

## 5. Complexity Analysis

**Training (single fit):**

The dominant cost is training E = 100 trees. Each tree is trained by:
1. Drawing a bootstrap sample: O(N)
2. Building the tree: at each of D = 10 levels, for each split candidate, evaluate sqrt(F) features on N/2^level samples.

Overall per-tree: O(N * sqrt(F) * D * log N) where the log N factor comes from sorting each feature.

Total fit: O(E * N * sqrt(F) * D * log N)

With E=100, N=9153, F=8, D=10:
Approximately: 100 * 9153 * 2.83 * 10 * 13.1 = 339 million operations.

**5-fold CV fit:**
5 * O(E * N * sqrt(F) * D * log N)

**Prediction:**

For each record, traverse E = 100 trees to depth D = 10: O(E * D) per record.
Total: O(N * E * D)

**Space:**

Each tree stores approximately 2^D = 1024 nodes (upper bound for a full binary tree of depth D).
Total for E trees: O(E * 2^D) = O(100 * 1024) = O(100,000) nodes.
In practice less, because trees are pruned and rarely fully balanced.

**Scalability notes:**

scikit-learn parallelizes tree training with `n_jobs=-1` (all CPU cores). Measured training time of 2.7 seconds for ~10,000 records is consistent with the theoretical complexity.

---

## 6. Hyperparameter Choices

| Hyperparameter | Value | Rationale |
|---|---|---|
| n_estimators | 100 | Standard baseline; more trees reduce variance with diminishing returns |
| max_depth | 10 | Prevents overfitting to individual training records |
| class_weight | "balanced" | Compensates for class imbalance (more legitimate than Sybil records) |
| random_state | 42 | Reproducibility |

---

## 7. Results (OOS, 5-fold CV by vehicle_id)

| Sybil Rate | F1 | F1 std | Precision | Recall | Specificity |
|---|---|---|---|---|---|
| 5% | 0.665 | 0.330 | 0.724 | 0.622 | 0.993 |
| 10% | 0.694 | 0.179 | 0.866 | 0.594 | 0.995 |
| 15% | 0.890 | 0.072 | 0.894 | 0.890 | 0.985 |
| 20% | 0.954 | 0.022 | 0.938 | 0.974 | 0.981 |
| 25% | 0.949 | 0.027 | 0.926 | 0.975 | 0.971 |
| 30% | 0.975 | 0.010 | 0.968 | 0.981 | 0.987 |
| 35% | 0.959 | 0.025 | 0.938 | 0.981 | 0.967 |
| 40% | 0.967 | 0.016 | 0.950 | 0.985 | 0.966 |
| **Mean** | **0.882** | **0.128** | **0.901** | **0.875** | **0.981** |

**Note on high variance at low sybil rates:** At 5% sybil rate, F1_std = 0.330. This reflects that with only 443 Sybil records out of 7,754 total (5.71%), some CV folds receive too few Sybil vehicles in the training partition to learn a stable decision boundary. Those folds produce F1 = 0 or near 0, while folds with more Sybil vehicles produce near-perfect F1. The spread between folds drives the high standard deviation.

**ROC-AUC:** 0.9999 mean across sybil rates 10%-40%. The class probabilities output by `predict_proba()` nearly perfectly separate Sybil from legitimate vehicles in probability space, even when the operating-point F1 is lower.

---

## 8. Strengths

- Strong generalization (F1 = 0.975 OOS at 30%) without requiring domain-specific feature engineering.
- Fast training (2.7 s) compared to GWO (98 s) and LSTM (16.8 s).
- Parallelizable across CPU cores.
- Robust to missing or irrelevant features (random feature subsampling naturally downweights unhelpful features).

---

## 9. Weaknesses

- Requires labeled training data. Cannot be deployed in a network with no prior attack history.
- Performance degrades sharply at low sybil rates (<15%) due to class imbalance, even with `class_weight="balanced"`.
- Black-box: individual predictions cannot be easily explained.

---

## 10. Possible Improvements

- **SMOTE oversampling:** Synthetic Minority Oversampling Technique (Chawla et al., 2002) generates synthetic Sybil records to balance the class distribution at low sybil rates, potentially recovering performance below 15%.
- **Threshold calibration:** Instead of using the default 0.5 decision threshold, calibrate using Platt scaling or isotonic regression to optimize for precision or recall depending on the deployment priority.
- **Online learning:** Random Forests can be extended to incremental learning (e.g., Mondrian forests) to update the model as new labeled data arrives without full retraining.

---

## 11. References

Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5-32.

Breiman, L. (1996). Bagging predictors. *Machine Learning*, 24(2), 123-140.

Chawla, N. V., Bowyer, K. W., Hall, L. O., and Kegelmeyer, W. P. (2002). SMOTE: Synthetic Minority Over-sampling Technique. *Journal of Artificial Intelligence Research*, 16, 321-357.

Sakthi Sahana V. (2024). *sybil-attack-detection-vanet*. GitHub repository. https://github.com/126160042-crypto/sybil-attack-detection-vanet
