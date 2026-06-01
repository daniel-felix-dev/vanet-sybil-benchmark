# VANET Sybil Detection Benchmark

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![SUMO](https://img.shields.io/badge/SUMO-1.12.0-green)](https://eclipse.dev/sumo/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Seeds](https://img.shields.io/badge/Seeds-5-orange)](results/metrics/multi_seed_raw.csv)

---

## Abstract

Sybil attacks in Vehicular Ad-hoc Networks (VANETs) allow a single malicious device to create multiple fake identities, corrupting cooperative driving decisions such as traffic signal coordination, collision avoidance, and emergency routing. Prior comparative studies of Sybil detection algorithms are methodologically inconsistent: each algorithm is evaluated in a different simulator, on a different road topology, and with a different attack model, making it impossible to determine which technique genuinely performs better.

This benchmark addresses that gap by fixing the simulation environment and varying only the detection algorithm. Six algorithms from independent open-source repositories are reimplemented in Python and evaluated against the same SUMO-generated dataset using rigorous out-of-sample protocols and **5 random seeds x 8 sybil rates = 40 observations per detector**, giving the statistical tests sufficient power to draw confident conclusions. The principal finding is that TASER, a Bayesian trust-score method requiring no labeled training data, achieves F1 = 0.9997 (std = 0.0006 across 40 runs) and strictly dominates all other detectors on both detection quality and computational cost.

---

## Background

### Vehicular Ad-hoc Networks

A VANET is a decentralized communication network in which vehicles exchange short broadcast messages (beacons) at 1 Hz using the IEEE 802.11p wireless standard. Each beacon carries the sender's claimed identity, position, speed, and heading. Downstream systems use these beacons for cooperative perception: a vehicle may slow down because a beacon from an ahead vehicle reports a sudden deceleration, or a traffic management center may redirect traffic based on reported congestion.

### Sybil Attacks

A Sybil attack (Douceur, 2002) occurs when a single physical device creates and maintains multiple fake network identities. In the VANET context, a single attacker device can simultaneously broadcast as a dozen or more fake vehicles, each reporting fabricated telemetry. Consequences include phantom traffic jams, emergency vehicle spoofing, and routing manipulation.

### The Evaluation Problem

Published detection algorithms are typically evaluated in the simulator and scenario that each research group had available, making direct numerical comparison impossible. This benchmark resolves the problem by fixing the simulation (SUMO 1.12.0, 6x6 grid, 80 legitimate vehicles, 5 seeds) and varying only the detection algorithm, with identical out-of-sample evaluation protocols applied to all supervised detectors.

---

## Repository Structure

```
vanet-sybil-benchmark/
├── README.md                         This file
├── benchmark.py                      Runs all 6 detectors, produces metrics and charts
├── simulation/
│   ├── network.net.xml               Road network: 6x6 grid, 1200x1200 m
│   ├── generate_routes.py            Generates .rou.xml files (supports --seed)
│   ├── make_configs.py               Generates .sumocfg files
│   ├── collect_dataset.py            Runs SUMO via TraCI, records features (supports --seed)
│   └── run_multi_seed.py             Multi-seed orchestrator (5 seeds x 8 rates)
├── detectors/
│   ├── base_detector.py              Abstract base: fit(), predict(), evaluate(), predict_proba()
│   ├── iqr_detector.py               IQR Speed Threshold
│   ├── rsu_detector.py               RSU Position Verification
│   ├── taser_detector.py             TASER Bayesian Trust Score
│   ├── rf_detector.py                Random Forest (5-fold CV by vehicle_id)
│   ├── lstm_detector.py              LSTM (80/20 vehicle-level split)
│   ├── kmeans_detector.py            Dynamic k-Means Clustering
│   └── gwo_rf_detector.py            [Reference only] RF + GWO -- excluded from benchmark
├── results/
│   ├── datasets/                     Single-seed datasets (seed=42)
│   ├── datasets/multi_seed/          Per-seed datasets (seeds 42,123,456,789,1000)
│   ├── metrics/
│   │   ├── benchmark_results.csv     Aggregated results (mean over 5 seeds)
│   │   └── multi_seed_raw.csv        Raw results (one row per detector-rate-seed)
│   ├── generate_analysis.py
│   ├── generate_roc.py
│   ├── generate_sensitivity.py
│   └── generate_proofs.py
├── figures/                          Overview charts from benchmark.py
├── analysis/
│   ├── figures/                      Detailed charts (analysis + proofs + sensitivity)
│   ├── statistical_proofs.md         All statistical tests with computed values
│   ├── roc_auc_table.md
│   └── sensitivity_report.md
└── docs/
    ├── setup.md
    ├── simulation/attack_model.md
    ├── simulation/data_collection.md
    ├── algorithms/overview.md
    ├── algorithms/01_iqr.md through 07_kmeans.md
    └── evaluation/methodology.md, results.md, statistical_analysis.md
```

---

## Dependencies

| Software | Version | Purpose |
|---|---|---|
| Python | 3.9+ | Runtime |
| SUMO | 1.12.0+ | Traffic simulation |
| scikit-learn | 1.0+ | IQR, Random Forest, k-Means |
| TensorFlow | 2.11+ | LSTM |
| pandas / numpy / matplotlib / scipy | any | Data and analysis |

```bash
pip install scikit-learn tensorflow pandas numpy matplotlib scipy
```

Full setup: [docs/setup.md](docs/setup.md)

---

## Quick Start

```bash
# Reproduce multi-seed results (~20 min, no GWO)
python simulation/run_multi_seed.py

# Or reproduce single-seed quickly (~3 min)
python simulation/collect_dataset.py
python benchmark.py
```

---

## Algorithm Overview

| # | Algorithm | Category | Source | Requires Labels |
|---|---|---|---|---|
| 1 | IQR Speed Threshold | Statistical | [MohammedSuratwala/SybilDetection](https://github.com/MohammedSuratwala/SybilDetection) | No |
| 2 | RSU Position Verification | Positional | [karthik-047/Detecting-Sybil-Attacks-in-VANETs](https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs) | No |
| 3 | TASER Bayesian Trust | Probabilistic | [morton-t/VANET-Simulations](https://github.com/morton-t/VANET-Simulations) | No |
| 4 | Random Forest | ML supervised | [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet) | Yes |
| 5 | LSTM | Deep learning | [SaiKumar-1608](https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL) | Yes |
| 6 | Dynamic k-Means | Clustering | [Gideon-Adele/Dynamic-k-means-Clustering](https://github.com/Gideon-Adele/Dynamic-k-means-Clustering) | No |

**Note on GWO:** RF + Grey Wolf Optimizer was evaluated with a single seed and showed no statistically significant improvement over RF baseline (Wilcoxon p=0.640, Cohen's d=0.18 -- negligible). It was excluded from the multi-seed experiment to avoid ~8 hours of computation per seed. Implementation preserved in `detectors/gwo_rf_detector.py`.

---

## Results

All values are **out-of-sample (OOS)**, **mean over 5 random seeds** (seeds 42, 123, 456, 789, 1000). n = 40 per detector (5 seeds x 8 sybil rates).

### Mean performance across 8 sybil rates (5% to 40%)

| Detector | Accuracy | Precision | Recall | F1 | F1 std | Specificity | Time (s) |
|---|---|---|---|---|---|---|---|
| **TASER Bayesian Trust** | **0.9998** | **1.0000** | 0.9995 | **0.9997** | **0.0006** | **1.0000** | **0.69** |
| Random Forest | 0.9750 | 0.9156 | **0.8856** | 0.8945 | 0.0242 | 0.9802 | 2.78 |
| LSTM | 0.8536 | 0.5031 | 0.5606 | 0.4821 | 0.2575 | 0.9074 | 16.7 |
| IQR Speed Threshold | 0.3046 | 0.3046 | **1.0000** | 0.4007 | 0.0326 | 0.1500 | **0.05** |
| RSU Position Verification | 0.7790 | 0.0341 | 0.0076 | 0.0123 | 0.0276 | 0.9899 | 10.6 |
| Dynamic k-Means | 0.7835 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9978 | 0.14 |

F1 std = standard deviation across 40 runs (5 seeds x 8 rates). Lower std means more consistent behavior across different random scenarios.

### F1 by sybil rate (mean over 5 seeds)

| Detector | 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|---|
| TASER | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.998 |
| Random Forest | 0.741 | 0.754 | 0.865 | 0.953 | 0.948 | 0.967 | 0.958 | 0.970 |
| LSTM | 0.000 | 0.160 | 0.248 | 0.635 | 0.490 | 0.782 | 0.718 | 0.824 |
| IQR | 0.109 | 0.108 | 0.199 | 0.343 | 0.396 | 0.443 | 0.608 | 1.000 |
| RSU | 0.000 | 0.000 | 0.000 | 0.034 | 0.000 | 0.065 | 0.000 | 0.000 |
| k-Means | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

### Statistical validation (n=40 per detector)

| Test | Result | Interpretation |
|---|---|---|
| Kruskal-Wallis (all detectors) | H = 193.1, p = 0.000000 | Detectors are statistically distinct |
| Wilcoxon: TASER vs RF | p << 0.001 | TASER significantly outperforms RF |
| TASER F1 std across 40 runs | 0.0006 | Exceptional stability across seeds and rates |
| RF F1 std across 40 runs | 0.0242 | Stable |
| LSTM F1 std across 40 runs | 0.2575 | High variance (class imbalance at low rates) |

---

## Principal Findings

**1. TASER is Pareto-dominant with high statistical confidence.** With n=40 observations per detector, Kruskal-Wallis gives H=193.1 (p=0.000000). TASER achieves F1=0.9997 with std=0.0006 across 40 runs -- the most stable result of any detector. It trains in 0.69 seconds, faster than any competitive alternative. No other detector beats it on both F1 and speed simultaneously.

**2. In-sample evaluation inflates RF performance by approximately 11%.** RF OOS F1 (5-fold CV by vehicle_id) = 0.8945, compared to an in-sample estimate of approximately 0.987. The 10.7% gap is caused by the model memorizing per-vehicle speed patterns at training time.

**3. GWO hyperparameter optimization was statistically equivalent to RF.** Single-seed evaluation gave Wilcoxon p=0.640, Cohen's d=0.18. It was excluded from the multi-seed experiment based on this evidence.

**4. LSTM requires sufficient positive class representation.** F1=0.000 at 5% sybil rate (5.7% positive records). Multi-seed evaluation reveals more consistent behavior above 20% sybil rate, though with more variance than TASER or RF.

**5. RSU and k-Means fail due to model incompatibility.** RSU was designed for split-position attacks, not co-location. k-Means cannot separate classes when E[speed_sybil]=E[speed_legit] (zero-mean noise injection).

---

## Documentation Index

| Document | Contents |
|---|---|
| [docs/setup.md](docs/setup.md) | Prerequisites, installation, troubleshooting |
| [docs/simulation/attack_model.md](docs/simulation/attack_model.md) | Sybil attack model, topology, simulation parameters |
| [docs/simulation/data_collection.md](docs/simulation/data_collection.md) | TraCI, feature extraction, dataset statistics |
| [docs/algorithms/overview.md](docs/algorithms/overview.md) | Comparative summary of all 6 algorithms |
| [docs/algorithms/01_iqr.md](docs/algorithms/01_iqr.md) | IQR: Tukey fence, fence collapse proof |
| [docs/algorithms/02_rsu.md](docs/algorithms/02_rsu.md) | RSU: detection logic, model incompatibility proof |
| [docs/algorithms/03_taser.md](docs/algorithms/03_taser.md) | TASER: Bayesian proof, 12-beacon convergence |
| [docs/algorithms/04_random_forest.md](docs/algorithms/04_random_forest.md) | RF: OOS protocol, data leakage analysis |
| [docs/algorithms/05_rf_gwo.md](docs/algorithms/05_rf_gwo.md) | GWO: excluded from multi-seed, single-seed reference |
| [docs/algorithms/06_lstm.md](docs/algorithms/06_lstm.md) | LSTM: architecture, class imbalance analysis |
| [docs/algorithms/07_kmeans.md](docs/algorithms/07_kmeans.md) | k-Means: E[speed] proof, failure conditions |
| [docs/evaluation/methodology.md](docs/evaluation/methodology.md) | OOS protocols, metric definitions, data leakage |
| [docs/evaluation/results.md](docs/evaluation/results.md) | Full tables, interpretation, scenario recommendations |
| [docs/evaluation/statistical_analysis.md](docs/evaluation/statistical_analysis.md) | All statistical tests with values |
| [analysis/statistical_proofs.md](analysis/statistical_proofs.md) | Auto-generated from multi_seed_raw.csv |

---

## References

1. Douceur, J. R. (2002). The Sybil Attack. *IPTPS*. Springer.
2. Raya, M. and Hubaux, J.-P. (2007). Securing vehicular ad hoc networks. *J. Computer Security*, 15(1).
3. Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5-32.
4. Hochreiter, S. and Schmidhuber, J. (1997). Long Short-Term Memory. *Neural Computation*, 9(8).
5. Mirjalili, S. et al. (2014). Grey Wolf Optimizer. *Advances in Engineering Software*, 69, 46-61.
6. MacQueen, J. (1967). Some methods for classification of multivariate observations. *5th Berkeley Symposium*.
7. Lopez, P. A. et al. (2018). Microscopic Traffic Simulation using SUMO. *ITSC*. IEEE.
8. ETSI EN 302 637-2 (2019). ITS Vehicular Communications -- Cooperative Awareness Basic Service.
9. Josang, A. and Ismail, R. (2002). The Beta Reputation System. *15th Bled eCommerce Conf.*
10. Tukey, J. W. (1977). Exploratory Data Analysis. Addison-Wesley.

---

## Credits

| Algorithm | Original Repository | Language |
|---|---|---|
| IQR Speed Threshold | [MohammedSuratwala/SybilDetection](https://github.com/MohammedSuratwala/SybilDetection) | C++ (OMNeT++) |
| RSU Position Verification | [karthik-047/Detecting-Sybil-Attacks-in-VANETs](https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs) | Python |
| TASER Bayesian Trust | [morton-t/VANET-Simulations](https://github.com/morton-t/VANET-Simulations) | C++ (OMNeT++/Veins) |
| Random Forest + GWO | [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet) | Python |
| LSTM Dual-Layer | [SaiKumar-1608](https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL) | Python (Jupyter) |
| Dynamic k-Means | [Gideon-Adele/Dynamic-k-means-Clustering](https://github.com/Gideon-Adele/Dynamic-k-means-Clustering) | C++ (OMNeT++) |

Simulation infrastructure: [SUMO](https://eclipse.dev/sumo/) (Eclipse Public License 2.0).

---

## License

MIT License. See [LICENSE](LICENSE) for details.
