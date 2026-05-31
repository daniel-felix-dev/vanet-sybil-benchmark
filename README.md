# VANET Sybil Detection Benchmark

When a car in a connected road network creates dozens of fake identities to manipulate traffic decisions, that is a Sybil attack. Detecting it is harder than it looks because the fake nodes can behave like real vehicles most of the time, only injecting misinformation at critical moments.

There are several published algorithms for catching these attacks, but each paper tests its own method in its own simulator with its own network, so you cannot tell from the numbers alone which one actually works better. This benchmark fixes the simulation and varies only the detection algorithm, giving you a direct, apples-to-apples comparison across seven approaches.

---

## Setup and execution

Full installation instructions are in [docs/setup.md](docs/setup.md). Once dependencies are in place, the whole pipeline runs in four steps:

```bash
python simulation/generate_routes.py    # build vehicle routes for each attack scenario
python simulation/collect_dataset.py    # run SUMO and record one CSV per scenario (~30s)
python benchmark.py                     # evaluate all 7 detectors (~12 min)
python results/generate_analysis.py    # produce the analysis charts
```

The step-by-step explanation with expected outputs lives in [docs/running.md](docs/running.md).

---

## Simulation parameters

The network is a 6x6 street grid (1200 x 1200 m) built with SUMO's netgenerate. Each scenario has 80 legitimate vehicles and a variable number of Sybil identities controlled by 5 attacker devices. Four attack intensities are tested: 10%, 20%, 30%, and 40% Sybil rate. All experiments use the same random seed, so every result is fully reproducible.

Sybil nodes in the simulation do two things that real attacks commonly do: they all report the same physical location (co-location) and they inject random speed noise into their beacon messages, producing readings well outside the normal 0-14 m/s range.

---

## Results

### Average performance across all attack intensities

| Detector | Accuracy | Precision | Recall | F1 | Specificity | Training time |
|---|---|---|---|---|---|---|
| TASER Bayesian Trust | 0.998 | **1.000** | 0.995 | **0.997** | **1.000** | 0.87 s |
| Random Forest | 0.996 | 0.985 | 0.988 | 0.987 | 0.997 | **0.57 s** |
| Random Forest + GWO | 0.992 | 0.976 | 0.993 | 0.984 | 0.991 | 117 s |
| LSTM | 0.951 | 0.680 | 0.733 | 0.704 | 0.963 | 10 s |
| IQR Speed Threshold | 0.387 | 0.387 | **1.000** | 0.474 | 0.250 | 0.05 s |
| RSU Position Verification | 0.759 | 0.091 | 0.028 | 0.043 | 0.987 | 11.3 s |
| Dynamic k-Means | 0.760 | 0.000 | 0.000 | 0.000 | 0.996 | 0.64 s |

### F1 broken down by attack intensity

| Detector | 10% Sybil | 20% Sybil | 30% Sybil | 40% Sybil |
|---|---|---|---|---|
| TASER Bayesian Trust | 1.000 | 1.000 | 1.000 | 0.989 |
| Random Forest | 0.968 | 0.990 | 0.994 | 0.994 |
| Random Forest + GWO | 1.000 | 0.972 | 0.974 | 0.991 |
| LSTM | 0.000 | 0.842 | 1.000 | 0.973 |
| IQR Speed Threshold | 0.110 | 0.347 | 0.439 | 1.000 |
| RSU Position Verification | 0.000 | 0.171 | 0.000 | 0.000 |
| Dynamic k-Means | 0.000 | 0.000 | 0.000 | 0.000 |

---

## Which detector should you use?

The recommendations below are calculated from utility functions applied to the measured data. Every claim is backed by numbers. Full derivations are in [analysis/scenario_guide.md](analysis/scenario_guide.md).

| Your situation | Best choice | Why |
|---|---|---|
| Detection must finish in under 1 second | Random Forest | F1 = 0.987 in 0.57 s; efficiency score of 2.19 (F1 divided by log of training time) beats all others |
| You cannot afford any false positives | TASER | The only detector with Precision = 1.000 at every attack intensity tested |
| The attack is already at 30% or more | TASER or RF | Both stay above F1 = 0.989 even at 40% Sybil rate |
| No labeled training data available | TASER | Works without labels and still achieves F1 = 0.997 and Specificity = 1.000 |
| Very limited compute (embedded device) | IQR | Runs in 0.05 s using only 2 stored values; use RF if you can afford 0.57 s |
| You need to catch attacks early (10%) | TASER or RF+GWO | Both reach F1 = 1.000 at 10% Sybil rate |

Three detectors sit on the Pareto frontier, meaning no other option beats them on both quality and speed simultaneously: **TASER**, **Random Forest**, and **IQR Speed Threshold**.

RF+GWO is not on that frontier. Random Forest reaches higher F1 (0.987 vs 0.984) in 200x less time. The GWO optimizer finds better hyperparameters in some runs but the improvement never justifies the overhead.

---

## Documentation index

| File | What you will find there |
|---|---|
| [docs/setup.md](docs/setup.md) | How to install SUMO, Python, and all libraries |
| [docs/running.md](docs/running.md) | Every pipeline step with expected console output |
| [docs/extending.md](docs/extending.md) | How to add your own detector in about 20 lines |
| [analysis/detector_profiles.md](analysis/detector_profiles.md) | Deep dive into each algorithm with convergence math |
| [analysis/scenario_guide.md](analysis/scenario_guide.md) | Utility scores and ranking for six real deployment scenarios |
| [analysis/math_justifications.txt](analysis/math_justifications.txt) | Raw computed statistics, Pareto frontier, dominance matrix |

---

## Repository layout

```
vanet-sybil-benchmark/
├── simulation/          SUMO network, route files, TraCI data collector
├── detectors/           Seven detection algorithms sharing a common interface
├── results/
│   ├── datasets/        One CSV per sybil rate (7k-12k rows each)
│   ├── metrics/         benchmark_results.csv with all 28 measurements
│   └── generate_analysis.py
├── figures/             Overview charts from benchmark.py
├── analysis/
│   ├── figures/         Eight detailed charts from generate_analysis.py
│   ├── detector_profiles.md
│   ├── scenario_guide.md
│   └── math_justifications.txt
├── docs/
│   ├── setup.md
│   ├── running.md
│   └── extending.md
└── benchmark.py
```
