"""
run_multi_seed_split.py
=======================
Runs the split-position benchmark across 5 seeds x 8 sybil rates = 40 runs.
Mirrors the replication design of run_multi_seed.py for co-location.

Usage:
    python simulation/run_multi_seed_split.py
    python simulation/run_multi_seed_split.py --quick   # 2 seeds x 4 rates
"""

import os, sys, time, argparse
import subprocess
import numpy as np
import pandas as pd

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_DIR = os.path.join(BASE, "simulation")
DS_DIR  = os.path.join(BASE, "results", "datasets", "split_position_multiseed")
MET_DIR = os.path.join(BASE, "results", "metrics")
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


def generate_split(rate: int, seed: int) -> str:
    """Generate a split-position dataset for this (rate, seed) pair."""
    out_path = os.path.join(DS_DIR, f"dataset_sybil{rate}_seed{seed}.csv")
    if os.path.exists(out_path):
        print(f"    [cached] split_sybil{rate}_seed{seed}.csv")
        return out_path

    # Reuse the existing SUMO configs (already generated for co-location)
    run_cmd([
        PYTHON,
        os.path.join(SIM_DIR, "collect_dataset_split.py"),
        str(rate),
        "--seed", str(seed),
    ])

    # collect_dataset_split saves to the default split_position/ dir;
    # move it to our per-seed directory.
    default_path = os.path.join(
        BASE, "results", "datasets", "split_position",
        f"dataset_sybil{rate}.csv"
    )
    if os.path.exists(default_path):
        import shutil
        shutil.copy2(default_path, out_path)
        print(f"    Generated: split_sybil{rate}_seed{seed}.csv")
    else:
        raise FileNotFoundError(
            f"Expected output not found: {default_path}"
        )
    return out_path


def run_detectors(dataset_path: str, rate: int, seed: int) -> list:
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
            row["sybil_rate"]   = rate
            row["seed"]         = seed
            row["fit_time_s"]   = round(time.time() - t0, 2)
            row["attack_model"] = "split_position"
            rows.append(row)
            print(f"      {det.name}: f1={row['f1']:.3f}")
        except Exception as e:
            print(f"      {det.name}: ERROR {e}")
            rows.append({
                "detector": det.name, "sybil_rate": rate, "seed": seed,
                "attack_model": "split_position",
                **{m: float("nan") for m in METRICS},
                "f1_std": float("nan"), "fit_time_s": -1,
            })
    return rows


def aggregate(all_rows: list) -> pd.DataFrame:
    df = pd.DataFrame(all_rows)
    cols = METRICS + ["fit_time_s"]
    agg_rows = []
    for (det, rate), grp in df.groupby(["detector", "sybil_rate"]):
        row = {"detector": det, "sybil_rate": rate,
               "n_seeds": len(grp), "attack_model": "split_position"}
        for c in cols:
            vals = grp[c].dropna().values
            row[c]          = round(float(np.mean(vals)), 4)
            row[f"{c}_std"] = round(
                float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0, 4
            )
        agg_rows.append(row)
    return pd.DataFrame(agg_rows).sort_values(["detector", "sybil_rate"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    rates = RATES_QUICK if args.quick else RATES_ALL
    seeds = SEEDS_QUICK if args.quick else SEEDS_ALL

    print(f"Split-position multi-seed benchmark:")
    print(f"  Seeds:  {seeds}")
    print(f"  Rates:  {rates}")
    print(f"  Total:  {len(seeds) * len(rates)} runs")
    print()

    all_results = []
    t_total = time.time()

    for seed in seeds:
        for rate in rates:
            print(f"  seed={seed}  rate={rate}%")
            try:
                ds = generate_split(rate, seed)
                rows = run_detectors(ds, rate, seed)
                all_results.extend(rows)
            except Exception as e:
                print(f"  FAILED: {e}")

    # Save raw results
    raw_path = os.path.join(MET_DIR, "multi_seed_split_raw.csv")
    pd.DataFrame(all_results).to_csv(raw_path, index=False)
    print(f"\nRaw results -> {raw_path}")

    # Save aggregated (replaces single-seed benchmark_split_results.csv)
    agg = aggregate(all_results)
    agg_path = os.path.join(MET_DIR, "benchmark_split_results.csv")
    agg.to_csv(agg_path, index=False)
    print(f"Aggregated  -> {agg_path}")

    elapsed = (time.time() - t_total) / 60
    print(f"\nTotal time: {elapsed:.1f} min")
    summary = agg.groupby("detector")[["f1", "f1_std"]].mean().round(4)
    print("\nMean F1 and std (split-position, all rates, 5 seeds):")
    print(summary.sort_values("f1", ascending=False).to_string())
