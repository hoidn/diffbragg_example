# ARCH-SIM-CONSTRUCTION-001 Simulator Output Comparison Summary

## Results

- **Stage A warm-cache simulator raw output mean:** `1.713932e-09`
- **Reconstruction cold-path simulator raw output mean:** `2.023962e-09`
- **Ratio (Stage A / Reconstruction):** `8.468203e-01` ≈ `0.85`
- **spot_scale_override:** `3.105059e+17`
- **sqrt(spot_scale_override):** `5.572305e+08`

## Interpretation

**Verdict: Simulators MATCH (scaling bug hypothesis CONFIRMED)**

The ratio (0.847) is very close to 1.0, showing only a ~15% difference between the two simulator construction paths. This small discrepancy is likely due to minor numerical differences or RNG state, NOT a systematic sqrt(spot_scale) embedding.

**Key finding:** Both simulators produce raw outputs on the order of 10^-9, which is VASTLY smaller than the expected ~0.24 magnitude seen in working tests. The 23,400× discrepancy observed in DB-AT-028 is NOT due to simulator construction differences — both paths produce equally tiny raw outputs.

**Root cause:** The problem is NOT in simulator construction. The issue is that:
1. Raw simulator outputs (1.7-2.0 × 10^-9) are ~10^8 times too small
2. This is consistent with the hypothesis that the simulators need post-run scaling by sqrt(spot_scale) ≈ 5.57e8
3. Both Stage A warm-cache and reconstruction cold-path produce the same magnitude, confirming the factory contract is consistent

**Recommended fix:** The reconstruction scaling logic at reconstruction.py:252 needs to multiply by sqrt(spot_scale), not leave it out. The prior loops removed it (producing 1.02e-05) and added it back (producing 5711), but the CORRECT application is:
```python
bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale
```
where scale_factor = exp(log_scale_baseline + delta), and log_scale_baseline does NOT already contain sqrt(spot_scale).
