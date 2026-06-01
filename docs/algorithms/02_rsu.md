# RSU Position Verification Detector

**Source:** [karthik-047/Detecting-Sybil-Attacks-in-VANETs](https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs) (Python + SUMO)
**Reimplementation:** `detectors/rsu_detector.py`
**Category:** Positional / infrastructure-based (unsupervised)
**Requires labeled data:** No

---

## 1. Objective

Use a fixed grid of Road-Side Units (RSUs) to detect vehicle pairs whose claimed positions are mutually inconsistent. If two vehicles are both observed near the same RSU at the same time but their reported positions are far apart from each other, one of them is likely lying about its location.

---

## 2. Theoretical Background

RSU-based Sybil detection exploits a fundamental physical constraint: a radio transceiver can only be near one RSU at a time. If two vehicle identities are both detected by the same RSU (meaning both claim to be within the RSU's communication range), but the positions they report are far apart, the two identities cannot both be physically real -- at least one must be a fabricated Sybil identity.

This idea generalizes the position verification concept from Rasmussen and Capkun (2010), who proposed using infrastructure with known positions to verify node location claims. The RSU approach does not require cryptographic infrastructure: it exploits physical proximity detection (radio range) rather than secure ranging.

---

## 3. Algorithm Description

### 3.1 Detection Logic

```
Procedure RSU.fit(D):
    pair_count = empty dict  // maps (v1, v2) -> integer count

    for each time step t:
        // For each RSU r:
        for each RSU r with position (x_r, y_r):
            // Find vehicles within RSU_range of r
            nearby = {v : dist(pos_v(t), pos_r) <= RSU_range}

            // Check all pairs of nearby vehicles
            for each pair (v1, v2) in combinations(nearby, 2):
                x1, y1 = pos_v1(t)
                x2, y2 = pos_v2(t)
                if dist((x1,y1), (x2,y2)) > dist_thresh:
                    key = sorted(v1, v2)  // canonical pair order
                    pair_count[key] += 1

    // Confirm Sybil pairs that triggered frequently enough
    flagged = empty set
    for each (v1, v2), count in pair_count:
        if count >= min_freq:
            flagged.add(v1)
            flagged.add(v2)

    return flagged
```

### 3.2 Parameters

| Parameter | Value | Meaning |
|---|---|---|
| RSU_range | 100 m | Maximum distance for RSU to detect a vehicle |
| dist_thresh | 150 m | Minimum pairwise distance to flag as suspicious |
| min_freq | 5 | Minimum triggering events to confirm Sybil status |
| Number of RSUs | 20 | Fixed grid (4x5) covering the 1200x1200 m network |

---

## 4. Mathematical Formulation

Let P_v(t) = (x_v(t), y_v(t)) be the reported position of vehicle v at step t.
Let R_r = (x_r, y_r) be the fixed position of RSU r.

**Observation set for RSU r at step t:**

```
O(r, t) = {v : ||P_v(t) - R_r|| <= RSU_range}
```

**Suspicious pair detection:**

For each pair (v1, v2) in O(r, t):

```
if ||P_v1(t) - P_v2(t)|| > dist_thresh:
    increment pair_count[(v1, v2)]
```

**Confirmation:**

```
Sybil = {v : exists u such that pair_count[(u,v)] >= min_freq}
```

---

## 5. Why RSU Fails with Co-location Attacks

The RSU algorithm was designed to detect a specific attack variant: a single physical device claiming to be at multiple different positions simultaneously. Under this attack:

- Device D is physically near RSU r (within RSU_range = 100 m)
- Device D broadcasts as identity v1 claiming to be at location L1 (near r)
- Device D also broadcasts as identity v2 claiming to be at location L2 (far from L1)
- ||L1 - L2|| > dist_thresh triggers the detection

In the co-location attack model used in this benchmark:
- All Sybil identities from the same attacker report the *same* position
- ||P_v1(t) - P_v2(t)|| = 0 for any two Sybil identities from the same attacker
- 0 < dist_thresh, so the condition is never triggered

This is a fundamental model incompatibility: the algorithm assumes Sybil identities claim *different* locations; the attack model uses *identical* locations. The algorithm cannot detect co-location attacks regardless of parameter tuning.

**At 20% sybil rate, partial detection occurs (F1 = 0.171).** This results from boundary cases where different attackers' Sybil identities are near the same RSU at some steps, and the random vehicle routes produce occasional pairwise distances above 150 m. This is incidental, not structural detection of co-location.

---

## 6. Complexity Analysis

**Time complexity:**

For each of T = 500 steps:
- For each of R = 20 RSUs: find vehicles within RSU_range -- O(V) distance computations
- For each nearby set of size k: check all O(k^2) pairs

The worst case occurs when all V vehicles are near the same RSU:

```
T_worst = O(T * R * V^2)
```

With T=500, R=20, V~100 (average active vehicles):

```
T_worst = 500 * 20 * 100^2 = 100,000,000 operations
```

100 million operations in pure Python (each operation is a distance computation: 4 multiplications, 2 additions, 1 square root) explains the observed 10.2 second training time.

**Space complexity:**

The pair_count dictionary can store at most O(V^2 / 2) unique pairs:

```
Space = O(V^2) pairs
```

With V = 130 (maximum across all scenarios): O(8,450) dictionary entries.

**Big-O summary:**
- Time: O(T * R * V^2) -- quadratic in vehicles, linear in steps and RSUs
- Space: O(V^2)

**Scalability concern:** For a real VANET with V = 1000 vehicles, T = 3600 steps, R = 20 RSUs:

```
Operations = 3600 * 20 * 1000^2 = 72 billion
```

At 10 million operations per second in Python, this would take approximately 7,200 seconds (2 hours). Vectorized implementation (NumPy broadcasting) could reduce this by 100-1000x, but the quadratic scaling remains a fundamental limitation.

---

## 7. Results (OOS)

| Sybil Rate | F1 | Precision | Recall | Specificity |
|---|---|---|---|---|
| 5% | 0.000 | 0.000 | 0.000 | 1.000 |
| 10% | 0.000 | 0.000 | 0.000 | 1.000 |
| 15% | 0.000 | 0.000 | 0.000 | 1.000 |
| 20% | 0.171 | 0.363 | 0.111 | 0.948 |
| 25% | 0.000 | 0.000 | 0.000 | 0.978 |
| 30% | 0.000 | 0.000 | 0.000 | 1.000 |
| 35% | 0.000 | 0.000 | 0.000 | 1.000 |
| 40% | 0.000 | 0.000 | 0.000 | 1.000 |
| **Mean** | **0.012** | **0.034** | **0.008** | **0.990** |

The F1 = 0.171 at 20% sybil rate is not structural detection -- it results from coincidental vehicle trajectory overlaps and is not reproducible across different random seeds.

---

## 8. Strengths

- High specificity (0.991): rarely produces false positives against legitimate vehicles.
- Works against split-position attacks (the attack variant it was designed for).
- Fully unsupervised, no labeled data required.

---

## 9. Weaknesses

- Fundamentally incompatible with co-location attacks (the predominant attack model).
- O(T * R * V^2) complexity: extremely slow for large networks (pure Python).
- Requires fixed RSU infrastructure.

---

## 10. References

Karthik (2024). *Detecting-Sybil-Attacks-in-VANETs*. GitHub repository. https://github.com/karthik-047/Detecting-Sybil-Attacks-in-VANETs

Rasmussen, K. B. and Capkun, S. (2010). Realization of RF Distance Bounding. *19th USENIX Security Symposium*.

Xiao, B., Yu, B., and Gao, C. (2006). Detection and Localization of Sybil Nodes in VANETs. *Proceedings of the 2006 Workshop on Dependability Issues in Wireless Ad Hoc Networks and Sensor Networks (DIWANS)*. ACM.
