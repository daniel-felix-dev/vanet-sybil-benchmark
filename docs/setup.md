# Setup

## Requirements

| Software | Version | Install |
|---|---|---|
| Python | 3.9+ | python.org |
| SUMO | 1.12.0 | eclipse.dev/sumo |
| scikit-learn | any | `pip install scikit-learn` |
| TensorFlow | 2.11+ | `pip install tensorflow` |
| pandas, numpy, matplotlib, scipy | any | `pip install pandas numpy matplotlib scipy` |

SUMO must be installed before running any simulation script. After install, verify:
```bash
sumo --version
python -c "import traci; print('OK')"
```

## Windows path (default)

The scripts expect SUMO at `C:\Program Files (x86)\Eclipse\Sumo`. If your install differs, update `SUMO_BIN` in `simulation/collect_dataset.py` and `simulation/collect_dataset_split.py`.

## Quick start

```bash
# 1. Generate routes (already committed, only needed if you change scenarios)
python simulation/generate_routes.py

# 2. Collect datasets (~35s)
python simulation/collect_dataset.py

# 3. Run benchmark (~20 min, 6 detectors x 8 rates)
python benchmark.py

# 4. Generate figures and analysis
python results/generate_analysis.py
```

For the **multi-seed benchmark** (5 seeds, used for the published results):
```bash
python simulation/run_multi_seed.py   # ~20 min
```

For the **split-position attack model**:
```bash
python simulation/collect_dataset_split.py
python benchmark_split.py
python results/compare_attack_models.py
```
