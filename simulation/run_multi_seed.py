"""
run_multi_seed.py
=================
Orchestrates the full multi-seed benchmark:
  1. For each (sybil_rate, seed) pair: generates routes, collects dataset
  2. Runs all detectors on each dataset
  3. Aggregates results: mean +/- std across seeds per (detector, sybil_rate)
  4. Saves aggregated CSV and figures

Usage:
    python simulation/run_multi_seed.py             # all rates and seeds
    python simulation/run_multi_seed.py --quick     # 2 seeds, 4 rates (testing)
"""

import os, sys, time, csv, argparse
import subprocess
import numpy as np
import pandas as pd

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_DIR   = os.path.join(BASE, "simulation")
DS_DIR    = os.path.join(BASE, "results", "datasets")
MET_DIR   = os.path.join(BASE, "results", "metrics")
os.makedirs(DS_DIR, exist_ok=True)
os.makedirs(MET_DIR, exist_ok=True)

RATES_ALL  = [5, 10, 15, 20, 25, 30, 35, 40]
SEEDS_ALL  = [42, 123, 456, 789, 1000]
RATES_QUICK = [10, 20, 30, 40]
SEEDS_QUICK = [42, 123]

PYTHON = sys.executable


def run(cmd, cwd=None):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or BASE)
    if result.returncode != 0:
        print("STDERR:", result.stderr[-600:])
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout


def generate_and_collect(rate: int, seed: int) -> str:
    """Generate routes with given seed, collect dataset. Returns dataset path."""
    out_path = os.path.join(DS_DIR, f"dataset_sybil{rate}_seed{seed}.csv")
    if os.path.exists(out_path):
        print(f"    [skip] dataset_sybil{rate}_seed{seed}.csv already exists")
        return out_path

    # 1. generate routes
    run([PYTHON, os.path.join(SIM_DIR, "generate_routes.py"),
         str(rate), "--seed", str(seed)])

    # 2. generate SUMO config
    run([PYTHON, os.path.join(SIM_DIR, "make_configs.py"), str(rate)])

    # 3. collect dataset
    run([PYTHON, os.path.join(SIM_DIR, "collect_dataset.py"),
         str(rate), "--seed", str(seed),
         "--out", out_path])

    return out_path


def run_detectors_on(dataset_path: str, rate: int, seed: int) -> list[dict]:
    """Run all detectors on one dataset, return list of metric dicts."""
    sys.path.insert(0, BASE)
    import importlib
    import detectors as det_module
    importlib.reload(det_module)
    from detectors import ALL_DETECTORS

    df = pd.read_csv(dataset_path)
    results = []
    METRICS = ["accuracy", "precision", "recall", "f1", "specificity"]

    for DetClass in ALL_DETECTORS:
        det = DetClass()
        t0 = time.time()
        try:
            det.fit(df)
            if hasattr(det, "cv_evaluate"):
                cv = det.cv_evaluate(df, k=5)
                row = {"detector": det.name,
                       **{m: cv[m]["mean"] for m in METRICS}}
            else:
                row = det.evaluate(df)
            row["sybil_rate"] = rate
            row["seed"]       = seed
            row["fit_time_s"] = round(time.time() - t0, 2)
            results.append(row)
            print(f"      {det.name}: f1={row['f1']:.3f} ({row['fit_time_s']}s)")
        except Exception as e:
            print(f"      {det.name}: ERROR {e}")
            results.append({
                "detector": det.name, "sybil_rate": rate, "seed": seed,
                **{m: float("nan") for m in METRICS}, "fit_time_s": -1
            })
    return results


def aggregate(all_rows: list[dict]) -> pd.DataFrame:
    """Average metrics across seeds for each (detector, sybil_rate)."""
    df = pd.DataFrame(all_rows)
    METRICS = ["accuracy", "precision", "recall", "f1", "specificity", "fit_time_s"]

    agg_rows = []
    for (det, rate), grp in df.groupby(["detector", "sybil_rate"]):
        row = {"detector": det, "sybil_rate": rate}
        for m in METRICS:
            vals = grp[m].dropna().values
            row[m]              = round(float(np.mean(vals)), 4)
            row[f"{m}_std"]     = round(float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0, 4)
        agg_rows.append(row)
    return pd.DataFrame(agg_rows).sort_values(["detector","sybil_rate"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true",
                        help="Run 2 seeds x 4 rates for quick testing")
    args = parser.parse_args()

    rates = RATES_QUICK if args.quick else RATES_ALL
    seeds = SEEDS_QUICK if args.quick else SEEDS_ALL

    print(f"Multi-seed benchmark: {len(rates)} rates x {len(seeds)} seeds "
          f"= {len(rates)*len(seeds)} runs")
    print(f"Rates: {rates}")
    print(f"Seeds: {seeds}")

    all_results = []
    t_total = time.time()

    for rate in rates:
        for seed in seeds:
            print(f"\n  rate={rate}%  seed={seed}")
            try:
                ds_path = generate_and_collect(rate, seed)
                rows    = run_detectors_on(ds_path, rate, seed)
                all_results.extend(rows)
            except Exception as e:
                print(f"  FAILED: {e}")

    # Save raw
    raw_path = os.path.join(MET_DIR, "benchmark_multi_seed_raw.csv")
    pd.DataFrame(all_results).to_csv(raw_path, index=False)
    print(f"\nRaw results -> {raw_path}")

    # Save aggregated
    agg = aggregate(all_results)
    agg_path = os.path.join(MET_DIR, "benchmark_multi_seed_agg.csv")
    agg.to_csv(agg_path, index=False)
    print(f"Aggregated  -> {agg_path}")

    # Print summary
    print(f"\nTotal time: {(time.time()-t_total)/60:.1f} min")
    summary = agg.groupby("detector")[["f1","f1_std"]].mean().round(4)
    print("\nMean F1 across all rates and seeds:")
    print(summary.sort_values("f1", ascending=False).to_string())
