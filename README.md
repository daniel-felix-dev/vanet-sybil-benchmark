# VANET Sybil Detection — Unified Benchmark

Comparative evaluation of **7 Sybil attack detection algorithms** under identical SUMO simulation conditions. A single pipeline generates the dataset; each detector processes the same data, enabling a fair algorithmic comparison.

---

## What is this?

Prior studies evaluate each detection algorithm in its own simulator, network topology, and attack model, making cross-paper comparison unreliable. This repository fixes the simulation layer and varies **only the detection algorithm**, producing directly comparable metrics.

**Simulation:** SUMO 1.12.0, 6×6 grid, 80 legitimate vehicles, sybil rates 10–40%.  
**Detectors:** IQR, RSU Verification, TASER, Random Forest, RF+GWO, LSTM, Dynamic k-Means.

---

## Quick start

```bash
python simulation/generate_routes.py
python simulation/collect_dataset.py   # ~30 s
python benchmark.py                    # ~12 min
```

Full setup guide: [docs/setup.md](docs/setup.md) | Step-by-step: [docs/running.md](docs/running.md)

---

## Results

### Mean performance across sybil rates 10–40%

| Detector | Accuracy | Precision | Recall | F1-Score | Specificity | Fit time (s) |
|---|---|---|---|---|---|---|
| **TASER Bayesian Trust** | **0.9979** | **1.0000** | 0.9947 | **0.9973** | **1.0000** | 0.87 |
| **Random Forest** | 0.9961 | 0.9853 | **0.9880** | 0.9866 | 0.9968 | **0.57** |
| RF + GWO | 0.9915 | 0.9760 | 0.9927 | 0.9842 | 0.9912 | 117.3 |
| LSTM | 0.9506 | 0.6804 | 0.7330 | 0.7038 | 0.9626 | 10.0 |
| IQR Speed Threshold | 0.3874 | 0.3874 | 1.0000 | 0.4740 | 0.2500 | 0.05 |
| RSU Verification | 0.7588 | 0.0908 | 0.0278 | 0.0426 | 0.9870 | 11.3 |
| Dynamic k-Means | 0.7602 | 0.0000 | 0.0000 | 0.0000 | 0.9960 | 0.64 |

### F1-Score by sybil rate

| Detector | 10% | 20% | 30% | 40% |
|---|---|---|---|---|
| TASER Bayesian Trust | 1.000 | 1.000 | 1.000 | 0.989 |
| Random Forest | 0.968 | 0.990 | 0.994 | 0.994 |
| RF + GWO | 1.000 | 0.972 | 0.974 | 0.991 |
| LSTM | 0.000 | 0.842 | 1.000 | 0.973 |
| IQR Speed Threshold | 0.110 | 0.347 | 0.439 | 1.000 |
| RSU Verification | 0.000 | 0.171 | 0.000 | 0.000 |
| Dynamic k-Means | 0.000 | 0.000 | 0.000 | 0.000 |

---

## When to use which algorithm

Recommendations are backed by utility functions computed from the benchmark data.  
Full mathematical derivations: [analysis/scenario_guide.md](analysis/scenario_guide.md)

| Scenario | Recommended | Key reason |
|---|---|---|
| **Real-time (≤1 s latency)** | Random Forest | Efficiency = 2.19 (F1/ln(time+1)); 0.57 s fit, F1 = 0.987 |
| **Zero false positives** | TASER | Only detector with Precision = 1.000 at every sybil rate |
| **High sybil rate (≥30%)** | TASER | F1 = 1.000 at 30%, 0.989 at 40%; Pareto-optimal |
| **No labeled data** | TASER | F1 = 0.997, Specificity = 1.000; no training required |
| **Embedded / minimal compute** | IQR | 0.05 s, 2 floats of memory; recall = 1.0 |
| **Low sybil rate (≤10%)** | TASER | F1 = 1.000 at 10%; converges in ≤ 12 beacons |

**Pareto-optimal detectors** (no other detector is both faster AND more accurate):  
TASER · Random Forest · IQR Speed Threshold

**RF + GWO is dominated** by RF baseline: higher F1 (0.987 vs. 0.984) at 200× lower training time.

---

## Documentation

| Document | Contents |
|---|---|
| [docs/setup.md](docs/setup.md) | Prerequisites, installation, SUMO setup |
| [docs/running.md](docs/running.md) | Pipeline walkthrough, expected outputs, partial runs |
| [docs/extending.md](docs/extending.md) | Adding a new detector (template + interface) |
| [analysis/detector_profiles.md](analysis/detector_profiles.md) | Per-detector strengths, weaknesses, trade-offs, math |
| [analysis/scenario_guide.md](analysis/scenario_guide.md) | Utility-function-based scenario recommendations |
| [analysis/math_justifications.txt](analysis/math_justifications.txt) | Raw computed statistics (efficiency, dominance, utility scores) |

---

## Repository structure

```
vanet-sybil-benchmark/
├── simulation/                  # SUMO scenario + TraCI collector
├── detectors/                   # 7 detection algorithms
├── results/
│   ├── datasets/                # dataset_sybil{10,20,30,40}.csv
│   ├── metrics/                 # benchmark_results.csv
│   └── generate_analysis.py    # produces analysis/figures/*
├── figures/                     # benchmark overview charts
├── analysis/
│   ├── figures/                 # 8 detailed analysis charts
│   ├── detector_profiles.md
│   ├── scenario_guide.md
│   └── math_justifications.txt
├── docs/
│   ├── setup.md
│   ├── running.md
│   └── extending.md
└── benchmark.py
```
