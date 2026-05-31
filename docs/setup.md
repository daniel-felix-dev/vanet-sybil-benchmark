# Setting Up the Environment

## What you need

| Software | Minimum version | What it does |
|---|---|---|
| Python | 3.9 | Runs all scripts |
| SUMO | 1.12.0 | Simulates vehicle traffic |
| scikit-learn | 1.0 | IQR, Random Forest, k-Means detectors |
| TensorFlow | 2.11 | LSTM detector |
| pandas, numpy, matplotlib | any recent | Data handling and charts |

---

## Installing SUMO

SUMO is the traffic simulator that generates the vehicle movement data. You need it even if you only want to run the detectors, because the datasets were produced by it and you will need to reproduce them.

### Windows

Download the installer from [eclipse.dev/sumo](https://eclipse.dev/sumo/) and run it. The default path is `C:\Program Files (x86)\Eclipse\Sumo`.

After installing, tell your system where SUMO lives by setting an environment variable. Open PowerShell and run:

```powershell
[System.Environment]::SetEnvironmentVariable(
    "SUMO_HOME",
    "C:\Program Files (x86)\Eclipse\Sumo",
    "User"
)
```

Close and reopen your terminal, then confirm it worked:

```powershell
echo $env:SUMO_HOME
# Should print the path above
```

### Linux

```bash
sudo apt-get install sumo sumo-tools
export SUMO_HOME=/usr/share/sumo
# Add that export to your ~/.bashrc to make it permanent
```

### macOS

```bash
brew install sumo
export SUMO_HOME=$(brew --prefix sumo)/share/sumo
```

---

## Installing Python libraries

```bash
pip install scikit-learn tensorflow joblib pandas numpy matplotlib
```

Quick check that everything loaded:

```python
import traci      # bundled with SUMO, no separate install
import sklearn
import tensorflow
print("all good")
```

If `traci` is not found, your Python cannot see the SUMO tools folder. Fix it:

```python
import sys, os
sys.path.insert(0, os.path.join(os.environ["SUMO_HOME"], "tools"))
import traci  # should work now
```

---

## A note on TensorFlow and GPUs

TensorFlow 2.11 and later does not support GPU acceleration on native Windows. The LSTM detector will run on CPU, which is slow enough that you will notice (expect 8 to 13 seconds per scenario) but not slow enough to block the benchmark. If you want GPU support on Windows, run everything inside WSL2.

---

## Common errors and fixes

**`traci` not found:** SUMO_HOME is not set or Python cannot reach the tools folder. Add `SUMO_HOME/tools` to your PYTHONPATH.

**`FatalTraCIError: connection closed by SUMO`:** The route file contains an invalid edge. Re-run `generate_routes.py` to rebuild the routes from the current network.

**`ModuleNotFoundError: sklearn`:** Run `pip install scikit-learn`.

**LSTM outputs F1 = 0.000 at 10% Sybil rate:** This is expected behavior, not a bug. With only 5-6% positive samples, the network cannot learn the Sybil pattern in 20 epochs. See [analysis/detector_profiles.md](../analysis/detector_profiles.md) for the full explanation.
