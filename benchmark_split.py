"""
benchmark_split.py
==================
Runs all 6 detectors against the SPLIT-POSITION attack datasets and saves
results to results/metrics/benchmark_split_results.csv.

Run AFTER: python simulation/collect_dataset_split.py
"""
import os, sys, time, csv
import pandas as pd
import numpy as np

BASE    = os.path.dirname(os.path.abspath(__file__))
DS_DIR  = os.path.join(BASE, "results", "datasets", "split_position")
MET_DIR = os.path.join(BASE, "results", "metrics")
os.makedirs(MET_DIR, exist_ok=True)

sys.path.insert(0, BASE)
from detectors import ALL_DETECTORS

RATES   = [5, 10, 15, 20, 25, 30, 35, 40]
METRICS = ["accuracy", "precision", "recall", "f1", "specificity"]


def load(rate):
    path = os.path.join(DS_DIR, f"dataset_sybil{rate}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Run collect_dataset_split.py first: {path}")
    return pd.read_csv(path)


def run():
    results = []
    for rate in RATES:
        print(f"\n{'='*50}")
        print(f"[SPLIT-POSITION] Sybil Rate: {rate}%")
        df = load(rate)
        n_s = df["is_sybil"].sum()
        print(f"  Records: {len(df)} | Sybil: {n_s} ({n_s/len(df)*100:.1f}%)")

        for DetClass in ALL_DETECTORS:
            det = DetClass()
            t0 = time.time()
            try:
                det.fit(df)
                if hasattr(det, "cv_evaluate"):
                    cv = det.cv_evaluate(df, k=5)
                    m = {"detector": det.name,
                         **{k: round(cv[k]["mean"], 4) for k in METRICS},
                         "f1_std": round(cv["f1"]["std"], 4)}
                else:
                    m = det.evaluate(df)
                    m["f1_std"] = 0.0
                m["sybil_rate"] = rate
                m["fit_time_s"] = round(time.time() - t0, 2)
                m["attack_model"] = "split_position"
                results.append(m)
                print(f"  {det.name}: f1={m['f1']:.3f} ({m['fit_time_s']}s)")
            except Exception as e:
                import traceback; traceback.print_exc()
                results.append({"detector": det.name, "sybil_rate": rate,
                                 "attack_model": "split_position",
                                 **{k: float("nan") for k in METRICS},
                                 "f1_std": float("nan"), "fit_time_s": -1})

    out = os.path.join(MET_DIR, "benchmark_split_results.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\nResults -> {out}")

    # Print summary
    df_r = pd.DataFrame(results)
    print("\n=== SPLIT-POSITION SUMMARY ===")
    s = df_r.groupby("detector")[["f1","precision","recall","specificity"]].mean().round(4)
    print(s.sort_values("f1", ascending=False).to_string())
    return results


if __name__ == "__main__":
    run()
