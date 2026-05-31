"""
generate_analysis.py
====================
Generates all figures for analysis/ and computes mathematical justifications
for the scenario recommendation guide.

Outputs:
  analysis/figures/  — 8 PNG charts
  analysis/math_justifications.txt  — computed statistics used in scenario_guide.md
"""

import os, math, textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA    = os.path.join(BASE, "results", "metrics", "benchmark_results.csv")
DS_DIR  = os.path.join(BASE, "results", "datasets")
ANA_FIG = os.path.join(BASE, "analysis", "figures")
ANA_DIR = os.path.join(BASE, "analysis")
os.makedirs(ANA_FIG, exist_ok=True)

df = pd.read_csv(DATA)
RATES     = sorted(df["sybil_rate"].unique())
DETECTORS = [
    "TASER Bayesian Trust",
    "Random Forest",
    "Random Forest + GWO",
    "LSTM",
    "IQR Speed Threshold",
    "RSU Position Verification",
    "Dynamic k-Means",
]
METRICS = ["accuracy", "precision", "recall", "f1", "specificity"]
COLORS  = {
    "TASER Bayesian Trust":      "#2196F3",
    "Random Forest":             "#4CAF50",
    "Random Forest + GWO":       "#8BC34A",
    "LSTM":                      "#FF9800",
    "IQR Speed Threshold":       "#F44336",
    "RSU Position Verification": "#9C27B0",
    "Dynamic k-Means":           "#795548",
}

plt.rcParams.update({
    "figure.dpi": 150, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.3, "font.size": 10,
})

# ─────────────────────────────────────────────────────────────────────────────
# MATHEMATICAL COMPUTATIONS
# ─────────────────────────────────────────────────────────────────────────────

summary = df.groupby("detector")[METRICS + ["fit_time_s"]].agg(
    ["mean", "std", "min", "max"]
)
summary.columns = ["_".join(c) for c in summary.columns]

# 1. F1 std across sybil rates (robustness — lower is better)
f1_std = df.groupby("detector")["f1"].std().rename("f1_std")

# 2. Efficiency ratio: F1_mean / log(fit_time_mean + 1)
fit_mean = df.groupby("detector")["fit_time_s"].mean()
f1_mean  = df.groupby("detector")["f1"].mean()
efficiency = (f1_mean / np.log1p(fit_mean)).rename("efficiency")

# 3. Weighted utility functions per scenario
def utility(weights: dict, det_row) -> float:
    """Compute weighted utility: weights keys are metric names."""
    total_w = sum(abs(w) for w in weights.values())
    return sum(w * det_row.get(k, 0) for k, w in weights.items()) / total_w

scenarios = {
    "Latency-critical (real-time)": {
        "f1_mean": 0.4, "precision_mean": 0.3,
        "neg_log_fit": 0.3,          # higher weight to speed
    },
    "Zero false-positives (safety)": {
        "precision_mean": 0.7, "f1_mean": 0.3,
    },
    "High Sybil rate (≥30%)": {
        "f1_at_30": 0.4, "f1_at_40": 0.4, "precision_mean": 0.2,
    },
    "No labels available (unsupervised)": {
        "recall_mean": 0.5, "specificity_mean": 0.5,
    },
    "Resource-constrained (embedded)": {
        "f1_mean": 0.3, "neg_log_fit": 0.7,
    },
    "Low Sybil rate (≤10%)": {
        "f1_at_10": 0.6, "precision_at_10": 0.4,
    },
}

# Build per-detector stats dict
det_stats = {}
for det in DETECTORS:
    sub = df[df["detector"] == det].set_index("sybil_rate")
    row = {
        "f1_mean":        sub["f1"].mean(),
        "precision_mean": sub["precision"].mean(),
        "recall_mean":    sub["recall"].mean(),
        "specificity_mean": sub["specificity"].mean(),
        "f1_std":         sub["f1"].std(),
        "fit_time_mean":  sub["fit_time_s"].mean(),
        "neg_log_fit":    -math.log1p(sub["fit_time_s"].mean()),  # negated for utility
        "efficiency":     sub["f1"].mean() / math.log1p(sub["fit_time_s"].mean()),
    }
    for r in RATES:
        if r in sub.index:
            row[f"f1_at_{r}"]        = sub.loc[r, "f1"]
            row[f"precision_at_{r}"] = sub.loc[r, "precision"]
            row[f"recall_at_{r}"]    = sub.loc[r, "recall"]
        else:
            row[f"f1_at_{r}"] = row[f"precision_at_{r}"] = row[f"recall_at_{r}"] = 0.0
    det_stats[det] = row

# 4. Pareto frontier (F1_mean vs -fit_time)
def is_pareto(det, all_dets):
    """A detector is Pareto-optimal if no other dominates it on both F1 and speed."""
    me = all_dets[det]
    for other_name, other in all_dets.items():
        if other_name == det:
            continue
        if other["f1_mean"] >= me["f1_mean"] and other["fit_time_mean"] <= me["fit_time_mean"]:
            if other["f1_mean"] > me["f1_mean"] or other["fit_time_mean"] < me["fit_time_mean"]:
                return False
    return True

pareto = {d: is_pareto(d, det_stats) for d in DETECTORS}

# 5. Dominance matrix: det_A dominates det_B if F1_A > F1_B at every sybil rate
dom_matrix = pd.DataFrame(0, index=DETECTORS, columns=DETECTORS)
for a in DETECTORS:
    for b in DETECTORS:
        if a == b:
            continue
        f1_a = df[df["detector"] == a].sort_values("sybil_rate")["f1"].values
        f1_b = df[df["detector"] == b].sort_values("sybil_rate")["f1"].values
        if all(f1_a >= f1_b):
            dom_matrix.loc[a, b] = 1

# 6. Utility scores per scenario
scenario_scores = {}
for sc_name, weights in scenarios.items():
    scores = {}
    for det in DETECTORS:
        row = det_stats[det]
        # normalise neg_log_fit to [0,1] across detectors if present
        s = 0.0
        total_w = 0.0
        for k, w in weights.items():
            val = row.get(k, 0.0)
            s += w * val
            total_w += abs(w)
        scores[det] = s / total_w if total_w > 0 else 0.0
    scenario_scores[sc_name] = scores

# ─────────────────────────────────────────────────────────────────────────────
# WRITE MATH JUSTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────

out_lines = []
out_lines.append("=" * 78)
out_lines.append("MATHEMATICAL JUSTIFICATIONS FOR SCENARIO RECOMMENDATIONS")
out_lines.append("=" * 78)

out_lines.append("\n── 1. Summary statistics ──")
for det in DETECTORS:
    r = det_stats[det]
    out_lines.append(
        f"  {det:<30} F1_mean={r['f1_mean']:.4f}  F1_std={r['f1_std']:.4f}"
        f"  Prec_mean={r['precision_mean']:.4f}  Rec_mean={r['recall_mean']:.4f}"
        f"  fit_time={r['fit_time_mean']:.2f}s"
        f"  efficiency={r['efficiency']:.4f}"
    )

out_lines.append("\n── 2. Pareto frontier (F1 vs speed) ──")
for det in DETECTORS:
    out_lines.append(f"  {'✓' if pareto[det] else '✗'} {det}")

out_lines.append("\n── 3. Dominance matrix (row dominates column at all sybil rates) ──")
out_lines.append("  " + dom_matrix.to_string().replace("\n", "\n  "))

out_lines.append("\n── 4. Utility scores per scenario ──")
for sc_name, scores in scenario_scores.items():
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    out_lines.append(f"\n  Scenario: {sc_name}")
    for det, s in ranked:
        out_lines.append(f"    {det:<30} utility={s:.4f}")

out_lines.append("\n── 5. F1 per sybil rate (all detectors) ──")
pivot = df.pivot_table(index="detector", columns="sybil_rate", values="f1")
out_lines.append("  " + pivot.to_string().replace("\n", "\n  "))

out_lines.append("\n── 6. Efficiency ratio F1_mean / ln(fit_time + 1) ──")
eff_sorted = efficiency.sort_values(ascending=False)
for det, val in eff_sorted.items():
    ft = det_stats[det]["fit_time_mean"]
    f1 = det_stats[det]["f1_mean"]
    out_lines.append(f"  {det:<30} = {f1:.4f} / ln({ft:.2f}+1) = {val:.4f}")

math_path = os.path.join(ANA_DIR, "math_justifications.txt")
with open(math_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
print(f"Math justifications -> {math_path}")

# ─────────────────────────────────────────────────────────────────────────────
# FIGURES
# ─────────────────────────────────────────────────────────────────────────────

# ── Fig 1: F1 Heatmap ────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
pivot_f1 = df.pivot_table(index="detector", columns="sybil_rate", values="f1")
pivot_f1 = pivot_f1.loc[DETECTORS]

cmap = LinearSegmentedColormap.from_list("rg", ["#F44336", "#FFF176", "#4CAF50"])
im = ax.imshow(pivot_f1.values, cmap=cmap, aspect="auto", vmin=0, vmax=1)
ax.set_xticks(range(len(RATES)))
ax.set_xticklabels([f"{r}%" for r in RATES])
ax.set_yticks(range(len(DETECTORS)))
ax.set_yticklabels(DETECTORS, fontsize=9)
ax.set_xlabel("Sybil Rate")
ax.set_title("F1-Score Heatmap — Detector × Sybil Rate")
plt.colorbar(im, ax=ax, label="F1-Score")
for i in range(len(DETECTORS)):
    for j in range(len(RATES)):
        val = pivot_f1.values[i, j]
        ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                fontsize=8, color="black" if val > 0.3 else "white")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "heatmap_f1.png"), dpi=150)
plt.close()
print("Saved heatmap_f1.png")

# ── Fig 2: Radar per detector ─────────────────────────────────────────────────
mean_metrics = df.groupby("detector")[METRICS].mean()
angles = np.linspace(0, 2 * np.pi, len(METRICS), endpoint=False).tolist()
angles += angles[:1]

fig, axes = plt.subplots(2, 4, figsize=(16, 8), subplot_kw=dict(polar=True))
axes = axes.flatten()
for idx, det in enumerate(DETECTORS):
    ax = axes[idx]
    vals = mean_metrics.loc[det, METRICS].tolist()
    vals += vals[:1]
    ax.plot(angles, vals, color=COLORS[det], linewidth=2)
    ax.fill(angles, vals, color=COLORS[det], alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(["Acc", "Prec", "Rec", "F1", "Spec"], fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["", "0.5", "", "1.0"], fontsize=6)
    ax.set_title(det.replace(" ", "\n") if len(det) > 20 else det,
                 fontsize=8, pad=10, color=COLORS[det], fontweight="bold")
axes[-1].set_visible(False)
fig.suptitle("Metric Radar — Mean across all sybil rates", fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "radar_per_detector.png"), dpi=150)
plt.close()
print("Saved radar_per_detector.png")

# ── Fig 3: Efficiency scatter (F1 vs fit_time) ───────────────────────────────
fig, ax = plt.subplots(figsize=(9, 6))
for det in DETECTORS:
    r = det_stats[det]
    x = r["fit_time_mean"]
    y = r["f1_mean"]
    err = r["f1_std"]
    star = "★" if pareto[det] else ""
    ax.errorbar(x, y, yerr=err, fmt="o", color=COLORS[det],
                markersize=10, capsize=4, linewidth=1.5)
    ax.annotate(f"{det} {star}",
                (x, y), textcoords="offset points",
                xytext=(8, 4), fontsize=8, color=COLORS[det])

ax.set_xscale("log")
ax.set_xlabel("Mean Fit Time (s) — log scale")
ax.set_ylabel("Mean F1-Score (± std across sybil rates)")
ax.set_title("Computational Efficiency vs Detection Quality\n★ = Pareto-optimal")
ax.set_ylim(-0.05, 1.1)
ax.set_xlim(0.03, 200)
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "cost_vs_f1.png"), dpi=150)
plt.close()
print("Saved cost_vs_f1.png")

# ── Fig 4: Precision–Recall per sybil rate ───────────────────────────────────
fig, axes = plt.subplots(1, 4, figsize=(16, 4), sharey=True)
for ax, rate in zip(axes, RATES):
    sub = df[df["sybil_rate"] == rate]
    for det in DETECTORS:
        row = sub[sub["detector"] == det].iloc[0]
        ax.scatter(row["recall"], row["precision"],
                   color=COLORS[det], s=100, zorder=3)
        ax.annotate(det.split()[0], (row["recall"], row["precision"]),
                    textcoords="offset points", xytext=(4, 3), fontsize=7,
                    color=COLORS[det])
    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)
    ax.set_xlabel("Recall")
    ax.set_title(f"Sybil Rate = {rate}%")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.2, linewidth=1)
axes[0].set_ylabel("Precision")
fig.suptitle("Precision–Recall Space per Sybil Rate", fontsize=12, fontweight="bold")
# Legend
handles = [mpatches.Patch(color=COLORS[d], label=d) for d in DETECTORS]
fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8,
           bbox_to_anchor=(0.5, -0.08), framealpha=0.85)
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "precision_recall_space.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("Saved precision_recall_space.png")

# ── Fig 5: F1 variance (boxplot-style) ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
f1_by_det = [df[df["detector"] == d]["f1"].values for d in DETECTORS]
bp = ax.boxplot(f1_by_det, patch_artist=True, widths=0.5,
                medianprops=dict(color="white", linewidth=2))
for patch, det in zip(bp["boxes"], DETECTORS):
    patch.set_facecolor(COLORS[det])
    patch.set_alpha(0.8)
ax.set_xticks(range(1, len(DETECTORS) + 1))
ax.set_xticklabels(DETECTORS, rotation=20, ha="right", fontsize=9)
ax.set_ylabel("F1-Score")
ax.set_title("F1-Score Distribution across Sybil Rates\n(spread = robustness indicator)")
ax.set_ylim(-0.05, 1.1)
# Annotate mean
for i, det in enumerate(DETECTORS):
    m = det_stats[det]["f1_mean"]
    ax.text(i + 1, 1.05, f"μ={m:.3f}", ha="center", fontsize=7, color=COLORS[det])
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "f1_variance.png"), dpi=150)
plt.close()
print("Saved f1_variance.png")

# ── Fig 6: Speed distribution legit vs sybil ─────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, rate in zip(axes, [10, 40]):
    ds_path = os.path.join(DS_DIR, f"dataset_sybil{rate}.csv")
    if not os.path.exists(ds_path):
        continue
    ds = pd.read_csv(ds_path)
    legit = ds[ds["is_sybil"] == 0]["speed"]
    sybil = ds[ds["is_sybil"] == 1]["speed"]
    bins  = np.linspace(0, 40, 60)
    ax.hist(legit, bins=bins, density=True, alpha=0.6, color="#2196F3",
            label=f"Legit (n={len(legit):,})")
    ax.hist(sybil, bins=bins, density=True, alpha=0.6, color="#F44336",
            label=f"Sybil (n={len(sybil):,})")
    q1 = legit.quantile(0.25)
    q3 = legit.quantile(0.75)
    iqr = q3 - q1
    fence = q1 - 1.5 * iqr
    ax.axvline(fence, color="black", linestyle="--", linewidth=1.5,
               label=f"IQR fence={fence:.2f}")
    ax.set_xlabel("Speed (m/s)")
    ax.set_ylabel("Density")
    ax.set_title(f"Speed Distribution — Sybil Rate {rate}%")
    ax.legend(fontsize=8)
fig.suptitle("Why IQR Detects Speed Anomalies", fontsize=11, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "speed_distribution.png"), dpi=150)
plt.close()
print("Saved speed_distribution.png")

# ── Fig 7: TP / FP / FN breakdown ────────────────────────────────────────────
# Estimate TP, FP, FN from precision, recall and sybil counts
fig, axes = plt.subplots(1, 4, figsize=(16, 5), sharey=False)
for ax, rate in zip(axes, RATES):
    sub_rate = df[df["sybil_rate"] == rate]
    ds_path  = os.path.join(DS_DIR, f"dataset_sybil{rate}.csv")
    if os.path.exists(ds_path):
        ds = pd.read_csv(ds_path)
        n_pos = int(ds["is_sybil"].sum())
        n_neg = len(ds) - n_pos
    else:
        n_pos, n_neg = 1, 1

    tps, fps, fns = [], [], []
    labels = []
    for det in DETECTORS:
        row = sub_rate[sub_rate["detector"] == det].iloc[0]
        prec = row["precision"]
        rec  = row["recall"]
        tp   = rec * n_pos
        fp   = (tp / prec - tp) if prec > 0 else 0
        fn   = n_pos - tp
        tps.append(tp / n_pos)    # normalised
        fps.append(fp / n_neg)
        fns.append(fn / n_pos)
        labels.append(det.split()[0])

    x = np.arange(len(DETECTORS))
    ax.bar(x, tps, label="TP rate", color="#4CAF50", alpha=0.85)
    ax.bar(x, fns, bottom=tps, label="FN rate", color="#FF9800", alpha=0.85)
    ax.bar(x, fps, bottom=[t+f for t, f in zip(tps, fns)],
           label="FP rate (vs neg)", color="#F44336", alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=7)
    ax.set_title(f"{rate}% Sybil")
    ax.set_ylim(0, 2.1)
    if ax == axes[0]:
        ax.set_ylabel("Rate (normalised per class)")
axes[-1].legend(loc="upper right", fontsize=7)
fig.suptitle("TP / FN / FP Breakdown per Detector and Sybil Rate",
             fontsize=11, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "tp_fp_fn_breakdown.png"), dpi=150)
plt.close()
print("Saved tp_fp_fn_breakdown.png")

# ── Fig 8: Scenario utility ranking ──────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
axes_flat = axes.flatten()
for ax, (sc_name, scores) in zip(axes_flat, scenario_scores.items()):
    ranked = sorted(scores.items(), key=lambda x: x[1])
    dets   = [d for d, _ in ranked]
    vals   = [v for _, v in ranked]
    colors = [COLORS[d] for d in dets]
    bars   = ax.barh(range(len(dets)), vals, color=colors, alpha=0.85)
    ax.set_yticks(range(len(dets)))
    ax.set_yticklabels(dets, fontsize=8)
    ax.set_xlabel("Utility Score")
    ax.set_title(sc_name, fontsize=9, fontweight="bold")
    ax.set_xlim(0, max(vals) * 1.25 if max(vals) > 0 else 1)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
                f"{val:.3f}", va="center", fontsize=7)
fig.suptitle("Utility Score per Scenario × Detector\n"
             "(computed from weighted metric combinations)",
             fontsize=11, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "scenario_utility_ranking.png"), dpi=150)
plt.close()
print("Saved scenario_utility_ranking.png")

print(f"\nAll figures saved to {ANA_FIG}")
print(f"Math justifications saved to {math_path}")
