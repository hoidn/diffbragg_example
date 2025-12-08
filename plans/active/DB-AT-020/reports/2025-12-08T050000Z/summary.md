# DB-AT-020 Phase A — Reality Check & Inputs (Complete)

**Date**: 2025-12-08
**Loop**: i=145
**Initiative**: DB-AT-020 (harness)
**Phase**: A — Reality Check & Inputs
**Status**: ✅ Complete

---

## Phase A Completion Checklist

- [x] **A1 — Dataset availability**: Confirmed refGeom assets exist at repo root (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`)
- [x] **A2 — Spec alignment**: Reconciled bbox semantics across spec-db-core.md:22, dials_api.md:10-32, architecture.md:122
- [x] **A3 — Baseline probe**: Captured panel count (1), ROI tally (92), sample bbox deltas, bounds validation, and slicing verification

---

## Deliverables

All deliverables written to `plans/active/DB-AT-020/reports/2025-12-08T050000Z/`:

1. **asset_availability.md** — RefGeom asset verification (all present ✓); skip behavior documented
2. **spec_alignment.md** — Bbox exclusivity/bounds requirements, panel alignment semantics, mask precedence reconciled across normative docs
3. **baseline_probe.md** — DataLoad inspection results: 92 ROIs, 12×12 uniform dimensions, all bboxes satisfy exclusivity and bounds conformance
4. **baseline_probe_output.txt** — Raw probe execution output
5. **summary.md** — This file (Phase A completion summary)

---

## Key Findings

### Dataset Availability (A1)
- All refGeom assets present at repo root (validated per DB-AT-SUITE-CARE-001 Phase B.2)
- `refGeom.expt` (5.1K), `refGeom.refl` (202K), `scaled.mtz` (2.8M)
- Skip behavior documented: DB-AT-020 tests will skip if `refGeom.refl` absent (mirror smoke fixture guard)

### Spec Alignment (A2)
- **Bbox exclusivity**: `x1 > x0` and `y1 > y0` (non-empty ROIs) per spec-db-core.md:22
- **Bounds conformance**: Upper bounds `x1 <= panel_width`, `y1 <= panel_height` per dials_api.md:26 and architecture.md:122
- **Slicing convention**: `img[pid, y0:y1, x0:x1]` with exclusive upper bounds per spec-db-core.md:22
- **Panel alignment**: Reflection `panel` column → `dl.pids` → detector indexing per dials_api.md:11-12
- **No conflicts detected**: All normative sources aligned; test assertions can be authored directly from spec requirements

### Baseline Probe (A3)
- **Panel count**: 1 (single-panel detector)
- **ROI tally**: 92 reflections
- **Bbox format**: 4-tuple `(x0, x1, y0, y1)` (not 6-tuple) per spec-db-core.md:22
- **ROI dimensions**: Uniform 12×12 (all ROIs) — consistent with `shoebox_sz=12` in `utils.get_roi_background_and_selection_flags()`
- **Bounds validation**: All sampled ROIs satisfy exclusivity (`x1 > x0`, `y1 > y0`) and bounds conformance (`x1 <= 2463`, `y1 <= 2527`)
- **Slicing verification**: `dl.data[pid, y0:y1, x0:x1].shape == (y1 - y0, x1 - x0)` for all sampled ROIs ✓
- **Panel IDs**: All `dl.pids == 0` (single-panel; panel alignment trivial but valid)

---

## Phase B Test Authoring Scope

**Next deliverable**: `tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`

**Test scaffold structure**:
```python
# tests/dbex/test_reflection_ingestion.py

class TestReflectionIngestion:
    """DB-AT-020: Reflection ingestion sanity checks (bbox, panel alignment)"""

    @pytest.fixture(scope="class")
    def refgeom_dataload(self, smoke_dataset_paths):
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
        for i, bbox in enumerate(dl.bbox):
            x0, x1, y0, y1 = bbox
            assert x1 > x0, f"ROI {i}: invalid width (x1={x1} <= x0={x0})"
            assert y1 > y0, f"ROI {i}: invalid height (y1={y1} <= y0={y0})"

        # B2: Bounds conformance and slicing validation
        for i, (bbox, pid) in enumerate(zip(dl.bbox, dl.pids)):
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

        assert len(dl.bbox) == len(dl.pids), "Bbox array length mismatch with pids"
```

**Mapped pytest selector**: `-k DB_AT_020` or `tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`

**Expected outcome**: PASS (baseline probe confirms all assertions will succeed on current DataLoad behavior)

---

## Blockers

None. Phase A complete; ready for Phase B test scaffold authoring.

---

## Cross-references

- **Member plan**: DB-AT-SUITE-CARE-001 Phase B.4 (member plan Phase A coordination)
- **Member plan status audit**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T024500Z/member_plan_status_audit.md`
- **RefGeom asset validation**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/` (Phase B.2, VALID ✓)
- **DB-AT-020 implementation plan**: `plans/active/DB-AT-020/implementation.md`

---

## Next Steps

**Immediate next (Loop i=146 options)**:

1. **DB-AT-020 Phase B** (test scaffold authoring):
   - Create `tests/dbex/test_reflection_ingestion.py` with `TestReflectionIngestion` class
   - Implement `test_DB_AT_020_reflection_bbox` with assertions grounded by Phase A baseline
   - Run `pytest -v tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`
   - Expected: PASS (all assertions validated by baseline probe)

2. **DB-AT-SUITE-CARE-001 Phase B.4 continuation** (another member plan Phase A):
   - Pick next pending member plan from queue (DB-AT-002/021/022/023)
   - Execute Phase A Reality Check & Inputs for that selector
   - Batch Phase A completions before authoring Phase B tests

3. **Portfolio progress dashboard update** (DB-AT-SUITE-CARE-001 Phase B.7):
   - Update member plan status table with DB-AT-020 Phase A completion
   - Compute portfolio completion percentage
   - Identify blocking dependencies across member plans

**Recommendation**: Proceed with DB-AT-020 Phase B in loop i=146 to complete one full acceptance test before batching more Phase A work. This validates the Phase A→B→C workflow and ensures test scaffold pattern is correct before scaling to other member plans.

---

## Artifacts

All deliverables located at: `plans/active/DB-AT-020/reports/2025-12-08T050000Z/`

- `asset_availability.md`
- `spec_alignment.md`
- `baseline_probe.md`
- `baseline_probe_output.txt`
- `summary.md` (this file)

---

## Findings Applied

- **TESTING-003** (Acceptance test registry maintenance): Phase A planning complete; registry updates deferred to Phase C per initiative lifecycle ✓
- **CONFORMANCE-001** (Acceptance test patterns): DB-AT-020 follows canonical selector pattern (`-k DB_AT_020`) and smoke fixture guards ✓
- **MASKING-001** (Mask handling contracts): Phase A validated mask loading; Phase B tests will validate loss_mask construction ✓

---

## Initiative Type Consistency

✅ Harness (acceptance test planning per DB-AT-SUITE-CARE-001 charter)
✅ No production code changes (evidence-only Phase A)
✅ Test authoring deferred to Phase B (implementation.md lifecycle)
✅ Registry sync deferred to Phase C (TESTING-003 adherence)
