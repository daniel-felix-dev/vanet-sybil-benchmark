"""
generate_additional_figures.py
Generates supplementary visualizations not covered by the main scripts.

Figures produced:
  f1_trend_lines.png          - F1 vs sybil rate line chart (all detectors)
  attack_model_comparison.png - Co-location vs split-position mean F1 bar chart
  data_leakage_comparison.png - RF in-sample vs OOS F1 (data leakage visual)
  kmeans_criterion_fix.png    - k-Means F1 before/after criterion correction
  heatmap_f1_split.png        - Split-position F1 heatmap (matches heatmap_f1)
  precision_by_rate.png       - Precision vs sybil rate per detector
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG    = os.path.join(BASE, "analysis", "figures")
METS   = os.path.join(BASE, "results", "metrics")

df  = pd.read_csv(os.path.join(METS, "benchmark_results.csv"))
raw = pd.read_csv(os.path.join(METS, "multi_seed_raw.csv"))
sp  = pd.read_csv(os.path.join(METS, "benchmark_split_results.csv"))

RATES    = [5, 10, 15, 20, 25, 30, 35, 40]
DET_ORDER = [
    "TASER Bayesian Trust",
    "Dynamic k-Means",
    "Random Forest",
    "LSTM",
    "IQR Speed Threshold",
    "RSU Position Verification",
]
LABELS = ["TASER", "k-Means", "RF", "LSTM", "IQR", "RSU"]
COLORS = ["#2ecc71", "#27ae60", "#3498db", "#e67e22", "#9b59b6", "#e74c3c"]

prate_co = df.pivot_table(index="detector", columns="sybil_rate", values="f1")
prate_sp = sp.pivot_table(index="detector", columns="sybil_rate", values="f1")
agg_co   = df.groupby("detector")["f1"].mean()
agg_sp   = sp.groupby("detector")["f1"].mean()

# ─────────────────────────────────────────────────────────────────────────────
# 1. F1 trend lines (line chart, all detectors, co-location)
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
for det, label, color in zip(DET_ORDER, LABELS, COLORS):
    vals = [prate_co.loc[det, r] for r in RATES]
    ax.plot(RATES, vals, marker="o", label=label, color=color, linewidth=2, markersize=5)

ax.set_xlabel("Sybil Rate (%)", fontsize=12)
ax.set_ylabel("F1-Score", fontsize=12)
ax.set_title("F1-Score vs Sybil Rate — Co-location Attack", fontsize=13)
ax.set_xticks(RATES)
ax.set_xticklabels([f"{r}%" for r in RATES])
ax.set_ylim(-0.05, 1.05)
ax.legend(loc="lower right", ncol=2, fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "f1_trend_lines.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved f1_trend_lines.png")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Attack model comparison — grouped bar chart
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 5))
x = np.arange(len(LABELS))
w = 0.38
co_vals = [agg_co[d] for d in DET_ORDER]
sp_vals = [agg_sp[d] for d in DET_ORDER]

b1 = ax.bar(x - w/2, co_vals, w, label="Co-location",   color="#3498db", alpha=0.85)
b2 = ax.bar(x + w/2, sp_vals, w, label="Split-position", color="#e67e22", alpha=0.85)

for bar in b1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
            f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=8)
for bar in b2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
            f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(LABELS, fontsize=11)
ax.set_ylabel("Mean F1-Score (over 8 rates)", fontsize=11)
ax.set_title("Attack Model Comparison: Co-location vs Split-position", fontsize=13)
ax.set_ylim(0, 1.12)
ax.legend(fontsize=11)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "attack_model_comparison.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved attack_model_comparison.png")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Data leakage comparison — in-sample vs OOS for RF
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
rf_oos = prate_co.loc["Random Forest", RATES].values
rf_ins = [0.987] * len(RATES)  # documented in-sample estimate (constant approx)
ax.plot(RATES, rf_ins, "r--", linewidth=2, label="In-sample (row-level CV) ≈ 0.987", marker="s", markersize=5)
ax.plot(RATES, rf_oos, "b-",  linewidth=2, label="Out-of-sample (vehicle-level CV)", marker="o", markersize=5)
ax.fill_between(RATES, rf_oos, rf_ins, alpha=0.15, color="red", label="Leakage gap")

ax.set_xlabel("Sybil Rate (%)", fontsize=12)
ax.set_ylabel("F1-Score", fontsize=12)
ax.set_title("Random Forest: Data Leakage Visualised\n"
             "In-sample vs Vehicle-level Out-of-sample F1", fontsize=12)
ax.set_xticks(RATES)
ax.set_xticklabels([f"{r}%" for r in RATES])
ax.set_ylim(0.5, 1.05)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
mid = len(RATES) // 2
ax.annotate("9.3 pp gap\n(mean)",
            xy=(RATES[mid], (rf_ins[mid]+rf_oos[mid])/2),
            xytext=(RATES[mid]-3, 0.92),
            fontsize=10, color="red",
            arrowprops=dict(arrowstyle="->", color="red"))
plt.tight_layout()
plt.savefig(os.path.join(FIG, "data_leakage_comparison.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved data_leakage_comparison.png")

# ─────────────────────────────────────────────────────────────────────────────
# 4. k-Means criterion fix — before vs after per rate
# ─────────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
km_after  = prate_co.loc["Dynamic k-Means", RATES].values
km_before = np.zeros(len(RATES))  # original criterion gave F1=0.000

x = np.arange(len(RATES))
w = 0.38
ax.bar(x - w/2, km_before, w, color="#e74c3c", alpha=0.85, label="Original criterion (mean speed z-score)")
ax.bar(x + w/2, km_after,  w, color="#27ae60", alpha=0.85, label="Corrected criterion (std_speed MAD z-score)")

ax.set_xticks(x)
ax.set_xticklabels([f"{r}%" for r in RATES], fontsize=11)
ax.set_ylabel("F1-Score", fontsize=12)
ax.set_title("Dynamic k-Means: Impact of Criterion Correction\n"
             "Mean Speed → Speed Variance (MAD-normalised)", fontsize=12)
ax.set_ylim(0, 1.10)
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)
for i, v in enumerate(km_after):
    ax.text(x[i] + w/2, v + 0.01, f"{v:.3f}", ha="center", va="bottom", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "kmeans_criterion_fix.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved kmeans_criterion_fix.png")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Split-position heatmap (matches style of heatmap_f1.png)
# ─────────────────────────────────────────────────────────────────────────────
data = prate_sp.loc[DET_ORDER, RATES].values
fig, ax = plt.subplots(figsize=(10, 4))
im = ax.imshow(data, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(RATES)))
ax.set_xticklabels([f"{r}%" for r in RATES], fontsize=11)
ax.set_yticks(range(len(LABELS)))
ax.set_yticklabels(LABELS, fontsize=11)
ax.set_xlabel("Sybil Rate", fontsize=11)
for i in range(len(LABELS)):
    for j in range(len(RATES)):
        val = data[i, j]
        color = "white" if val < 0.35 or val > 0.85 else "black"
        ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                fontsize=8.5, color=color, fontweight="bold")
plt.colorbar(im, ax=ax, label="F1-Score")
ax.set_title("F1-Score Heatmap — Split-position Attack", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(FIG, "heatmap_f1_split.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved heatmap_f1_split.png")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Precision by rate — shows which detectors maintain precision under load
# ─────────────────────────────────────────────────────────────────────────────
prate_prec = df.pivot_table(index="detector", columns="sybil_rate", values="precision")
fig, ax = plt.subplots(figsize=(10, 5))
for det, label, color in zip(DET_ORDER, LABELS, COLORS):
    vals = [prate_prec.loc[det, r] for r in RATES]
    ax.plot(RATES, vals, marker="o", label=label, color=color, linewidth=2, markersize=5)

ax.axhline(1.0, color="gray", linestyle="--", linewidth=1, alpha=0.5)
ax.set_xlabel("Sybil Rate (%)", fontsize=12)
ax.set_ylabel("Precision", fontsize=12)
ax.set_title("Precision vs Sybil Rate — Co-location Attack\n"
             "Only TASER maintains Precision = 1.000 at every rate", fontsize=12)
ax.set_xticks(RATES)
ax.set_xticklabels([f"{r}%" for r in RATES])
ax.set_ylim(-0.05, 1.08)
ax.legend(loc="lower right", ncol=2, fontsize=10)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "precision_by_rate.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved precision_by_rate.png")

print(f"\nAll figures -> {FIG}")
