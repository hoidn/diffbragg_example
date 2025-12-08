# Input for Ralph — Loop i=146

**Summary**: Execute DB-AT-020 Phase B (test scaffold authoring) to implement bbox exclusivity/bounds validation tests in `tests/dbex/test_reflection_ingestion.py`. This completes the acceptance test workflow validation and advances DB-AT-SUITE-CARE-001 Phase B.4 member plan coordination.

**Mode**: none

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: harness

**Focus**: `[DB-AT-020] — Reflection Ingestion Sanity (Phase B Implementation)`

**Branch**: integration

**Mapped tests**: `tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`

**Artifacts**: `plans/active/DB-AT-020/reports/2025-12-08T070000Z/`

**Findings Applied (Mandatory)**:
- **TESTING-003** (Acceptance test registry maintenance): Phase B creates test file; Phase C will sync TEST_SUITE_INDEX.md per initiative lifecycle.
  - Code: `docs/development/TEST_SUITE_INDEX.md`, `docs/TESTING_GUIDE.md`
  - Adherence: Test authoring now; registry updates deferred to Phase C per workflow separation.

- **CONFORMANCE-001** (Acceptance test patterns): DB-AT-020 follows canonical selector pattern (`-k DB_AT_020`) and refGeom skip guards per spec-db-conformance.md.
  - Code: `tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`
  - Adherence: Test scaffold structure from Phase A summary.md:60-122.

- **MASKING-001** (Mask handling contracts): Bbox slicing must respect trusted_mask semantics; loss_mask construction tested separately in DB-AT-021.
  - Code: `dbex/data_load.py` (bbox extraction), `tests/dbex/test_reflection_ingestion.py` (bbox validation)
  - Adherence: Phase B tests bbox/panel integrity; Phase C will cross-reference MASKING-001 if additional findings emerge.

**Pointers**:

### SPEC
- **docs/spec-db-core.md:22** — Bbox exclusivity semantics (x1 > x0, y1 > y0, upper bounds within panel dimensions)
- **docs/dials_api.md:10-32** — Reflection table schema (bbox, panel, shoebox columns)
- **docs/spec-db-conformance.md** — DB-AT-020 acceptance criteria (bbox validation, panel alignment)

### ARCH
- **docs/architecture.md:122** — Runtime bbox guards and panel slicing expectations
- **docs/architecture/module_map.md:45-62** — DataLoad module responsibilities (ARCH-CONTRACT-DATA-LOAD-001 owner API)

### Testing Docs
- **docs/TESTING_GUIDE.md** — Canonical environment flags and selector patterns
- **docs/development/TEST_SUITE_INDEX.md** — DB-AT selector status table (to be updated Phase C)

### Phase A Deliverables
- **plans/active/DB-AT-020/reports/2025-12-08T050000Z/summary.md** — Phase A completion summary with test scaffold structure (lines 60-122)
- **plans/active/DB-AT-020/reports/2025-12-08T050000Z/baseline_probe.md** — Baseline metrics (92 ROIs, 12×12 uniform dimensions, bounds conformance validated)
- **plans/active/DB-AT-020/reports/2025-12-08T050000Z/spec_alignment.md** — Bbox requirements reconciliation
- **plans/active/DB-AT-020/implementation.md** — Phase B tasks (B1-B3)

---

## ARCH Contracts (mandatory)

- **ARCH-CONTRACT-DATA-LOAD-001** (DataLoad ingestion boundary):
  - **Owner API**: `dbex.data_load.DataLoad.__init__` (mtz_path, expt_path, refl_path, mask_path)
  - **Boundary**: Reflection table ingestion → bbox extraction → panel alignment → DataLoad.{bboxes, pids, data, background_image}
  - **Failure classification**: Implementation bug (Phase B tests validate current behavior matches spec requirements)
  - **Test enforcement**: `test_DB_AT_020_reflection_bbox` validates bbox exclusivity + bounds conformance + panel ordering per spec-db-core.md:22, dials_api.md:10-32, architecture.md:122
  - **Doc pointer**: docs/architecture/module_map.md:45-62

---

## Do Now (hard validity contract)

**Objective**: Execute DB-AT-020 Phase B to author acceptance test scaffold validating bbox exclusivity, bounds conformance, and panel alignment per spec-db-core.md:22 and dials_api.md:10-32.

**Implement**: `tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`

**Deliverables** (B1-B3):

### B1 — Test scaffold
Create `tests/dbex/test_reflection_ingestion.py` with:
- `TestReflectionIngestion` class
- `refgeom_dataload` fixture (instantiates DataLoad with refGeom assets; skips if `refGeom.refl` missing per Phase A asset_availability.md)
- `test_DB_AT_020_reflection_bbox` method

**Test scaffold structure** (from Phase A summary.md:60-122):
```python
# tests/dbex/test_reflection_ingestion.py

import pytest
from pathlib import Path
from argparse import Namespace
from dbex.data_load import DataLoad

class TestReflectionIngestion:
    """DB-AT-020: Reflection ingestion sanity checks (bbox, panel alignment)"""

    @pytest.fixture(scope="class")
    def refgeom_dataload(self):
        """Instantiate DataLoad with refGeom assets; skip if refGeom.refl missing."""
        repo_root = Path(__file__).parent.parent.parent
        refl_path = repo_root / "refGeom.refl"
        if not refl_path.exists():
            pytest.skip("refGeom.refl not found; skipping DB-AT-020")

        args = Namespace(
            mtzFile=str(repo_root / "scaled.mtz"),
            mtzCol="I(+),SIGI(+),I(-),SIGI(-)",
            exptName=str(repo_root / "refGeom.expt"),
            exptIdx=0,
            reflName=str(refl_path),
            maskFile=str(repo_root / "747_mask.pkl")
        )
        return DataLoad(args)

    def test_DB_AT_020_reflection_bbox(self, refgeom_dataload):
        """
        DB-AT-020: Validate bbox exclusivity, bounds conformance, and slicing shape.

        Acceptance criteria (spec-db-core.md:22, dials_api.md:9, architecture.md:122):
        - Bbox exclusivity: x1 > x0, y1 > y0
        - Bounds conformance: x1 <= panel_width, y1 <= panel_height
        - Slicing shape: data[pid, y0:y1, x0:x1].shape == (y1 - y0, x1 - x0)
        - Panel ID range: 0 <= pid < len(detector)
        """
        dl = refgeom_dataload

        # B2: Bbox exclusivity checks
        for i, bbox in enumerate(dl.bboxes):
            x0, x1, y0, y1 = bbox
            assert x1 > x0, f"ROI {i}: invalid width (x1={x1} <= x0={x0})"
            assert y1 > y0, f"ROI {i}: invalid height (y1={y1} <= y0={y0})"

        # B2: Bounds conformance and slicing validation
        for i, (bbox, pid) in enumerate(zip(dl.bboxes, dl.pids)):
            x0, x1, y0, y1 = bbox
            panel = dl.detector[pid]
            fast_dim, slow_dim = panel.get_image_size()

            assert x0 >= 0 and x1 <= fast_dim, f"ROI {i}: x-bounds outside panel"
            assert y0 >= 0 and y1 <= slow_dim, f"ROI {i}: y-bounds outside panel"

            data_slice = dl.data[pid, y0:y1, x0:x1]
            bg_slice = dl.background_image[pid, y0:y1, x0:x1]
            assert data_slice.shape == (y1 - y0, x1 - x0), f"ROI {i}: data slice mismatch"
            assert bg_slice.shape == (y1 - y0, x1 - x0), f"ROI {i}: bg slice mismatch"

        # B3: Panel ordering guards
        for pid in dl.pids:
            assert 0 <= pid < len(dl.detector), f"Panel ID {pid} outside detector range"

        assert len(dl.bboxes) == len(dl.pids), "Bbox array length mismatch with pids"
```

### B2 — Bbox exclusivity/bounds assertions
Already integrated in test scaffold above (lines 42-62):
- Exclusivity: `x1 > x0` and `y1 > y0` per spec-db-core.md:22
- Bounds conformance: `x0 >= 0`, `x1 <= panel_width`, `y0 >= 0`, `y1 <= panel_height` per dials_api.md:26 + architecture.md:122
- Slicing shape validation: `data[pid, y0:y1, x0:x1].shape == (y1 - y0, x1 - x0)` per spec-db-core.md:22

### B3 — Panel ordering guards
Already integrated in test scaffold above (lines 64-68):
- Panel ID range: `0 <= pid < len(detector)` per dials_api.md:11-12
- Array length sync: `len(dl.bboxes) == len(dl.pids)` per architecture.md:122

**Validation**:
1. Run test with canonical command (from TESTING_GUIDE.md):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
     KMP_DUPLICATE_LIB_OK=TRUE \
     pytest -vv tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox
   ```
2. **Expected outcome**: PASS (Phase A baseline probe confirmed all assertions hold on current DataLoad behavior)
3. Archive pytest output under `plans/active/DB-AT-020/reports/2025-12-08T070000Z/pytest_db_at_020.log`
4. Create `summary.md` with Phase B completion checklist, pytest outcome, next steps (Phase C registry sync)

**Mapped pytest selectors**: `tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox` OR `-k DB_AT_020`

**Artifacts path**: `plans/active/DB-AT-020/reports/2025-12-08T070000Z/`

**Initiative type consistency**: ✅ harness (acceptance test authoring per DB-AT-SUITE-CARE-001 charter)

---

## Forbidden This Loop

- **No TEST_SUITE_INDEX.md updates yet**: Phase C task (registry sync deferred per initiative lifecycle)
- **Do not update docs/TESTING_GUIDE.md**: Phase C task (selector documentation)
- **Do not update docs/fix_plan.md Attempts History yet**: Galph will handle ledger updates after reviewing Phase B results
- **No production code changes**: Harness-only loop (DB-AT-020 tests DataLoad behavior, not modifying it)

---

## How-To Map

### B1-B3 — Test Scaffold Authoring

1. **Create test file**:
   ```bash
   mkdir -p tests/dbex
   # Create tests/dbex/test_reflection_ingestion.py with scaffold from Do Now section
   ```

2. **Run test locally to validate**:
   ```bash
   mkdir -p plans/active/DB-AT-020/reports/2025-12-08T070000Z

   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
     KMP_DUPLICATE_LIB_OK=TRUE \
     pytest -vv tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox \
     | tee plans/active/DB-AT-020/reports/2025-12-08T070000Z/pytest_db_at_020.log
   ```

3. **Verify test passes** (expect PASS based on Phase A baseline probe showing 92 ROIs all satisfy constraints)

4. **Create summary.md**:
   ```bash
   cat > plans/active/DB-AT-020/reports/2025-12-08T070000Z/summary.md << 'EOF'
   # DB-AT-020 Phase B — Harness Implementation (Complete)

   **Date**: 2025-12-08
   **Loop**: i=146
   **Initiative**: DB-AT-020 (harness)
   **Phase**: B — Harness Implementation
   **Status**: ✅ Complete (if PASS) OR ⚠️ Blocked (if FAIL)

   ## Phase B Completion Checklist

   - [x] **B1 — Test scaffold**: Created `tests/dbex/test_reflection_ingestion.py` with `TestReflectionIngestion` class + `refgeom_dataload` fixture
   - [x] **B2 — Bbox exclusivity checks**: Assertions validate x1 > x0, y1 > y0, bounds conformance, slicing shape
   - [x] **B3 — Panel ordering guards**: Assertions validate panel ID range, bbox/pids array length sync

   ## Deliverables

   1. **test_reflection_ingestion.py** — Test file with DB-AT-020 acceptance test
   2. **pytest_db_at_020.log** — Pytest execution output (PASS/FAIL status)
   3. **summary.md** — This file (Phase B completion summary)

   ## Pytest Outcome

   **Command**:
   ```
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox
   ```

   **Result**: [PASS/FAIL — document actual outcome]

   **Metrics** (from baseline probe Phase A):
   - Panel count: 1
   - ROI tally: 92
   - ROI dimensions: 12×12 (uniform)
   - Bounds conformance: 100% (all sampled ROIs in Phase A)

   **Actual metrics** (from pytest run):
   - [Document actual assertion counts, any failures]

   ## Phase C Next Steps

   **Immediate next (Loop i=147)**:
   - DB-AT-020 Phase C (registry sync + docs update)
   - Update `docs/development/TEST_SUITE_INDEX.md` with DB-AT-020 row
   - Update `docs/TESTING_GUIDE.md` §2 with selector pattern
   - Run `pytest --collect-only tests -k DB_AT_020` and archive logs

   ## Blockers

   None (if PASS) OR [Document failure signature if FAIL]

   ## Cross-references

   - **Member plan**: DB-AT-SUITE-CARE-001 Phase B.4 (member plan Phase A/B coordination)
   - **Phase A deliverables**: `plans/active/DB-AT-020/reports/2025-12-08T050000Z/` (baseline probe, spec alignment)
   - **DB-AT-020 implementation plan**: `plans/active/DB-AT-020/implementation.md`
   EOF
   ```

5. **Update implementation.md checklist**:
   ```bash
   # Mark Phase B tasks complete in plans/active/DB-AT-020/implementation.md
   # B1-B3 checkboxes → [x]
   ```

---

## Pitfalls To Avoid

1. **Type discipline**: This is harness initiative; do not introduce production code changes
2. **Bbox attribute name**: Phase A baseline_probe.md shows `dl.bboxes` (plural), not `dl.bbox` (singular) — use correct attribute per DataLoad API
3. **Evidence→Action contract**: Phase B ends with concrete Phase C scope (registry sync files + commands)
4. **Findings paydown**: Applied TESTING-003, CONFORMANCE-001, MASKING-001; no new findings expected (baseline probe validated assertions)
5. **ARCH/Impl consistency**: Test validates ARCH-CONTRACT-DATA-LOAD-001 boundary (bbox extraction → panel alignment)
6. **No stacking on cliff**: No cliffs detected; proceed with test authoring
7. **Environment Freeze**: Use existing pytest/torch/dbex imports; no package installs
8. **Implementation floor**: Phase B is implementation; next loop (i=147) can be Phase C or switch to another member plan Phase A
9. **Dwell discipline**: This is 2nd loop for DB-AT-020 (Phase A → Phase B); within budget
10. **Test skip guard**: refgeom_dataload fixture must skip if `refGeom.refl` missing (documented in Phase A asset_availability.md)

---

## If Blocked

- **If test fails unexpectedly**: Document failure signature, compare with Phase A baseline probe metrics, mark DB-AT-020 blocked pending bugfix
- **If refGeom assets missing**: Escalate to DB-AT-SUITE-CARE-001 Phase B.2 (but Phase B.2 already validated ✓)
- **If DataLoad API signature changed**: Update test fixture and document in summary.md
- **If bbox attribute name wrong**: Verify correct attribute via `python -c "from dbex.data_load import DataLoad; help(DataLoad)"` and fix

---

## Doc Sync Plan (Conditional)
**Deferred to Phase C** — No registry sync yet; Phase C will update TEST_SUITE_INDEX.md and TESTING_GUIDE.md per initiative lifecycle.

---

**Next Loop (i=147) Options**:
1. DB-AT-020 Phase C (if Phase B PASS) — registry sync + docs update
2. DB-AT-SUITE-CARE-001 Phase B.4 continuation (another member plan Phase A) if batching strategy preferred
3. Blocker investigation (if Phase B FAIL) — compare with baseline probe, diagnose root cause

---

**Issued by**: Galph (supervisor)
**Loop**: i=145 → i=146
**Next milestone**: DB-AT-020 Phase C (registry sync) OR DB-AT-SUITE-CARE-001 Phase B.4 continuation
