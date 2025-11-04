# MAP-SCALE-001 Ralph Loop Summary (2025-11-04T120500Z)

## Objective
Implement refined structure factor plumbing so DB_AT_024 can enforce thresholds without xfail.

## Problem Statement (from SPEC)
> **DB-AT-024 Mapping consistency** (docs/spec-db-conformance.md:43-46)
> - Median ROI correlation ≥ 0.2 between torch Bragg output and data-background
> - Localization success rate ≥ 90% (brightest pixel within central half-box)

Prior loops established:
- **SCALE-001** (docs/findings.md:15): Structure factors must remain unscaled before simulation
- **SCALE-002** (docs/findings.md:16): Apply √spot_scale post-simulation only
- **SCALE-003** (docs/findings.md:17): Zero-iteration helper must ingest DiffBragg-refined √spot_scale (~5.6e8) AND refined |F| amplitudes
- **SCALE-004** (docs/findings.md:27): DiffBragg calibration metadata + refined Fopt required together

## Implementation Completed

### 1. MTZ Reader Helper (`dbex/nanobrag_bridge.py:681-778`)
Added `load_refined_mtz()` to read DiffBragg-refined structure factors:
- Handles `F(+),SIGF(+),F(-),SIGF(-)` column format with `type_hints="amplitude"`
- Returns CPU numpy arrays (indices int32 [n_refl, 3], amplitudes float32 [n_refl])
- Per SCALE-001: Returns unscaled amplitudes (no sqrt(spot_scale) multiplication)
- Validation: Shape checks, file existence, graceful errors with available columns listed

### 2. Test Updates (`tests/dbex/test_mapping_consistency.py`)
- Lines 35,39: Imported `load_refined_mtz`
- Lines 64-120: Updated `canonical_assets` fixture to load refined MTZ with fallback to raw scaled.mtz
- Lines 162-172: Test body uses refined HKL if available, else falls back
- Lines 220,287-309: Removed provisional xfail, added refined source tracking, hard asserts for thresholds
- Search: "`refined_hkl`" confirms integration

### 3. Golden Generator Updates (`scripts/generate_simple_cubic_golden.py`)
- Lines 736-757: Persist `_temp.mtz` as `refined_structure_factors.mtz` to torch dir + fixtures
- Lines 799-802: Add refined MTZ to manifest.json with SHA256 checksum
- Lines 867-873: Include refined MTZ in fixture copy validation list
- Search: "`refined_structure_factors`" confirms all references

### 4. Refined MTZ Fixture Generated
Executed golden generator per input.md How-To Map:
```bash
python scripts/generate_simple_cubic_golden.py \
  --canonical-out plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/refined_capture \
  --emit-manifest \
  --fixtures tests/fixtures/golden_data/simple_cubic
```

Output:
- `tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz` (955 KB)
- Manifest checksum: `830199fb10aa448a...`
- Golden dataset metrics: corr=0.81, localization=100% (18 ROIs)

## Test Execution & Blocker

Ran targeted selector:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z \
pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1
```

**Result**: FAILED (geometry mismatch blocker)
- Refined MTZ loaded successfully (`HKL source: refined_structure_factors.mtz`)
- Calibration metadata applied correctly (spot_scale_override=3.185e17)
- **Metrics**: corr_median=0.0352 (< 0.2), localization=0% (< 90%)

### Root Cause
Refined MTZ structure factors are optimized for **DiffBragg-refined geometry**, but test uses workspace `refGeom.expt` (original, unrefined geometry). Golden generator refines geometry+crystal+Fopt together; test must use matching refined geometry for amplitudes to align.

## Artifacts
- `plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/blockers.md` — Detailed root cause analysis, resolution options
- `plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/mapping_metrics.json` — Test metrics (corr=0.0352)
- `plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/refined_capture/metrics.json` — Golden metrics (corr=0.81)
- `plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/golden_capture.log` — Generator execution log
- `plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z/pytest_db_at_024.log` — Test execution log

## Static Analysis
No new files touched requiring linter/formatter runs; bridge helper and test updates follow project conventions.

## Full Test Suite
Deferred (blocker encountered; no point running full suite until geometry mismatch resolved).

## Next Actions (Supervisor Decision Required)
1. **Option 1 (Recommended)**: Update golden generator to persist refined experiment/reflections to fixtures; update DB_AT_024 to load refined geometry
2. **Option 2**: Generate separate zero-iteration baseline with unrefined geometry; accept lower thresholds
3. **Option 3**: Defer to MAP-SCALE-002; document geometry dependency in SCALE-004 finding

## ADR/Spec Alignment
- **SPEC DB-AT-024** (docs/spec-db-conformance.md:43-46): Thresholds attempted but blocked by geometry mismatch
- **SCALE-001** (docs/findings.md:15): Honored (unscaled structure factors)
- **SCALE-002** (docs/findings.md:16): Honored (post-sim sqrt scaling)
- **SCALE-004** (docs/findings.md:27): Extended (geometry dependency discovered)

## Exit Criteria Status
- ✅ Exit criterion #1: Refined MTZ helper implemented and working
- ✅ Exit criterion #2: Test updated to load refined MTZ
- ✅ Exit criterion #3: Golden generator persists refined MTZ to fixtures
- ❌ Exit criterion #4 (implicit): DB_AT_024 passes thresholds — **BLOCKED** by geometry mismatch

## Recommendations for Next Loop
- Address geometry mismatch (blockers.md Option 1)
- Update `docs/findings.md` SCALE-004 with geometry dependency note
- Once resolved, run full test suite and update TEST_SUITE_INDEX.md
