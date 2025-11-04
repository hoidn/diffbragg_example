# MAP-SCALE-001 Blockers (2025-11-04T120500Z)

## Issue: Geometry/Structure Factor Mismatch

**Status**: BLOCKED
**Date**: 2025-11-04
**Loop**: Ralph implementation loop

### Summary
DB_AT_024 selector fails to meet thresholds (corr=0.0352 < 0.2, localization=0%) even with refined structure factors and calibration metadata loaded correctly.

### Root Cause Analysis

1. **Golden dataset generation** (successful):
   - Uses DiffBragg refinement pipeline (`scripts/generate_simple_cubic_golden.py`)
   - Refines geometry, crystal orientation, AND structure factors together
   - Produces refined MTZ with Fopt optimized for the **refined geometry**
   - Achieves excellent metrics: corr=0.81, localization=100% (18 ROIs)

2. **DB_AT_024 test** (blocked):
   - Uses workspace `refGeom.expt` and `refGeom.refl` (original, unrefined geometry)
   - Loads refined MTZ from fixtures (structure factors optimized for **different geometry**)
   - Geometry mismatch causes poor alignment: corr=0.0352, localization=0% (92 ROIs)

### Evidence

**Golden dataset metrics** (`plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/refined_capture/metrics.json`):
```json
{
  "n_panels": 1,
  "median_correlation": 0.8125,
  "localization_success_rate": 1.0,
  "metrics_sample": 18
}
```

**DB_AT_024 test metrics** (`plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/mapping_metrics.json`):
```json
{
  "n_roi": 92,
  "corr_median": 0.0352,
  "localization_success_rate": 0.0,
  "hkl_source": "refined_structure_factors.mtz"
}
```

### Diagnostic Details

- Refined MTZ successfully loaded via `load_refined_mtz()` (column format "F(+),SIGF(+),F(-),SIGF(-)" with type "amplitude")
- Calibration metadata correctly applied (spot_scale_override=3.185e17, sqrt=5.643e8)
- Zero-iteration helper produces Bragg intensities (max=4.84e7, mean=1.32e6)
- Target/Bragg scale mismatch persists despite refined amplitudes

### Required Resolution

**Option 1: Use refined geometry in DB_AT_024 fixture**
- Copy DiffBragg-refined experiment (with refined detector/crystal) to `tests/fixtures/golden_data/simple_cubic/`
- Update DB_AT_024 to load refined geometry instead of workspace `refGeom.expt`
- Ensures consistency between refined structure factors and refined geometry

**Option 2: Generate separate zero-iteration fixture**
- Run zero-iteration simulation with original `refGeom.expt` + `scaled.mtz` (no refinement)
- Capture baseline metrics without DiffBragg optimization
- Accept lower thresholds for zero-iteration mapping (e.g., corr ≥ 0.05 instead of 0.2)

**Option 3: Defer to MAP-SCALE-002**
- Document geometry dependency in SCALE-004 finding
- Treat DB_AT_024 as integration test requiring full DiffBragg pipeline
- Implement MAP-SCALE-002 to automate ingestion of both refined geometry and refined Fopt

### Recommendation

**Pursue Option 1** (use refined geometry):
- Most aligned with MAP-SCALE-001 goal (source refined Fopt from DiffBragg outputs)
- DiffBragg refinement already produces both refined geometry and refined MTZ
- Update fixture paths: `refGeom.expt` → `refined.expt`, `refGeom.refl` → `refined.refl`
- Golden generator can persist these alongside `refined_structure_factors.mtz`

### Files Modified (This Loop)

- `dbex/nanobrag_bridge.py:681-778` — Added `load_refined_mtz()` helper (working correctly)
- `tests/dbex/test_mapping_consistency.py:35,64-120,162-172,220,287-309` — Updated test to load refined MTZ (loads successfully, but geometry mismatch blocks thresholds)
- `scripts/generate_simple_cubic_golden.py:736-757,799-802,867-873` — Persists refined MTZ to fixtures (working correctly)

### Next Actions

1. **Supervisor decision required**: Select Option 1, 2, or 3
2. **If Option 1**: Update `scripts/generate_simple_cubic_golden.py` to also copy refined experiment/reflections to fixtures
3. **If Option 2**: Generate separate zero-iteration baseline and adjust thresholds
4. **If Option 3**: Update `docs/findings.md` SCALE-004 with geometry dependency note and defer to MAP-SCALE-002

### References

- `input.md:31-35` — If Blocked policy (blockers.md + fix_plan Attempts History)
- `docs/findings.md:27` — SCALE-004 (calibration + Fopt requirement)
- `plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/summary.md` — Remediation strategy (assumed geometry match)
- `plans/active/MAP-SCALE-001/reports/2025-11-04T084948Z/summary.md` — Evidence showing refined torch capture matches targets at corr≈0.99
