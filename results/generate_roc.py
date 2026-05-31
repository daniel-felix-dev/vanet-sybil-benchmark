"""
generate_roc.py
===============
Generates ROC curves and AUC values for every detector that produces
soft probability scores (not just hard 0/1 labels).

Detectors with soft scores:
  - TASER: uses 1 - trust_score as Sybil probability
  - Random Forest: predict_proba (sklearn)
  - LSTM: sigmoid output

Detectors without soft scores (hard classifiers only):
  - IQR: binary flag; ROC is a single point
  - RSU: binary flag
  - k-Means: binary flag

For hard classifiers the single operating point is plotted on the
ROC space (recall vs 1-specificity) for completeness.

Output: analysis/figures/roc_curves_sybil{rate}.png  (one per sybil rate)
        analysis/roc_auc_table.md
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS_DIR  = os.path.join(BASE, "results", "datasets")
ANA_DIR = os.path.join(BASE, "analysis")
FIG_DIR = os.path.join(ANA_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

sys.path.insert(0, BASE)
from detectors import (TASERDetector, RFDetector, LSTMDetector,
                       IQRDetector, RSUDetector, KMeansDetector)

# Detectors with continuous probability output
SOFT_DETECTORS = [
    ("TASER Bayesian Trust", TASERDetector,  "#2196F3"),
    ("Random Forest",        RFDetector,     "#4CAF50"),
    ("LSTM",                 LSTMDetector,   "#FF9800"),
]
# Hard-label-only detectors (plot as single operating point)
HARD_DETECTORS = [
    ("IQR Speed Threshold",       IQRDetector,    "#F44336"),
    ("RSU Position Verification", RSUDetector,    "#9C27B0"),
    ("Dynamic k-Means",           KMeansDetector, "#795548"),
]

RATES = [10, 20, 30, 40]   # use existing 4-rate datasets for ROC

plt.rcParams.update({
    "font.size": 12, "axes.spines.top": False,
    "axes.spines.right": False, "figure.dpi": 150,
})

auc_records = []

for rate in RATES:
    ds_path = os.path.join(DS_DIR, f"dataset_sybil{rate}.csv")
    if not os.path.exists(ds_path):
        print(f"Skipping rate {rate}% (dataset not found)")
        continue
    df = pd.read_csv(ds_path)
    y_true = df["is_sybil"].values

    fig, ax = plt.subplots(figsize=(10, 8))

    # Diagonal (random classifier)
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, alpha=0.4, label="Random (AUC = 0.50)")

    # Soft detectors: full ROC curve
    for name, DetClass, color in SOFT_DETECTORS:
        try:
            det = DetClass()
            det.fit(df)
            scores = det.predict_proba(df)
            fpr, tpr, _ = roc_curve(y_true, scores)
            roc_auc = auc(fpr, tpr)
            ax.plot(fpr, tpr, color=color, linewidth=2.5,
                    label=f"{name}  AUC = {roc_auc:.4f}")
            auc_records.append({"detector": name, "sybil_rate": rate,
                                 "auc": round(roc_auc, 4), "type": "soft"})
        except Exception as e:
            print(f"  {name} at {rate}%: {e}")

    # Hard detectors: single operating point
    for name, DetClass, color in HARD_DETECTORS:
        try:
            det = DetClass()
            det.fit(df)
            y_pred = det.predict(df)
            tp = int(((y_true == 1) & (y_pred == 1)).sum())
            fn = int(((y_true == 1) & (y_pred == 0)).sum())
            fp = int(((y_true == 0) & (y_pred == 1)).sum())
            tn = int(((y_true == 0) & (y_pred == 0)).sum())
            tpr_pt = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            fpr_pt = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            ax.scatter(fpr_pt, tpr_pt, color=color, s=130, marker="D", zorder=5,
                       label=f"{name}  (single op. point)")
            auc_records.append({"detector": name, "sybil_rate": rate,
                                 "auc": None, "type": "hard"})
        except Exception as e:
            print(f"  {name} at {rate}%: {e}")

    ax.set_xlabel("False Positive Rate  (1 - Specificity)", fontsize=13)
    ax.set_ylabel("True Positive Rate  (Recall)", fontsize=13)
    ax.set_title(f"ROC Curves at {rate}% Sybil Rate\n"
                 f"(diamond = hard classifier at its default threshold)",
                 fontsize=13)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.05)
    ax.legend(fontsize=10, framealpha=0.9, loc="lower right")
    fig.tight_layout()
    out = os.path.join(FIG_DIR, f"roc_curves_sybil{rate}.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved roc_curves_sybil{rate}.png")

# AUC summary table
auc_df = pd.DataFrame(auc_records)
soft = auc_df[auc_df["type"] == "soft"].pivot_table(
    index="detector", columns="sybil_rate", values="auc"
)

lines = ["# ROC AUC Summary", "",
         "AUC values for detectors that produce probability scores.",
         "Hard classifiers (IQR, RSU, k-Means) produce a single operating point",
         "and do not have a meaningful AUC.", ""]

if not soft.empty:
    lines.append("| Detector | 10% | 20% | 30% | 40% | Mean AUC |")
    lines.append("|---|---|---|---|---|---|")
    for det in soft.index:
        vals = soft.loc[det].values
        vals_str = "  |  ".join(f"{v:.4f}" if not np.isnan(v) else "n/a" for v in vals)
        mean_auc = np.nanmean(vals)
        lines.append(f"| {det} | {vals_str} | {mean_auc:.4f} |")

lines += [
    "",
    "## Interpretation",
    "",
    "AUC = 1.0 means the detector perfectly separates Sybil from legitimate at every",
    "possible threshold. AUC = 0.5 is equivalent to random guessing.",
    "",
    "An AUC close to 1.0 for TASER confirms that the trust score is a reliable",
    "Sybil indicator, not just at the default lambda = 0.15 threshold, but across",
    "the entire operating range. The same applies to Random Forest's class probabilities.",
]

out_md = os.path.join(ANA_DIR, "roc_auc_table.md")
with open(out_md, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"ROC AUC table -> {out_md}")
