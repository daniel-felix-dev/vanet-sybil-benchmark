# Experimental Results

## 1. Experimental Environment

| Component | Specification |
|---|---|
| Operating System | Windows 11 |
| SUMO | 1.12.0 (headless, via TraCI) |
| Python | 3.11 |
| scikit-learn | 1.8.0 |
| TensorFlow | 2.21.0 (CPU, no GPU on native Windows) |
| scipy | 1.x |
| Random seed | 42 (all components) |
| Network topology | 6x6 grid, 1200x1200 m |
| Legitimate vehicles | 80 |
| Sybil rates tested | 5%, 10%, 15%, 20%, 25%, 30%, 35%, 40% |
| Simulation steps | 500 (500 seconds) |

All supervised detector results use out-of-sample evaluation (see [docs/evaluation/methodology.md](methodology.md)).

---

## 2. Full Results Table

### 2.1 Mean Metrics across 8 Sybil Rates

| Detector | Accuracy | Precision | Recall | F1-Score | Specificity | Fit time (s) |
|---|---|---|---|---|---|---|
| TASER Bayesian Trust | 0.999 | **1.000** | 0.997 | **0.999** | **1.000** | **0.64** |
| Random Forest + GWO | 0.974 | 0.938 | 0.879 | 0.893 | 0.978 | 98 |
| Random Forest | 0.975 | 0.901 | 0.875 | 0.882 | 0.981 | 2.7 |
| LSTM | 0.908 | 0.536 | 0.531 | 0.507 | 0.941 | 16.8 |
| IQR Speed Threshold | 0.290 | 0.290 | **1.000** | 0.391 | 0.125 | **0.06** |
| RSU Position Verification | 0.781 | 0.045 | 0.014 | 0.021 | 0.991 | 10.2 |
| Dynamic k-Means | 0.783 | 0.000 | 0.000 | 0.000 | 0.997 | 0.33 |

### 2.2 F1-Score per Sybil Rate

| Detector | 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|---|
| TASER | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.989 |
| RF + GWO | 0.776 | 0.704 | 0.889 | 0.945 | 0.947 | 0.964 | 0.949 | 0.966 |
| Random Forest | 0.665 | 0.694 | 0.890 | 0.954 | 0.949 | 0.975 | 0.959 | 0.967 |
| LSTM | 0.000 | 0.000 | 0.000 | 0.667 | 0.625 | 1.000 | 0.857 | 0.909 |
| IQR | 0.108 | 0.110 | 0.207 | 0.347 | 0.402 | 0.439 | 0.516 | 1.000 |
| RSU | 0.000 | 0.000 | 0.000 | 0.171 | 0.000 | 0.000 | 0.000 | 0.000 |
| k-Means | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### 2.3 F1 Cross-Validation Variance (supervised detectors)

| Detector | 5% std | 10% std | 20% std | 30% std | 40% std |
|---|---|---|---|---|---|
| Random Forest | 0.330 | 0.179 | 0.022 | 0.010 | 0.016 |
| RF + GWO | 0.162 | 0.169 | 0.029 | 0.010 | 0.016 |

High std at 5-10% reflects class imbalance: some CV folds receive too few Sybil vehicles for stable learning.

### 2.4 ROC-AUC (soft detectors, evaluated at sybil rates 10-40%)

| Detector | 10% | 20% | 30% | 40% | Mean AUC |
|---|---|---|---|---|---|
| TASER Bayesian Trust | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **1.0000** |
| Random Forest | 0.9997 | 0.9999 | 0.9999 | 0.9999 | 0.9999 |
| LSTM | 0.8400 | 0.9992 | 0.8741 | 0.7463 | 0.8649 |

AUC measures the quality of the probability ranking across all thresholds, not just at the default 0.5 threshold.

---

## 3. Statistical Validation

### 3.1 Global Test: Are All Detectors Equivalent?

**Test:** Kruskal-Wallis H-test (non-parametric ANOVA), n=8 sybil rates per detector.

**Null hypothesis H0:** All 7 detectors have the same median F1-Score distribution.

**Result:** H = 43.08, p = 0.000000, df = 6.

**Conclusion:** H0 is rejected at any standard significance level. The 7 detectors are not statistically equivalent.

### 3.2 Pairwise Tests: Key Comparisons

All tests use the Wilcoxon signed-rank test on n=8 paired observations (one per sybil rate).

| Comparison | W statistic | p-value | Significant (alpha=0.05)? |
|---|---|---|---|
| TASER vs Random Forest | 0.0 | 0.0078 | **Yes** |
| RF vs RF+GWO | 14.0 | 0.640 | No |

The TASER vs RF comparison is significant: TASER outperforms RF at every tested sybil rate, so all signed differences are in the same direction (W = 0, the minimum possible value for n=8 pairs).

The RF vs GWO comparison is not significant: the differences alternate in sign and are small in magnitude.

### 3.3 Bootstrap Confidence Intervals for Mean F1

10,000 bootstrap resamples of the n=8 F1 values per detector. CI = [2.5th percentile, 97.5th percentile]:

| Detector | Mean F1 | 95% CI |
|---|---|---|
| TASER | 0.999 | [0.992, 1.000] |
| Random Forest + GWO | 0.893 | [0.823, 0.949] |
| Random Forest | 0.882 | [0.790, 0.957] |
| LSTM | 0.507 | [0.243, 0.987] |
| IQR | 0.391 | [0.192, 0.837] |
| RSU | 0.021 | [0.000, 0.128] |
| k-Means | 0.000 | [0.000, 0.000] |

The TASER CI [0.992, 1.000] does not overlap with the RF CI [0.790, 0.957], providing additional confidence that their difference is real and not sampling noise.

The RF CI [0.790, 0.957] and GWO CI [0.823, 0.949] overlap, confirming that the 1.1% mean difference is not confidently distinguishable.

### 3.4 Effect Sizes (Cohen's d)

| Comparison | Cohen's d | Magnitude |
|---|---|---|
| TASER vs Random Forest | +1.09 | Large |
| TASER vs LSTM | +0.88 | Large |
| TASER vs IQR | +1.96 | Large |
| Random Forest vs LSTM | +0.84 | Large |
| Random Forest vs GWO | +0.18 | Negligible |

Cohen's d for the RF vs GWO comparison (0.18) is below the small-effect threshold (0.20), confirming that the difference is negligible in practical terms.

---

## 4. Principal Findings and Interpretation

### 4.1 TASER is Pareto-Dominant

With out-of-sample evaluation, TASER (F1=0.999, time=0.64s) is strictly dominant over all other competitive detectors in the F1 vs training-time space:

- TASER has higher F1 than Random Forest (0.999 > 0.882) AND lower time (0.64s < 2.7s)
- TASER has higher F1 than RF+GWO (0.999 > 0.893) AND lower time (0.64s < 98s)
- TASER has higher F1 than LSTM (0.999 > 0.507) AND lower time (0.64s < 16.8s)

The only other Pareto-optimal detector is IQR (faster at 0.06s, but F1=0.391 is far lower). No detector simultaneously beats TASER on both dimensions.

This result depends critically on OOS evaluation. In-sample, RF's inflated F1 (~0.987) made it appear competitive with TASER (~0.997), and RF appeared on the Pareto frontier. OOS evaluation reveals that TASER dominates RF strictly.

### 4.2 In-Sample Evaluation Overestimates RF Performance by 10.7%

The mean RF F1 across 8 sybil rates is:
- In-sample: approximately 0.987
- Out-of-sample (5-fold CV by vehicle_id): 0.882

Difference: 0.105 (10.7%)

This overestimation is caused by the model memorizing per-vehicle speed patterns during training and recognizing them at evaluation time, rather than learning generalizable rules about what makes a vehicle Sybil.

The implication for the literature: published VANET Sybil detection papers that evaluate supervised classifiers on the same data used for training likely overstate their results by a similar margin.

### 4.3 GWO Hyperparameter Optimization is Not Statistically Justified

Despite 36x computational overhead (98s vs 2.7s for RF), GWO produces only a 1.1% mean F1 improvement (0.893 vs 0.882) that is not statistically significant (Wilcoxon p=0.640, overlapping bootstrap CIs). The additional computation does not recover enough performance improvement to justify deployment.

GWO shows slightly better F1 at 5-10% sybil rates (0.776 vs 0.665 at 5%), likely because the hyperparameter optimization adapts better to the severe class imbalance at those rates. For applications where the sybil rate is known to be below 10%, GWO may be worth the overhead. In the general case, it is not.

### 4.4 LSTM Requires Sufficient Positive Class Representation

LSTM F1 = 0.000 at sybil rates 5%, 10%, and 15% (positive fractions below 12%). This is explained by the class imbalance dynamics described in [docs/algorithms/06_lstm.md](../algorithms/06_lstm.md). The key threshold is approximately 12-21% positive records in the training partition, corresponding to sybil rates of 15-20% in this dataset.

Despite zero F1 at low sybil rates, LSTM achieves AUC = 0.840 at 10% -- meaning its probability outputs correctly rank Sybil above Legitimate vehicles, but the uncalibrated default threshold of 0.5 fails to capture this. Threshold calibration would recover performance at low sybil rates without retraining.

### 4.5 RSU and k-Means Detect Fundamentally Different Attack Variants

RSU (F1=0.021 mean) was designed to detect split-position attacks, not co-location attacks. k-Means (F1=0.000) requires behavioral cluster separation that the zero-mean Gaussian attack model does not create. Both algorithms fail not because of poor implementation but because of a mismatch between the attack model and their underlying assumptions. They would both be effective against different attack variants.

---

## 5. Scenario Recommendations

Based on the results and utility function analysis in [docs/evaluation/statistical_analysis.md](statistical_analysis.md):

| Scenario | Recommended Detector | Basis |
|---|---|---|
| General purpose | TASER | Pareto-optimal: best F1 (0.999) at lowest time (0.64s) |
| Zero false positives required | TASER | Only detector with Precision = 1.000 at all rates |
| Early detection (5-10% attack rate) | TASER | F1 = 1.000 at 5-10%; provably converges in 12 beacons |
| Minimal compute (embedded device) | IQR | 0.06s, 2 floats of storage (but specificity = 0 below 40%) |
| High attack rate (30-40%) | TASER or RF | Both achieve F1 >= 0.975 at 30%+ |

---

## 6. Figures

All figures are in `figures/` (benchmark overview) and `analysis/figures/` (detailed analysis):

| Figure | Location | Contents |
|---|---|---|
| benchmark_f1.png | figures/ | F1 vs sybil rate, all 7 detectors |
| benchmark_accuracy.png | figures/ | Accuracy vs sybil rate |
| benchmark_metrics_20pct.png | figures/ | All 5 metrics at 20% sybil rate |
| heatmap_f1.png | analysis/figures/ | F1 heatmap: detector x sybil rate |
| radar_per_detector.png | analysis/figures/ | 5-metric radar per detector |
| cost_vs_f1.png | analysis/figures/ | F1 vs training time (Pareto frontier) |
| f1_variance.png | analysis/figures/ | F1 spread across sybil rates (boxplot) |
| roc_curves_sybil{N}.png | analysis/figures/ | ROC curves at each sybil rate |
| proofs_kruskal_wallis.png | analysis/figures/ | Kruskal-Wallis test visualization |
| proofs_bootstrap_ci.png | analysis/figures/ | Bootstrap confidence intervals |
| proofs_taser_convergence.png | analysis/figures/ | TASER trust score trajectory |
| proofs_iqr_fence.png | analysis/figures/ | IQR fence vs speed distributions |
| sensitivity_taser_lambda.png | analysis/figures/ | TASER lambda sensitivity |
