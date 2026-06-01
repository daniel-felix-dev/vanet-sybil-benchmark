# Setup Guide

This document covers everything needed to install, configure, and run the VANET Sybil Detection Benchmark on a clean machine. Follow the sections in order.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Installing SUMO](#2-installing-sumo)
3. [Python Environment](#3-python-environment)
4. [Path Configuration](#4-path-configuration)
5. [Verifying the Installation](#5-verifying-the-installation)
6. [Running the Full Pipeline](#6-running-the-full-pipeline)
7. [Partial Runs and Customization](#7-partial-runs-and-customization)
8. [Output Files Reference](#8-output-files-reference)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. System Requirements

| Component | Minimum | Notes |
|---|---|---|
| Operating System | Windows 10 / Windows 11 | Linux and macOS require path adjustments (see Section 4) |
| Python | 3.9 | Tested on 3.11. Python 3.12 also works. |
| SUMO | 1.12.0 | Default install path: `C:\Program Files (x86)\Eclipse\Sumo` |
| RAM | 8 GB | 16 GB recommended when running LSTM |
| Disk | 2 GB free | For datasets, figures, and model checkpoints |
| GPU | Optional | TensorFlow 2.11+ does not use GPU on native Windows. LSTM runs on CPU. |

---

## 2. Installing SUMO

SUMO (Simulation of Urban MObility) is the open-source traffic simulator that generates the vehicle movement data used by this benchmark.

### Windows

1. Download the installer from [eclipse.dev/sumo](https://eclipse.dev/sumo/).
2. Run the installer. Accept the default path: `C:\Program Files (x86)\Eclipse\Sumo`.
3. Verify the installation by opening a terminal and running:

```powershell
sumo --version
```

Expected output starts with `Eclipse SUMO sumo Version 1.12.0` (or later).

4. (Optional) Set the `SUMO_HOME` environment variable:

```powershell
[System.Environment]::SetEnvironmentVariable(
    "SUMO_HOME",
    "C:\Program Files (x86)\Eclipse\Sumo",
    "User"
)
```

Close and reopen the terminal for the variable to take effect.

### Linux

```bash
sudo apt-get install sumo sumo-tools        # Ubuntu / Debian
export SUMO_HOME=/usr/share/sumo
```

Add the export to `~/.bashrc` to make it permanent.

### macOS

```bash
brew install sumo
export SUMO_HOME=$(brew --prefix sumo)/share/sumo
```

### Verify TraCI Access

TraCI is the Python interface to SUMO. It ships with SUMO and should be importable after installation:

```python
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo"), "tools"))
import traci
print("TraCI OK:", traci.__file__)
```

If this raises `ModuleNotFoundError`, add the SUMO tools folder to `PYTHONPATH` or install via pip:

```bash
pip install traci sumolib
```

---

## 3. Python Environment

Create an isolated environment to avoid version conflicts:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

Install all dependencies:

```bash
pip install scikit-learn tensorflow joblib pandas numpy matplotlib scipy
```

### Package Roles

| Package | Version tested | Purpose |
|---|---|---|
| scikit-learn | 1.8.0 | IQR, Random Forest, k-Means |
| tensorflow | 2.21.0 | LSTM detector |
| pandas | any | Dataset I/O and manipulation |
| numpy | any | Numerical operations |
| matplotlib | any | All figures and charts |
| scipy | any | Statistical tests (Kruskal-Wallis, Wilcoxon, bootstrap) |
| joblib | any | Model persistence |

### Minimal Install (no LSTM)

If you do not need the LSTM detector:

```bash
pip install scikit-learn pandas numpy matplotlib scipy
```

Then remove LSTM from `detectors/__init__.py`:

```python
# Comment out these lines:
# from .lstm_detector import LSTMDetector
# And remove LSTMDetector from ALL_DETECTORS
```

### Verify All Imports

```bash
python -c "
import pandas, numpy, sklearn, matplotlib, scipy
print('Core packages: OK')
try:
    import tensorflow
    print('TensorFlow:', tensorflow.__version__)
except ImportError:
    print('TensorFlow: not installed (LSTM disabled)')
try:
    import traci
    print('TraCI: OK')
except ImportError:
    print('TraCI: not found -- see Section 2')
"
```

---

## 4. Path Configuration

Two scripts contain paths that may need adjustment for non-default SUMO installations.

### simulation/collect_dataset.py

```python
SUMO_BIN = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo.exe"
```

Change this line to point to your SUMO binary. On Linux: `/usr/bin/sumo`.

### simulation/generate_routes.py

```python
SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"
SUMO_BIN  = os.path.join(SUMO_HOME, "bin")
TOOLS     = os.path.join(SUMO_HOME, "tools")
```

On Linux, adjust to:

```python
SUMO_HOME = "/usr/share/sumo"
SUMO_BIN  = "/usr/bin"
TOOLS     = os.path.join(SUMO_HOME, "tools")
```

Also change `duarouter.exe` to `duarouter` (without the `.exe` extension) in the `run()` call inside that file.

---

## 5. Verifying the Installation

Run these checks in order. Each depends on the previous step working.

### Check 1: SUMO binary

```bash
sumo --version
```

### Check 2: Dataset files exist

The pre-generated datasets are committed to the repository. Confirm all eight are present:

```bash
python -c "
import os
missing = []
for r in [5,10,15,20,25,30,35,40]:
    p = f'results/datasets/dataset_sybil{r}.csv'
    if not os.path.exists(p):
        missing.append(p)
if missing:
    print('Missing:', missing)
    print('Run: python simulation/collect_dataset.py')
else:
    print('All 8 datasets present.')
"
```

### Check 3: Detector imports

```bash
python -c "
from detectors import ALL_DETECTORS
names = [D().name for D in ALL_DETECTORS]
print('Detectors loaded:', len(names))
for n in names:
    print(' -', n)
"
```

Expected: 7 detectors listed.

### Check 4: Benchmark smoke test (fast)

```bash
python -c "
import pandas as pd
from detectors import IQRDetector, TASERDetector, RFDetector

df = pd.read_csv('results/datasets/dataset_sybil20.csv')
for Cls in [IQRDetector, TASERDetector, RFDetector]:
    det = Cls()
    det.fit(df)
    print(det.name, '->', det.evaluate(df)['f1'])
"
```

This runs three fast detectors on the 20% sybil dataset and should complete in under 10 seconds.

---

## 6. Running the Full Pipeline

Run these commands in order. Each step depends on the previous.

### Step 1: Generate route files

```bash
python simulation/generate_routes.py
```

Generates eight `.rou.xml` files (one per sybil rate: 5% to 40%) using SUMO's `randomTrips.py` and `duarouter`. Runtime: under 1 minute.

### Step 2: Generate SUMO configuration files

```bash
python simulation/make_configs.py
```

Generates eight `.sumocfg` files referencing the corresponding route files. Runtime: under 1 second.

### Step 3: Collect datasets via TraCI

```bash
python simulation/collect_dataset.py
```

Runs eight SUMO simulations headlessly (500 steps each), recording per-vehicle features at every step. Runtime: approximately 35 seconds total.

Expected output per scenario:

```
Running scenario sybil20% seed=42...
  step 0/500 | 1 vehicles active
  step 100/500 | 30 vehicles active
  ...
  Saved 9153 records (7231 legit, 1922 sybil) -> results/datasets/dataset_sybil20.csv
```

### Step 4: Run the benchmark

```bash
python benchmark.py
```

Evaluates all 6 detectors (IQR, RSU, TASER, RF, LSTM, k-Means) on all 8 datasets using out-of-sample protocols (5-fold CV by vehicle_id for RF, 80/20 vehicle split for LSTM). Runtime: approximately 20 minutes.

Expected output per scenario:

```
Sybil Rate: 20%
  Records: 9153 | Legit: 7231 | Sybil: 1922 | Sybil%: 21.0%
  [TASER Bayesian Trust] fitting... acc=1.000 f1=1.000 (0.62s)
  [Random Forest] fitting... acc=0.980 f1=0.954 (2.68s) [5-fold CV OOS] f1_std=0.022
  ...
```

Outputs:
- `results/metrics/benchmark_results.csv`
- `figures/benchmark_f1.png`, `figures/benchmark_accuracy.png`
- `figures/benchmark_metrics_20pct.png`, `figures/benchmark_precision_recall.png`

### Step 5: Generate analysis figures

```bash
python results/generate_analysis.py
```

Produces 8 detailed charts in `analysis/figures/`. Runtime: under 1 minute.

### Step 6: Generate ROC curves

```bash
python results/generate_roc.py
```

Produces one ROC chart per sybil rate (4 charts using the 10%, 20%, 30%, 40% subsets) and an AUC summary table. Runtime: 3 to 5 minutes (LSTM training is repeated).

### Step 7: Generate sensitivity analysis

```bash
python results/generate_sensitivity.py
```

Sweeps hyperparameters for TASER (lambda), RSU (dist_thresh, min_freq), and IQR (multiplier k). Runtime: approximately 5 minutes.

### Step 8: Generate statistical proofs

```bash
python results/generate_proofs.py
```

Runs all 11 statistical tests (Kruskal-Wallis, Wilcoxon, bootstrap CI, Cohen's d, linear regression, convergence proofs, IQR fence derivation, Pareto analysis). Produces `analysis/statistical_proofs.md` and 8 proof figures. Runtime: 3 to 5 minutes.

---

## 7. Partial Runs and Customization

### Run only specific sybil rates

```bash
python simulation/collect_dataset.py 20 30    # only 20% and 30%
```

**Note on GWO:** The Grey Wolf Optimizer variant of Random Forest (`gwo_rf_detector.py`) is not included in `ALL_DETECTORS` by default. A single-seed evaluation showed no statistically significant benefit over the RF baseline (Wilcoxon p=0.640, Cohen's d=0.18). It can be added back by importing `GWORFDetector` in `detectors/__init__.py` if needed for comparison purposes.

### Run a single detector

```python
# In Python or a temporary script:
import pandas as pd
from detectors import TASERDetector

df = pd.read_csv("results/datasets/dataset_sybil30.csv")
det = TASERDetector()
det.fit(df)
print(det.evaluate(df))
```

### Reproduce with a different seed

```bash
python simulation/generate_routes.py --seed 123
python simulation/collect_dataset.py --seed 123 --out results/datasets/dataset_sybil20_seed123.csv 20
```

The `run_multi_seed.py` script orchestrates full multi-seed runs across all 8 rates and 5 seeds:

```bash
python simulation/run_multi_seed.py --quick    # 2 seeds x 4 rates (testing)
python simulation/run_multi_seed.py            # 5 seeds x 8 rates (full)
```

---

## 8. Output Files Reference

| File | Generated by | Contents |
|---|---|---|
| `results/datasets/dataset_sybil{N}.csv` | `collect_dataset.py` | Per-vehicle per-step features, 8 files |
| `results/metrics/benchmark_results.csv` | `benchmark.py` | 56 rows: F1, precision, recall, specificity, fit_time per (detector, rate) |
| `figures/benchmark_f1.png` | `benchmark.py` | F1 vs sybil rate, all 7 detectors |
| `figures/benchmark_accuracy.png` | `benchmark.py` | Accuracy vs sybil rate |
| `figures/benchmark_metrics_20pct.png` | `benchmark.py` | All 5 metrics at 20% sybil rate |
| `figures/benchmark_precision_recall.png` | `benchmark.py` | Precision-recall scatter |
| `analysis/figures/heatmap_f1.png` | `generate_analysis.py` | F1 heatmap: detector x sybil rate |
| `analysis/figures/radar_per_detector.png` | `generate_analysis.py` | 5-metric radar chart per detector |
| `analysis/figures/cost_vs_f1.png` | `generate_analysis.py` | Pareto frontier: F1 vs training time |
| `analysis/figures/roc_curves_sybil{N}.png` | `generate_roc.py` | ROC curves at each sybil rate |
| `analysis/figures/sensitivity_*.png` | `generate_sensitivity.py` | Hyperparameter sensitivity (4 charts) |
| `analysis/figures/proofs_*.png` | `generate_proofs.py` | Statistical test visualizations (8 charts) |
| `analysis/math_justifications.txt` | `generate_analysis.py` | Utility scores, Pareto, dominance matrix |
| `analysis/statistical_proofs.md` | `generate_proofs.py` | All 11 statistical tests with results |
| `analysis/roc_auc_table.md` | `generate_roc.py` | AUC per detector per rate |
| `analysis/sensitivity_report.md` | `generate_sensitivity.py` | Sensitivity tables and interpretation |

---

## 9. Troubleshooting

**`ModuleNotFoundError: No module named 'traci'`**
TraCI is not on the Python path. Install it via pip (`pip install traci`) or add `$SUMO_HOME/tools` to `PYTHONPATH`.

**`FatalTraCIError: connection closed by SUMO`**
The route file contains an edge that does not exist in the network. Re-run `python simulation/generate_routes.py` to regenerate valid routes from the current network file.

**LSTM shows F1 = 0.000 at sybil rates below 15%**
This is expected behavior. With fewer than 12% positive records, the LSTM defaults to predicting all-Legitimate. See `docs/algorithms/06_lstm.md` for the full explanation.

**`ValueError: dict contains fields not in fieldnames`**
An older version of `benchmark_results.csv` is present. Delete it and re-run `python benchmark.py`.

**`benchmark.py` takes more than 2 hours**
GWO runs 180 Random Forest fits per sybil rate. Remove `GWORFDetector` from `ALL_DETECTORS` in `detectors/__init__.py` to reduce runtime to approximately 8 minutes.

**TensorFlow warnings about CUDA or GPU**
TensorFlow on native Windows does not support GPU acceleration from version 2.11 onward. This is expected. The LSTM runs on CPU without any changes to the code.
