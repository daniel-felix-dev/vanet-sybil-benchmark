# Sybil Attack Model and Simulation Setup

## 1. Overview

This document describes the attack model, road network, and simulation parameters used to generate the datasets evaluated in this benchmark. All datasets were produced by a single, deterministic SUMO simulation with seed 42, so every number in the experimental results can be reproduced exactly by following the steps in [docs/setup.md](../setup.md).

---

## 2. Background: Sybil Attacks in VANETs

### 2.1 What is a VANET?

A Vehicular Ad-hoc Network (VANET) is a distributed communication system in which vehicles and roadside infrastructure exchange short broadcast messages, called beacons or Cooperative Awareness Messages (CAMs), at a frequency of 1 Hz. Each beacon encodes the sender's claimed identity, GPS position, speed, acceleration, and heading. The IEEE 802.11p physical layer (also known as DSRC in North America and ITS-G5 in Europe) provides direct vehicle-to-vehicle and vehicle-to-infrastructure communication without relying on a central server.

Higher-level applications -- collision avoidance, emergency vehicle preemption, traffic signal coordination, and platooning -- depend on the accuracy of the information carried in these beacons. Because a vehicle may need to react within 100 milliseconds to a hazard warning received from a neighbor, the system was designed for low latency and infrastructure independence rather than for cryptographic identity verification. This design trade-off leaves VANETs vulnerable to identity-based attacks.

### 2.2 The Sybil Attack

Douceur (2002) formally defined the Sybil attack as an attack in which a single malicious entity presents multiple distinct identities to other participants in a distributed system. The attacker exploits the fact that remote entities cannot easily verify whether two distinct identities correspond to two distinct physical devices or to a single device operating multiple virtual identities.

In the VANET context, a Sybil attacker carries one physical radio transceiver but broadcasts beacon messages under several different vehicle identifiers simultaneously (or in rapid alternation). Each fake identifier is a Sybil node. The attacker controls the content of each Sybil node's beacons and can fabricate position, speed, or identity fields to serve any adversarial objective.

### 2.3 Why Sybil Attacks Are Dangerous

The impact of Sybil attacks in VANETs depends on how applications use beacon data:

**Traffic manipulation.** If Sybil nodes report stopped vehicles on a clear road, navigation applications will reroute legitimate traffic away from that road, creating artificial congestion on alternate routes. A single device with 10 fake identities can fabricate the appearance of a multi-vehicle accident.

**Emergency vehicle spoofing.** Sybil nodes that impersonate emergency vehicles with flashing-light identifiers can receive signal priority at intersections, causing disruption to legitimate traffic management.

**Cooperative collision avoidance corruption.** Autonomous vehicle safety systems that brake in response to sudden deceleration messages from neighboring vehicles can be triggered by Sybil nodes broadcasting false emergency stops.

**Routing protocol manipulation.** Geographic routing protocols in VANETs elect forwarding vehicles based on position. An attacker controlling many Sybil nodes in an area can concentrate forwarding elections on itself, enabling message dropping, eavesdropping, or selectively modifying forwarded content.

---

## 3. Attack Model Used in This Benchmark

### 3.1 Attacker Configuration

The benchmark simulates 5 physical attacker devices operating simultaneously in the same network. Each attacker device controls a variable number of Sybil identities depending on the sybil rate scenario. The total number of identities (legitimate + Sybil) in each scenario is defined such that the Sybil fraction among all active vehicle identities equals the target rate.

Sybil rate is defined as:

```
sybil_rate = N_sybil / N_total
           = N_sybil / (N_legit + N_sybil)
```

where N_legit = 80 (fixed across all scenarios) and N_sybil varies. The 8 tested sybil rates and the corresponding identity counts are:

| Sybil Rate | N_legit | N_sybil | N_total | Sybil fraction in dataset |
|---|---|---|---|---|
| 5% | 80 | 5 | 85 | 5.7% |
| 10% | 80 | 5 | 85 | 5.8% |
| 15% | 80 | 10 | 90 | 11.5% |
| 20% | 80 | 20 | 100 | 21.0% |
| 25% | 80 | 25 | 105 | 25.1% |
| 30% | 80 | 30 | 110 | 28.1% |
| 35% | 80 | 40 | 120 | 34.7% |
| 40% | 80 | 50 | 130 | 39.8% |

Note: the sybil fraction in the dataset differs slightly from the nominal sybil rate because vehicles depart and arrive at different times. The dataset fraction is computed from actual active vehicle counts across all 500 simulation steps.

### 3.2 Sybil Node Behavior

Each Sybil identity exhibits two behaviors that are common in documented Sybil attacks:

**Behavior 1: Position co-location.**

All Sybil identities controlled by the same physical attacker report the same physical position at each time step:

```
position_sybil_i(t) = position_master(t)   for all i in attacker's identity set
```

where `position_master(t)` is the actual position of the attacker's physical device at step t. This co-location behavior models the fundamental physical constraint that a single radio transceiver cannot occupy multiple physical locations simultaneously.

**Behavior 2: Speed injection.**

Each Sybil identity's reported speed is the attacker's true speed plus a sample from a zero-mean Gaussian distribution:

```
speed_sybil(t) = speed_true(t) + epsilon(t),   epsilon ~ N(0, sigma^2)
```

with sigma = 8 m/s. Since the legitimate speed range is approximately [0, 13.89] m/s (0 to 50 km/h), adding noise with sigma = 8 m/s frequently produces values below 0 or above 14 m/s, which are physically implausible for a standard vehicle. This behavior models the beacon forgery that a Sybil attacker would perform to disrupt speed-based safety applications.

### 3.3 Why These Two Behaviors

The co-location property is a structural consequence of physics: a single device physically cannot be in two places at once. Any Sybil detection algorithm based on position consistency can in principle exploit this. The speed injection property models the attacker's incentive to inject false data: an attacker that simply replicated legitimate vehicle behavior would have no effect on the network and no reason to deploy a Sybil attack. The sigma = 8 m/s value was selected to produce clearly detectable anomalies while remaining within a realistic range of sensor error magnitudes.

---

## 4. Road Network

### 4.1 Topology

The road network is a 6-by-6 regular grid generated by SUMO's `netgenerate` tool:

```bash
netgenerate --grid --grid.number 6 --grid.length 200 \
  -o simulation/network.net.xml
```

Key parameters:

| Parameter | Value |
|---|---|
| Grid size | 6 x 6 intersections |
| Cell edge length | 200 meters |
| Total area | 1200 x 1200 meters |
| Number of directed edges | 120 |
| Default speed limit | 13.89 m/s (50 km/h) |
| Number of RSUs placed | 20 (on a 4x5 interior grid) |

The 6x6 grid was chosen because it provides uniform coverage across the simulation area, ensures every vehicle has multiple valid route choices, and avoids the boundary effects that occur in single-road (highway) topologies. The 200-meter cell spacing matches the effective communication range of 802.11p transceivers in urban conditions.

### 4.2 RSU Placement

The 20 Road-Side Units (RSUs) are placed at fixed positions on a 4x5 subgrid within the network:

```
position_RSU(c, r) = (1200 * (c + 0.5) / 4,  1200 * (r + 0.5) / 5)
  for c in {0, 1, 2, 3},  r in {0, 1, 2, 3, 4}
```

This placement ensures coverage across the full simulation area with no more than 300 meters between any road point and its nearest RSU. RSUs do not move and have a fixed detection range of 100 meters.

---

## 5. Simulation Parameters

| Parameter | Value | Source |
|---|---|---|
| Simulator | SUMO 1.12.0 | Eclipse Foundation |
| Interface | TraCI (Python API) | Bundled with SUMO |
| Simulation duration | 500 steps | Each step = 1 second |
| Beacon interval | 1 Hz (every step) | ETSI EN 302 637-2 |
| Communication range | 150 meters | Neighbor detection radius |
| Vehicle depart times | Uniform random in [0, 100] | SUMO route file |
| Random seed | 42 | Fully reproducible |
| Legitimate vehicle speed range | [0, 13.89] m/s | SUMO vType maxSpeed |
| Sybil speed noise | N(0, 8^2) m/s | Added to true speed |
| Number of attackers | 5 | Fixed across all scenarios |

---

## 6. Limitations

**Single topology.** All experiments use the 6x6 urban grid. Highway scenarios (linear topology, higher speeds, fewer intersections) or random topologies (irregular connectivity) may produce different relative rankings among detectors.

**Single seed.** The benchmark uses seed 42 for all scenarios. While the results are fully reproducible, they represent one particular realization of the random processes (vehicle routes, departure times, attacker placement). Multiple seeds would provide confidence intervals for the reported F1 values.

**Simplified mobility model.** SUMO uses the Krauss car-following model by default. Real vehicle behavior is more complex, with variable reaction times, driver hesitation, and platooning effects not captured in the simulation.

**Fixed attack model.** Only the co-location + speed injection attack is modeled. Stealthy attacks (small speed noise), adaptive attacks (alternating between anomalous and normal behavior), and position-only attacks (no speed injection) are not tested. The relative performance of detectors may differ under alternative attack strategies.

---

## 7. References

Douceur, J. R. (2002). The Sybil Attack. *1st International Workshop on Peer-to-Peer Systems (IPTPS)*, Lecture Notes in Computer Science, vol 2429, pp. 251-260. Springer, Berlin.

ETSI EN 302 637-2 V1.4.1 (2019). *Intelligent Transport Systems (ITS); Vehicular Communications; Basic Set of Applications; Part 2: Specification of Cooperative Awareness Basic Service*. European Telecommunications Standards Institute.

Lopez, P. A., Behrisch, M., Bieker-Walz, L., Erdmann, J., Flotterod, Y., Hilbrich, R., Lucken, L., Rummel, J., Wagner, P., and Wiessner, E. (2018). Microscopic Traffic Simulation using SUMO. *21st International Conference on Intelligent Transportation Systems (ITSC 2018)*. IEEE.

Raya, M. and Hubaux, J.-P. (2007). Securing vehicular ad hoc networks. *Journal of Computer Security*, 15(1), 39-68.
