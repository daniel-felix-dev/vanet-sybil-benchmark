# VANET Sybil Detection Benchmark

When a car in a connected road network creates dozens of fake identities to manipulate traffic decisions, that is a Sybil attack. Detecting it is harder than it looks because the fake nodes can behave like real vehicles most of the time, only injecting misinformation at critical moments.

There are several published algorithms for catching these attacks, but each paper tests its own method in its own simulator with its own network, so you cannot tell from the numbers alone which one actually works better. This benchmark fixes the simulation and varies only the detection algorithm, giving you a direct, apples-to-apples comparison across seven approaches.

All supervised detectors (Random Forest, RF+GWO, LSTM) are evaluated out-of-sample: Random Forest and RF+GWO use 5-fold cross-validation split by vehicle ID; LSTM uses an 80/20 vehicle-level split. No detector is evaluated on data it trained on.

---

## Setup and execution

Full installation instructions are in [docs/setup.md](docs/setup.md). Once dependencies are in place, the pipeline runs in sequence:

```bash
python simulation/generate_routes.py
python simulation/collect_dataset.py
python benchmark.py
python results/generate_analysis.py
python results/generate_roc.py
python results/generate_sensitivity.py
python results/generate_proofs.py
```

See [docs/running.md](docs/running.md) for timing estimates and options to skip slow detectors.

---

## Simulation parameters

The network is a 6x6 street grid (1200 x 1200 m) built with SUMO's netgenerate. Each scenario has 80 legitimate vehicles and a variable number of Sybil identities controlled by 5 attacker devices. Eight attack intensities are tested: 5%, 10%, 15%, 20%, 25%, 30%, 35%, 40%. All experiments use seed 42, so every result is fully reproducible.

Sybil nodes in the simulation do two things that real attacks commonly do: they all report the same physical location (co-location) and inject Gaussian noise (sigma = 8 m/s) into their reported speed, producing readings outside the normal 0-14 m/s range.

---

## Results

All F1 values are **out-of-sample**. In-sample numbers are not reported.

### Average performance across all 8 attack intensities

| Detector | Accuracy | Precision | Recall | F1 | Specificity | Training time |
|---|---|---|---|---|---|---|
| TASER Bayesian Trust | 0.999 | **1.000** | 0.997 | **0.999** | **1.000** | 0.64 s |
| Random Forest + GWO | 0.974 | 0.938 | 0.879 | 0.893 | 0.978 | 98 s |
| Random Forest | 0.975 | 0.901 | **0.875** | 0.882 | 0.981 | **2.7 s** |
| LSTM | 0.908 | 0.536 | 0.531 | 0.507 | 0.941 | 16.8 s |
| IQR Speed Threshold | 0.290 | 0.290 | **1.000** | 0.391 | 0.125 | 0.06 s |
| RSU Position Verification | 0.781 | 0.045 | 0.014 | 0.021 | 0.991 | 10.2 s |
| Dynamic k-Means | 0.783 | 0.000 | 0.000 | 0.000 | 0.997 | 0.33 s |

### F1 by attack intensity

| Detector | 5% | 10% | 15% | 20% | 25% | 30% | 35% | 40% |
|---|---|---|---|---|---|---|---|---|
| TASER | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.989 |
| RF + GWO | 0.776 | 0.704 | 0.889 | 0.945 | 0.947 | 0.964 | 0.949 | 0.966 |
| Random Forest | 0.665 | 0.694 | 0.890 | 0.954 | 0.949 | 0.975 | 0.959 | 0.967 |
| LSTM | 0.000 | 0.000 | 0.000 | 0.667 | 0.625 | 1.000 | 0.857 | 0.909 |
| IQR | 0.108 | 0.110 | 0.207 | 0.347 | 0.402 | 0.439 | 0.516 | 1.000 |
| RSU | 0.000 | 0.000 | 0.000 | 0.171 | 0.000 | 0.000 | 0.000 | 0.000 |
| k-Means | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

**Note on RF vs RF+GWO:** Wilcoxon signed-rank test gives p = 0.64 (not significant at alpha = 0.05). Bootstrap 95% confidence intervals overlap substantially. The 1.1% mean F1 difference between GWO (0.893) and RF (0.882) is not statistically distinguishable with the current sample size. GWO costs 36x more training time (98 s vs 2.7 s) for a difference that cannot be confirmed by these tests.

---

## Which detector to use

Recommendations are backed by utility functions computed from the data. See [analysis/scenario_guide.md](analysis/scenario_guide.md) for the full derivations.

| Situation | Best choice | Key reason |
|---|---|---|
| Detection must finish quickly | Random Forest | F1 = 0.882 OOS in 2.7 s average |
| Zero false positives required | TASER | Only detector with Precision = 1.000 at every attack intensity |
| High attack rate (30%+) | TASER | F1 = 1.000 at 30%, 0.989 at 40%, 0.64 s training |
| No labeled data available | TASER | Works without labels, F1 = 0.999, Specificity = 1.000 |
| Very limited compute | IQR | 0.06 s, stores 2 floats, but specificity = 0 below 40% |
| Early detection (5-10%) | TASER | F1 = 1.000 at 5% and 10%; RF drops to 0.665-0.694 OOS |

TASER, Random Forest, and IQR sit on the Pareto frontier: no other detector outperforms them on both F1 and training speed simultaneously. TASER strictly dominates RF+GWO (higher F1, lower training time).

---

## Documentation index

| File | Contents |
|---|---|
| [docs/setup.md](docs/setup.md) | Prerequisites and installation |
| [docs/running.md](docs/running.md) | Pipeline walkthrough with expected outputs |
| [docs/extending.md](docs/extending.md) | How to add a new detector |
| [analysis/detector_profiles.md](analysis/detector_profiles.md) | Per-detector analysis with math |
| [analysis/scenario_guide.md](analysis/scenario_guide.md) | Utility-function recommendations per scenario |
| [analysis/complexity_analysis.md](analysis/complexity_analysis.md) | Formal Big-O analysis per detector |
| [analysis/roc_auc_table.md](analysis/roc_auc_table.md) | ROC AUC values (TASER=1.000, RF=0.9999) |
| [analysis/sensitivity_report.md](analysis/sensitivity_report.md) | Hyperparameter sensitivity analysis |
| [analysis/statistical_proofs.md](analysis/statistical_proofs.md) | 11 statistical tests backing all claims |
| [analysis/math_justifications.txt](analysis/math_justifications.txt) | Raw computed statistics |

---

## Repository layout

```
vanet-sybil-benchmark/
├── simulation/          SUMO scenario + TraCI data collector
├── detectors/           Seven detection algorithms (common OOS evaluation interface)
├── results/
│   ├── datasets/        dataset_sybil{5,10,15,20,25,30,35,40}.csv
│   ├── metrics/         benchmark_results.csv (56 rows, 8 rates x 7 detectors)
│   ├── generate_analysis.py
│   ├── generate_roc.py
│   ├── generate_sensitivity.py
│   └── generate_proofs.py
├── figures/             Overview charts
├── analysis/
│   ├── figures/         16 detailed charts (8 analysis + 8 proofs/sensitivity)
│   ├── detector_profiles.md
│   ├── scenario_guide.md
│   ├── complexity_analysis.md
│   ├── roc_auc_table.md
│   ├── sensitivity_report.md
│   ├── statistical_proofs.md
│   └── math_justifications.txt
├── docs/
│   ├── setup.md
│   ├── running.md
│   └── extending.md
└── benchmark.py
```
