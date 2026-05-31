# Running the Benchmark

## The pipeline at a glance

Data flows through four stages. Each stage depends on the previous one, so run them in order.

```
netgenerate
    |
    v
network.net.xml        (the road network, already committed)
    |
    v
generate_routes.py     (creates vehicle routes for each attack scenario)
    |
    v
collect_dataset.py     (runs SUMO via TraCI, records one CSV per scenario)
    |
    v
benchmark.py           (runs all 7 detectors, saves metrics and charts)
    |
    v
generate_analysis.py   (produces 8 detailed analysis charts)
```

Total time for the full run: about 60 minutes on a typical laptop with 8 sybil rates. The GWO optimizer accounts for most of that (~80 seconds per rate). Skipping RF+GWO reduces total time to around 8 minutes.

Random Forest uses 5-fold cross-validation split by vehicle_id (out-of-sample). LSTM uses an 80/20 vehicle-level split. Neither is evaluated on the data it trained on.

---

## Running everything

```bash
python simulation/generate_routes.py         # 8 rates: 5,10,15,20,25,30,35,40
python simulation/collect_dataset.py         # ~35 s total
python benchmark.py                          # ~60 min (all detectors, 8 rates)
python results/generate_analysis.py          # analysis figures
python results/generate_roc.py               # ROC curves and AUC table
python results/generate_sensitivity.py       # hyperparameter sensitivity
python results/generate_proofs.py            # statistical proofs
```

---

## Step 1: the road network

The file `simulation/network.net.xml` is already in the repository, so you normally do not need to regenerate it. If you want to start from scratch or change the grid size, run:

```bash
netgenerate \
  --grid --grid.number=6 --grid.length=200 \
  --default.speed=13.89 \
  --output-file=simulation/network.net.xml
```

This produces a 6x6 grid with 120 road segments covering a 1200x1200 meter area.

---

## Step 2: generating routes

```bash
python simulation/generate_routes.py          # all eight sybil rates: 5,10,15,20,25,30,35,40
python simulation/generate_routes.py 20       # just the 20% scenario
```

Internally this calls SUMO's `randomTrips.py` to build valid connected routes for 80 legitimate vehicles, then appends Sybil vehicles that share a departure edge. Routes never repeat an edge, which prevents SUMO from rejecting them for forming loops.

Expected output:

```
Generating routes sybil10%...
  sybil10%: legit=80, sybil_ids=5 -> routes_sybil10.rou.xml
Generating routes sybil20%...
  ...
Done.
```

After this step you will also need the SUMO config files. If they are not already present:

```bash
python simulation/make_configs.py
```

---

## Step 3: collecting the dataset

```bash
python simulation/collect_dataset.py          # all four scenarios
python simulation/collect_dataset.py 30       # just the 30% scenario
```

This starts SUMO in headless mode via TraCI, runs 500 simulation steps, and records features for every vehicle at every step. The whole thing takes about 30 seconds for all four scenarios.

Example output for one scenario:

```
Running scenario sybil30%...
  step 0/500 -- 2 vehicles active
  step 100/500 -- 37 vehicles active
  step 200/500 -- 17 vehicles active
  step 300/500 -- 17 vehicles active
  step 400/500 -- 15 vehicles active
  Saved 10086 records (7249 legit, 2837 sybil) -> results/datasets/dataset_sybil30.csv
```

Each row in the CSV is one vehicle at one time step. The columns are:

| Column | Meaning |
|---|---|
| step | Simulation step, from 0 to 499 |
| vehicle_id | SUMO ID, starts with "legit_" or "sybil_" |
| x, y | Reported position in meters |
| speed | Reported speed in m/s (Sybil nodes add Gaussian noise with std = 8) |
| accel | Speed change since the previous step |
| angle | Heading in degrees |
| edge_id | Which road segment the vehicle is on |
| n_neighbors | How many other vehicles are within 150 m |
| min_rsu_dist | Distance to the nearest of the 20 RSUs |
| mean_rsu_dist | Average distance to all 20 RSUs |
| is_sybil | Ground truth: 1 for Sybil, 0 for legitimate |
| attacker_id | Which attacker device controls this Sybil node (-1 for legitimate) |

---

## Step 4: running the benchmark

```bash
python benchmark.py
```

Progress looks like this:

```
Sybil Rate: 20%
  Records: 9153 | Legit: 7231 | Sybil: 1922 | Sybil%: 21.0%
  [TASER Bayesian Trust] fitting... acc=1.000 f1=1.000 (0.90s)
  [Random Forest] fitting... acc=0.996 f1=0.990 (0.53s)
  [Random Forest + GWO] fitting...
    GWO best params: n_est=171, depth=8, loss=0.0318
  acc=0.988 f1=0.972 (119.37s)
  ...
```

When it finishes you will find:

- `results/metrics/benchmark_results.csv`: the full results table (28 rows)
- `figures/benchmark_f1.png`: F1 vs sybil rate for all detectors
- `figures/benchmark_accuracy.png`
- `figures/benchmark_metrics_20pct.png`: all five metrics at 20% sybil rate
- `figures/benchmark_precision_recall.png`

---

## Step 5: analysis charts

```bash
python results/generate_analysis.py
```

Produces eight charts in `analysis/figures/` and a text file with all the computed statistics that back the scenario recommendations in [analysis/scenario_guide.md](../analysis/scenario_guide.md).

---

## Running only some detectors

If you want to skip the slow RF+GWO optimizer (saves about 8 minutes), open `benchmark.py` and change the import at the top:

```python
from detectors import (
    IQRDetector, RSUDetector, TASERDetector,
    RFDetector, LSTMDetector, KMeansDetector,
    # GWORFDetector  <-- comment this out
)
ALL_DETECTORS = [
    IQRDetector, RSUDetector, TASERDetector,
    RFDetector, LSTMDetector, KMeansDetector,
]
```

To run a single detector for a quick test:

```python
ALL_DETECTORS = [TASERDetector]
RATES = [20]   # just one scenario
```
