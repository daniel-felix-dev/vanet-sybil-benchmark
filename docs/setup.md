# Environment Setup

## Prerequisites

| Software | Version | Purpose |
|---|---|---|
| Python | 3.9 + | Runtime for all scripts |
| SUMO | 1.12.0 | Traffic simulation engine |
| scikit-learn | ≥ 1.0 | IQR, RF, k-Means detectors |
| TensorFlow | ≥ 2.11 | LSTM detector |
| pandas / numpy / matplotlib | any | Data handling and figures |
| joblib | any | Model persistence |

---

## 1. Install SUMO

### Windows
Download the Windows installer from [eclipse.dev/sumo](https://eclipse.dev/sumo/).  
Default install path: `C:\Program Files (x86)\Eclipse\Sumo\`.

Set the `SUMO_HOME` environment variable permanently:

```powershell
[System.Environment]::SetEnvironmentVariable(
    "SUMO_HOME",
    "C:\Program Files (x86)\Eclipse\Sumo",
    "User"
)
```

Verify:
```powershell
$env:SUMO_HOME
# Should print: C:\Program Files (x86)\Eclipse\Sumo
```

### Linux / macOS
```bash
sudo apt-get install sumo sumo-tools   # Ubuntu/Debian
# or
brew install sumo                       # macOS

export SUMO_HOME=/usr/share/sumo
```

---

## 2. Install Python dependencies

```bash
pip install scikit-learn tensorflow joblib pandas numpy matplotlib
```

Verify the critical ones:

```python
import traci      # SUMO Python bindings (bundled with SUMO)
import sklearn    # scikit-learn
import tensorflow # TensorFlow / Keras
```

> **Note — Windows + TensorFlow:** TensorFlow ≥ 2.11 does not support native Windows GPU. The LSTM detector runs on CPU, which is sufficient for this benchmark. Expected LSTM fit time: 8–13 s per scenario.

---

## 3. Verify TraCI access

```python
import sys, os
sys.path.insert(0, os.path.join(os.environ["SUMO_HOME"], "tools"))
import traci
print("TraCI OK —", traci.__file__)
```

---

## 4. Clone the repository

```bash
git clone https://github.com/daniel-felix-dev/vanet-sybil-benchmark.git
cd vanet-sybil-benchmark
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: traci` | SUMO tools not in `sys.path` | Check `SUMO_HOME` and add `$SUMO_HOME/tools` to `PYTHONPATH` |
| `FatalTraCIError: connection closed by SUMO` | Route file has invalid edges | Re-run `generate_routes.py` after regenerating `network.net.xml` |
| `ModuleNotFoundError: sklearn` | scikit-learn not installed | `pip install scikit-learn` |
| `KMeans n_jobs error` | sklearn ≥ 1.x removed `n_jobs` from KMeans | Already patched in `kmeans_detector.py` |
| LSTM produces `acc=0.0` | Too few Sybil samples at low rate | Expected at 10% — see [analysis/detector_profiles.md](../analysis/detector_profiles.md#lstm) |
