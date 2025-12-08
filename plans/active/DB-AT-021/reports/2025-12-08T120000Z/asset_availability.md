# DB-AT-021 Phase A1: Asset Availability Check

**Initiative**: DB-AT-021 (Mask Semantics Guard)
**Phase**: A1 — Asset Availability Reality Check
**Date**: 2025-12-08T12:00:00Z
**Objective**: Validate canonical refGeom assets + 747_mask.pkl to ground Phase B test authoring

---

## Cross-Reference: DB-AT-SUITE-CARE-001 Phase B.2 Validation

**Source**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md`
**Validation date**: 2025-12-08T02:00:00Z (Loop i=143, 5 loops prior)
**Status**: ✅ ALL VALID

### refGeom Asset Checksums (from B.2 validation)

| Asset | Size | SHA256 (first 16 hex) | Format Check | Status |
|-------|------|----------------------|--------------|--------|
| `refGeom.expt` | 5.1K | 184d744fe62d51c1 | Valid JSON with detector/beam/crystal keys (1 panel) | ✅ VALID |
| `refGeom.refl` | 202K | 7ab679640d867a8c | DIALS reflection table, 282 reflections, bbox column present | ✅ VALID |
| `scaled.mtz` | 2.8M | 341108a13c56bc82 | MTZ structure factors, 34807 reflections, 21 columns | ✅ VALID |
| `747_mask.pkl` | 6.0M | 3603bd8aa32a36fd | Pickle loadable (tuple container) | ✅ VALID |

**Full checksums**:
```
184d744fe62d51c129b8972318b8a778e3dcbb904775948527e9c575e93a24c1  refGeom.expt
7ab679640d867a8ccbb0652575647a830e2cca42bc49211128ed855ff0685774  refGeom.refl
341108a13c56bc8290ea96d5b8a0bae33ab7670340d191273eecb29de0cce2ae  scaled.mtz
3603bd8aa32a36fd48cae271494a762c4315a4a45ba7e5d1239d0c8f57bb5848  747_mask.pkl
```

---

## 747_mask.pkl Validation (This Loop)

**Path**: `./747_mask.pkl` (repository root)
**File check**:
```
-rw-rw-r-- 1 ollie ollie 6.0M Oct 15 12:53 747_mask.pkl
747_mask.pkl: data
```

**Status**: ✅ Present, size matches B.2 validation (6.0M), readable

**Format notes** (from B.2):
- Type: tuple container (likely per-panel masks)
- Consistent with usage in `tests/conftest.py:111,141,156,168`
- Loaded successfully via pickle.load()

---

## Asset Availability Summary

**All 4 canonical assets validated**:
1. ✅ `refGeom.expt` — DIALS experiment (detector geometry, beam, crystal)
2. ✅ `refGeom.refl` — DIALS reflection table (282 reflections)
3. ✅ `scaled.mtz` — MTZ structure factors (34807 reflections)
4. ✅ `747_mask.pkl` — Detector trusted mask (tuple container)

**Location**: Repository root (not under `tests/fixtures/`)

**Access pattern** (for Phase B test scaffold):
```python
from pathlib import Path

repo_root = Path(__file__).parent.parent.parent  # from tests/dbex/
expt_path = repo_root / "refGeom.expt"
refl_path = repo_root / "refGeom.refl"
mtz_path = repo_root / "scaled.mtz"
mask_path = repo_root / "747_mask.pkl"
```

---

## Skip Behavior (Phase B Test Design)

**Pattern**: Mirror DB-AT-020 smoke fixture guard

**Implementation**:
```python
import pytest
from pathlib import Path

@pytest.fixture
def refgeom_assets():
    repo_root = Path(__file__).parent.parent.parent
    expt_path = repo_root / "refGeom.expt"
    refl_path = repo_root / "refGeom.refl"
    mtz_path = repo_root / "scaled.mtz"
    mask_path = repo_root / "747_mask.pkl"

    # Skip if any asset missing
    if not all(p.exists() for p in [expt_path, refl_path, mtz_path, mask_path]):
        pytest.skip("refGeom canonical assets not found (expected at repo root)")

    return {
        "expt": expt_path,
        "refl": refl_path,
        "mtz": mtz_path,
        "mask": mask_path
    }
```

**Rationale**: Tests must be resilient to asset absence (e.g., CI environment, fresh clone without asset regeneration).

---

## Recommendations for Phase B

1. **Fixture reuse**: Check if `refgeom_dataload` fixture exists in `tests/conftest.py` or `tests/dbex/conftest.py`
   - If shared across ≥3 member plans, extract to shared conftest.py
   - Otherwise, define locally in `tests/dbex/test_mask_semantics.py`

2. **Skip guard**: Wrap all test methods with `refgeom_assets` fixture to ensure clean skip behavior

3. **Asset immutability**: Phase B tests must NOT modify canonical assets (read-only access)

4. **Checksum stability**: If tests fail due to asset corruption, compare current checksums against baseline above

---

## Status: ✅ A1 COMPLETE

**Next**: Proceed to Phase A2 (Spec Alignment)
