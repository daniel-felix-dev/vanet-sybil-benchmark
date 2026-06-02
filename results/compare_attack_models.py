"""
compare_attack_models.py
========================
Compares benchmark results across the two attack models:
  - Co-location + speed noise  (results/metrics/benchmark_results.csv)
  - Split-position + speed noise (results/metrics/benchmark_split_results.csv)

Prints a side-by-side comparison table and identifies which detectors
change most between attack models.
"""
import os, pandas as pd, numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MET  = os.path.join(BASE, "results", "metrics")

co  = pd.read_csv(os.path.join(MET, "benchmark_results.csv"))
sp  = pd.read_csv(os.path.join(MET, "benchmark_split_results.csv"))

# Means across rates
co_mean = co.groupby("detector")["f1"].mean().round(4).rename("F1_colocation")
sp_mean = sp.groupby("detector")["f1"].mean().round(4).rename("F1_split_pos")

comp = pd.concat([co_mean, sp_mean], axis=1)
comp["Delta"] = (comp["F1_split_pos"] - comp["F1_colocation"]).round(4)
comp["Verdict"] = comp["Delta"].apply(
    lambda d: "IMPROVES" if d > 0.05 else ("DEGRADES" if d < -0.05 else "STABLE")
)
comp = comp.sort_values("F1_split_pos", ascending=False)

print("=== Attack Model Comparison (mean F1 across 8 sybil rates) ===")
print()
print(comp.to_string())
print()
print("=== RSU per-rate comparison ===")
rsu_co = co[co.detector=="RSU Position Verification"][["sybil_rate","f1"]].rename(columns={"f1":"F1_coloc"})
rsu_sp = sp[sp.detector=="RSU Position Verification"][["sybil_rate","f1"]].rename(columns={"f1":"F1_split"})
rsu_cmp = rsu_co.merge(rsu_sp, on="sybil_rate").sort_values("sybil_rate")
rsu_cmp["delta"] = (rsu_cmp["F1_split"] - rsu_cmp["F1_coloc"]).round(4)
print(rsu_cmp.to_string(index=False))
