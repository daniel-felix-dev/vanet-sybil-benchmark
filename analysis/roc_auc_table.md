# ROC AUC Summary

AUC values for detectors that produce probability scores.
Hard classifiers (IQR, RSU, k-Means) produce a single operating point
and do not have a meaningful AUC.

| Detector | 10% | 20% | 30% | 40% | Mean AUC |
|---|---|---|---|---|---|
| LSTM | 0.5706  |  0.9975  |  0.8856  |  0.9453 | 0.8498 |
| Random Forest | 0.9997  |  0.9999  |  0.9999  |  0.9999 | 0.9999 |
| TASER Bayesian Trust | 1.0000  |  1.0000  |  1.0000  |  1.0000 | 1.0000 |

## Interpretation

AUC = 1.0 means the detector perfectly separates Sybil from legitimate at every
possible threshold. AUC = 0.5 is equivalent to random guessing.

An AUC close to 1.0 for TASER confirms that the trust score is a reliable
Sybil indicator, not just at the default lambda = 0.15 threshold, but across
the entire operating range. The same applies to Random Forest's class probabilities.