# DB-AT-021 Mask Semantics Guard — Loop Summary

**Timestamp**: 2025-11-04T060900Z
**Owner**: Ralph
**Status**: ✅ Complete (all exit criteria met)
**Spec**: `docs/spec-db-core.md:29-55`, `docs/spec-db-conformance.md:31-34`

---

## Problem Statement

Implement DB-AT-021 acceptance test to validate DIALS trusted mask hydration and loss mask semantics per spec-db-core.md contracts:

> **Spec-db-core.md:29-30** (quoted):
> "DIALS trusted mask SHALL be a tuple of `flex.bool` per panel (True=trusted) shaped `(slow, fast)`."
>
> **Spec-db-core.md:55** (quoted):
> "The loss SHALL be computed only over `(background >= 0) ∧ trusted_mask`."

---

## Acceptance Focus & Module Scope

- **Acceptance focus**: AT-21 (Mask semantics guard)
- **Module scope**: Data models (DataLoad mask hydration, prepare_refinement_inputs loss mask)

---

## SPEC/ADR Alignment

### SPEC Lines Implemented

1. **spec-db-core.md:29-30**: DIALS trusted mask format (tuple of flex.bool per panel, True=trusted, (slow, fast) shape)
2. **spec-db-core.md:55**: Loss mask policy `(background >= 0) & trusted_mask`
3. **spec-db-conformance.md:32-33**: DB-AT-021 acceptance criteria (mask polarity, shape alignment, loss-mask consistency)

### ADR / ARCH Alignment

- **docs/architecture.md** (DataLoad module responsibilities): Hydrate DIALS metadata including masks
- **docs/config_crosswalk.md:86-95**: Mask polarity conventions (DIALS True=trusted vs DiffBragg inverted semantics)

---

## Search Summary

**Search-first evidence** (file:line pointers):

- `dbex/data_load.py:1-97` — Existing DataLoad.__init__ structure (MTZ, Experiment, Reflections, background)
- `dbex/nanobrag_bridge.py:65-149` — Existing prepare_refinement_inputs with mask polarity guard
- `tests/dbex/test_nanobrag_bridge.py:1-100` — Existing test patterns (fixtures, mock detectors)
- `tests/dbex/test_reflection_ingestion.py:58-65` — Canonical args pattern (mtzCol="F,SIGF")

**Partial implementations found**: None (mask loading was not yet implemented in DataLoad)

---

## Implementation

### Code Changes

#### 1. `dbex/data_load.py:99-152` — Mask loading and geometry fixtures

**Changes**:
- Added `import pickle, numpy as np`
- Load DIALS trusted mask from `args.maskFile` (optional, fallback to all-True mask if absent)
- Convert flex.bool tuple → numpy array [panel, slow, fast] with proper reshaping
- Polarity guard: reject masks with <50% True pixels (ValueError per spec-db-core.md:29)
- Expose `self.trusted_mask`, `self.detector`, `self.beam`, `self.crystal` attributes

**Rationale**:
- Maintains backward compatibility (optional maskFile, defaults to fully-trusted)
- Follows spec-db-core.md:29-55 polarity and shape requirements
- Provides fixtures required by prepare_refinement_inputs (detector for pixel pitch validation)

**File pointer**: `dbex/data_load.py:99-152`

#### 2. `tests/dbex/test_mask_semantics.py:1-245` — DB-AT-021 test suite (NEW FILE)

**Tests authored** (3 total):
1. `test_DB_AT_021_trusted_mask_shape_and_polarity`: Validates dtype=bool, shape=[panel,slow,fast], >50% True coverage
2. `test_DB_AT_021_loss_mask_consistency`: Validates loss_mask == (background>=0) & trusted_mask, target zeroing
3. `test_DB_AT_021_detector_beam_crystal_fixtures`: Validates DataLoad exposes detector/beam/crystal attributes

**Fixtures**:
- `canonical_args`: SimpleNamespace with refGeom assets (mtzCol="F,SIGF" per test_reflection_ingestion.py:60)
- `data_load_instance`: DataLoad instance with skip guards for missing assets

**Metrics emission**:
- When `DBAT021_ARTIFACT_DIR` env set: writes `mask_metrics.json`, `mask_shape_polarity_metrics.json`
- Captures trusted_fraction, loss_mask_fraction, roi_count, per_roi_metrics

**File pointer**: `tests/dbex/test_mask_semantics.py:1-245`

---

## Test Results

### Targeted Selectors

**Command**:
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBAT021_ARTIFACT_DIR=plans/active/DB-AT-021/reports/2025-11-04T060900Z
export KMP_DUPLICATE_LIB_OK=TRUE
pytest -v tests/dbex/test_mask_semantics.py -k DB_AT_021
```

**Result**: ✅ 3 passed, 4 warnings

**Metrics** (from `mask_metrics.json`):
- `roi_count`: 92
- `trusted_fraction`: 0.9153 (91.5% of pixels trusted)
- `loss_mask_fraction`: 0.0021 (0.21% of full image, sparse ROI coverage as expected)
- `mean_roi_loss_coverage`: 0.9876 (98.8% of ROI pixels included in loss mask)
- Per-ROI coverage ranges: 95.8% - 100% (excellent mask quality)

**Collect-only**:
```bash
pytest --collect-only tests -k DB_AT_021
```

**Result**: ✅ 3/55 tests collected (52 deselected)

### Static Analysis

**Command**:
```bash
python -m py_compile dbex/data_load.py tests/dbex/test_mask_semantics.py
```

**Result**: ✅ No syntax errors

### Full Test Suite (Hard Gate)

**Command**:
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
pytest -v tests/
```

**Result**: ✅ 54 passed, 1 skipped, 9 warnings
**Collection**: ✅ No collection failures

**File pointer**: `plans/active/DB-AT-021/reports/2025-11-04T060900Z/pytest_full_suite.log`

---

## Artifacts

All artifacts under `plans/active/DB-AT-021/reports/2025-11-04T060900Z/`:

| Artifact | Description | Size |
|----------|-------------|------|
| `pytest_db_at_021.log` | Targeted test run log (3 tests) | 2.0K |
| `collect_db_at_021.log` | Pytest collection log (3/55 collected) | 1.7K |
| `mask_metrics.json` | Loss mask metrics + per-ROI coverage | 23K |
| `mask_shape_polarity_metrics.json` | Mask shape/dtype/coverage | 170B |
| `pytest_full_suite.log` | Full suite run (54 passed) | 36K |
| `summary.md` | This document | - |

---

## Documentation Updates

### 1. `docs/TESTING_GUIDE.md:67`

**Change**: Promoted DB_AT_021 from "Planned" to "Active"

**Entry**:
```markdown
| Mask semantics | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_021` | Trusted-mask polarity, shape alignment, and loss-mask consistency per `docs/spec-db-core.md:29-55`. Validates DataLoad mask hydration (True=include polarity guard, >50% coverage), loss mask computation `(background >= 0) & trusted_mask`, and target zeroing outside loss mask. | Active | Tests: `tests/dbex/test_mask_semantics.py` (3 tests collected, 3 passed). Canonical: trusted_fraction=91.5%, loss_mask_fraction=0.21%, mean_roi_loss_coverage=98.8%, 92 ROIs. Skip guard active when `747_mask.pkl` absent. Artifacts: `plans/active/DB-AT-021/reports/2025-11-04T060900Z/` (pytest_db_at_021.log, collect_db_at_021.log, mask_metrics.json, mask_shape_polarity_metrics.json). Findings: CONFORMANCE-001, TESTING-003, MASKING-001, CONFIG-001. |
```

### 2. `docs/development/TEST_SUITE_INDEX.md:23`

**Change**: Promoted DB_AT_021 from "planned" to "active" with full metadata

**Entry**:
```markdown
| Mask semantics (DB_AT_021) | `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_021` | active | `docs/spec-db-core.md:29-55`, `docs/spec-db-conformance.md:31-34` | Validates DataLoad trusted mask hydration (DIALS True=include polarity, >50% coverage guard), loss mask consistency `(background >= 0) & trusted_mask`, and target zeroing outside loss mask. Includes 3 tests: `test_DB_AT_021_trusted_mask_shape_and_polarity`, `test_DB_AT_021_loss_mask_consistency`, `test_DB_AT_021_detector_beam_crystal_fixtures`. Canonical refGeom: trusted_fraction=91.5%, loss_mask_fraction=0.21%, mean_roi_loss_coverage=98.8%, 92 ROIs, 1 panel (2527×2463). Skips gracefully if `747_mask.pkl` missing. Collection log: `plans/active/DB-AT-021/reports/2025-11-04T060900Z/collect_db_at_021.log` (3 tests collected). Test log: `plans/active/DB-AT-021/reports/2025-11-04T060900Z/pytest_db_at_021.log` (3 passed). Artifacts: `plans/active/DB-AT-021/reports/2025-11-04T060900Z/` (mask_metrics.json, mask_shape_polarity_metrics.json). Finding refs: CONFORMANCE-001, TESTING-003, MASKING-001, CONFIG-001. |
```

### 3. `docs/fix_plan.md` (DB-AT-021 section)

**Change**: Status → "done", added Attempts History entry 2025-11-04T060900Z

**Attempts History snippet**:
```
* 2025-11-04T060900Z (implementation) — Implemented DataLoad.__init__ mask loading (pickle.load → flex.bool → numpy [panel,slow,fast] with >50% polarity guard); authored tests/dbex/test_mask_semantics.py (3 tests: shape/polarity, loss-mask consistency, fixtures validation); all tests passed; Metrics: 3 tests collected/passed, trusted_fraction=91.5%, loss_mask_fraction=0.21%, mean_roi_loss_coverage=98.8%, full suite 54 passed/1 skipped; Artifacts: plans/active/DB-AT-021/reports/2025-11-04T060900Z/; Next Actions: DB-AT-022 background sentinel validation.
```

---

## Findings Applied (Mandatory)

Per `input.md:11`:
- **CONFORMANCE-001**: Selector naming/env flags enforced (KMP_DUPLICATE_LIB_OK=TRUE)
- **TESTING-003**: Collect-only log captured before promoting selector to Active
- **MASKING-001**: Low global loss_mask_fraction (0.21%) is expected sparse ROI behavior (98.8% coverage within ROIs)
- **CONFIG-001**: Maintained mask polarity (DIALS True=trusted) and detector alignment from config crosswalk

---

## Next Most-Important Item

**DB-AT-022**: Background sentinel validation
**Rationale**: Leverages newly-available `DataLoad.background_image` to validate `-1` sentinel handling per `docs/spec-db-conformance.md:38`

**Scope preview**:
- Verify background_image == -1 outside ROIs
- Validate ROI coverage matches reflection metadata
- Optional: recompute background with trusted_mask and compare

---

## Completion Checklist

- [x] Acceptance & module scope declared (AT-21, data models)
- [x] SPEC/ADR quotes present (spec-db-core.md:29-55, spec-db-conformance.md:32-33)
- [x] Search-first evidence captured (4 file:line pointers)
- [x] Static analysis passed (py_compile clean)
- [x] Full `pytest -v tests/` run executed once and passed (54 passed, 1 skipped, no collection failures)
- [x] New selector promoted to Active in TESTING_GUIDE.md and TEST_SUITE_INDEX.md
- [x] Artifacts persisted under `plans/active/DB-AT-021/reports/2025-11-04T060900Z/`
- [x] Attempts History updated in docs/fix_plan.md

---

**End of Loop Summary**
