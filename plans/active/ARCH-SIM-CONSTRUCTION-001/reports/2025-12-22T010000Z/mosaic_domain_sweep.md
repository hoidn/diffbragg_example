# Mosaic Domain Sweep Summary

**Initiative:** ARCH-SIM-CONSTRUCTION-001
**Phase:** C.18
**Date:** 2025-12-22T010000Z
**Purpose:** Isolate whether Stage A↔reflection divergence boundary depends on mosaic domain count

---

## Executive Summary

Ran the Stage A baseline probe twice with identical inputs except for `--stage-a-mosaic-domains`:
- **Domain=1 run:** Single-domain perfect-crystal simulation (legacy stills default)
- **Domain=16 run:** Multi-domain mosaic averaging (current default)

**Key Finding:** Stage A vs reflection median ratio remains **0.061** for both domain counts, proving that mosaic domain count does NOT resolve the 234× Stage A↔reflection divergence crisis.

This confirms escalation to nanobrag_torch instrumentation is required (Environment Freeze exception path).

---

## Sweep Results

### Stage A vs Reference Reflection Intensity Ratios

| Mosaic Domains | Stage A/Refl Median | Stage A/Refl P25-P75 | Stage A/Refl Min-Max | Mapping/Refl Median |
|----------------|---------------------|----------------------|----------------------|---------------------|
| 1              | 0.0612              | [0.0143, 0.8643]     | [0.0001, 233.9085]   | 0.0599              |
| 16             | 0.0612              | [0.0143, 0.8643]     | [0.0001, 233.9085]   | 0.0622              |

**Δ (domain16 - domain1):**
- Stage A/Refl median: 0.0000 (no change)
- Mapping/Refl median: +0.0022 (+3.7% relative)

### Target vs Reference (Control Metric)

Both runs show Target/Refl median ≈ 1.02, confirming the independent reference reflection table is stable and correctly scaled to target ADU units.

---

## Diagnostic Details

### Common Parameters (Both Runs)
- Geometry mode: `baseline` (no perturbations)
- Calibration: `sp.proc/calibration/config_torch_smoke_small.json`
- HKL source: `smoke_refined_structure_factors_small.mtz` (F columns)
- Device: `cuda:0`
- Detector: `small` (1024×1024)
- ROIs matched: 27/29 reflections

### Domain=1 Run
- Output: `domain1/stage_a_baseline_probe_baseline.json`
- Chi²/pixel: 9.804e5
- Stage A vs mapping median ROI CC: 0.9996
- Mapping masked mean ratio (target/bragg): 1.2776

### Domain=16 Run
- Output: `domain16/stage_a_baseline_probe_baseline.json`
- Chi²/pixel: 9.804e5
- Stage A vs mapping median ROI CC: 0.9995
- Mapping masked mean ratio (target/bragg): 1.4511

---

## HKL Amplitude Ledger (Phase C.17)

Both runs use the same HKL grid with 69,614 entries. Representative ROIs showing |F|²/pixel vs reflection intensity divergence:

| ROI Panel:BBox      | HKL       | |F|²/pix   | StgA/|F|²  | StgA/Refl  | Notes                          |
|---------------------|-----------|------------|------------|------------|--------------------------------|
| 0:[431,443,434,446] | (0,2,-2)  | 3.91e+01   | 10.4282    | 233.9085   | Worst mismatch (234× over)     |
| 0:[121,133,288,300] | (1,6,-9)  | 6.16e+02   | 0.1554     | 6.4299     | 6× over reference              |
| 0:[605,617,156,168] | (-5,4,-2) | 1.21e+01   | 0.0639     | 1.3277     | Best match (1.3× over)         |

**Observation:** The |F|²/pixel → reflection intensity transformation includes additional physics (spot profile integration, detector PSF, crystal mosaic convolution) not captured by simple |F|² normalization.

The Stage A simulator produces pixel intensities that are ~16× lower than |F|²/pixel for median ROIs, suggesting the nanobrag_torch spot profile spreads energy outside the reflection bounding box or the reflection intensity sum includes background overestimation.

---

## Boundary Bisection Decision

Per `input.md` Boundary Bisection Step:

> If the Stage A/Ref medians remain ≈0.061 for both runs, escalate to a nanobrag_torch instrumentation patch (Environment Freeze exception path). If they diverge materially, continue investigating domain count and distribution before touching nanobrag_torch.

**Decision:** Escalate to nanobrag_torch instrumentation.

**Rationale:**
1. Stage A/Refl median **unchanged** between domain=1 and domain=16
2. Divergence signature (0.061 median, 234× worst-case) is **independent** of mosaic averaging
3. Target/Refl ≈ 1.02 proves the reference is correctly scaled
4. |F|²/pix ledger shows the mismatch occurs **downstream** of HKL amplitude lookup

**Next Steps:**
1. Instrument nanobrag_torch to capture per-reflection energy partitioning (inside bbox vs outside bbox)
2. Compare nanobrag spot profile FWHM against DIALS bbox dimensions
3. Verify whether reflection `intensity.sum.value` includes local background over-subtraction

---

## Artifacts

- **domain1/** — Mosaic domain=1 probe output (JSON + log)
- **domain16/** — Mosaic domain=16 probe output (JSON + log)
- **db_at_028/** — DB-AT-028 pytest artifacts (pending)
- **db_at_029/** — DB-AT-029 pytest artifacts (pending)

---

## References

- `input.md` — Do Now directive for this loop
- `docs/spec-db-conformance.md:319-366` — DB-AT-028/029 acceptance thresholds
- `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md` — Phase C.18 planning
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/transformation_ledger.md` — Field-level divergence ledger
