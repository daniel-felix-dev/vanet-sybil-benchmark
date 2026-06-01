# VANET Sybil Detection Benchmark

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![SUMO](https://img.shields.io/badge/SUMO-1.12.0-green)](https://eclipse.dev/sumo/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Abstract

Sybil attacks in Vehicular Ad-hoc Networks (VANETs) allow a single malicious device to create multiple fake identities, corrupting cooperative driving decisions such as traffic signal coordination, collision avoidance, and emergency routing. Prior comparative studies of Sybil detection algorithms are methodologically inconsistent: each algorithm is evaluated in a different simulator, on a different road topology, and with a different attack model, making it impossible to determine which technique genuinely performs better.

This benchmark addresses that gap by fixing the simulation environment and varying only the detection algorithm. Seven algorithms from six independent open-source repositories are reimplemented in Python, evaluated against the same SUMO-generated dataset, and assessed using rigorous out-of-sample protocols that prevent the data leakage found in prior in-sample evaluations. The principal finding is that TASER, a Bayesian trust-score method that requires no labeled training data, achieves F1 = 0.999 across 8 sybil rate scenarios and strictly dominates all other detectors on both detection quality and computational cost.

---

## Background

### Vehicular Ad-hoc Networks

A VANET is a decentralized communication network in which vehicles exchange short broadcast messages (beacons) at 1 Hz using the IEEE 802.11p wireless standard. Each beacon carries the sender's claimed identity, position, speed, and heading. Downstream systems use these beacons for cooperative perception: a vehicle may slow down because a beacon from an ahead vehicle reports a sudden deceleration, or a traffic management center may redirect traffic based on reported congestion.

The correctness of these decisions depends entirely on the trustworthiness of beacon senders. VANETs have no central authentication authority by design (infrastructure availability cannot be guaranteed in all scenarios), which leaves them vulnerable to identity-based attacks.

### Sybil Attacks

A Sybil attack, first formally described by Douceur (2002), occurs when a single physical device creates and maintains multiple fake network identities (Sybil nodes). In the VANET context, a single attacker device can simultaneously broadcast as a dozen or more fake vehicles, each reporting a distinct (or identical) position and fabricated telemetry. Consequences include:

- **Phantom traffic jam**: Sybil nodes report stopped vehicles on a clear road, causing legitimate vehicles to take detours.
- **Emergency vehicle spoofing**: Sybil nodes impersonate emergency vehicles to manipulate signal priority.
- **Cooperative collision avoidance corruption**: Sybil nodes inject false hazard warnings to cause unnecessary braking.
- **Routing manipulation**: Sybil nodes dominate routing protocols by controlling a majority of identities in a geographic area.

### The Evaluation Problem

Published detection algorithms are typically evaluated in the simulator and scenario that each research group had available. TASER (Morton et al.) was evaluated in OMNeT++ with Veins and SUMO. The IQR method (Suratwala) was evaluated in a standalone OMNeT++ simulation. RSU-based verification (Karthik) was evaluated in SUMO with Python. Machine learning approaches (Sakthi) were evaluated on a pre-generated dataset of 75,000 records. These environments differ in network topology, vehicle density, attack model, and evaluation metric definitions, so the reported numbers cannot be compared directly.

This benchmark resolves the comparison problem by:

1. Fixing the simulation (SUMO 1.12.0, 6x6 grid, 80 legitimate vehicles, identical seeds).
2. Fixing the attack model (co-location + speed injection, 5 attackers, 8 sybil rate scenarios).
3. Applying identical out-of-sample evaluation protocols to all supervised detectors.
4. Running all algorithms in the same Python process, on the same hardware, against the same datasets.

---

## Repository Structure

```
vanet-sybil-benchmark/
│
├── README.md                        This file
│
├── benchmark.py                     Main entry point. Runs all 7 detectors against
│                                    all 8 sybil-rate datasets and saves metrics + charts.
│
├── simulation/
│   ├── network.net.xml              Road network: 6x6 grid, 200m cells, 1200x1200m total
│   ├── generate_routes.py           Generates .rou.xml files via randomTrips + duarouter
│   ├── make_configs.py              Generates .sumocfg files
│   ├── collect_dataset.py           Runs SUMO via TraCI, records per-vehicle features
│   ├── run_multi_seed.py            Multi-seed orchestrator (5 seeds x 8 rates)
│   ├── routes_sybil{N}.rou.xml      Pre-generated route files (N = 5,10,...,40)
│   └── scenario_sybil{N}.sumocfg   SUMO configuration files
│
├── detectors/
│   ├── __init__.py                  Exports ALL_DETECTORS list
│   ├── base_detector.py             Abstract base: fit(), predict(), evaluate(), predict_proba()
│   ├── iqr_detector.py              IQR Speed Threshold
│   ├── rsu_detector.py              RSU Position Verification
│   ├── taser_detector.py            TASER Bayesian Trust Score
│   ├── rf_detector.py               Random Forest (5-fold CV by vehicle_id)
│   ├── gwo_rf_detector.py           Random Forest + Grey Wolf Optimizer
│   ├── lstm_detector.py             LSTM (80/20 vehicle-level split)
│   └── kmeans_detector.py           Dynamic k-Means Clustering
│
├── results/
│   ├── datasets/                    dataset_sybil{5,10,15,20,25,30,35,40}.csv
│   ├── metrics/                     benchmark_results.csv (56 rows)
│   ├── generate_analysis.py         Produces 8 analysis charts + math_justifications.txt
│   ├── generate_roc.py              Produces ROC curves and AUC table
│   ├── generate_sensitivity.py      Hyperparameter sensitivity (TASER, RSU, IQR)
│   └── generate_proofs.py           11 statistical tests, proofs, and proof figures
│
├── figures/                         4 benchmark overview charts (PNG, 150 dpi)
│
├── analysis/
│   ├── figures/                     16 detailed charts (analysis + proofs + sensitivity)
│   ├── math_justifications.txt      Utility scores, Pareto frontier, dominance matrix
│   ├── statistical_proofs.md        All 11 statistical tests with computed results
│   ├── roc_auc_table.md             AUC values per detector per sybil rate
│   └── sensitivity_report.md        Hyperparameter sensitivity tables
│
└── docs/
    ├── setup.md                     Complete environment setup guide
    ├── simulation/
    │   ├── attack_model.md          Sybil attack model and simulation parameters
    │   └── data_collection.md       TraCI data collection methodology
    ├── algorithms/
    │   ├── overview.md              Comparative summary of all 7 algorithms
    │   ├── 01_iqr.md                IQR Speed Threshold
    │   ├── 02_rsu.md                RSU Position Verification
    │   ├── 03_taser.md              TASER Bayesian Trust Score
    │   ├── 04_random_forest.md      Random Forest with OOS evaluation
    │   ├── 05_rf_gwo.md             Random Forest + Grey Wolf Optimizer
    │   ├── 06_lstm.md               LSTM for temporal Sybil detection
    │   └── 07_kmeans.md             Dynamic k-Means Clustering
    └── evaluation/
        ├── methodology.md           OOS evaluation protocol and metric definitions
        ├── results.md               Full results tables and statistical interpretation
        └── statistical_analysis.md  All statistical tests with context and discussion
```

---

## Dependencies

| Software | Version | Installation |
|---|---|---|
| Python | 3.9+ | [python.org](https://www.python.org/) |
| SUMO | 1.12.0+ | [eclipse.dev/sumo](https://eclipse.dev/sumo/) |
| scikit-learn | 1.0+ | `pip install scikit-learn` |
| TensorFlow | 2.11+ | `pip install tensorflow` |
| pandas | any | `pip install pandas` |
| numpy | any | `pip install numpy` |
| matplotlib | any | `pip install matplotlib` |
| scipy | any | `pip install scipy` |

Full installation instructions are in [docs/setup.md](docs/setup.md).

Quick install after SUMO is set up:

```bash
pip install scikit-learn tensorflow pandas numpy matplotlib scipy
```

---

## Quick Start

```bash
# 1. Generate route files for all 8 sybil rates
python simulation/generate_routes.py

# 2. Generate SUMO configuration files
python simulation/make_configs.py

# 3. Collect datasets via TraCI (~35 seconds)
python simulation/collect_dataset.py

# 4. Run the benchmark (~60 min with GWO, ~8 min without)
python benchmark.py

# 5. Generate detailed analysis charts and statistical proofs
python results/generate_analysis.py
python results/generate_roc.py
python results/generate_sensitivity.py
python results/generate_proofs.py
```

Results are saved to `results/metrics/benchmark_results.csv`. Charts go to `figures/` and `analysis/figures/`.

---

## Algorithm Overview

| # | Algorithm | Category | Source Repository | Requires Labels |
|---|---|---|---|---|
| 1 | IQR Speed Threshold | Statistical | [MohammedSuratwala/SybilDetection](https://github.com/MohammedSuratwala/SybilDetection) | No |
| 2 | RSU Position Verification | Positional | [karthik-047/Detecting-Sybil-Attacks-in-VANETs](https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs) | No |
| 3 | TASER Bayesian Trust | Probabilistic | [morton-t/VANET-Simulations](https://github.com/morton-t/VANET-Simulations) | No |
| 4 | Random Forest | ML supervised | [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet) | Yes |
| 5 | Random Forest + GWO | ML optimized | [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet) | Yes |
| 6 | LSTM | Deep learning | [SaiKumar-1608/Dual-Layer-Framework](https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL) | Yes |
| 7 | Dynamic k-Means | Clustering | [Gideon-Adele/Dynamic-k-means-Clustering](https://github.com/Gideon-Adele/Dynamic-k-means-Clustering) | No |

Detailed documentation for each algorithm is in `docs/algorithms/`.

---

## Results

All numbers below are **out-of-sample (OOS)**. Supervised detectors use vehicle-level train/test splits: 5-fold cross-validation by vehicle_id for Random Forest and RF+GWO, and 80/20 vehicle-level split for LSTM. No detector is evaluated on data it trained on.

### Mean performance across 8 sybil rates (5% to 40%)

| Detector | Accuracy | Precision | Recall | F1-Score | Specificity | Training time |
|---|---|---|---|---|---|---|
| **TASER Bayesian Trust** | **0.999** | **1.000** | 0.997 | **0.999** | **1.000** | **0.64 s** |
| Random Forest + GWO | 0.974 | 0.938 | 0.879 | 0.893 | 0.978 | 98 s |
| Random Forest | 0.975 | 0.901 | **0.875** | 0.882 | 0.981 | 2.7 s |
| LSTM | 0.908 | 0.536 | 0.531 | 0.507 | 0.941 | 16.8 s |
| IQR Speed Threshold | 0.290 | 0.290 | **1.000** | 0.391 | 0.125 | 0.06 s |
| RSU Position Verification | 0.781 | 0.045 | 0.014 | 0.021 | 0.991 | 10.2 s |
| Dynamic k-Means | 0.783 | 0.000 | 0.000 | 0.000 | 0.997 | 0.33 s |

### F1-Score by sybil rate

| Detector | 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|---|
| TASER | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.989 |
| RF + GWO | 0.776 | 0.704 | 0.889 | 0.945 | 0.947 | 0.964 | 0.949 | 0.966 |
| Random Forest | 0.665 | 0.694 | 0.890 | 0.954 | 0.949 | 0.975 | 0.959 | 0.967 |
| LSTM | 0.000 | 0.000 | 0.000 | 0.667 | 0.625 | 1.000 | 0.857 | 0.909 |
| IQR | 0.108 | 0.110 | 0.207 | 0.347 | 0.402 | 0.439 | 0.516 | 1.000 |
| RSU | 0.000 | 0.000 | 0.000 | 0.171 | 0.000 | 0.000 | 0.000 | 0.000 |
| k-Means | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### ROC-AUC (soft detectors, evaluated at sybil rates 10%, 20%, 30%, 40%)

| Detector | 10% | 20% | 30% | 40% | Mean AUC |
|---|---|---|---|---|---|
| TASER Bayesian Trust | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **1.0000** |
| Random Forest | 0.9997 | 0.9999 | 0.9999 | 0.9999 | 0.9999 |
| LSTM | 0.8400 | 0.9992 | 0.8741 | 0.7463 | 0.8649 |

### Statistical validation

| Test | Result | Interpretation |
|---|---|---|
| Kruskal-Wallis (all detectors, n=8) | H = 43.08, p = 0.000000 | Detectors are not statistically equivalent |
| Wilcoxon: TASER vs RF | W = 0.0, p = 0.0078 | TASER is significantly better than RF |
| Wilcoxon: RF vs RF+GWO | W = 14.0, p = 0.640 | Not significant -- GWO adds no confirmed benefit |
| Bootstrap 95% CI for RF | [0.790, 0.957] | -- |
| Bootstrap 95% CI for RF+GWO | [0.823, 0.949] | Overlaps with RF interval |

---

## Principal Findings

**1. TASER is Pareto-dominant.** With out-of-sample evaluation, TASER achieves higher mean F1 (0.999) than any other detector while also training faster (0.64 s) than any competitive alternative. No other detector beats it on both dimensions simultaneously, placing it alone at the Pareto frontier together with IQR (which is faster but far less accurate). This result was not visible in earlier in-sample evaluations because RF's F1 appeared competitive at 0.987.

**2. In-sample evaluation inflates supervised detector performance by 10%.** Random Forest F1 drops from 0.987 (in-sample) to 0.882 (5-fold CV by vehicle_id, out-of-sample), a 10.7% overestimate. This finding has implications for the literature: published comparisons that do not split by entity ID may substantially overstate generalization performance.

**3. GWO hyperparameter optimization provides no statistically confirmed benefit over baseline RF.** The 1.1% mean F1 difference (GWO: 0.893 vs RF: 0.882) is not significant at alpha = 0.05 (Wilcoxon p = 0.640, overlapping bootstrap CIs). GWO costs 36x more training time (98 s vs 2.7 s).

**4. LSTM fails below 15% sybil rate due to class imbalance.** With fewer than 12% positive records, the model defaults to predicting all-Legitimate. TASER converges to flag a Sybil node in at most 12 beacons regardless of attack rate, making it the correct choice for early-phase detection.

**5. RSU Position Verification is model-incompatible with co-location attacks.** The RSU algorithm flags vehicle pairs that are seen near the same RSU but whose reported positions are more than 150 m apart. Co-location attacks report the same position (distance = 0 m), which is below the threshold. This is not a tuning failure but a fundamental incompatibility between the algorithm's assumption and the attack model.

Full analysis, scenario recommendations, and statistical proofs are in the `docs/` and `analysis/` directories.

---

## Documentation Index

| Document | Contents |
|---|---|
| [docs/setup.md](docs/setup.md) | Prerequisites, installation, path configuration, troubleshooting |
| [docs/simulation/attack_model.md](docs/simulation/attack_model.md) | Sybil attack model, network topology, simulation parameters |
| [docs/simulation/data_collection.md](docs/simulation/data_collection.md) | TraCI interface, feature extraction, dataset statistics |
| [docs/algorithms/overview.md](docs/algorithms/overview.md) | Side-by-side algorithm comparison, complexity table |
| [docs/algorithms/01_iqr.md](docs/algorithms/01_iqr.md) | IQR: theory, math, complexity, results |
| [docs/algorithms/02_rsu.md](docs/algorithms/02_rsu.md) | RSU: theory, detection logic, model incompatibility analysis |
| [docs/algorithms/03_taser.md](docs/algorithms/03_taser.md) | TASER: Bayesian update proof, convergence derivation, sensitivity |
| [docs/algorithms/04_random_forest.md](docs/algorithms/04_random_forest.md) | RF: OOS protocol, data leakage analysis, CV variance |
| [docs/algorithms/05_rf_gwo.md](docs/algorithms/05_rf_gwo.md) | GWO: wolf optimizer equations, why benefit is unconfirmed |
| [docs/algorithms/06_lstm.md](docs/algorithms/06_lstm.md) | LSTM: architecture, class imbalance analysis, AUC vs F1 |
| [docs/algorithms/07_kmeans.md](docs/algorithms/07_kmeans.md) | k-Means: clustering approach, why it fails, when it could work |
| [docs/evaluation/methodology.md](docs/evaluation/methodology.md) | OOS protocols, metric definitions, data leakage formal definition |
| [docs/evaluation/results.md](docs/evaluation/results.md) | Full results tables, figures, critical discussion |
| [docs/evaluation/statistical_analysis.md](docs/evaluation/statistical_analysis.md) | All 11 statistical tests with computed values |
| [analysis/statistical_proofs.md](analysis/statistical_proofs.md) | Auto-generated: tests run on current benchmark_results.csv |
| [analysis/roc_auc_table.md](analysis/roc_auc_table.md) | Auto-generated: AUC values |
| [analysis/sensitivity_report.md](analysis/sensitivity_report.md) | Auto-generated: hyperparameter sensitivity |

---

## References

1. Douceur, J. R. (2002). *The Sybil Attack*. International Workshop on Peer-to-Peer Systems (IPTPS). Springer, Berlin, Heidelberg.

2. Raya, M., and Hubaux, J.-P. (2007). *Securing vehicular ad hoc networks*. Journal of Computer Security, 15(1), 39-68.

3. Grover, J., Lim, M. K., and Singh, K. (2011). *Sybil attack in platooning vehicular networks*. Second International Conference on Vehicular Infrastructure Technology and Application.

4. Breiman, L. (2001). *Random Forests*. Machine Learning, 45(1), 5-32.

5. Hochreiter, S., and Schmidhuber, J. (1997). *Long Short-Term Memory*. Neural Computation, 9(8), 1735-1780.

6. Mirjalili, S., Mirjalili, S. M., and Lewis, A. (2014). *Grey Wolf Optimizer*. Advances in Engineering Software, 69, 46-61.

7. MacQueen, J. (1967). *Some methods for classification and analysis of multivariate observations*. Proceedings of the 5th Berkeley Symposium on Mathematical Statistics and Probability.

8. ETSI EN 302 637-2 (2019). *Intelligent Transport Systems (ITS); Vehicular Communications; Basic Set of Applications; Part 2: Specification of Cooperative Awareness Basic Service*.

9. German, R., Dressler, F., and Sommer, C. (2008). *Car2X communication: Sensing, controlling, and actuating in vehicular networks*. IEEE Transactions on Vehicular Technology.

10. Lopez, P. A., et al. (2018). *Microscopic Traffic Simulation using SUMO*. 21st International Conference on Intelligent Transportation Systems.

---

## Credits and Acknowledgments

This benchmark reimplements and adapts algorithms from the following open-source projects. All algorithmic design credit belongs to their original authors.

| Algorithm | Original Repository | Original Language | License |
|---|---|---|---|
| IQR Speed Threshold | [MohammedSuratwala/SybilDetection](https://github.com/MohammedSuratwala/SybilDetection) | C++ (OMNeT++) | -- |
| RSU Position Verification | [karthik-047/Detecting-Sybil-Attacks-in-VANETs](https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs) | Python | -- |
| TASER Bayesian Trust | [morton-t/VANET-Simulations](https://github.com/morton-t/VANET-Simulations) | C++ (OMNeT++/Veins) | -- |
| Random Forest + GWO | [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet) | Python | -- |
| LSTM Dual-Layer Framework | [SaiKumar-1608](https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL) | Python (Jupyter) | -- |
| Dynamic k-Means | [Gideon-Adele/Dynamic-k-means-Clustering](https://github.com/Gideon-Adele/Dynamic-k-means-Clustering) | C++ (OMNeT++) | -- |

Simulation infrastructure: [SUMO](https://eclipse.dev/sumo/) (Eclipse Public License 2.0).

---

## License

This project is released under the [MIT License](LICENSE).

```
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
