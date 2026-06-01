from .iqr_detector    import IQRDetector
from .rsu_detector    import RSUDetector
from .taser_detector  import TASERDetector
from .rf_detector     import RFDetector
from .lstm_detector   import LSTMDetector
from .kmeans_detector import KMeansDetector

# GWORFDetector is excluded from the benchmark because single-seed evaluation
# already demonstrated statistical equivalence with the RF baseline
# (Wilcoxon p=0.640, Cohen's d=0.18 -- negligible effect).
# The implementation is preserved in gwo_rf_detector.py for reference.

ALL_DETECTORS = [
    IQRDetector,
    RSUDetector,
    TASERDetector,
    RFDetector,
    LSTMDetector,
    KMeansDetector,
]
