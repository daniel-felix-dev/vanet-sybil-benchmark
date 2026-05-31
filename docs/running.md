# Running the Benchmark

## Pipeline overview

```
netgenerate          generate_routes.py      make_configs.py
     │                      │                      │
     v                      v                      v
network.net.xml    routes_sybil{N}.rou.xml   scenario_sybil{N}.sumocfg
                                  │
                                  v
                        collect_dataset.py  (TraCI)
                                  │
                                  v
                   results/datasets/dataset_sybil{N}.csv
                                  │
                                  v
                           benchmark.py
                                  │
                        ┌─────────┴─────────┐
                        v                   v
               results/metrics/      figures/*.png
               benchmark_results.csv
```

Total time (all 4 scenarios): **~12 minutes** on a modern laptop.

---

## Quick start (all steps in sequence)

```bash
# From the repo root
python simulation/generate_routes.py
python simulation/make_configs.py
python simulation/collect_dataset.py
python benchmark.py
```

---

## Step-by-step

### Step 1 — Generate the SUMO network

The network is already committed to the repo (`simulation/network.net.xml`).  
To regenerate it from scratch:

```bash
netgenerate \
  --grid --grid.number=6 --grid.length=200 \
  --default.speed=13.89 \
  --output-file=simulation/network.net.xml
```

This creates a 6×6 grid with 1200×1200 m² total area, 120 edges.

### Step 2 — Generate route files

```bash
python simulation/generate_routes.py
# Runs for all 4 sybil rates: 10, 20, 30, 40%
# Or for a specific rate:
python simulation/generate_routes.py 20
```

Internally uses SUMO's `randomTrips.py` + `duarouter` to produce valid connected routes for 80 legitimate vehicles, then appends Sybil vehicles with shared departure edges and no-loop routes.

Expected output:
```
Generating routes sybil10%...
  sybil10%: legit=80, sybil_ids=5 -> routes_sybil10.rou.xml
...
```

### Step 3 — Generate SUMO config files

```bash
python simulation/make_configs.py
```

Produces `scenario_sybil{N}.sumocfg` for each rate (references the matching route file).

### Step 4 — Collect datasets via TraCI

```bash
python simulation/collect_dataset.py
# Or a single scenario:
python simulation/collect_dataset.py 30
```

Expected output per scenario:
```
==================================================
Running scenario sybil30%...
  step 0/500 — 1 vehicles active
  step 100/500 — 37 vehicles active
  ...
  Saved 10086 records (7249 legit, 2837 sybil) -> results/datasets/dataset_sybil30.csv
All done in 29.7s
```

Each CSV row represents one vehicle at one simulation step. Columns:

| Column | Description |
|---|---|
| `step` | Simulation step (0–499) |
| `vehicle_id` | SUMO vehicle ID (`legit_N` or `sybil_N`) |
| `x`, `y` | Reported position (m) |
| `speed` | Reported speed (m/s); Sybil nodes inject Gaussian noise σ=8 |
| `accel` | Δspeed since previous step (m/s²) |
| `angle` | Heading in degrees |
| `edge_id` | Current road segment ID |
| `n_neighbors` | Vehicles within 150 m |
| `min_rsu_dist` | Distance to nearest RSU (m) |
| `mean_rsu_dist` | Mean distance to all 20 RSUs (m) |
| `is_sybil` | Ground truth label (0=legit, 1=sybil) |
| `attacker_id` | Attacker device index (-1 for legitimate) |

### Step 5 — Run the benchmark

```bash
python benchmark.py
```

Runs all 7 detectors against all 4 datasets. Expected total time: **~12 min** (GWO dominates at ~117 s per scenario).

Progress indicator:
```
============================================================
Sybil Rate: 20%
============================================================
  Records: 9153 | Legit: 7231 | Sybil: 1922 | Sybil%: 21.0%
  [TASER Bayesian Trust] fitting... acc=1.000 f1=1.000 (0.90s)
  [Random Forest] fitting... acc=0.996 f1=0.990 (0.53s)
  [Random Forest + GWO] fitting... acc=0.988 f1=0.972 (119.37s)
  ...
```

Outputs:
- `results/metrics/benchmark_results.csv` — full metrics table
- `figures/benchmark_f1.png` — F1 vs sybil rate (all detectors)
- `figures/benchmark_accuracy.png`
- `figures/benchmark_metrics_20pct.png`
- `figures/benchmark_precision_recall.png`

### Step 6 — Generate analysis figures

```bash
python results/generate_analysis.py
```

Produces 8 detailed charts in `analysis/figures/` plus mathematical justifications in `analysis/math_justifications.txt`.

---

## Partial runs

**Single detector, all rates:**

Edit `benchmark.py` and filter `ALL_DETECTORS` to the one you want, or pass it directly:

```python
# benchmark.py — temporary override
from detectors import TASERDetector
ALL_DETECTORS = [TASERDetector]
```

**Skip GWO (speed up to ~3 min):**

```python
from detectors import (IQRDetector, RSUDetector, TASERDetector,
                       RFDetector, LSTMDetector, KMeansDetector)
ALL_DETECTORS = [IQRDetector, RSUDetector, TASERDetector,
                 RFDetector, LSTMDetector, KMeansDetector]
```

---

## Output file locations

```
results/
  datasets/
    dataset_sybil10.csv     7,747 rows
    dataset_sybil20.csv     9,153 rows
    dataset_sybil30.csv    10,086 rows
    dataset_sybil40.csv    12,000 rows
  metrics/
    benchmark_results.csv  28 rows (7 detectors × 4 rates)

figures/
  benchmark_f1.png
  benchmark_accuracy.png
  benchmark_metrics_20pct.png
  benchmark_precision_recall.png

analysis/
  figures/
    heatmap_f1.png
    radar_per_detector.png
    cost_vs_f1.png
    precision_recall_space.png
    f1_variance.png
    speed_distribution.png
    tp_fp_fn_breakdown.png
    scenario_utility_ranking.png
  math_justifications.txt
  detector_profiles.md
  scenario_guide.md
```
