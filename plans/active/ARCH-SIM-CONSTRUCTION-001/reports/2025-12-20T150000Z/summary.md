# ARCH-SIM-CONSTRUCTION-001 — Supervisor Loop 2025-12-20T150000Z

## Focus
- Initiative: ARCH-SIM-CONSTRUCTION-001 (Tier 0)
- Mode: Parity localization against independent reference (DIALS refGeom reflection table)
- Selector signature: DB-AT-028/029 deterministic parity crisis (chi²/pixel≈2.1e5, median ROI CC=-0.053)

## Evidence Reviewed
1. `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T010000Z/stage_a_baseline_probe_baseline.json`
   - Reflection parity block shows 27/29 ROIs matched; StageA vs ref median ratio 0.0612, mapping vs ref identical, target vs ref 1.0196.
   - Extremes: ROI 0 ratio 2.28e-3 (stageA mean 0.0199 ADU/pixel vs ref 8.69), ROI 19 ratio 2.34e2 (stageA 1601.8 vs ref 6.86).
   - Global telemetry still reports `model_mean_masked=87.118 ADU`, so energy is conserved but spatially mislocalized.
2. `pytest_db_at_028_029.log` (same report) — selectors still fail with unchanged chi² and ROI correlation signature despite Exit Criterion #1 (StageA↔mapping parity) being green.

## Conclusions
- Deterministic parity crisis persists at the StageA→target boundary even after mapping parity and cold-path fixes.
- Independent reflection-table comparison confirms the simulator output is not simply missing a scalar factor: most ROIs are under-predicted by 16× while a minority absorb >200× the expected intensity, so the energy budget is misapplied per ROI.
- Root cause scope: shared between StageA warm cache and mapping forward helper (common dependencies: `build_structure_factor_grid`, HKL amplitudes, calibration metadata, nanobrag_torch Simulator).

## Next Hypothesis
Investigate whether the HKL amplitudes loaded from `scaled.mtz` (or refined MTZ) already encode reflection intensities squared while `build_structure_factor_grid`/`nanobrag_torch` assume true amplitudes (|F|). If we are feeding intensity-like magnitudes into an amplitude slot, the simulator will square them again, producing the observed "a few ROIs 200× high / most ≪1" distribution. Need a transformation ledger that maps each matched reflection to:
- DIALS reflection intensity per pixel
- StageA/mapping ROI prediction
- HKL amplitude retrieved for that Miller index
- Derived `amp^2` vs reflection ratio

This will show whether the mismatch is born before the simulator (HKL ingestion) or inside the physics kernel.

## Proposed Action (for Ralph)
- Extend `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` to emit a **Transformation Ledger** per matched reflection: include the Miller index, HKL amplitude from `mapping_context.hkl_amplitudes`, computed `amp^2` per-pixel prediction, and compare all four values (reflection, target, StageA, amp-derived). This will identify whether structure-factor ingestion double-scales intensities before StageA ever runs.
- Re-run the probe in both baseline + perturbed geometry modes plus DB-AT-028/029 to keep deterministic parity evidence current.

Artifacts from this loop: transformation ledger summary + planning notes (this file) stored under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T150000Z/`.
