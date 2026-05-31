from .iqr_detector    import IQRDetector
from .rsu_detector    import RSUDetector
from .taser_detector  import TASERDetector
from .rf_detector     import RFDetector
from .gwo_rf_detector import GWORFDetector
from .lstm_detector   import LSTMDetector
from .kmeans_detector import KMeansDetector

ALL_DETECTORS = [
    IQRDetector,
    RSUDetector,
    TASERDetector,
    RFDetector,
    GWORFDetector,
    LSTMDetector,
    KMeansDetector,
]
