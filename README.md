# VANET Sybil Detection Benchmark

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![SUMO](https://img.shields.io/badge/SUMO-1.12.0-green)](https://eclipse.dev/sumo/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Seeds](https://img.shields.io/badge/Seeds-5-orange)](results/metrics/multi_seed_raw.csv)

Comparative benchmark of **6 Sybil attack detection algorithms** for VANETs. All detectors run on the same SUMO-generated dataset under identical conditions, with rigorous out-of-sample evaluation (vehicle-level splits) and 5 random seeds.

Two attack models are tested: **co-location** (all fake IDs report the same position) and **split-position** (IDs report distinct positions around RSU centers — the model RSU detection was designed for).

---

## Quick Start

```bash
pip install scikit-learn tensorflow pandas numpy matplotlib scipy

# Collect datasets (seed=42, ~35s)
python simulation/collect_dataset.py

# Run benchmark (6 detectors, 8 sybil rates, ~20 min)
python benchmark.py

# Multi-seed benchmark (5 seeds, published results, ~20 min)
python simulation/run_multi_seed.py

# Split-position attack model
python simulation/collect_dataset_split.py
python benchmark_split.py
```

---

## Results (co-location attack, 5 seeds × 8 rates = 40 runs)

All F1 values are out-of-sample.

| Detector | F1 | F1 std | Precision | Recall | Specificity | Time (s) |
|---|---|---|---|---|---|---|
| **TASER** | **0.9997** | 0.0006 | **1.0000** | 0.9995 | **1.0000** | **1.07** |
| **Dynamic k-Means** | **0.9795** | -- | 0.9671 | 0.9944 | 0.9895 | 0.30 |
| Random Forest | 0.8945 | 0.0242 | 0.9156 | 0.8856 | 0.9802 | 5.03 |
| LSTM | 0.4487 | 0.2575 | 0.4638 | 0.4735 | 0.9280 | 35.9 |
| IQR | 0.4007 | 0.0326 | 0.3046 | **1.0000** | 0.1500 | **0.13** |
| RSU | 0.0123 | 0.0276 | 0.0341 | 0.0076 | 0.9899 | 23.7 |

### F1 by sybil rate (mean over 5 seeds)

| Detector | 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|---|
| TASER | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.998 |
| k-Means | 0.961 | 0.986 | 0.954 | 0.993 | 0.986 | 0.990 | 0.991 | 0.975 |
| Random Forest | 0.741 | 0.754 | 0.865 | 0.953 | 0.948 | 0.967 | 0.958 | 0.970 |
| LSTM | 0.000 | 0.050 | 0.050 | 0.443 | 0.499 | 0.851 | 0.883 | 0.814 |
| IQR | 0.109 | 0.108 | 0.198 | 0.343 | 0.396 | 0.443 | 0.608 | 1.000 |
| RSU | 0.000 | 0.000 | 0.000 | 0.034 | 0.000 | 0.064 | 0.000 | 0.000 |

### Attack model comparison (single seed, mean over 8 rates)

| Detector | Co-location F1 | Split-position F1 |
|---|---|---|
| TASER | 0.9997 | 1.0000 |
| Random Forest | 0.8945 | 0.9948 |
| **RSU** | 0.0123 | **0.8350** |
| **k-Means** | **0.9795** | **0.9226** |
| LSTM | 0.4487 | 0.4662 |
| IQR | 0.4007 | 0.3808 |

---

## Key Findings

1. **TASER is Pareto-optimal** — highest F1 (0.9997) with lowest competitive training time (0.69s). Precision = 1.000 at all rates, robust to both attack models. Provably flags Sybil nodes within 12 beacons.

2. **In-sample evaluation inflates RF by 9.3 pp** — OOS RF F1 = 0.895 vs in-sample ≈ 0.987. Vehicle-level splits are required to prevent data leakage.

3. **RSU failure is model-specific, not algorithmic** — F1 jumps from 0.012 (co-location) to 0.835 (split-position), confirming RSU works correctly in the attack scenario it was designed for.

4. **k-Means improved from F1=0.000 to F1=0.9795** by switching from mean-speed z-score to MAD-based std_speed z-score. Speed noise (sigma=8) raises variance, not mean — the original criterion was mathematically wrong.

5. **Kruskal-Wallis H=180.7** (p < 10⁻³⁶, n=40) confirms statistical significance. Wilcoxon W=0 for TASER vs RF and TASER vs k-Means (p < 0.001).

---

## Repository Structure

```
├── simulation/
│   ├── collect_dataset.py          co-location datasets (seed-aware)
│   ├── collect_dataset_split.py    split-position datasets
│   ├── run_multi_seed.py           5-seed orchestrator
│   ├── generate_routes.py / make_configs.py
│   └── network.net.xml + routes_sybil{N}.rou.xml
├── detectors/
│   ├── iqr_detector.py / rsu_detector.py / taser_detector.py
│   ├── rf_detector.py / lstm_detector.py / kmeans_detector.py
│   └── base_detector.py / __init__.py
├── results/
│   ├── datasets/                   co-location CSVs (seed=42 + multi_seed/)
│   ├── datasets/split_position/    split-position CSVs
│   └── metrics/                    benchmark_results.csv, multi_seed_raw.csv,
│                                   benchmark_split_results.csv
├── benchmark.py                    main benchmark runner
├── benchmark_split.py              split-position benchmark
├── docs/
│   ├── setup.md                    installation and usage
│   ├── detectors.md                algorithm reference
│   └── attack_models.md            co-location vs split-position
└── results/
    ├── generate_analysis.py
    ├── generate_roc.py / generate_sensitivity.py / generate_proofs.py
    └── compare_attack_models.py
```

---

## References

All algorithms sourced from independent open-source repositories:

| Algorithm | Source |
|---|---|
| IQR | [MohammedSuratwala/SybilDetection](https://github.com/MohammedSuratwala/SybilDetection) |
| RSU | [karthik-047/Detecting-Sybil-Attacks-in-VANETs](https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs) |
| TASER | [morton-t/VANET-Simulations](https://github.com/morton-t/VANET-Simulations) |
| RF | [126160042-crypto/sybil-attack-detection-vanet](https://github.com/126160042-crypto/sybil-attack-detection-vanet) |
| LSTM | [SaiKumar-1608](https://github.com/SaiKumar-1608/A-Dual-Layer-Sybil-Attack-Detection-Framework-for-RSU-less-VANETs-Using-Machine-Learning-and-POL) |
| k-Means | [Gideon-Adele/Dynamic-k-means-Clustering](https://github.com/Gideon-Adele/Dynamic-k-means-Clustering) |

Simulation: [SUMO 1.12.0](https://eclipse.dev/sumo/) (Eclipse Public License 2.0)

---

## License

[MIT License](LICENSE)
