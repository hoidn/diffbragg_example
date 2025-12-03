# Crystal Unit Mismatch Analysis — DIAG-UNIT-001

## Summary

This trace demonstrates that `nanobrag_torch.Crystal` real-space vectors (rot_a/b/c) are stored in meters while being labeled as Ångströms, and scattering vectors are in m⁻¹ while labeled as Å⁻¹. When these are dotted together in `compute_physics_for_position`, the HKL fractional coordinates come out at ~1e-9 (off by 10¹⁰), causing all lookups to fall outside the HKL grid and default to F=0.

## Evidence

- **Scattering vector magnitude:** `1.984e+10` (labeled as Å⁻¹ but clearly m⁻¹ given magnitude ~5.8×10⁹)
- **rot_a magnitude:** `2.738e-09` (labeled as Å but clearly m given magnitude ~3×10⁻⁹)
- **HKL fractional coords (raw):** mean `4.213e-09` (should be O(1) for typical Miller indices)
- **HKL fractional coords (corrected × 1e10):** mean `4.213e+01` (now in reasonable range)

## Specification Reference

Per `docs/spec-db-core.md:14`:

> Crystal: Å and degrees; convert to meters only for geometry-physics dot products.

The current implementation violates this by storing crystal vectors in meters from the start, rather than converting only at dot-product time.

## Artifact Paths

- Trace log: `active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/simulator_trace.log`
- Metrics JSON: `active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/simulator_trace_metrics.json`
- This analysis: `active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T130945Z/crystal_unit_analysis.md`
