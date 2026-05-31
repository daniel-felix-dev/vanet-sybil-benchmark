# Adding a New Detector

All detectors inherit from `detectors/base_detector.py` and implement two methods: `fit` and `predict`.

## 1. Create the detector file

```python
# detectors/my_detector.py

import numpy as np
import pandas as pd
from .base_detector import BaseDetector


class MyDetector(BaseDetector):
    name = "My Detector"          # shown in benchmark output and figures

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self._sybil_ids = set()   # store decisions at fit time

    def fit(self, df: pd.DataFrame):
        """
        Train / calibrate on the full dataset.
        df columns: step, vehicle_id, x, y, speed, accel, angle,
                    edge_id, n_neighbors, min_rsu_dist, mean_rsu_dist,
                    is_sybil, attacker_id
        """
        # Example: flag vehicles whose mean speed exceeds threshold
        mean_speed = df.groupby("vehicle_id")["speed"].mean()
        self._sybil_ids = set(mean_speed[mean_speed > self.threshold].index)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Return binary array aligned with df index. 1 = Sybil, 0 = Legit."""
        return df["vehicle_id"].isin(self._sybil_ids).astype(int).values
```

## 2. Register in `__init__.py`

```python
# detectors/__init__.py

from .my_detector import MyDetector    # add this import

ALL_DETECTORS = [
    IQRDetector,
    RSUDetector,
    TASERDetector,
    RFDetector,
    GWORFDetector,
    LSTMDetector,
    KMeansDetector,
    MyDetector,                        # add here
]
```

## 3. Run

```bash
python benchmark.py
```

Your detector will appear in all benchmark outputs and figures automatically.

---

## BaseDetector interface

```python
class BaseDetector(ABC):
    name: str                          # display name

    def fit(self, df: pd.DataFrame):   # receives full dataset
        ...

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        ...                            # returns int array shape (len(df),)

    def evaluate(self, df: pd.DataFrame) -> dict:
        # provided — calls fit() then predict() internally
        # returns: accuracy, precision, recall, f1, specificity
        ...
```

`evaluate()` is already implemented in the base class — do not override it unless you need custom metric logic.

---

## Tips

- **Unsupervised detectors** (IQR, k-Means, RSU) should not use `df["is_sybil"]` in `fit()`. The framework will evaluate using ground truth separately.
- **Supervised detectors** (RF, LSTM) may use `df["is_sybil"]` in `fit()` — but note they are then evaluated on the same data (in-sample). For proper out-of-sample evaluation, split inside `fit()`.
- **Decision granularity**: decisions are made per-vehicle (not per-step). A vehicle is flagged Sybil if *any* of its steps triggers the detector — or if the aggregated profile crosses a threshold. This matches real VANET deployment where detection happens after enough beacons have been received.
- **Feature set**: all features collected by `collect_dataset.py` are available. The most discriminative in practice: `speed`, `accel`, `min_rsu_dist`, `n_neighbors`.
