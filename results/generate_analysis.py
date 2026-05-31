"""
generate_analysis.py
Generates all figures for analysis/ and computes mathematical
justifications for the scenario recommendation guide.

Outputs:
  analysis/figures/  -- 8 PNG charts
  analysis/math_justifications.txt  -- computed statistics
"""

import os, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 13,
})

# ---- Mathematical computations -----------------------------------------------

summary = df.groupby("detector")[METRICS + ["fit_time_s"]].agg(["mean","std","min","max"])
summary.columns = ["_".join(c) for c in summary.columns]

f1_std   = df.groupby("detector")["f1"].std().rename("f1_std")
fit_mean = df.groupby("detector")["fit_time_s"].mean()
f1_mean  = df.groupby("detector")["f1"].mean()
efficiency = (f1_mean / np.log1p(fit_mean)).rename("efficiency")

scenarios = {
    "Latency-critical (real-time)": {
        "f1_mean": 0.4, "precision_mean": 0.3, "neg_log_fit": 0.3,
    },
    "Zero false-positives (safety)": {
        "precision_mean": 0.7, "f1_mean": 0.3,
    },
    "High Sybil rate (>=30%)": {
        "f1_at_30": 0.4, "f1_at_40": 0.4, "precision_mean": 0.2,
    },
    "No labels available (unsupervised)": {
        "recall_mean": 0.5, "specificity_mean": 0.5,
    },
    "Resource-constrained (embedded)": {
        "f1_mean": 0.3, "neg_log_fit": 0.7,
    },
    "Low Sybil rate (<=10%)": {
        "f1_at_10": 0.6, "precision_at_10": 0.4,
    },
}

det_stats = {}
for det in DETECTORS:
    sub = df[df["detector"] == det].set_index("sybil_rate")
    row = {
        "f1_mean":          sub["f1"].mean(),
        "precision_mean":   sub["precision"].mean(),
        "recall_mean":      sub["recall"].mean(),
        "specificity_mean": sub["specificity"].mean(),
        "f1_std":           sub["f1"].std(),
        "fit_time_mean":    sub["fit_time_s"].mean(),
        "neg_log_fit":      -math.log1p(sub["fit_time_s"].mean()),
        "efficiency":       sub["f1"].mean() / math.log1p(sub["fit_time_s"].mean()),
    }
    for r in RATES:
        if r in sub.index:
            row[f"f1_at_{r}"]        = sub.loc[r, "f1"]
            row[f"precision_at_{r}"] = sub.loc[r, "precision"]
            row[f"recall_at_{r}"]    = sub.loc[r, "recall"]
        else:
            row[f"f1_at_{r}"] = row[f"precision_at_{r}"] = row[f"recall_at_{r}"] = 0.0
    det_stats[det] = row

def is_pareto(det, all_dets):
    me = all_dets[det]
    for oname, other in all_dets.items():
        if oname == det:
            continue
        if (other["f1_mean"] >= me["f1_mean"] and
                other["fit_time_mean"] <= me["fit_time_mean"] and
                (other["f1_mean"] > me["f1_mean"] or
                 other["fit_time_mean"] < me["fit_time_mean"])):
            return False
    return True

pareto = {d: is_pareto(d, det_stats) for d in DETECTORS}

dom_matrix = pd.DataFrame(0, index=DETECTORS, columns=DETECTORS)
for a in DETECTORS:
    for b in DETECTORS:
        if a == b:
            continue
        fa = df[df["detector"] == a].sort_values("sybil_rate")["f1"].values
        fb = df[df["detector"] == b].sort_values("sybil_rate")["f1"].values
        if all(fa >= fb):
            dom_matrix.loc[a, b] = 1

scenario_scores = {}
for sc_name, weights in scenarios.items():
    scores = {}
    for det in DETECTORS:
        row = det_stats[det]
        s, tw = 0.0, 0.0
        for k, w in weights.items():
            s += w * row.get(k, 0.0)
            tw += abs(w)
        scores[det] = s / tw if tw > 0 else 0.0
    scenario_scores[sc_name] = scores

# ---- Write math justifications -----------------------------------------------

out = []
out.append("=" * 78)
out.append("MATHEMATICAL JUSTIFICATIONS FOR SCENARIO RECOMMENDATIONS")
out.append("=" * 78)

out.append("\n-- 1. Summary statistics --")
for det in DETECTORS:
    r = det_stats[det]
    out.append(
        f"  {det:<30} F1_mean={r['f1_mean']:.4f}  F1_std={r['f1_std']:.4f}"
        f"  Prec={r['precision_mean']:.4f}  Rec={r['recall_mean']:.4f}"
        f"  time={r['fit_time_mean']:.2f}s  eff={r['efficiency']:.4f}"
    )

out.append("\n-- 2. Pareto frontier (F1 vs speed) --")
for det in DETECTORS:
    out.append(f"  {'YES' if pareto[det] else 'NO '} {det}")

out.append("\n-- 3. Dominance matrix (1 = row dominates column at ALL sybil rates) --")
out.append("  " + dom_matrix.to_string().replace("\n", "\n  "))

out.append("\n-- 4. Utility scores per scenario --")
for sc_name, scores in scenario_scores.items():
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    out.append(f"\n  Scenario: {sc_name}")
    for det, s in ranked:
        out.append(f"    {det:<30} utility={s:.4f}")

out.append("\n-- 5. F1 per sybil rate --")
pivot = df.pivot_table(index="detector", columns="sybil_rate", values="f1")
out.append("  " + pivot.to_string().replace("\n", "\n  "))

out.append("\n-- 6. Efficiency = F1_mean / ln(fit_time + 1) --")
for det, val in efficiency.sort_values(ascending=False).items():
    ft = det_stats[det]["fit_time_mean"]
    f1 = det_stats[det]["f1_mean"]
    out.append(f"  {det:<30} = {f1:.4f} / ln({ft:.2f}+1) = {val:.4f}")

math_path = os.path.join(ANA_DIR, "math_justifications.txt")
with open(math_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"Math justifications -> {math_path}")

# ---- Figures -----------------------------------------------------------------

# Fig 1: F1 Heatmap
fig, ax = plt.subplots(figsize=(12, 7))
pivot_f1 = df.pivot_table(index="detector", columns="sybil_rate", values="f1").loc[DETECTORS]
cmap = LinearSegmentedColormap.from_list("rg", ["#F44336","#FFF176","#4CAF50"])
im = ax.imshow(pivot_f1.values, cmap=cmap, aspect="auto", vmin=0, vmax=1)
ax.set_xticks(range(len(RATES)))
ax.set_xticklabels([f"{r}%" for r in RATES], fontsize=13)
ax.set_yticks(range(len(DETECTORS)))
ax.set_yticklabels(DETECTORS, fontsize=12)
ax.set_xlabel("Sybil Rate", fontsize=13)
ax.set_title("F1-Score per Detector and Sybil Rate\n(green = high, red = low)",
             fontsize=14, pad=12)
plt.colorbar(im, ax=ax, label="F1-Score")
for i in range(len(DETECTORS)):
    for j in range(len(RATES)):
        val = pivot_f1.values[i, j]
        ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                fontsize=11, color="black" if val > 0.35 else "white", fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "heatmap_f1.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved heatmap_f1.png")

# Fig 2: Radar charts
mean_metrics = df.groupby("detector")[METRICS].mean()
angles = np.linspace(0, 2*np.pi, len(METRICS), endpoint=False).tolist()
angles += angles[:1]

fig, axes = plt.subplots(2, 4, figsize=(22, 11), subplot_kw=dict(polar=True))
axes = axes.flatten()
for idx, det in enumerate(DETECTORS):
    ax = axes[idx]
    vals = mean_metrics.loc[det, METRICS].tolist() + [mean_metrics.loc[det, METRICS[0]]]
    ax.plot(angles, vals, color=COLORS[det], linewidth=2.5)
    ax.fill(angles, vals, color=COLORS[det], alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(["Accuracy","Precision","Recall","F1","Specificity"], fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25","0.50","0.75","1.0"], fontsize=7)
    title = det if len(det) <= 15 else det.replace(" ", "\n", 1)
    ax.set_title(title, fontsize=11, pad=14, color=COLORS[det], fontweight="bold")
axes[-1].set_visible(False)
fig.suptitle("Detection Quality Profile (mean over all sybil rates)",
             fontsize=15, fontweight="bold", y=1.01)
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "radar_per_detector.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved radar_per_detector.png")

# Fig 3: Cost vs F1 scatter
fig, ax = plt.subplots(figsize=(13, 8))
for det in DETECTORS:
    r = det_stats[det]
    star = " (*)" if pareto[det] else ""
    ax.errorbar(r["fit_time_mean"], r["f1_mean"], yerr=r["f1_std"],
                fmt="o", color=COLORS[det], markersize=13, capsize=5,
                linewidth=2, label=f"{det}{star}")
    ax.annotate(f"{det}{star}", (r["fit_time_mean"], r["f1_mean"]),
                textcoords="offset points", xytext=(10, 5),
                fontsize=10, color=COLORS[det])
ax.set_xscale("log")
ax.set_xlabel("Mean training time (seconds, log scale)", fontsize=13)
ax.set_ylabel("Mean F1-Score  (error bar = std across sybil rates)", fontsize=13)
ax.set_title("Speed vs Quality Tradeoff\n(*) marks detectors on the Pareto frontier",
             fontsize=14)
ax.set_ylim(-0.05, 1.15)
ax.set_xlim(0.03, 250)
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "cost_vs_f1.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved cost_vs_f1.png")

# Fig 4: Precision-Recall space per sybil rate
fig, axes = plt.subplots(1, 4, figsize=(22, 6), sharey=True)
for ax, rate in zip(axes, RATES):
    sub = df[df["sybil_rate"] == rate]
    for det in DETECTORS:
        row = sub[sub["detector"] == det].iloc[0]
        ax.scatter(row["recall"], row["precision"], color=COLORS[det], s=130, zorder=3)
        ax.annotate(det.split()[0], (row["recall"], row["precision"]),
                    textcoords="offset points", xytext=(5, 4), fontsize=9,
                    color=COLORS[det], fontweight="bold")
    ax.set_xlim(-0.05, 1.1); ax.set_ylim(-0.05, 1.1)
    ax.set_xlabel("Recall", fontsize=12)
    ax.set_title(f"Sybil Rate = {rate}%", fontsize=13, fontweight="bold")
    ax.plot([0,1],[0,1],"k--", alpha=0.2, linewidth=1)
axes[0].set_ylabel("Precision", fontsize=12)
fig.suptitle("Precision vs Recall at Each Sybil Rate",
             fontsize=15, fontweight="bold")
handles = [mpatches.Patch(color=COLORS[d], label=d) for d in DETECTORS]
fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=10,
           bbox_to_anchor=(0.5, -0.12), framealpha=0.9)
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "precision_recall_space.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("Saved precision_recall_space.png")

# Fig 5: F1 variance boxplot
fig, ax = plt.subplots(figsize=(14, 7))
f1_by_det = [df[df["detector"] == d]["f1"].values for d in DETECTORS]
bp = ax.boxplot(f1_by_det, patch_artist=True, widths=0.55,
                medianprops=dict(color="white", linewidth=2.5))
for patch, det in zip(bp["boxes"], DETECTORS):
    patch.set_facecolor(COLORS[det])
    patch.set_alpha(0.82)
ax.set_xticks(range(1, len(DETECTORS)+1))
ax.set_xticklabels(DETECTORS, rotation=18, ha="right", fontsize=11)
ax.set_ylabel("F1-Score", fontsize=13)
ax.set_title("F1-Score Spread across All Sybil Rates\nNarrow box = consistent performance regardless of attack intensity",
             fontsize=13)
ax.set_ylim(-0.05, 1.15)
for i, det in enumerate(DETECTORS):
    m = det_stats[det]["f1_mean"]
    ax.text(i+1, 1.09, f"avg={m:.3f}", ha="center", fontsize=9, color=COLORS[det],
            fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "f1_variance.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved f1_variance.png")

# Fig 6: Speed distribution legit vs sybil
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
for ax, rate in zip(axes, [10, 40]):
    ds_path = os.path.join(DS_DIR, f"dataset_sybil{rate}.csv")
    if not os.path.exists(ds_path):
        continue
    ds = pd.read_csv(ds_path)
    legit = ds[ds["is_sybil"] == 0]["speed"]
    sybil = ds[ds["is_sybil"] == 1]["speed"]
    bins  = np.linspace(-5, 45, 70)
    ax.hist(legit, bins=bins, density=True, alpha=0.65, color="#2196F3",
            label=f"Legitimate (n={len(legit):,})")
    ax.hist(sybil, bins=bins, density=True, alpha=0.65, color="#F44336",
            label=f"Sybil (n={len(sybil):,})")
    q1, q3 = legit.quantile(0.25), legit.quantile(0.75)
    fence = q1 - 1.5*(q3-q1)
    ax.axvline(fence, color="black", linestyle="--", linewidth=2,
               label=f"IQR lower fence = {fence:.1f} m/s")
    ax.set_xlabel("Speed (m/s)", fontsize=13)
    ax.set_ylabel("Density", fontsize=13)
    ax.set_title(f"Speed Distribution at {rate}% Sybil Rate", fontsize=13)
    ax.legend(fontsize=10)
fig.suptitle("How IQR and TASER Detect Sybil Nodes via Speed Anomalies",
             fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "speed_distribution.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved speed_distribution.png")

# Fig 7: TP/FP/FN breakdown
fig, axes = plt.subplots(1, 4, figsize=(22, 6), sharey=False)
for ax, rate in zip(axes, RATES):
    sub_rate = df[df["sybil_rate"] == rate]
    ds_path  = os.path.join(DS_DIR, f"dataset_sybil{rate}.csv")
    if os.path.exists(ds_path):
        ds = pd.read_csv(ds_path)
        n_pos, n_neg = int(ds["is_sybil"].sum()), len(ds) - int(ds["is_sybil"].sum())
    else:
        n_pos, n_neg = 1, 1

    tps, fps, fns, labels = [], [], [], []
    for det in DETECTORS:
        row  = sub_rate[sub_rate["detector"] == det].iloc[0]
        tp   = row["recall"] * n_pos
        fp   = (tp / row["precision"] - tp) if row["precision"] > 0 else 0
        fn   = n_pos - tp
        tps.append(tp / n_pos)
        fps.append(fp / max(n_neg, 1))
        fns.append(fn / n_pos)
        labels.append(det.split()[0])

    x = np.arange(len(DETECTORS))
    ax.bar(x, tps, color="#4CAF50", alpha=0.85, label="True Positives")
    ax.bar(x, fns, bottom=tps, color="#FF9800", alpha=0.85, label="False Negatives")
    ax.bar(x, fps, bottom=[t+f for t,f in zip(tps,fns)],
           color="#F44336", alpha=0.7, label="False Positives")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=38, ha="right", fontsize=9)
    ax.set_title(f"{rate}% Sybil", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 2.2)
    if ax == axes[0]:
        ax.set_ylabel("Rate (normalised per class)", fontsize=11)
axes[-1].legend(loc="upper right", fontsize=10)
fig.suptitle("True Positives / False Negatives / False Positives per Detector",
             fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "tp_fp_fn_breakdown.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved tp_fp_fn_breakdown.png")

# Fig 8: Scenario utility ranking
fig, axes = plt.subplots(2, 3, figsize=(21, 12))
axes_flat = axes.flatten()
for ax, (sc_name, scores) in zip(axes_flat, scenario_scores.items()):
    ranked = sorted(scores.items(), key=lambda x: x[1])
    dets   = [d for d,_ in ranked]
    vals   = [v for _,v in ranked]
    colors = [COLORS[d] for d in dets]
    bars   = ax.barh(range(len(dets)), vals, color=colors, alpha=0.85, height=0.6)
    ax.set_yticks(range(len(dets)))
    ax.set_yticklabels(dets, fontsize=10)
    ax.set_xlabel("Utility Score", fontsize=11)
    ax.set_title(sc_name, fontsize=12, fontweight="bold")
    lim = max(abs(min(vals)), max(vals)) * 1.3 if vals else 1
    ax.set_xlim(min(min(vals)*1.3, -0.1), lim)
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    for bar, val in zip(bars, vals):
        xpos = bar.get_width() + lim*0.03 if val >= 0 else bar.get_width() - lim*0.03
        ha = "left" if val >= 0 else "right"
        ax.text(xpos, bar.get_y()+bar.get_height()/2,
                f"{val:.3f}", va="center", fontsize=9, ha=ha)
fig.suptitle("Which Detector Wins in Each Deployment Scenario?\n"
             "(higher utility = better fit for that scenario)",
             fontsize=14, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(ANA_FIG, "scenario_utility_ranking.png"),
            dpi=150, bbox_inches="tight")
plt.close()
print("Saved scenario_utility_ranking.png")

print(f"\nAll figures -> {ANA_FIG}")
print(f"Math justifications -> {math_path}")
