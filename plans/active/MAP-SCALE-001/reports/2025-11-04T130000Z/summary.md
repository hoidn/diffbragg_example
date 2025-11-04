# MAP-SCALE-001 Summary (2025-11-04T130000Z)

## Problem Statement
Per SCALE-004 (docs/findings.md:27), DiffBragg-refined Fopt require matching refined geometry to achieve parity. Prior loop (2025-11-04T120500Z) identified that mixing refined MTZ with legacy refGeom caused poor metrics (corr≈0.035, localization=0%).

## Implementation
**SPEC quotes**: 
- docs/spec-db-conformance.md:44-46: "DB‑AT‑024 Mapping consistency...median ROI correlation ≥ 0.2 and ≥90% ROIs contain a local intensity maximum within the central half‑box."

**ADR alignment**:
- docs/architecture.md (implied): data ingestion should load refined geometry when available

**Search evidence**:
- scripts/generate_simple_cubic_golden.py:736: Existing refined MTZ persistence block
- tests/dbex/test_mapping_consistency.py:64: canonical_assets fixture (legacy geometry hardcoded)
- dbex/run_diffbragg.py:20-24: DiffBragg writes refined geometry to `_geom_ref.expt/.refl`

**Changes made**:

1. **scripts/generate_simple_cubic_golden.py:736-781** — Extended refined asset persistence:
   - Added `_geom_ref.expt` and `_geom_ref.refl` to copy workflow alongside `_temp.mtz`
   - Saves to `torch/refined.expt` and `torch/refined.refl` in canonical output
   - Copies to fixtures if `--fixtures` flag provided
   - Added comprehensive warning if any refined asset is missing

2. **scripts/generate_simple_cubic_golden.py:802-836** — Updated manifest metadata:
   - Added logic to detect refined geometry presence (`has_refined_geometry`)
   - Updated `structure_factor_source`, `experiment_source`, `reflection_source` fields to cite refined assets when available
   - Added `refined_experiment` and `refined_reflections` entries to manifest checksums

3. **scripts/generate_simple_cubic_golden.py:901-917** — Extended fixture copy validation:
   - Added refined.expt and refined.refl to files_to_copy list with existence checks
   - Maintained MANIFEST-001 guard (no copy if sources missing)

4. **tests/dbex/test_mapping_consistency.py:63-145** — Updated canonical_assets fixture:
   - Added refined geometry path resolution with fallback to legacy
   - Emits warning if refined geometry not found
   - Passes `using_refined_geometry` flag to test for diagnostics
   - DataLoad now consumes refined geometry when available

5. **tests/dbex/test_mapping_consistency.py:236-255** — Enhanced test diagnostics:
   - Added `using_refined_geometry` and `geometry_source` to metrics JSON
   - Added print statements showing which geometry was loaded

## Test Results

**Targeted test** (pytest DB_AT_024):
- Command: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1`
- **FAILED**: corr_median=0.0190 (threshold 0.2), localization=1.09% (threshold 90%)
- Confirmed refined geometry loaded successfully (`using_refined_geometry: True`, `geometry_source: .../refined.expt`)
- Refined MTZ loaded (`hkl_source: refined_structure_factors.mtz`)
- Calibration applied (spot_scale_override=3.185e17, sqrt=5.643e8)

**Golden generator** (canonical capture):
- Successfully persisted refined.expt (5.1K), refined.refl (67K), refined_structure_factors.mtz (955K)
- DiffBragg refinement converged (5 cycles, final sigZ=6.311)
- Parity metrics (DiffBragg vs nanobrag_torch simulators): median_correlation=0.807, localization=100%
- Assets confirmed in fixtures: `ls tests/fixtures/golden_data/simple_cubic/refined*`

## First Divergence
**Issue**: Zero-iteration simulation with refined geometry + refined Fopt + calibration still produces poor correlation (0.019) against background-subtracted target data, despite:
1. Refined geometry being loaded correctly (path confirmed, no fallback warning)
2. Refined structure factors being used (load_refined_mtz succeeded)
3. Calibration metadata applied (spot_scale_override from config_torch.json)

**Hypothesis**:
- Golden capture's 0.807 correlation is **simulator parity** (DiffBragg output vs nanobrag_torch output), NOT target data alignment
- DB_AT_024 compares **simulator output vs real detector data**
- Zero-iteration forward pass (no iterative refinement) may legitimately have poor correlation with real data even when using refined assets
- Alternatively, there may be a subtle bug in how refined geometry is being consumed by DataLoad or simulate_forward_once

**Comparison**:
- Golden capture: 18 ROIs, corr=0.807 (simulator parity, post-refinement)
- DB_AT_024 test: 92 ROIs, corr=0.019 (zero-iteration vs real data)
- Prior attempt with legacy geometry: 92 ROIs, corr=0.035

**Next Actions**:
- Run full pytest suite to check if other tests regressed
- Document this divergence in fix_plan Attempts History
- Recommend follow-up investigation: either (a) test expectation needs adjustment (zero-iteration may not hit thresholds), or (b) there's a loading bug preventing refined geometry from being used correctly by simulator

## Artifacts
- plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/golden_capture.log (DiffBragg refinement, asset persistence)
- plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/pytest_db_at_024.log (test failure log)
- plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/mapping_metrics.json (corr=0.019, diagnostics)
- plans/active/MAP-SCALE-001/reports/2025-11-04T130000Z/refined_capture/manifest.json (refined asset checksums)
- tests/fixtures/golden_data/simple_cubic/{refined.expt,refined.refl,refined_structure_factors.mtz} (persisted assets)

## Metrics
- Refined assets persisted: 3 files (expt=5.1K, refl=67K, mtz=955K)
- Canonical capture: DiffBragg sigZ=6.311, torch max=45855, simulator parity corr=0.807
- DB_AT_024 test: n_roi=92, corr_median=0.0190, localization=1.09%, calibration applied
- Full suite: pending
