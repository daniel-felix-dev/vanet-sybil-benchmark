"""
VANET Sybil Detection Benchmark
================================
Runs all 6 detectors against each sybil-rate dataset and produces:
  - results/metrics/benchmark_results.csv
  - figures/benchmark_*.png
"""
import os, sys, time, csv
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE    = os.path.dirname(os.path.abspath(__file__))
DS_DIR  = os.path.join(BASE, "results", "datasets")
MET_DIR = os.path.join(BASE, "results", "metrics")
FIG_DIR = os.path.join(BASE, "figures")
os.makedirs(MET_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

sys.path.insert(0, BASE)
from detectors import ALL_DETECTORS

RATES   = [5, 10, 15, 20, 25, 30, 35, 40]
METRICS = ["accuracy", "precision", "recall", "f1", "specificity"]
COLORS  = ["#2196F3","#4CAF50","#F44336","#FF9800","#9C27B0","#795548"]

STYLE = {"figure.figsize":(10,6),"axes.spines.top":False,
         "axes.spines.right":False,"axes.grid":True,"grid.alpha":0.3,"font.size":11}
plt.rcParams.update(STYLE)


def load_dataset(rate: int) -> pd.DataFrame:
    path = os.path.join(DS_DIR, f"dataset_sybil{rate}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}. Run collect_dataset.py first.")
    return pd.read_csv(path)


def run_benchmark() -> list[dict]:
    results = []

    for rate in RATES:
        print(f"\n{'='*60}")
        print(f"Sybil Rate: {rate}%")
        print(f"{'='*60}")
        df = load_dataset(rate)
        n_legit = (df["is_sybil"] == 0).sum()
        n_sybil = (df["is_sybil"] == 1).sum()
        print(f"  Records: {len(df)} | Legit: {n_legit} | Sybil: {n_sybil} "
              f"| Sybil%: {n_sybil/len(df)*100:.1f}%")

        for DetectorClass in ALL_DETECTORS:
            det = DetectorClass()
            print(f"  [{det.name}] fitting...", end=" ", flush=True)
            t0 = time.time()
            try:
                det.fit(df)
                # RF uses 5-fold CV by vehicle_id (out-of-sample)
                if hasattr(det, "cv_evaluate"):
                    cv = det.cv_evaluate(df, k=5)
                    metrics = {
                        "detector": det.name,
                        **{m: round(cv[m]["mean"], 4) for m in METRICS},
                        "f1_std": round(cv["f1"]["std"], 4),
                    }
                    oos_note = f" [5-fold CV OOS] f1_std={metrics['f1_std']:.3f}"
                else:
                    # LSTM already sets test_metrics_ with vehicle-level split
                    metrics = det.evaluate(df)
                    oos_note = " [80/20 OOS]" if hasattr(det, "test_metrics_") and det.test_metrics_ else ""

                elapsed = round(time.time() - t0, 2)
                metrics["sybil_rate"] = rate
                metrics["fit_time_s"] = elapsed
                results.append(metrics)
                print(f"acc={metrics['accuracy']:.3f} f1={metrics['f1']:.3f} "
                      f"({elapsed}s){oos_note}")
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"ERROR: {e}")
                results.append({
                    "detector": det.name, "sybil_rate": rate,
                    **{m: float("nan") for m in METRICS}, "fit_time_s": -1
                })

    return results


def save_results(results: list[dict]):
    path = os.path.join(MET_DIR, "benchmark_results.csv")
    fieldnames = ["detector", "sybil_rate"] + METRICS + ["f1_std", "fit_time_s"]
    # Ensure every row has all fields (fill missing with empty string)
    clean = [{f: row.get(f, "") for f in fieldnames} for row in results]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean)
    print(f"\nResults saved -> {path}")
    return path


def make_figures(results: list[dict]):
    df = pd.DataFrame(results)
    detectors = df["detector"].unique().tolist()

    # ── Fig 1: F1 vs Sybil Rate per detector ──────────────────────────────────
    fig, ax = plt.subplots()
    for det, color in zip(detectors, COLORS):
        sub = df[df["detector"] == det].sort_values("sybil_rate")
        ax.plot(sub["sybil_rate"], sub["f1"], marker="o", color=color,
                linewidth=2, markersize=7, label=det)
    ax.set_xlabel("Sybil Rate (%)")
    ax.set_ylabel("F1-Score")
    ax.set_title("Sybil Detection Benchmark - F1-Score vs Sybil Rate\n(SUMO 6x6 grid, 80 legit vehicles)")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=9, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "benchmark_f1.png"), dpi=150)
    plt.close()
    print("Saved benchmark_f1.png")

    # ── Fig 2: Accuracy vs Sybil Rate ─────────────────────────────────────────
    fig, ax = plt.subplots()
    for det, color in zip(detectors, COLORS):
        sub = df[df["detector"] == det].sort_values("sybil_rate")
        ax.plot(sub["sybil_rate"], sub["accuracy"], marker="s", color=color,
                linewidth=2, markersize=7, label=det)
    ax.set_xlabel("Sybil Rate (%)")
    ax.set_ylabel("Accuracy")
    ax.set_title("Sybil Detection Benchmark - Accuracy vs Sybil Rate")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=9, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "benchmark_accuracy.png"), dpi=150)
    plt.close()
    print("Saved benchmark_accuracy.png")

    # ── Fig 3: Grouped bar - all metrics at 20% sybil rate ────────────────────
    df20 = df[df["sybil_rate"] == 20].set_index("detector")
    x = np.arange(len(detectors))
    w = 0.15
    fig, ax = plt.subplots(figsize=(14, 6))
    for i, (metric, color) in enumerate(zip(METRICS, COLORS)):
        vals = [df20.loc[d, metric] if d in df20.index else 0 for d in detectors]
        ax.bar(x + i*w, vals, w, label=metric.capitalize(), color=color, alpha=0.85)
    ax.set_xticks(x + w*2)
    ax.set_xticklabels(detectors, rotation=15, ha="right", fontsize=9)
    ax.set_ylabel("Score")
    ax.set_title("All Metrics at 20% Sybil Rate - Detector Comparison")
    ax.set_ylim(0, 1.15)
    ax.legend(framealpha=0.85)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "benchmark_metrics_20pct.png"), dpi=150)
    plt.close()
    print("Saved benchmark_metrics_20pct.png")

    # ── Fig 4: Recall vs Precision scatter ────────────────────────────────────
    fig, ax = plt.subplots()
    for det, color in zip(detectors, COLORS):
        sub = df[df["detector"] == det]
        ax.scatter(sub["precision"], sub["recall"], color=color,
                   s=80, label=det, zorder=3)
        # annotate sybil rate
        for _, row in sub.iterrows():
            ax.annotate(f"{int(row['sybil_rate'])}%",
                        (row["precision"], row["recall"]),
                        fontsize=7, ha="left", va="bottom")
    ax.set_xlabel("Precision")
    ax.set_ylabel("Recall")
    ax.set_title("Precision vs Recall - All Detectors & Sybil Rates")
    ax.set_xlim(-0.05, 1.1); ax.set_ylim(-0.05, 1.1)
    ax.legend(fontsize=8, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "benchmark_precision_recall.png"), dpi=150)
    plt.close()
    print("Saved benchmark_precision_recall.png")


def print_summary(results: list[dict]):
    df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY - Mean metrics across all sybil rates")
    print("="*80)
    summary = df.groupby("detector")[METRICS].mean().round(4)
    print(summary.to_string())


if __name__ == "__main__":
    results = run_benchmark()
    save_results(results)
    make_figures(results)
    print_summary(results)
    print("\nBenchmark complete.")
