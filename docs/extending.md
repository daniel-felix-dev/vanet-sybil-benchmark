# Adding a New Detector

Every detector in this project inherits from a shared base class and implements two methods. The benchmark runner picks them up automatically, so once you write the class you just need to add one line to the import list.

---

## The interface

```python
class BaseDetector(ABC):
    name: str                           # shown in all output and charts

    def fit(self, df: pd.DataFrame):    # called once per scenario
        ...

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        ...                             # return array of 0s and 1s, same length as df
```

`evaluate()` is already implemented in the base class. It calls `predict()` and computes accuracy, precision, recall, F1, and specificity against the `is_sybil` column. Do not override it unless you need custom metric logic.

---

## Step 1: write the detector

Create a file in `detectors/`. Here is a minimal working example that flags vehicles whose average speed is unusually high:

```python
# detectors/high_speed_detector.py

import numpy as np
import pandas as pd
from .base_detector import BaseDetector


class HighSpeedDetector(BaseDetector):
    name = "High Speed Threshold"

    def __init__(self, z_threshold: float = 2.5):
        # z_threshold: how many standard deviations above the mean is suspicious
        self.z_threshold = z_threshold
        self._flagged = set()

    def fit(self, df: pd.DataFrame):
        # Compute each vehicle's mean speed across all its steps
        per_vehicle = df.groupby("vehicle_id")["speed"].mean()

        global_mean = per_vehicle.mean()
        global_std  = per_vehicle.std()

        # Flag vehicles whose mean speed is more than z_threshold std above normal
        self._flagged = set(
            per_vehicle[per_vehicle > global_mean + self.z_threshold * global_std].index
        )

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return df["vehicle_id"].isin(self._flagged).astype(int).values
```

---

## Step 2: register it

Open `detectors/__init__.py` and add two lines:

```python
from .high_speed_detector import HighSpeedDetector   # add this

ALL_DETECTORS = [
    IQRDetector,
    RSUDetector,
    TASERDetector,
    RFDetector,
    GWORFDetector,
    LSTMDetector,
    KMeansDetector,
    HighSpeedDetector,   # and this
]
```

---

## Step 3: run

```bash
python benchmark.py
```

Your detector will appear in all benchmark outputs, charts, and the summary table.

---

## Available features

Every row in the dataset has these columns to work with:

| Feature | Notes |
|---|---|
| speed | Most discriminative; Sybil nodes inject noise (std = 8 m/s) |
| accel | Derivative of speed; amplifies the noise signal |
| min_rsu_dist | Distance to nearest RSU; useful for position-based detectors |
| n_neighbors | Vehicles within 150 m; Sybil groups inflate this count |
| x, y | Reported position |
| angle | Heading |
| edge_id | Road segment identifier (categorical) |
| step | Time step; useful for sequential or temporal methods |

---

## Design notes

Decisions are made per vehicle, not per step. A vehicle gets one final label applied to all its rows. Your detector should accumulate evidence across steps in `fit()` and store which vehicle IDs to flag, then in `predict()` simply look up whether each row's `vehicle_id` is in that set.

Unsupervised detectors like IQR and k-Means must not read `df["is_sybil"]` during `fit()`. The framework supplies ground truth only for evaluation, not for training. Supervised detectors like Random Forest may use it.

If you want proper generalization testing, split inside `fit()` and train only on the training half. The current benchmark evaluates on the full dataset (in-sample), which gives optimistic numbers for supervised methods.
