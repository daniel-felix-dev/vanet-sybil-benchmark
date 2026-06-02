# Attack Models

The benchmark tests two Sybil attack models. All other simulation parameters are fixed (same network, same vehicles, same seeds).

---

## Co-location + Speed Noise (primary)

**Files:** `results/datasets/dataset_sybil{N}.csv`

Each attacker controls multiple fake identities that all report **the same physical position** (the attacker's true location). Each Sybil beacon adds Gaussian noise N(0, 8²) to the reported speed, producing values outside the legitimate range [0, 13.89] m/s.

This is the most common Sybil attack model in the literature. Detectors designed for speed-anomaly detection (TASER, IQR, RF, k-Means) perform well. RSU position verification fails because all Sybil IDs report identical positions (inter-pair distance ≈ 0 m < 150 m threshold).

---

## Split-Position + Speed Noise

**Files:** `results/datasets/split_position/dataset_sybil{N}.csv`

Each attacker's Sybil identities report **different positions**, all within 80 m of the same RSU. Identities 0 and 1 are placed at opposite ends (distance = 160 m > 150 m threshold), guaranteeing RSU detection. Speed injection is identical to the co-location model.

This is the attack model RSU was designed for. RSU F1 rises from 0.012 to 0.835. TASER remains perfect (F1 = 1.000) and RF improves (F1 = 0.995) because distinct positions add discriminative features.

### Geometry

```
RSU center (rx, ry)
  Identity 0 → (rx + 80, ry)         distance to RSU: 80m ✓
  Identity 1 → (rx - 80, ry)         distance to RSU: 80m ✓
  Mutual distance: 160m > 150m → RSU flags the pair ✓
```

---

## Comparison

| Detector | Co-location F1 | Split-position F1 | Delta |
|---|---|---|---|
| TASER | 0.9997 | 1.0000 | +0.000 |
| Random Forest | 0.8945 | 0.9948 | **+0.100** |
| RSU | 0.0123 | 0.8350 | **+0.823** |
| k-Means | 0.9795 | 0.9226 | −0.057 |
| LSTM | 0.4487 | 0.4662 | +0.018 |
| IQR | 0.4007 | 0.3808 | −0.020 |

**Key finding:** Detection guarantees depend critically on the alignment between the algorithm's assumptions and the attack model. TASER is the only detector robust to both models (F1 ≥ 0.999 in both). RSU and RF gain substantially in split-position because distinct reported positions provide richer features for detection.
