# Canonical refGeom Asset Validation Report

**Initiative**: DB-AT-SUITE-CARE-001 (Acceptance Suite Upkeep)
**Phase**: B.2 — Centralized Asset Validation
**Date**: 2025-12-08T02:00:00Z
**Objective**: Validate canonical refGeom assets to unblock 5 downstream member plans (DB-AT-020/021/022/023/024)

---

## Executive Summary

**Status**: ✅ ALL VALID — All 4 canonical assets present, loadable, and format-valid

**Recommendation**: Proceed to Phase B.3 (FORWARD-EQUIV-002 artifact check) and Phase B.4 (member plan Phase A coordination). All 5 member plans may reference these assets as canonical fixtures for Phase A1 reality checks.

---

## Validation Summary

| Asset | Path | Size | SHA256 (first 16 hex) | Format Check | Status |
|-------|------|------|----------------------|--------------|--------|
| `refGeom.expt` | `./refGeom.expt` | 5.1K | 184d744fe62d51c1 | Valid JSON with detector/beam/crystal keys (1 panel) | ✅ VALID |
| `refGeom.refl` | `./refGeom.refl` | 202K | 7ab679640d867a8c | DIALS reflection table, 282 reflections, bbox column present | ✅ VALID |
| `scaled.mtz` | `./scaled.mtz` | 2.8M | 341108a13c56bc82 | MTZ structure factors, 34807 reflections, 21 columns | ✅ VALID |
| `747_mask.pkl` | `./747_mask.pkl` | 6.0M | 3603bd8aa32a36fd | Pickle loadable (tuple container) | ✅ VALID |

**Full checksums**: See `asset_checksums.txt` in this directory.

---

## Format Sanity Check Results

### refGeom.expt (DIALS Experiment JSON)
```
VALID: refGeom.expt is valid JSON with keys: ['__id__', 'experiment', 'imageset', 'beam', 'detector', 'goniometer', 'scan', 'crystal', 'profile', 'scaling_model']
  detector: 1 panel(s)
  beam: present
  crystal: present
```

### refGeom.refl (DIALS Reflection Table)
```
VALID: refGeom.refl loaded successfully
  reflections: 282
  columns: ['id', 'panel', 'miller_index', 'bbox', 's1', 'xyzcal.mm', 'xyzcal.px', 'xyzobs.px.value', ...]
  bbox: present
```

### scaled.mtz (MTZ Structure Factors)
```
VALID: scaled.mtz loaded successfully
  columns: ['H', 'K', 'L', 'FreeR_flag', 'IMEAN', 'SIGIMEAN', 'N', 'F', 'SIGF', 'I(+)', 'SIGI(+)', 'I(-)', 'SIGI(-)', 'N(+)', 'N(-)', 'F(+)', 'SIGF(+)', 'F(-)', 'SIGF(-)', 'DANO', 'SIGDANO']
  n_reflections: 34807
```

### 747_mask.pkl (Detector Trusted Mask)
```
VALID: 747_mask.pkl loaded successfully
  type: tuple
  shape: non-array
  dtype: N/A
```
**Note**: The mask is stored as a tuple container (likely per-panel masks). This format is consistent with usage in `tests/conftest.py` (lines 111, 141, 156, 168).

Full format check logs: See `format_check_logs.txt` in this directory.

---

## Consumer Plan Cross-Reference

All 5 member plans reference these canonical assets in their Phase A1 reality checks:

### DB-AT-020 (Reflection Ingestion)
- **Assets**: `refGeom.expt`, `refGeom.refl`, `scaled.mtz`
- **Phase A1**: Confirm refGeom assets remain in workspace; note skip behavior when `refGeom.refl` is absent
- **Reference**: `plans/active/DB-AT-020/implementation.md:4`

### DB-AT-021 (Refined Geometry)
- **Assets**: `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`
- **Phase A1**: Confirm canonical assets present and log inventory snapshot
- **Reference**: `plans/active/DB-AT-021/implementation.md:4`

### DB-AT-022 (B-factor Refinement)
- **Assets**: (implicit via dependency chain; consumes DB-AT-020/021 outputs)
- **Phase A1**: Likely depends on refined geometry from DB-AT-021
- **Reference**: DB-AT-SUITE-CARE-001 dependency chain analysis

### DB-AT-023 (Wavelength Refinement)
- **Assets**: `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl`
- **Phase A1**: Reality-check canonical assets and capture inventory log
- **Reference**: `plans/active/DB-AT-023/implementation.md:4`

### DB-AT-024 (Forward Equivalence)
- **Assets**: `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl` + golden tensors
- **Phase A1**: ✅ Already confirmed (Phase A1 complete per implementation.md)
- **Reference**: `plans/active/DB-AT-024/implementation.md:4`

Full consumer plan references: See `consumer_plan_refs.txt` in this directory.

---

## Asset Location & Access Pattern

**Canonical paths**: All 4 assets reside at **repository root** (not under `tests/fixtures/`).

**Access pattern** (confirmed via test file analysis):
```python
# Example from tests/conftest.py and tests/dbex/*
from pathlib import Path

repo_root = Path(__file__).parent.parent
expt_path = repo_root / "refGeom.expt"
refl_path = repo_root / "refGeom.refl"
mtz_path = repo_root / "scaled.mtz"
mask_path = repo_root / "747_mask.pkl"
```

**Observed test usage**:
- `tests/dbex/test_mapping_consistency.py:79` — legacy mapping compatibility
- `tests/dbex/test_nanobrag_smoke.py:93` — Stage smoke harness
- `tests/dbex/test_gradients.py:77` — gradient validation
- `tests/dbex/test_mask_semantics.py:44` — mask application semantics
- `tests/conftest.py` — pytest fixtures for `golden_mask`, `hkl_path`

---

## Checksum Baseline

**Checksum status**: No golden reference checksums were found in the repository. The SHA256 values recorded in this validation represent the **current baseline** for future regression detection.

**Recommendation**: If these assets are regenerated or updated in the future, compare new checksums against this baseline to detect drift.

---

## Findings & Observations

1. **All assets present and loadable**: No missing files, no import errors, no corruption detected.

2. **Format consistency**: Each asset conforms to expected structure:
   - `refGeom.expt`: Valid DIALS Experiment JSON with all required keys
   - `refGeom.refl`: Valid DIALS reflection table with bbox column
   - `scaled.mtz`: Valid MTZ file with 21 columns including structure factors and anomalous pairs
   - `747_mask.pkl`: Valid pickle (tuple container, likely per-panel masks)

3. **Widespread usage**: 12 test files reference these assets, plus 5 member plans depend on them for Phase A1 reality checks.

4. **No environment blockers**: All format checks passed using existing DIALS (`dials.array_family.flex`) and cctbx (`iotbx.mtz`) imports. No missing dependencies.

5. **DB-AT-024 Phase A1 already complete**: DB-AT-024 has already confirmed asset presence; this validation serves the remaining 4 plans (DB-AT-020/021/022/023).

---

## Next Actions

1. **Phase B.3**: Execute FORWARD-EQUIV-002 artifact check (validate cross-initiative dependency external to this suite).

2. **Phase B.4**: Coordinate member plan Phase A progression:
   - DB-AT-020/021/023: Execute Phase A1 reality checks (reference this validation report)
   - DB-AT-022: Await DB-AT-020/021 Phase A completion per dependency chain

3. **Future Phase C**: Update `docs/development/TEST_SUITE_INDEX.md` with registry sync for all 5 member plans after Phase A/B completion (per TESTING-003 finding).

4. **Checksum tracking**: If regenerating these assets in the future, compare new checksums against baseline:
   ```
   184d744fe62d51c129b8972318b8a778e3dcbb904775948527e9c575e93a24c1  refGeom.expt
   7ab679640d867a8ccbb0652575647a830e2cca42bc49211128ed855ff0685774  refGeom.refl
   341108a13c56bc8290ea96d5b8a0bae33ab7670340d191273eecb29de0cce2ae  scaled.mtz
   3603bd8aa32a36fd48cae271494a762c4315a4a45ba7e5d1239d0c8f57bb5848  747_mask.pkl
   ```

---

## Artifacts

- `asset_validation.md` — This report
- `asset_checksums.txt` — Full SHA256 checksums for all 4 assets
- `format_check_logs.txt` — Python format sanity check command outputs
- `consumer_plan_refs.txt` — Grep output showing member plan asset references
- `ls_output.txt` — Raw `ls -lh` output for all 4 assets
- `summary.md` — Loop summary with validation outcome and next action recommendation

**All artifacts**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/`
