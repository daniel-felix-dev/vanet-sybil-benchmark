"""
TraCI-based dataset collector for the VANET Sybil benchmark.

For each simulation scenario (sybil rate 10/20/30/40%) runs SUMO headless
and records per-step features for every vehicle:
  - step, vehicle_id, x, y, speed, accel, angle, edge_id
  - n_neighbors (vehicles within 150m)
  - min_rsu_dist (distance to nearest RSU)
  - is_sybil (ground truth label)
  - attacker_id (which physical attacker, -1 for legit)

Output: results/datasets/dataset_sybil{rate}.csv
"""

import os, sys, math, csv, time
import traci

SUMO_BIN  = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo.exe"
SIM_DIR   = os.path.dirname(__file__)
OUT_DIR   = os.path.join(SIM_DIR, "..", "results", "datasets")
os.makedirs(OUT_DIR, exist_ok=True)

COMM_RANGE  = 150.0   # metres, neighbour detection range
N_RSU       = 20
GRID_SIZE   = 1200.0  # 6 cells × 200 m
SYBIL_SPEED_NOISE = 8.0   # m/s std dev of random speed noise injected for Sybil nodes

# Place RSUs on a 4×5 grid inside the network
RSU_POSITIONS = [
    (GRID_SIZE * (c + 0.5) / 4, GRID_SIZE * (r + 0.5) / 5)
    for r in range(5) for c in range(4)
]

RATES = [5, 10, 15, 20, 25, 30, 35, 40]

FIELDNAMES = [
    "step", "vehicle_id",
    "x", "y", "speed", "accel", "angle",
    "edge_id",
    "n_neighbors",
    "min_rsu_dist", "mean_rsu_dist",
    "is_sybil", "attacker_id",
]


def dist(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)


def rsu_distances(x, y):
    dists = [dist(x, y, rx, ry) for rx, ry in RSU_POSITIONS]
    return min(dists), sum(dists)/len(dists)


def run_scenario(rate, seed=42, out_path=None):
    import random
    rng = random.Random(seed + rate)

    cfg = os.path.join(SIM_DIR, f"scenario_sybil{rate}.sumocfg")
    out = out_path or os.path.join(OUT_DIR, f"dataset_sybil{rate}.csv")

    cmd = [SUMO_BIN, "-c", cfg, "--no-step-log", "--no-warnings"]
    traci.start(cmd)

    rows = []
    prev_speed  = {}   # for acceleration calculation
    # Map sybil_N -> attacker index (N_IDENTITIES per attacker)
    n_ids_per_atk = max(1, int(rate // 10))

    for step in range(500):
        traci.simulationStep()
        veh_ids = traci.vehicle.getIDList()

        # Collect REAL positions from SUMO
        real_pos = {}
        for vid in veh_ids:
            x, y = traci.vehicle.getPosition(vid)
            real_pos[vid] = (x, y)

        # --- Sybil realism: all sybil IDs from same attacker share a position ---
        # Find one representative legit vehicle's position per attacker group,
        # or use the first sybil in the group as the "master" position.
        attacker_master_pos = {}   # attacker_id -> (x, y)
        for vid in veh_ids:
            if vid.startswith("sybil_"):
                atk_id = int(vid.split("_")[1]) // n_ids_per_atk
                if atk_id not in attacker_master_pos:
                    attacker_master_pos[atk_id] = real_pos[vid]

        # Build reported positions (sybil nodes report master's position)
        reported_pos = {}
        for vid in veh_ids:
            if vid.startswith("sybil_"):
                atk_id = int(vid.split("_")[1]) // n_ids_per_atk
                reported_pos[vid] = attacker_master_pos.get(atk_id, real_pos[vid])
            else:
                reported_pos[vid] = real_pos[vid]

        for vid in veh_ids:
            x, y  = reported_pos[vid]
            speed = traci.vehicle.getSpeed(vid)
            angle = traci.vehicle.getAngle(vid)
            edge  = traci.vehicle.getRoadID(vid)

            is_sybil = 1 if vid.startswith("sybil_") else 0

            # Sybil nodes inject anomalous speed (outside normal 0-14 m/s range)
            if is_sybil:
                noise = rng.gauss(0, SYBIL_SPEED_NOISE)
                speed = max(0.0, speed + noise)   # can be 0 or >> maxSpeed
                attacker = int(vid.split("_")[1]) // n_ids_per_atk
            else:
                attacker = -1

            accel = speed - prev_speed.get(vid, speed)

            # Neighbours within COMM_RANGE (using reported positions)
            n_nb = sum(
                1 for oid, (ox, oy) in reported_pos.items()
                if oid != vid and dist(x, y, ox, oy) <= COMM_RANGE
            )

            min_rsu, mean_rsu = rsu_distances(x, y)

            rows.append({
                "step": step,
                "vehicle_id": vid,
                "x": round(x, 2),
                "y": round(y, 2),
                "speed": round(speed, 4),
                "accel": round(accel, 4),
                "angle": round(angle, 2),
                "edge_id": edge,
                "n_neighbors": n_nb,
                "min_rsu_dist": round(min_rsu, 2),
                "mean_rsu_dist": round(mean_rsu, 2),
                "is_sybil": is_sybil,
                "attacker_id": attacker,
            })
            prev_speed[vid] = speed

        if step % 100 == 0:
            print(f"  step {step}/500 | {len(veh_ids)} vehicles active")

    traci.close()

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    n_sybil = sum(1 for r in rows if r["is_sybil"])
    n_legit = len(rows) - n_sybil
    print(f"  Saved {len(rows)} records ({n_legit} legit, {n_sybil} sybil) -> {out}")
    return out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("rates", nargs="*", type=int)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out",  type=str, default=None,
                        help="Output path override (single rate only)")
    args = parser.parse_args()
    rates = args.rates if args.rates else RATES
    t0 = time.time()
    for rate in rates:
        print(f"\n{'='*50}")
        print(f"Running scenario sybil{rate}% seed={args.seed}...")
        run_scenario(rate, seed=args.seed, out_path=args.out if len(rates)==1 else None)
    print(f"\nAll done in {time.time()-t0:.1f}s")
