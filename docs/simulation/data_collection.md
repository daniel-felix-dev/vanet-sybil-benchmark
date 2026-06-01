# Data Collection via TraCI

## 1. Overview

This document describes how vehicle features are extracted from the SUMO simulation and organized into the datasets consumed by the benchmark. The extraction is performed by `simulation/collect_dataset.py`, which uses the TraCI Python API to query SUMO at each simulation step and records a row for every active vehicle.

---

## 2. TraCI Architecture

TraCI (Traffic Control Interface) is a client-server API bundled with SUMO. When a Python script calls `traci.start()`, it launches a SUMO process and establishes a socket connection. The script then drives the simulation step by step:

```
Python script                    SUMO process
-----------                      --------
traci.start(cmd)     ----------> starts SUMO, connects via TCP port
traci.simulationStep() -------> advances simulation by 1 step
traci.vehicle.getIDList() ----> returns list of active vehicle IDs
traci.vehicle.getPosition(v) -> returns (x, y) for vehicle v
...
traci.close()        ----------> terminates SUMO process
```

This architecture allows the Python script to read simulation state at each step, post-process it, and optionally modify vehicle behavior (not used in this benchmark, which only reads state).

---

## 3. Feature Extraction Logic

At each of the 500 simulation steps, the collector:

1. Calls `traci.simulationStep()` to advance time by 1 second.
2. Calls `traci.vehicle.getIDList()` to get all currently active vehicle IDs.
3. For each active vehicle v:
   a. Reads true SUMO state (position, speed, angle, edge) via TraCI.
   b. For Sybil vehicles: replaces position with the attacker's master position, adds Gaussian noise to speed.
   c. Computes derived features (n_neighbors, RSU distances).
   d. Writes one row to the dataset.

### 3.1 Feature Definitions

| Feature | Type | Units | Description |
|---|---|---|---|
| `step` | integer | -- | Simulation step, range [0, 499] |
| `vehicle_id` | string | -- | SUMO identifier: `legit_N` or `sybil_N` |
| `x` | float | meters | Reported x-position (Sybil: attacker master position) |
| `y` | float | meters | Reported y-position (Sybil: attacker master position) |
| `speed` | float | m/s | Reported speed (Sybil: true + N(0, 8^2)) |
| `accel` | float | m/s^2 | Delta speed: speed(t) - speed(t-1) |
| `angle` | float | degrees | Heading (0 = North, 90 = East) |
| `edge_id` | string | -- | Current road segment identifier |
| `n_neighbors` | integer | -- | Vehicles within 150 m of this vehicle |
| `min_rsu_dist` | float | meters | Distance to nearest of 20 RSUs |
| `mean_rsu_dist` | float | meters | Mean distance to all 20 RSUs |
| `is_sybil` | integer | -- | Ground truth: 0 = legitimate, 1 = Sybil |
| `attacker_id` | integer | -- | Attacker device index for Sybil (-1 for legitimate) |

### 3.2 Sybil Feature Modification

The collector modifies two features for Sybil vehicles:

**Position (x, y):** All Sybil identities belonging to attacker k report the position of the first Sybil identity from attacker k at that step. This represents co-location: the attacker's single physical device occupies one location.

**Speed:** The reported speed is computed as:

```
speed_reported = max(0.0, speed_true + epsilon),   epsilon ~ N(0, 64)
```

The `max(0.0, ...)` clamp prevents negative speeds, which would be detected as obviously invalid by any detector. Speeds above 13.89 m/s (the vType maximum) are allowed and represent the primary detection signal.

**Acceleration:** Computed from reported speed:

```
accel(t) = speed_reported(t) - speed_reported(t-1)
```

Because speed_reported includes noise, accel also contains noise. The noise amplification in accel (difference of two noisy quantities) provides an additional detection signal.

### 3.3 Neighbor Count Computation

For each vehicle v at step t, the neighbor count is:

```
n_neighbors(v, t) = |{u : u != v, dist(pos_v, pos_u) <= 150}|
```

where positions used are the reported positions (post-modification for Sybil). Co-located Sybil identities inflate each other's neighbor counts because they all appear at the same location.

### 3.4 RSU Distance Computation

The 20 RSUs are placed at fixed positions computed as:

```
RSU(c, r) = (1200 * (c + 0.5) / 4,   1200 * (r + 0.5) / 5)
  for c in {0,1,2,3},  r in {0,1,2,3,4}
```

For each vehicle v:

```
min_rsu_dist(v, t) = min over all RSUs r of: sqrt((x_v - x_r)^2 + (y_v - y_r)^2)
mean_rsu_dist(v, t) = mean over all RSUs r of: sqrt((x_v - x_r)^2 + (y_v - y_r)^2)
```

---

## 4. Dataset Statistics

The following table shows the record counts for each sybil rate scenario:

| Sybil Rate | Total records | Legit records | Sybil records | Sybil fraction |
|---|---|---|---|---|
| 5% | 7,754 | 7,311 | 443 | 5.71% |
| 10% | 7,747 | 7,296 | 451 | 5.82% |
| 15% | 8,195 | 7,249 | 946 | 11.54% |
| 20% | 9,153 | 7,231 | 1,922 | 21.00% |
| 25% | 9,690 | 7,254 | 2,436 | 25.14% |
| 30% | 10,086 | 7,249 | 2,837 | 28.13% |
| 35% | 11,088 | 7,237 | 3,851 | 34.73% |
| 40% | 12,000 | 7,227 | 4,773 | 39.78% |

The legitimate record count is approximately constant (~7,250) across scenarios because the 80 legitimate vehicles travel fixed routes with fixed departure times (controlled by seed 42). The variation in Sybil records reflects the different numbers of Sybil identities per scenario.

---

## 5. Reproducing the Datasets

The pre-generated datasets are committed to the repository in `results/datasets/`. To regenerate them from scratch:

```bash
python simulation/generate_routes.py   # creates route files
python simulation/make_configs.py      # creates sumocfg files
python simulation/collect_dataset.py   # runs SUMO, saves CSVs
```

To generate a single rate:

```bash
python simulation/collect_dataset.py 20   # only sybil20
```

To generate with a different seed (produces different vehicle routes and therefore different datasets):

```bash
python simulation/collect_dataset.py 20 --seed 123
```

The `--seed` parameter controls the Sybil speed noise random generator. The vehicle routes are controlled by the `--seed` parameter to `generate_routes.py`. Both must use the same seed to produce a consistent dataset for a given scenario.

---

## 6. Feature Importance Notes

The following features have the strongest discriminative power in this dataset, based on the attack model:

**`speed`:** The primary signal. Sybil nodes inject noise with sigma = 8 m/s, producing values frequently outside [0, 13.89] m/s. TASER and IQR rely exclusively on this feature.

**`accel`:** The secondary signal. Because speed is noisy and accel = speed(t) - speed(t-1), the acceleration of a Sybil node has variance 2 * sigma^2 = 128 (m/s^2)^2, compared to approximately 5-10 (m/s^2)^2 for a legitimate vehicle. Random Forest's feature importance analysis consistently ranks accel among the top 3 features.

**`n_neighbors`:** A positional signal. Co-located Sybil identities (all at the master's position) appear as neighbors of each other, inflating n_neighbors above what would be physically expected given their reported position in the network. This feature helps Random Forest distinguish Sybil clusters.

**`min_rsu_dist`:** A spatial context feature. Sybil identities cluster at the attacker's physical position, which may have a distinctive RSU distance profile compared to the spread of legitimate vehicles across the network. This feature has moderate discriminative power.

**`edge_id`:** A categorical feature encoding which road segment a vehicle occupies. After label encoding, it provides topological context that helps the tree-based models distinguish vehicles in isolated areas (more likely to be Sybil clusters) from vehicles in high-traffic corridors.

---

## 7. References

SUMO Documentation. (2023). *TraCI -- Traffic Control Interface*. Eclipse Foundation. Available at: https://sumo.dlr.de/docs/TraCI.html

Lopez et al. (2018). Microscopic Traffic Simulation using SUMO. *21st ITSC*. IEEE.

ETSI EN 302 637-2 V1.4.1 (2019). *ITS Vehicular Communications -- Cooperative Awareness Basic Service*. ETSI.
