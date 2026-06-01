"""
run_multi_seed.py
=================
Runs the full multi-seed benchmark: 5 seeds x 8 sybil rates = 40 runs.
GWO is excluded -- single-seed results showed no statistically significant
benefit over RF baseline (Wilcoxon p=0.640, Cohen's d=0.18).

Usage:
    python simulation/run_multi_seed.py             # full run
    python simulation/run_multi_seed.py --quick     # 2 seeds x 4 rates
"""

import os, sys, time, csv, argparse
import subprocess
import numpy as np
import pandas as pd

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_DIR   = os.path.join(BASE, "simulation")
DS_DIR    = os.path.join(BASE, "results", "datasets", "multi_seed")
MET_DIR   = os.path.join(BASE, "results", "metrics")
os.makedirs(DS_DIR,  exist_ok=True)
os.makedirs(MET_DIR, exist_ok=True)

RATES_ALL   = [5, 10, 15, 20, 25, 30, 35, 40]
SEEDS_ALL   = [42, 123, 456, 789, 1000]
RATES_QUICK = [10, 20, 30, 40]
SEEDS_QUICK = [42, 123]
PYTHON      = sys.executable
METRICS     = ["accuracy", "precision", "recall", "f1", "specificity"]


def run_cmd(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or BASE)
    if r.returncode != 0:
        print("STDERR:", r.stderr[-600:])
        raise RuntimeError(f"Command failed: {' '.join(str(c) for c in cmd)}")
    return r.stdout


def generate_and_collect(rate: int, seed: int) -> str:
    out_path = os.path.join(DS_DIR, f"dataset_sybil{rate}_seed{seed}.csv")
    if os.path.exists(out_path):
        print(f"    [cached] dataset_sybil{rate}_seed{seed}.csv")
        return out_path

    # Generate routes with this seed
    run_cmd([PYTHON, os.path.join(SIM_DIR, "generate_routes.py"),
             str(rate), "--seed", str(seed)])

    # Generate SUMO config (rate only, not seed-dependent)
    run_cmd([PYTHON, os.path.join(SIM_DIR, "make_configs.py"), str(rate)])

    # Collect dataset
    run_cmd([PYTHON, os.path.join(SIM_DIR, "collect_dataset.py"),
             str(rate), "--seed", str(seed), "--out", out_path])

    print(f"    Generated: dataset_sybil{rate}_seed{seed}.csv")
    return out_path


def run_detectors(dataset_path: str, rate: int, seed: int) -> list[dict]:
    sys.path.insert(0, BASE)
    import importlib
    import detectors as det_module
    importlib.reload(det_module)
    from detectors import ALL_DETECTORS

    df = pd.read_csv(dataset_path)
    rows = []

    for DetClass in ALL_DETECTORS:
        det = DetClass()
        t0 = time.time()
        try:
            det.fit(df)
            if hasattr(det, "cv_evaluate"):
                cv = det.cv_evaluate(df, k=5)
                row = {"detector": det.name,
                       **{m: round(cv[m]["mean"], 4) for m in METRICS},
                       "f1_std": round(cv["f1"]["std"], 4)}
            else:
                m = det.evaluate(df)
                row = {"detector": m["detector"],
                       **{k: m[k] for k in METRICS},
                       "f1_std": 0.0}
            row["sybil_rate"] = rate
            row["seed"]       = seed
            row["fit_time_s"] = round(time.time() - t0, 2)
            rows.append(row)
            print(f"      {det.name}: f1={row['f1']:.3f} ({row['fit_time_s']}s)")
        except Exception as e:
            print(f"      {det.name}: ERROR {e}")
            rows.append({"detector": det.name, "sybil_rate": rate, "seed": seed,
                         **{m: float("nan") for m in METRICS},
                         "f1_std": float("nan"), "fit_time_s": -1})
    return rows


def aggregate(all_rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(all_rows)
    cols = METRICS + ["fit_time_s"]
    agg_rows = []
    for (det, rate), grp in df.groupby(["detector", "sybil_rate"]):
        row = {"detector": det, "sybil_rate": rate, "n_seeds": len(grp)}
        for c in cols:
            vals = grp[c].dropna().values
            row[c]          = round(float(np.mean(vals)), 4)
            row[f"{c}_std"] = round(float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0, 4)
        agg_rows.append(row)
    return pd.DataFrame(agg_rows).sort_values(["detector", "sybil_rate"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    rates = RATES_QUICK if args.quick else RATES_ALL
    seeds = SEEDS_QUICK if args.quick else SEEDS_ALL

    print(f"Multi-seed benchmark: {len(seeds)} seeds x {len(rates)} rates = {len(seeds)*len(rates)} runs")
    print(f"Detectors: 6 (GWO excluded -- statistically equivalent to RF, Wilcoxon p=0.640)")
    print(f"Seeds: {seeds}")
    print(f"Rates: {rates}")
    print()

    all_results = []
    t_total = time.time()

    for seed in seeds:
        for rate in rates:
            print(f"  seed={seed}  rate={rate}%")
            try:
                ds = generate_and_collect(rate, seed)
                rows = run_detectors(ds, rate, seed)
                all_results.extend(rows)
            except Exception as e:
                print(f"  FAILED: {e}")

    # Save raw results
    raw_path = os.path.join(MET_DIR, "multi_seed_raw.csv")
    pd.DataFrame(all_results).to_csv(raw_path, index=False)
    print(f"\nRaw results -> {raw_path}")

    # Save aggregated (mean +/- std across seeds)
    agg = aggregate(all_results)
    agg_path = os.path.join(MET_DIR, "benchmark_results.csv")
    agg.to_csv(agg_path, index=False)
    print(f"Aggregated  -> {agg_path}")

    # Print summary
    elapsed = (time.time() - t_total) / 60
    print(f"\nTotal time: {elapsed:.1f} min")
    summary = agg.groupby("detector")[["f1","f1_std"]].mean().round(4)
    print("\nMean F1 and std across all rates and seeds:")
    print(summary.sort_values("f1", ascending=False).to_string())
