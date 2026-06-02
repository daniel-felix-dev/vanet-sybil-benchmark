"""
collect_dataset_split.py
========================
Variant of collect_dataset.py that implements the SPLIT-POSITION attack model.

In this model, each attacker's Sybil identities report DIFFERENT positions,
all within 80m of the same nearest RSU but separated from each other by
~160m (> RSU detection threshold of 150m). This is the attack model that
RSU Position Verification was designed to detect.

Speed injection (sigma=8 m/s) is kept the same as the co-location model
so that all detectors face the same telemetry anomalies.

Output: results/datasets/split_position/dataset_sybil{rate}.csv
        (does NOT overwrite the co-location datasets)
"""

import os, sys, math, csv, time
import traci

SUMO_BIN  = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo.exe"
SIM_DIR   = os.path.dirname(__file__)
OUT_DIR   = os.path.join(SIM_DIR, "..", "results", "datasets", "split_position")
os.makedirs(OUT_DIR, exist_ok=True)

COMM_RANGE        = 150.0
GRID_SIZE         = 1200.0
SYBIL_SPEED_NOISE = 8.0
# Radius around each RSU for distributing Sybil positions.
# 80m ensures all IDs are within RSU detection range (100m),
# and IDs placed opposite each other are 160m apart > 150m threshold.
SPLIT_RADIUS      = 80.0

RSU_POSITIONS = [
    (GRID_SIZE * (c + 0.5) / 4, GRID_SIZE * (r + 0.5) / 5)
    for r in range(5) for c in range(4)
]

RATES = [5, 10, 15, 20, 25, 30, 35, 40]

FIELDNAMES = [
    "step", "vehicle_id", "x", "y", "speed", "accel", "angle",
    "edge_id", "n_neighbors", "min_rsu_dist", "mean_rsu_dist",
    "is_sybil", "attacker_id",
]


def dist(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)


def nearest_rsu(x, y):
    return min(RSU_POSITIONS, key=lambda r: dist(x, y, r[0], r[1]))


def rsu_distances(x, y):
    dists = [dist(x, y, rx, ry) for rx, ry in RSU_POSITIONS]
    return min(dists), sum(dists)/len(dists)


def split_position(master_x, master_y, identity_idx, n_ids):
    """
    Return (x, y) for a Sybil identity in split-position mode.
    All identities are placed around the nearest RSU at SPLIT_RADIUS distance.

    Critical guarantee: IDs 0 and 1 are always placed at opposite sides
    (angles 0 and pi), ensuring their mutual distance is 2*SPLIT_RADIUS = 160m
    which exceeds the RSU detection threshold of 150m, regardless of n_ids.
    Additional IDs fill intermediate angles.
    """
    rx, ry = nearest_rsu(master_x, master_y)
    # Always place first two IDs opposite each other to guarantee detection
    if identity_idx == 0:
        angle = 0.0
    elif identity_idx == 1:
        angle = math.pi
    else:
        # Remaining IDs fill other angles
        angle = math.pi / 2 + (math.pi / 2) * (identity_idx - 2) / max(n_ids - 2, 1)
    return (
        rx + SPLIT_RADIUS * math.cos(angle),
        ry + SPLIT_RADIUS * math.sin(angle),
    )


def run_scenario(rate, seed=42, out_path=None):
    import random
    rng = random.Random(seed + rate)

    cfg = os.path.join(SIM_DIR, f"scenario_sybil{rate}.sumocfg")
    out = out_path or os.path.join(OUT_DIR, f"dataset_sybil{rate}.csv")

    cmd = [SUMO_BIN, "-c", cfg, "--no-step-log", "--no-warnings"]
    traci.start(cmd)

    rows = []
    prev_speed  = {}
    # In split-position mode, need >= 2 IDs per attacker for RSU to detect pairs.
    # At low rates this reorganizes the same total sybil count into fewer attackers.
    n_ids_per_atk = max(2, int(rate // 10))

    # Pre-collect identity index per sybil vehicle
    # sybil_K -> identity index within its attacker group
    sybil_identity_idx = {}  # vid -> local index within attacker group

    for step in range(500):
        traci.simulationStep()
        veh_ids = traci.vehicle.getIDList()

        # Real SUMO positions
        real_pos = {}
        for vid in veh_ids:
            x, y = traci.vehicle.getPosition(vid)
            real_pos[vid] = (x, y)

        # Assign identity indices and find master per attacker
        attacker_master_pos = {}
        attacker_counts = {}
        for vid in veh_ids:
            if vid.startswith("sybil_"):
                sybil_num = int(vid.split("_")[1])
                atk_id = sybil_num // n_ids_per_atk
                local_idx = sybil_num % n_ids_per_atk
                sybil_identity_idx[vid] = (atk_id, local_idx)
                if atk_id not in attacker_master_pos:
                    attacker_master_pos[atk_id] = real_pos[vid]
                attacker_counts[atk_id] = attacker_counts.get(atk_id, 0) + 1

        # Build SPLIT-POSITION reported positions
        reported_pos = {}
        for vid in veh_ids:
            if vid.startswith("sybil_") and vid in sybil_identity_idx:
                atk_id, local_idx = sybil_identity_idx[vid]
                master_x, master_y = attacker_master_pos[atk_id]
                n_ids = attacker_counts.get(atk_id, n_ids_per_atk)
                sx, sy = split_position(master_x, master_y, local_idx, n_ids)
                reported_pos[vid] = (sx, sy)
            else:
                reported_pos[vid] = real_pos[vid]

        for vid in veh_ids:
            x, y  = reported_pos[vid]
            speed = traci.vehicle.getSpeed(vid)
            angle = traci.vehicle.getAngle(vid)
            edge  = traci.vehicle.getRoadID(vid)
            is_sybil = 1 if vid.startswith("sybil_") else 0

            if is_sybil:
                noise = rng.gauss(0, SYBIL_SPEED_NOISE)
                speed = max(0.0, speed + noise)
                atk_id, _ = sybil_identity_idx.get(vid, (0, 0))
                attacker = atk_id
            else:
                attacker = -1

            accel = speed - prev_speed.get(vid, speed)

            n_nb = sum(
                1 for oid, (ox, oy) in reported_pos.items()
                if oid != vid and dist(x, y, ox, oy) <= COMM_RANGE
            )
            min_rsu, mean_rsu = rsu_distances(x, y)

            rows.append({
                "step": step, "vehicle_id": vid,
                "x": round(x, 2), "y": round(y, 2),
                "speed": round(speed, 4), "accel": round(accel, 4),
                "angle": round(angle, 2), "edge_id": edge,
                "n_neighbors": n_nb,
                "min_rsu_dist": round(min_rsu, 2),
                "mean_rsu_dist": round(mean_rsu, 2),
                "is_sybil": is_sybil, "attacker_id": attacker,
            })
            prev_speed[vid] = speed

        if step % 100 == 0:
            print(f"  step {step}/500 | {len(veh_ids)} vehicles active")

    traci.close()

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    n_s = sum(1 for r in rows if r["is_sybil"])
    n_l = len(rows) - n_s
    print(f"  Saved {len(rows)} records ({n_l} legit, {n_s} sybil) -> {out}")
    return out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("rates", nargs="*", type=int)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rates = args.rates if args.rates else RATES
    t0 = time.time()
    for rate in rates:
        print(f"\n{'='*50}")
        print(f"Running SPLIT-POSITION scenario sybil{rate}% seed={args.seed}...")
        run_scenario(rate, seed=args.seed)
    print(f"\nAll done in {time.time()-t0:.1f}s")
