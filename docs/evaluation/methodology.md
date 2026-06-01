# Evaluation Methodology

## 1. Overview

This document defines the metrics, evaluation protocols, and statistical methods used in this benchmark. The central methodological contribution is the use of out-of-sample (OOS) evaluation with vehicle-level data splitting, which corrects a systematic overestimation of performance present in prior in-sample evaluations of supervised Sybil detection algorithms.

---

## 2. Evaluation Metrics

### 2.1 Confusion Matrix

All metrics are derived from the four basic counts computed on the test set:

| | Predicted Sybil | Predicted Legit |
|---|---|---|
| **Actual Sybil** | TP (True Positive) | FN (False Negative) |
| **Actual Legit** | FP (False Positive) | TN (True Negative) |

- **TP:** Sybil vehicle correctly classified as Sybil
- **FP:** Legitimate vehicle incorrectly classified as Sybil (false alarm)
- **FN:** Sybil vehicle incorrectly classified as Legitimate (missed detection)
- **TN:** Legitimate vehicle correctly classified as Legitimate

### 2.2 Metric Definitions

**Accuracy:**

```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
```

Fraction of all vehicles correctly classified. Misleading when classes are imbalanced.

**Precision (Positive Predictive Value):**

```
Precision = TP / (TP + FP)
```

Of all vehicles flagged as Sybil, what fraction are truly Sybil. High precision means few false alarms. In safety-critical applications (emergency vehicle authentication), Precision = 1.000 is a hard requirement.

**Recall (Sensitivity, True Positive Rate):**

```
Recall = TP / (TP + FN)
```

Of all actual Sybil vehicles, what fraction were detected. High recall means few missed detections.

**F1-Score:**

```
F1 = 2 * Precision * Recall / (Precision + Recall)
   = 2 * TP / (2 * TP + FP + FN)
```

Harmonic mean of precision and recall. Preferred over accuracy when classes are imbalanced, because it equally weights false positives and false negatives.

**Specificity (True Negative Rate):**

```
Specificity = TN / (TN + FP)
```

Fraction of legitimate vehicles correctly cleared. Complement of the false positive rate: Specificity = 1 - FPR. High specificity means legitimate vehicles are rarely disrupted.

**AUC-ROC (Area Under the Receiver Operating Characteristic Curve):**

The ROC curve plots Recall (TPR) on the y-axis against FPR = 1 - Specificity on the x-axis as the classification threshold varies from 0 to 1. AUC is the area under this curve:

```
AUC = integral from 0 to 1 of TPR(FPR) dFPR
```

AUC = 0.5 corresponds to random guessing; AUC = 1.0 means perfect separation. AUC is only defined for detectors that produce continuous probability scores (TASER's inverted trust score, RF's predict_proba, LSTM's sigmoid output).

### 2.3 Efficiency Metric

The efficiency score (used in scenario analysis) is:

```
efficiency = F1_mean / ln(fit_time_mean + 1)
```

This penalizes slower detectors while rewarding higher F1. The logarithm ensures that very fast detectors (< 1 second) are not excessively rewarded, and very slow ones are not excessively penalized.

---

## 3. The Data Leakage Problem

### 3.1 Definition

Data leakage in machine learning occurs when information from the evaluation set is available to the model during training. This leads to overly optimistic evaluation metrics that do not reflect real-world generalization.

In the VANET dataset, each vehicle generates approximately 500 records (one per simulation step). If the dataset is split by record (not by vehicle), the same vehicle's records appear in both the training and evaluation partitions. The model can memorize per-vehicle patterns (vehicle legit_42 at step 150 typically has speed 9.3 m/s) and exploit them at evaluation time, producing inflated F1 scores.

### 3.2 Formal Statement

Let D = {(x_i, y_i, v_i)}_{i=1}^N be the dataset, where:
- x_i: feature vector for record i
- y_i: binary label (0 = Legitimate, 1 = Sybil)
- v_i: vehicle identifier

A classifier f: x -> y is said to be evaluated **in-sample** if:

```
f is trained on D and evaluated on D
```

A classifier is evaluated **out-of-sample** if:

```
There exist D_train and D_test such that:
  D_train union D_test = D
  D_train intersection D_test = empty set
  f is trained on D_train and evaluated on D_test
```

**Vehicle-level OOS** further requires that:

```
V_train = {v_i : (x_i, y_i, v_i) in D_train}
V_test  = {v_i : (x_i, y_i, v_i) in D_test}
V_train intersection V_test = empty set
```

No vehicle appears in both partitions. This ensures the classifier cannot recognize test vehicles from training observations.

### 3.3 Empirical Impact

In this benchmark, Random Forest F1 under the two protocols:

| Sybil Rate | In-sample F1 | OOS F1 (5-fold CV) | Overestimate |
|---|---|---|---|
| 5% | ~0.967 | 0.665 | +45.4% |
| 10% | ~0.963 | 0.694 | +38.8% |
| 20% | ~0.990 | 0.954 | +3.8% |
| 30% | ~0.994 | 0.975 | +2.0% |
| 40% | ~0.996 | 0.967 | +3.0% |
| **Mean** | ~0.987 | 0.882 | **+11.9%** |

The overestimation is largest at low sybil rates (5-10%), where the classifier learns fewer positive examples and memorizes them more aggressively.

---

## 4. OOS Evaluation Protocols

### 4.1 For Random Forest: 5-Fold Cross-Validation by Vehicle ID

```
Input: D = dataset, k = 5

Step 1: Compute vehicle-level labels
  for each vehicle v:
    y_v = max(y_i for all records with vehicle_id = v)

Step 2: Stratified k-fold split on vehicle IDs
  folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
  for each fold:
    train_vehicle_ids, test_vehicle_ids = folds.split(vehicles, labels)

Step 3: For each fold:
  D_train = records where vehicle_id in train_vehicle_ids
  D_test  = records where vehicle_id in test_vehicle_ids

  Fit LabelEncoder on D_train.edge_id (prevents edge encoding leakage)
  Fit classifier on D_train
  Evaluate classifier on D_test

Step 4: Aggregate metrics across 5 folds
  Report: mean F1, std F1, mean Precision, mean Recall, mean Specificity
```

**Why StratifiedKFold:** Simple k-fold might place all Sybil vehicles in a single fold (especially at low sybil rates where there are few Sybil vehicles). Stratified folding ensures each fold has a similar Sybil/Legitimate vehicle ratio.

**Why LabelEncoder on training data only:** The edge_id feature is categorical. If it is encoded using all edge IDs (including test), the encoding implicitly reveals which edges appear in the test distribution, a subtle form of leakage. Encoding on training data only ensures consistency.

### 4.2 For LSTM: 80/20 Vehicle-Level Split

```
Input: D = dataset

Step 1: Compute vehicle-level labels (same as above)

Step 2: Split 80/20 by vehicle ID (stratified)
  train_vids, test_vids = train_test_split(
    vehicle_ids, stratify=y_vehicle, test_size=0.20, random_state=42
  )

Step 3: Partition dataset
  D_train = records where vehicle_id in train_vids
  D_test  = records where vehicle_id in test_vids

Step 4: Fit StandardScaler on D_train features ONLY
  scaler = StandardScaler().fit(D_train[features])

Step 5: Build and train LSTM on D_train
  X_train = scaler.transform(D_train[features])
  model.fit(X_train, y_train, validation_split=0.15, early_stopping)

Step 6: Evaluate on D_test (held-out vehicles)
  X_test = scaler.transform(D_test[features])   // same scaler from training
  y_pred = model.predict(X_test) >= 0.5
  OOS_metrics = {F1, Precision, Recall, Specificity}

Step 7: Retrain on full D for production use
  (not used for metrics -- only for the production predict() method)
```

**Why 80/20 instead of 5-fold for LSTM:** Training an LSTM involves backpropagation through time, which is computationally expensive. Running 5 full training cycles (one per fold) would require approximately 85 seconds per dataset (5 * 17s), totaling approximately 11 minutes for all 8 datasets. The 80/20 single split achieves comparable reliability at 1/5 the cost.

### 4.3 For Unsupervised Detectors (TASER, IQR, RSU, k-Means)

These detectors do not use labels during fitting. There is no train/test leakage:
- TASER: trust scores are updated from speed observations only, not from labels
- IQR: computes fence from the speed distribution, not from labels
- RSU: computes position co-presence from position data, not from labels
- k-Means: clusters from behavioral profiles, not from labels

All four are evaluated on the full labeled dataset, where the labels are used only to compute the evaluation metrics (TP, FP, FN, TN), never to guide the detection logic.

---

## 5. Experimental Design

### 5.1 Reproducibility

All experiments use random seed 42 for:
- Vehicle route generation (randomTrips.py)
- Sybil speed noise (Gaussian sampling in collect_dataset.py)
- Train/test splits (random_state=42 in StratifiedKFold and train_test_split)
- RF and LSTM initialization (random_state=42, tf.random.set_seed(42))
- Bootstrap resampling (numpy default_rng(42))

Given the same seed, every number in the benchmark results is exactly reproducible.

### 5.2 Evaluation Grid

All 7 detectors are evaluated at all 8 sybil rates (5%, 10%, 15%, 20%, 25%, 30%, 35%, 40%), producing 56 measurement points total. Statistical comparisons use all 8 observations per detector as paired samples.

### 5.3 Limitations

- **Single random seed:** All results correspond to one specific realization of the random processes. Multiple seeds would provide confidence intervals but were not feasible within the computational budget.
- **Single topology:** Results may not generalize to highway or random topologies.
- **Single attack model:** Only co-location + speed injection is tested.

---

## 6. Statistical Tests

All statistical tests are performed in `results/generate_proofs.py` using the scipy library. Results are in `analysis/statistical_proofs.md`. A summary:

| Test | Purpose | n per group |
|---|---|---|
| Kruskal-Wallis H-test | Overall comparison of all 7 detectors | 8 per detector |
| Wilcoxon signed-rank | Pairwise comparison (key pairs) | 8 paired |
| Bootstrap 95% CI | Mean F1 confidence interval | 10,000 resamples |
| Cohen's d | Effect size for key comparisons | 8 per group |
| Linear regression | F1 trend vs sybil rate | 8 per detector |

See [docs/evaluation/statistical_analysis.md](statistical_analysis.md) for the full test results with computed values.
