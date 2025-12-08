# Input for Ralph — Loop i=145

**Summary**: Execute DB-AT-020 Phase A (Reality Check & Inputs) to validate refGeom assets, reconcile bbox spec alignment, and capture baseline ROI probe metrics. This unblocks DB-AT-020 Phase B test authoring and advances DB-AT-SUITE-CARE-001 Phase B.4 member plan coordination.

**Mode**: none

**ActionType**: planning

**DecisionStatus**: exploring

**InitiativeType**: harness

**Focus**: `[DB-AT-020] — Reflection Ingestion Sanity (Phase A Reality Check)`

**Branch**: integration

**Mapped tests**: none — evidence-only

**Artifacts**: `plans/active/DB-AT-020/reports/2025-12-08T050000Z/`

**Findings Applied (Mandatory)**:
- **TESTING-003** (Acceptance test registry maintenance): Phase A planning sets up pytest collect-only execution for Phase C; registry updates deferred to Phase C per initiative lifecycle.
  - Code: `docs/development/TEST_SUITE_INDEX.md`, `docs/TESTING_GUIDE.md`
  - Adherence: Phase A scopes test expectations; Phase C will sync registry post-implementation.

- **CONFORMANCE-001** (Acceptance test patterns): DB-AT-020 follows canonical selector pattern (`-k DB_AT_020`) and smoke fixture guards per spec-db-conformance.md.
  - Code: `tests/dbex/test_reflection_ingestion.py` (to be authored Phase B)
  - Adherence: Phase A spec alignment task (A2) validates bbox/mask semantics match spec-db-core.md:22, dials_api.md:10-32.

- **MASKING-001** (Mask handling contracts): Bbox/ROI logic must use canonical mask precedence (trusted_mask ∩ ROI ∩ background >= 0).
  - Code: `dbex/data_load.py`, `dbex/refinement/inputs.py`
  - Adherence: Phase A3 baseline probe will inspect mask application; Phase B tests will validate loss_mask construction.

**Pointers**:

### SPEC
- **docs/spec-db-core.md:22** — Bbox exclusivity semantics (x1 > x0, y1 > y0, upper bounds within panel dimensions)
- **docs/dials_api.md:10-32** — Reflection table schema (bbox, panel, shoebox columns)
- **docs/spec-db-conformance.md** — DB-AT-020 acceptance criteria (bbox validation, panel alignment)

### ARCH
- **docs/architecture.md:122** — Runtime bbox guards and panel slicing expectations
- **docs/architecture/module_map.md** — DataLoad module responsibilities
- **docs/architecture/tests_mapping.md** — Selector coverage expectations

### Testing Docs
- **docs/TESTING_GUIDE.md** — Canonical environment flags and selector patterns
- **docs/development/TEST_SUITE_INDEX.md** — DB-AT selector status table (to be updated Phase C)

### Member Plan Cross-Refs
- **DB-AT-SUITE-CARE-001 implementation.md:39** — Phase B.4 task definition (member plan Phase A coordination)
- **DB-AT-SUITE-CARE-001 reports/2025-12-07T024500Z/member_plan_status_audit.md** — DB-AT-020 classified as pending (0/3 phases)
- **DB-AT-SUITE-CARE-001 reports/2025-12-08T020000Z/** — Phase B.2 refGeom asset validation (VALID ✓)
- **DB-AT-020 implementation.md** — Phase A tasks A1-A3

---

## ARCH Contracts (mandatory)

- **ARCH-CONTRACT-DATA-LOAD-001** (DataLoad ingestion boundary):
  - **Owner API**: `dbex.data_load.DataLoad.__init__` (mtz_path, expt_path, refl_path, mask_path)
  - **Boundary**: Reflection table ingestion → bbox extraction → panel alignment → DataLoad.{bboxes, pids, data, background_image}
  - **Failure classification**: Implementation bug (Phase A validates current behavior; Phase B will test contracts)
  - **Doc pointer**: docs/architecture/module_map.md:45-62

---

## Do Now (hard validity contract)

**Objective**: Execute DB-AT-020 Phase A Reality Check & Inputs to validate refGeom asset availability, reconcile bbox spec alignment, and capture baseline ROI probe metrics.

**Implement**: Planning task execution in `plans/active/DB-AT-020/` (no production code changes)

**Deliverables** (A1-A3):

### A1 — Dataset availability
Confirm refGeom assets existence (refGeom.expt, refGeom.refl, scaled.mtz at repo root per DB-AT-SUITE-CARE-001 Phase B.2 validation). Document skip behavior (test will skip if refGeom.refl absent). Output: `asset_availability.md`.

### A2 — Spec alignment
Reconcile bbox semantics with normative docs:
- spec-db-core.md:22 (exclusivity: x1 > x0, y1 > y0, upper bounds < panel dimensions)
- dials_api.md:10-32 (reflection table schema: bbox columns, panel mapping)
- architecture.md:122 (runtime guards, panel slicing expectations)

Document bbox requirements, panel alignment semantics, and slicing shape validation expectations. Output: `spec_alignment.md`.

### A3 — Baseline probe
Execute lightweight DataLoad inspection to capture:
- Panel count
- ROI tally (len(bboxes))
- Sample bbox deltas (5-10 examples: x1-x0, y1-y0, panel id validation)
- Panel slicing shape verification (data[pid, y0:y1, x0:x1])

**Method**: Use Python REPL with dbex.data_load.DataLoad OR thin wrapper script (≤50 LOC, no DataLoad re-implementation per PROBE-FREEZE-001). Output: `baseline_probe.md`.

### Final summary
Create `summary.md` with:
- Phase A completion checklist (A1-A3 checked)
- Next step (Phase B test scaffold authoring scope: `tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`)
- Blockers (none expected)
- Cross-refs to DB-AT-SUITE-CARE-001 Phase B.4 progress

**Validation**:
- All 4 deliverable files exist under `plans/active/DB-AT-020/reports/2025-12-08T050000Z/`
- summary.md confirms Phase A completion and Phase B scope
- Planning notes clarify test authoring expectations

**Mapped pytest selectors**: none — evidence-only loop

**Artifacts path**: `plans/active/DB-AT-020/reports/2025-12-08T050000Z/`

**Initiative type consistency**: ✅ harness (acceptance test planning per DB-AT-SUITE-CARE-001 charter)

---

## Forbidden This Loop

- **No production code changes**: Evidence collection only
- **Do not author test files yet**: Phase B task (`tests/dbex/test_reflection_ingestion.py`)
- **Do not update TEST_SUITE_INDEX.md**: Phase C task (registry sync)
- **Do not extend plan-local diagnostic scripts**: Use thin wrapper (≤50 LOC) if needed for A3 probe, or execute manually via REPL

---

## How-To Map

### A1 — Dataset Availability
```bash
mkdir -p plans/active/DB-AT-020/reports/2025-12-08T050000Z

# Verify refGeom assets from DB-AT-SUITE-CARE-001 Phase B.2 validation
ls -lh refGeom.expt refGeom.refl scaled.mtz 2>&1 | tee plans/active/DB-AT-020/reports/2025-12-08T050000Z/asset_availability.md

# Append skip behavior note
cat >> plans/active/DB-AT-020/reports/2025-12-08T050000Z/asset_availability.md << 'EOF'

## Skip Behavior

DB-AT-020 tests will skip if refGeom.refl is absent (mirror smoke fixture guard per implementation.md A1).
EOF
```

### A2 — Spec Alignment
Create `plans/active/DB-AT-020/reports/2025-12-08T050000Z/spec_alignment.md` with:
- Bbox exclusivity requirements (x1 > x0, y1 > y0, upper bounds < panel dimensions)
- Panel alignment semantics (pids → detector panel indexing)
- Slicing expectations (data[pid, y0:y1, x0:x1] shape validation)
- Cross-references to spec-db-core.md:22, dials_api.md:10-32, architecture.md:122

### A3 — Baseline Probe

**Option 1**: Python REPL (recommended for simplicity)
```python
from dbex.data_load import DataLoad
import numpy as np

# Instantiate DataLoad with refGeom assets
DL = DataLoad(
    mtz_path="scaled.mtz",
    expt_path="refGeom.expt",
    refl_path="refGeom.refl",
    mask_path="747_mask.pkl"
)

# Capture metrics
panel_count = len(DL.detector)
roi_tally = len(DL.bboxes)
sample_bboxes = [(DL.bboxes[i], DL.pids[i]) for i in range(min(10, roi_tally))]

# Validate bbox deltas and slicing
for bbox, pid in sample_bboxes[:5]:
    x0, x1, y0, y1, _ = bbox
    width = x1 - x0
    height = y1 - y0
    slice_shape = DL.data[pid, y0:y1, x0:x1].shape
    print(f"ROI pid={pid}: width={width}, height={height}, slice_shape={slice_shape}")

# Write baseline_probe.md with results
```

**Option 2**: Thin wrapper script (≤50 LOC) if REPL output needs automation
```python
# plans/active/DB-AT-020/bin/probe_reflection_ingestion.py (if needed)
# Calls dbex.data_load.DataLoad, measures outputs, writes baseline_probe.md
# Must stay thin wrapper per PROBE-FREEZE-001
```

**Output**: `plans/active/DB-AT-020/reports/2025-12-08T050000Z/baseline_probe.md`

### Final Summary
Create `plans/active/DB-AT-020/reports/2025-12-08T050000Z/summary.md` with:
- Phase A completion checklist (A1-A3 checked)
- Next step: Phase B test scaffold authoring (`tests/dbex/test_reflection_ingestion.py::TestReflectionIngestion::test_DB_AT_020_reflection_bbox`)
- Blockers: none
- Cross-refs: DB-AT-SUITE-CARE-001 Phase B.4 progress, member_plan_status_audit.md

---

## Pitfalls To Avoid

1. **Type discipline**: This is harness initiative; do not retype to spec_change/bugfix
2. **No stacking on cliff**: No cliffs detected; proceed with evidence collection
3. **Evidence→Action contract**: Phase A ends with concrete Phase B test authoring scope (file:function for test scaffold)
4. **Findings paydown**: Applied TESTING-003, CONFORMANCE-001, MASKING-001; no implementation yet
5. **ARCH/Impl consistency**: Phase A validates current behavior; Phase B will test ARCH-CONTRACT-DATA-LOAD-001
6. **Probe saturation**: A3 baseline probe is first for this selector+signature; stay within thin wrapper policy
7. **Environment Freeze**: No package installs; use existing dbex imports only
8. **Scriptization policy**: If A3 needs script, keep ≤50 LOC thin wrapper (T1 tier)
9. **Shadow-pipeline guard**: Do not re-implement DataLoad; call existing API and measure outputs
10. **Implementation floor**: Phase A is planning; next loop (i=146) can be Phase B implementation or another member plan Phase A

---

## If Blocked

- **If refGeom assets missing**: Escalate to DB-AT-SUITE-CARE-001 (but Phase B.2 already validated ✓)
- **If spec alignment reveals conflicts**: Open spec_change initiative and cross-link
- **If baseline probe fails**: Document error and mark DB-AT-020 blocked pending bugfix
- **If thin wrapper exceeds LOC cap**: Execute probe manually via REPL and document inline in baseline_probe.md

---

## Doc Sync Plan (Conditional)
**Not applicable** — No tests authored yet; docs sync deferred to Phase C.

---

**Next Loop (i=146) Options**:
1. DB-AT-020 Phase B (if Phase A artifacts satisfactory)
2. Another member plan Phase A from pending queue (DB-AT-002/021/022/023) per DB-AT-SUITE-CARE-001 Phase B.4 batching strategy
3. Portfolio progress dashboard update (DB-AT-SUITE-CARE-001 Phase B.7)

---

**Issued by**: Galph (supervisor)
**Loop**: i=144 → i=145
**Next milestone**: DB-AT-020 Phase B (test scaffold authoring) OR DB-AT-SUITE-CARE-001 Phase B.4 continuation
